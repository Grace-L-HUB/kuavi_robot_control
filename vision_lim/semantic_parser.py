"""规则版语义解析：中文指令 -> 结构化 dict（后续可替换为大模型）。"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_COLOR_CN = {
    "红": "red",
    "红色": "red",
    "蓝": "blue",
    "蓝色": "blue",
    "绿": "green",
    "绿色": "green",
    "黄": "yellow",
    "黄色": "yellow",
    "白": "white",
    "白色": "white",
    "黑": "black",
    "黑色": "black",
}

_OBJECT_CN = {
    # 杯/瓶在抓取任务中同义，统一映射为 bottle（YOLO 侧 cup/bottle 均可匹配）
    "杯子": "bottle",
    "杯": "bottle",
    "球": "ball",
    "手机": "phone",
    "水瓶": "bottle",
    "瓶子": "bottle",
    "瓶": "bottle",
}

# Whisper 常见同音误识别 → 纠正后再做 NLU
_ASR_HOMOPHONE_FIX = {
    "屏子": "瓶子",
    "平子": "瓶子",
    "凭子": "瓶子",
    "屏": "瓶",
}


def fix_asr_homophones(text: str) -> str:
    """纠正 Whisper 同音错字（如「拿屏子」→「拿瓶子」）。"""
    s = text
    for wrong, right in sorted(_ASR_HOMOPHONE_FIX.items(), key=lambda x: -len(x[0])):
        s = s.replace(wrong, right)
    return s


def _normalize(text: str) -> str:
    s = text.strip()
    s = re.sub(r"[，。！？、；：\s]+", "", s)
    return s


def parse_instruction(text: str) -> Dict[str, Any]:
    """
    解析自然语言指令。规则版：匹配颜色词与物体词，推断 fetch/stop。
    输出字段与 vision_lim/readme 对齐：attribute 为英文颜色码。
    """
    raw = text.strip()
    raw = fix_asr_homophones(raw)
    norm = _normalize(raw)

    if any(k in raw for k in ("停止", "停下", "别动", "取消")):
        return {"action": "stop", "target": None, "attribute": None, "location": None}

    attribute: Optional[str] = None
    # 长词优先（如「红色」先于「红」）
    for cn in sorted(_COLOR_CN.keys(), key=len, reverse=True):
        if cn in norm:
            attribute = _COLOR_CN[cn]
            break

    target: Optional[str] = None
    for cn in sorted(_OBJECT_CN.keys(), key=len, reverse=True):
        if cn in norm:
            target = _OBJECT_CN[cn]
            break

    if target is not None or attribute is not None:
        action = "fetch"
    else:
        action = "unknown"

    return {
        "action": action,
        "target": target,
        "attribute": attribute,
        "location": None,
    }
