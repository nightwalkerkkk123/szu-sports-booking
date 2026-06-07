"""Composite matcher for combining multiple matchers."""

from collections.abc import Callable

from booking.matchers.contains_matcher import ContainsMatcher, PrefixMatcher
from booking.matchers.regex_matcher import TimeSlotMatcher
from booking.matchers.text_matcher import TextMatcher


class CompositeMatcher:
    """
    组合匹配器 - 支持多种匹配方式的组合

    示例:
        matcher = CompositeMatcher()
        matcher.add(TextMatcher(), weight=1.0)
        matcher.add(ContainsMatcher(), weight=0.8)
        result = matcher.match("粤海校区网球", "粤海")
    """

    def __init__(self):
        """初始化组合匹配器"""
        self._matchers: list[tuple[Callable, float]] = []

    def add(self, matcher: Callable, weight: float = 1.0) -> "CompositeMatcher":
        """
        添加一个匹配器

        参数:
            matcher: 匹配器实例
            weight: 权重因子

        返回:
            self, 支持链式调用
        """
        self._matchers.append((matcher, weight))
        return self

    def match(self, text: str, target: str) -> bool:
        """
        判断text是否匹配target（任一匹配器返回True即为匹配）

        参数:
            text: 待匹配的文本
            target: 目标文本

        返回:
            bool: 是否匹配
        """
        for matcher, weight in self._matchers:
            if weight > 0 and matcher.match(text, target):
                return True
        return False

    def match_with_score(self, text: str, target: str) -> tuple[bool, float]:
        """
        判断text是否匹配target，并返回匹配得分

        参数:
            text: 待匹配的文本
            target: 目标文本

        返回:
            tuple[bool, float]: (是否匹配, 匹配得分)
        """
        score = 0.0
        for matcher, weight in self._matchers:
            if weight > 0 and matcher.match(text, target):
                score += weight
        return score > 0, score


class AnyOfMatcher:
    """
    任意匹配器 - 只要任一条件匹配即返回True

    示例:
        matcher = AnyOfMatcher([
            TextMatcher(),
            ContainsMatcher(),
        ])
        matcher.match("粤海校区", "校区")  # True (ContainsMatcher匹配)
    """

    def __init__(self, matchers: list[Callable] | None = None):
        """
        初始化

        参数:
            matchers: 匹配器列表
        """
        self._matchers: list[Callable] = matchers or []

    def add(self, matcher: Callable) -> "AnyOfMatcher":
        """添加匹配器"""
        self._matchers.append(matcher)
        return self

    def match(self, text: str, target: str) -> bool:
        """
        判断是否匹配（任一匹配器成功）

        参数:
            text: 待匹配的文本
            target: 目标文本

        返回:
            bool: 是否匹配
        """
        return any(m.match(text, target) for m in self._matchers)


class AllOfMatcher:
    """
    全部匹配器 - 所有条件都匹配才返回True

     示例:
         matcher = AllOfMatcher([
             ContainsMatcher(),
             PrefixMatcher(),
         ])
         matcher.match("粤海校区", "粤")  # True
    """

    def __init__(self, matchers: list[Callable] | None = None):
        """
        初始化

        参数:
            matchers: 匹配器列表
        """
        self._matchers: list[Callable] = matchers or []

    def add(self, matcher: Callable) -> "AllOfMatcher":
        """添加匹配器"""
        self._matchers.append(matcher)
        return self

    def match(self, text: str, target: str) -> bool:
        """
        判断是否匹配（所有匹配器都成功）

        参数:
            text: 待匹配的文本
            target: 目标文本

        返回:
            bool: 是否全部匹配
        """
        return all(m.match(text, target) for m in self._matchers)


# 导出常用预配置组合
def create_flexible_matcher() -> CompositeMatcher:
    """
    创建灵活的组合匹配器

    优先级：精确匹配 > 前缀匹配 > 包含匹配
    """
    return (
        CompositeMatcher()
        .add(TextMatcher(), weight=1.0)
        .add(PrefixMatcher(), weight=0.9)
        .add(ContainsMatcher(), weight=0.8)
    )


def create_time_slot_matcher() -> TimeSlotMatcher:
    """创建时间段专用匹配器"""
    return TimeSlotMatcher()


def create_campus_matcher() -> AnyOfMatcher:
    """
    创建校区匹配器
    支持：精确匹配、包含匹配（匹配"粤海"即匹配"粤海校区"）
    """
    return AnyOfMatcher(
        [
            TextMatcher(),
            ContainsMatcher(),
        ]
    )
