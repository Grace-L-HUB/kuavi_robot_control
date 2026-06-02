"""解析 rostopic echo 导出的 CameraInfo 文本（camera_info.txt / camera_info1.txt）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _parse_float_list(line: str) -> List[float]:
    m = re.search(r"\[(.*)\]", line)
    if not m:
        return []
    return [float(x.strip()) for x in m.group(1).split(",") if x.strip()]


def parse_camera_info_file(path: str) -> Dict:
    """
    从 rostopic echo /camera/.../camera_info 保存的文本解析一条 CameraInfo。

    多帧以 '---' 分隔时取第一帧完整记录。
    """
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    blocks = [b.strip() for b in text.split("---") if b.strip()]
    block = blocks[0] if blocks else text

    result: Dict = {}
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("frame_id:"):
            result["frame_id"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("height:"):
            result["height"] = int(line.split(":")[1].strip())
        elif line.startswith("width:"):
            result["width"] = int(line.split(":")[1].strip())
        elif line.startswith("K:"):
            k = _parse_float_list(line)
            if len(k) == 9:
                result["fx"], result["fy"] = k[0], k[4]
                result["cx"], result["cy"] = k[2], k[5]
                result["K"] = k
        elif line.startswith("D:"):
            result["D"] = _parse_float_list(line)

    if "fx" not in result:
        raise ValueError(f"无法从 {path} 解析相机内参 K")
    return result


def intrinsics_dict_from_camera_info(info: Dict) -> Dict[str, float]:
    return {
        "fx": info["fx"],
        "fy": info["fy"],
        "cx": info["cx"],
        "cy": info["cy"],
        "width": info.get("width", 640),
        "height": info.get("height", 480),
        "frame_id": info.get("frame_id", ""),
    }


def load_intrinsics_from_camera_info_files(
    color_info_path: str,
    depth_info_path: str,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """从彩色/深度 camera_info 文件加载内参。"""
    color = intrinsics_dict_from_camera_info(parse_camera_info_file(color_info_path))
    depth = intrinsics_dict_from_camera_info(parse_camera_info_file(depth_info_path))
    return color, depth
