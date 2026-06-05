"""Regex matcher for pattern-based matching."""

import re
from re import Pattern


class RegexMatcher:
    """
    正则表达式匹配器

    示例:
        matcher = RegexMatcher()
        matcher.match("19:00-20:00", r"\\d{2}:\\d{2}-\\d{2}:\\d{2}")  # True
        matcher.match("粤海校区", r"校区$")  # True
    """

    def match(self, text: str, pattern: str, flags: int = 0) -> bool:
        """
        判断text是否匹配正则pattern

        参数:
            text: 待匹配的文本
            pattern: 正则表达式模式
            flags: re模块的flags

        返回:
            bool: 是否匹配

        异常:
            re.error: 如果正则表达式无效
        """
        try:
            compiled: Pattern = re.compile(pattern, flags)
            return compiled.search(text) is not None
        except re.error:
            return False

    def extract(self, text: str, pattern: str, flags: int = 0) -> str | None:
        """
        从text中提取匹配pattern的第一个分组

        参数:
            text: 待匹配的文本
            pattern: 正则表达式模式
            flags: re模块的flags

        返回:
            匹配的第一个分组，或None
        """
        try:
            compiled: Pattern = re.compile(pattern, flags)
            match = compiled.search(text)
            if match and match.groups():
                return match.group(1)
            return None
        except re.error:
            return None


class TimeSlotMatcher(RegexMatcher):
    """
    时间段专用匹配器

    支持的格式:
        - "19:00-20:00"
        - "19:00"
        - "19:00-20:00:30"
    """

    TIME_SLOT_PATTERN = r"(\d{1,2}:\d{2})(?::\d{2})?"

    def match_time_slot(self, text: str, target: str) -> bool:
        """
        判断text是否为target对应的时间段

        参数:
            text: 时间段文本，如 "19:00-20:00"
            target: 目标文本，如 "19:00"

        返回:
            bool: 是否匹配
        """
        text = text.strip()
        target = target.strip()

        # 完全匹配
        if text == target:
            return True

        # 开始时间匹配
        if "-" in text:
            start = text.split("-")[0].strip()
            if start == target:
                return True

        # 包含匹配
        if target in text:
            return True

        return False
