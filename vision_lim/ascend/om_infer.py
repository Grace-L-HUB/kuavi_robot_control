"""昇腾 CANN ACL 加载 .om 模型并推理。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_acl = None
_acl_initialized = False
_device_runtime: Dict[int, Dict] = {}


def _bootstrap_cann_pythonpath() -> None:
    """kuavi venv 下 import acl 失败时，自动追加 CANN site-packages。"""
    import os
    import sys

    candidates = []
    home = os.environ.get("ASCEND_TOOLKIT_HOME")
    if home:
        candidates.append(os.path.join(home, "python", "site-packages"))
        candidates.append(
            os.path.join(home, "opp", "built-in", "op_impl", "ai_core", "tbe")
        )
    candidates.append("/usr/local/Ascend/ascend-toolkit/latest/python/site-packages")
    candidates.append(
        "/usr/local/Ascend/ascend-toolkit/latest/opp/built-in/op_impl/ai_core/tbe"
    )

    for p in candidates:
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)


def is_ascend_available() -> bool:
    """当前 Python 环境是否可 import acl（需 CANN 在 PYTHONPATH 中）。"""
    try:
        import acl  # noqa: F401
        return True
    except ImportError:
        pass
    _bootstrap_cann_pythonpath()
    try:
        import acl  # noqa: F401
        return True
    except ImportError:
        return False


def _check_ret(msg: str, ret: int) -> None:
    if ret != 0:
        raise RuntimeError(f"{msg} failed, ret={ret}")


def _acl_ret(result: Any, msg: str) -> int:
    if isinstance(result, tuple):
        if len(result) == 2 and isinstance(result[1], int):
            _check_ret(msg, int(result[1]))
            return int(result[1])
        if len(result) == 1 and isinstance(result[0], int):
            _check_ret(msg, int(result[0]))
            return int(result[0])
    if isinstance(result, int):
        _check_ret(msg, result)
        return result
    raise TypeError(f"{msg}: 无法解析 ACL 返回值 {type(result)!r}")


def _acl_value_ret(result: Any, msg: str) -> Tuple[Any, int]:
    if isinstance(result, tuple):
        if len(result) >= 2:
            return result[0], int(result[1])
        if len(result) == 1:
            return result[0], 0
    if isinstance(result, int):
        return result, 0
    raise TypeError(f"{msg}: 无法解析 ACL 返回值 {type(result)!r}")


def _parse_dims(result: Any) -> Tuple[int, ...]:
    """解析 get_output_dims / get_cur_output_dims 的多种返回格式。"""
    if isinstance(result, dict):
        dims = result.get("dims") or result.get("dim") or []
        return tuple(int(x) for x in dims)
    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, dict) and "dims" in item:
                return tuple(int(x) for x in item["dims"])
            if isinstance(item, (list, tuple)) and item and isinstance(item[0], int):
                return tuple(int(x) for x in item)
    if isinstance(result, (list, tuple)) and result and isinstance(result[0], int):
        return tuple(int(x) for x in result)
    return ()


def _acl_obj(result: Any, msg: str) -> Any:
    """create_desc / create_dataset 等返回单个对象的 API。"""
    if isinstance(result, tuple) and result:
        if len(result) >= 2 and isinstance(result[1], int):
            _check_ret(msg, int(result[1]))
        return result[0]
    return result


def _ensure_acl() -> None:
    global _acl, _acl_initialized
    import acl as acl_mod

    _acl = acl_mod
    if not _acl_initialized:
        _acl_ret(_acl.init(), "acl.init")
        _acl_initialized = True


def _get_device_runtime(device_id: int) -> Dict:
    _ensure_acl()
    if device_id in _device_runtime:
        rt = _device_runtime[device_id]
        _acl_ret(_acl.rt.set_context(rt["context"]), "acl.rt.set_context")
        return rt

    _acl_ret(_acl.rt.set_device(device_id), "acl.rt.set_device")
    context, ret = _acl_value_ret(_acl.rt.create_context(device_id), "acl.rt.create_context")
    _check_ret("acl.rt.create_context", ret)
    _acl_ret(_acl.rt.set_context(context), "acl.rt.set_context")
    stream, ret = _acl_value_ret(_acl.rt.create_stream(), "acl.rt.create_stream")
    _check_ret("acl.rt.create_stream", ret)

    rt = {"context": context, "stream": stream, "models": 0}
    _device_runtime[device_id] = rt
    logger.info("ACL runtime ready on device %s", device_id)
    return rt


def _memcpy_kind(name: str, default: int) -> int:
    if _acl is None:
        return default
    return int(getattr(_acl, name, default))


class OmModel:
    def __init__(self, model_path: str, device_id: int = 0):
        self.model_path = str(Path(model_path).resolve())
        if not Path(self.model_path).is_file():
            raise FileNotFoundError(f"OM 模型不存在: {self.model_path}")
        self.device_id = device_id
        self._context = None
        self._stream = None
        self.model_id: Optional[int] = None
        self.model_desc = None
        self._input_buffers: List[Tuple[int, int]] = []
        self._output_buffers: List[Tuple[int, int]] = []
        self._output_shapes: List[Tuple[int, ...]] = []
        self._output_dtypes: List[np.dtype] = []
        self._input_dataset = None
        self._output_dataset = None
        self._loaded = False

    def _activate_context(self) -> None:
        rt = _get_device_runtime(self.device_id)
        self._context = rt["context"]
        self._stream = rt["stream"]
        _acl_ret(_acl.rt.set_context(self._context), "acl.rt.set_context")

    def load(self) -> None:
        if self._loaded:
            self._activate_context()
            return

        self._activate_context()

        model_id, ret = _acl_value_ret(
            _acl.mdl.load_from_file(self.model_path), "acl.mdl.load_from_file"
        )
        _check_ret("acl.mdl.load_from_file", ret)
        self.model_id = int(model_id)

        self.model_desc = _acl_obj(_acl.mdl.create_desc(), "acl.mdl.create_desc")
        _acl_ret(
            _acl.mdl.get_desc(self.model_desc, self.model_id),
            "acl.mdl.get_desc",
        )

        self._cache_output_meta()
        self._create_io()
        _device_runtime[self.device_id]["models"] += 1
        self._loaded = True
        logger.info("OM model loaded: %s (device=%s)", self.model_path, self.device_id)

    def _cache_output_meta(self) -> None:
        assert _acl is not None and self.model_desc is not None
        self._output_shapes = []
        self._output_dtypes = []
        n = _acl.mdl.get_num_outputs(self.model_desc)
        for i in range(n):
            shape: Tuple[int, ...] = ()
            if hasattr(_acl.mdl, "get_output_dims"):
                try:
                    shape = _parse_dims(_acl.mdl.get_output_dims(self.model_desc, i))
                except Exception as e:
                    logger.warning("get_output_dims(%s) failed: %s", i, e)
            dtype_val = 0
            try:
                dt = _acl.mdl.get_output_data_type(self.model_desc, i)
                if isinstance(dt, int):
                    dtype_val = dt
                elif isinstance(dt, tuple) and dt:
                    dtype_val = int(dt[0])
            except Exception as e:
                logger.warning("get_output_data_type(%s) failed: %s", i, e)
            self._output_shapes.append(shape)
            self._output_dtypes.append(_acl_dtype_to_numpy(dtype_val))

    def _create_io(self) -> None:
        assert _acl is not None and self.model_desc is not None
        input_count = _acl.mdl.get_num_inputs(self.model_desc)
        output_count = _acl.mdl.get_num_outputs(self.model_desc)

        self._input_dataset = _acl_obj(_acl.mdl.create_dataset(), "create input dataset")
        self._output_dataset = _acl_obj(_acl.mdl.create_dataset(), "create output dataset")
        self._input_buffers = []
        self._output_buffers = []

        for i in range(input_count):
            size = int(_acl.mdl.get_input_size_by_index(self.model_desc, i))
            ptr, ret = _acl_value_ret(_acl.rt.malloc(size, 0), f"malloc input {i}")
            _check_ret(f"malloc input {i}", ret)
            data_buffer = _acl.create_data_buffer(ptr, size)
            _acl_ret(
                _acl.mdl.add_dataset_buffer(self._input_dataset, data_buffer),
                f"add input buffer {i}",
            )
            self._input_buffers.append((int(ptr), size))

        for i in range(output_count):
            size = int(_acl.mdl.get_output_size_by_index(self.model_desc, i))
            ptr, ret = _acl_value_ret(_acl.rt.malloc(size, 0), f"malloc output {i}")
            _check_ret(f"malloc output {i}", ret)
            data_buffer = _acl.create_data_buffer(ptr, size)
            _acl_ret(
                _acl.mdl.add_dataset_buffer(self._output_dataset, data_buffer),
                f"add output buffer {i}",
            )
            self._output_buffers.append((int(ptr), size))

    def infer(self, inputs: Sequence[np.ndarray]) -> List[np.ndarray]:
        if not self._loaded:
            self.load()
        assert _acl is not None and self.model_desc is not None

        self._activate_context()

        if len(inputs) != len(self._input_buffers):
            raise ValueError(
                f"输入数量不匹配: got {len(inputs)}, model expects {len(self._input_buffers)}"
            )

        h2d = _memcpy_kind("ACL_MEMCPY_HOST_TO_DEVICE", 1)
        d2h = _memcpy_kind("ACL_MEMCPY_DEVICE_TO_HOST", 2)

        for i, arr in enumerate(inputs):
            if not isinstance(arr, np.ndarray):
                raise TypeError(f"输入 {i} 必须是 numpy.ndarray，实际为 {type(arr)!r}")
            arr = np.ascontiguousarray(arr, dtype=np.float32)
            ptr, size = self._input_buffers[i]
            if arr.nbytes > size:
                raise ValueError(
                    f"输入 {i} 字节 {arr.nbytes} 超过模型 buffer {size}；"
                    f"shape={arr.shape} dtype={arr.dtype}"
                )
            _acl_ret(
                _acl.rt.memcpy(ptr, size, arr.ctypes.data, arr.nbytes, h2d),
                f"memcpy H2D input {i}",
            )

        _acl_ret(
            _acl.mdl.execute(self.model_id, self._input_dataset, self._output_dataset),
            "acl.mdl.execute",
        )
        if self._stream is not None:
            _acl_ret(_acl.rt.synchronize_stream(self._stream), "acl.rt.synchronize_stream")

        outputs: List[np.ndarray] = []
        output_count = _acl.mdl.get_num_outputs(self.model_desc)
        for i in range(output_count):
            ptr, size = self._output_buffers[i]
            np_dtype = self._output_dtypes[i] if i < len(self._output_dtypes) else np.float32
            shape = self._output_shapes[i] if i < len(self._output_shapes) else ()

            if not shape or int(np.prod(shape)) <= 0:
                n_elems = size // np.dtype(np_dtype).itemsize
                shape = (n_elems,)

            host = np.empty(int(np.prod(shape)), dtype=np_dtype)
            copy_bytes = min(host.nbytes, size)
            _acl_ret(
                _acl.rt.memcpy(host.ctypes.data, copy_bytes, ptr, copy_bytes, d2h),
                f"memcpy D2H output {i}",
            )
            out = np.ascontiguousarray(host.reshape(shape))
            if not isinstance(out, np.ndarray):
                raise TypeError(f"输出 {i} 不是 ndarray: {type(out)!r}")
            outputs.append(out)

        return outputs

    def release(self) -> None:
        if not self._loaded or _acl is None:
            return
        try:
            self._activate_context()
            for ptr, _ in self._input_buffers + self._output_buffers:
                _acl.rt.free(ptr)
            if self.model_id is not None:
                _acl.mdl.unload(self.model_id)
            if self.model_desc is not None:
                _acl.mdl.destroy_desc(self.model_desc)
            rt = _device_runtime.get(self.device_id)
            if rt:
                rt["models"] = max(0, rt["models"] - 1)
        finally:
            self._loaded = False
            self.model_id = None
            self._input_buffers = []
            self._output_buffers = []

    def __del__(self) -> None:
        try:
            self.release()
        except Exception:
            pass


def _acl_dtype_to_numpy(dtype: int) -> np.dtype:
    assert _acl is not None
    mapping = {
        getattr(_acl, "FLOAT", 0): np.float32,
        getattr(_acl, "FLOAT16", 1): np.float16,
        getattr(_acl, "INT8", 2): np.int8,
        getattr(_acl, "INT32", 3): np.int32,
        getattr(_acl, "UINT8", 4): np.uint8,
    }
    return mapping.get(int(dtype), np.float32)


def default_om_path(name: str, repo_root: Optional[Path] = None) -> Path:
    root = repo_root or Path(__file__).resolve().parent.parent.parent
    return root / "ascend_models" / name
