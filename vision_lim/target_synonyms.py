"""COCO 目标类别同义组：YOLO 检测匹配时互为等价。

NLU 输出的 target（如 bottle）与 YOLO COCO 类名（如 cup）可能不一致，
通过本模块在检测筛选时做等价匹配。
"""

from __future__ import annotations

# 同义组：组内任意类名均可互相匹配
SYNONYM_GROUPS: list[frozenset[str]] = [
    frozenset({"bottle", "cup"}),
]


def expand_target_class(target_class: str) -> set[str]:
    """将 NLU/YOLO 目标类名展开为可匹配的 COCO 类名集合。"""
    t = target_class.lower().strip()
    for group in SYNONYM_GROUPS:
        if t in group:
            return set(group)
    return {t}


def matches_target_class(detected_class: str, target_class: str) -> bool:
    """检测框类别是否满足目标类别（含同义组）。"""
    return detected_class.lower().strip() in expand_target_class(target_class)