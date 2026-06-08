"""昇腾 CANN ACL 加载 .om 模型并推理。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_acl = None
_acl_initialized = False

# 同一 device 共享 Context/Stream（官方要求 load/execute 在同一 Context）
_device_runtime: Dict[int, Dict] = {}


def is_ascend_available() -> bool:
    """当前 Python 环境是否可 import acl（需 source CANN set_env.sh）。"""
    try:
        import acl  # noqa: F401
        return True
    except ImportError:
        return False


def _check_ret(msg: str, ret: int) -> None:
    if ret != 0:
        raise RuntimeError(f"{msg} failed, ret={ret}")


def _ensure_acl() -> None:
    global _acl, _acl_initialized
    import acl as acl_mod

    _acl = acl_mod
    if not _acl_initialized:
        _check_ret("acl.init", _acl.init())
        _acl_initialized = True


def _get_device_runtime(device_id: int) -> Dict:
    """init → set_device → create_context → set_context → stream"""
    _ensure_acl()
    if device_id in _device_runtime:
        rt = _device_runtime[device_id]
        _check_ret("acl.rt.set_context", _acl.rt.set_context(rt["context"]))
        return rt

    _check_ret("acl.rt.set_device", _acl.rt.set_device(device_id))
    context, ret = _acl.rt.create_context(device_id)
    _check_ret("acl.rt.create_context", ret)
    _check_ret("acl.rt.set_context", _acl.rt.set_context(context))
    stream, ret = _acl.rt.create_stream()
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
    """
    昇腾 .om 模型推理封装（CANN ACL Python API）。

    用法::

        model = OmModel("ascend_models/yolov8n.om", device_id=0)
        outputs = model.infer([input_np])
        model.release()
    """

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
        self._input_dataset = None
        self._output_dataset = None
        self._loaded = False

    def _activate_context(self) -> None:
        rt = _get_device_runtime(self.device_id)
        self._context = rt["context"]
        self._stream = rt["stream"]
        _check_ret("acl.rt.set_context", _acl.rt.set_context(self._context))

    def load(self) -> None:
        if self._loaded:
            self._activate_context()
            return

        self._activate_context()

        self.model_id, ret = _acl.mdl.load_from_file(self.model_path)
        _check_ret("acl.mdl.load_from_file", ret)

        self.model_desc = _acl.mdl.create_desc()
        _check_ret("acl.mdl.get_desc", _acl.mdl.get_desc(self.model_desc, self.model_id))

        self._create_io()
        _device_runtime[self.device_id]["models"] += 1
        self._loaded = True
        logger.info("OM model loaded: %s (device=%s)", self.model_path, self.device_id)

    def _create_io(self) -> None:
        assert _acl is not None and self.model_desc is not None
        input_count = _acl.mdl.get_num_inputs(self.model_desc)
        output_count = _acl.mdl.get_num_outputs(self.model_desc)

        self._input_dataset = _acl.mdl.create_dataset()
        self._output_dataset = _acl.mdl.create_dataset()
        self._input_buffers = []
        self._output_buffers = []

        h2d = _memcpy_kind("ACL_MEMCPY_HOST_TO_DEVICE", 1)
        for i in range(input_count):
            size = _acl.mdl.get_input_size_by_index(self.model_desc, i)
            ptr, ret = _acl.rt.malloc(size, 0)
            _check_ret(f"malloc input {i}", ret)
            data_buffer = _acl.create_data_buffer(ptr, size)
            _, ret = _acl.mdl.add_dataset_buffer(self._input_dataset, data_buffer)
            _check_ret(f"add input buffer {i}", ret)
            self._input_buffers.append((ptr, size))

        for i in range(output_count):
            size = _acl.mdl.get_output_size_by_index(self.model_desc, i)
            ptr, ret = _acl.rt.malloc(size, 0)
            _check_ret(f"malloc output {i}", ret)
            data_buffer = _acl.create_data_buffer(ptr, size)
            _, ret = _acl.mdl.add_dataset_buffer(self._output_dataset, data_buffer)
            _check_ret(f"add output buffer {i}", ret)
            self._output_buffers.append((ptr, size))

    def infer(self, inputs: Sequence[np.ndarray]) -> List[np.ndarray]:
        """执行推理，返回 host 侧 numpy 输出列表。"""
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
            arr = np.ascontiguousarray(arr)
            ptr, size = self._input_buffers[i]
            if arr.nbytes > size:
                raise ValueError(
                    f"输入 {i} 字节 {arr.nbytes} 超过模型 buffer {size}；"
                    f"shape={arr.shape} dtype={arr.dtype}"
                )
            _check_ret(
                f"memcpy H2D input {i}",
                _acl.rt.memcpy(ptr, size, arr.ctypes.data, arr.nbytes, h2d),
            )

        _check_ret(
            "acl.mdl.execute",
            _acl.mdl.execute(self.model_id, self._input_dataset, self._output_dataset),
        )
        if self._stream is not None:
            _check_ret("acl.rt.synchronize_stream", _acl.rt.synchronize_stream(self._stream))

        outputs: List[np.ndarray] = []
        output_count = _acl.mdl.get_num_outputs(self.model_desc)
        for i in range(output_count):
            ptr, size = self._output_buffers[i]
            dims, _ = _acl.mdl.get_cur_output_dims(self.model_desc, i)
            dtype, _ = _acl.mdl.get_output_data_type(self.model_desc, i)
            np_dtype = _acl_dtype_to_numpy(dtype)
            shape = tuple(int(d) for d in dims.get("dims", []))
            if not shape or shape[0] <= 0:
                shape = (size // np.dtype(np_dtype).itemsize,)

            host = np.empty(int(np.prod(shape)), dtype=np_dtype)
            _check_ret(
                f"memcpy D2H output {i}",
                _acl.rt.memcpy(host.ctypes.data, host.nbytes, ptr, size, d2h),
            )
            outputs.append(host.reshape(shape))

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
    return mapping.get(dtype, np.float32)


def default_om_path(name: str, repo_root: Optional[Path] = None) -> Path:
    root = repo_root or Path(__file__).resolve().parent.parent.parent
    return root / "ascend_models" / name
