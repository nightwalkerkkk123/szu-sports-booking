"""Text matcher for exact string matching."""


class TextMatcher:
    """
    精确文本匹配器

    示例:
        matcher = TextMatcher()
        matcher.match("粤海校区", "粤海校区")  # True
        matcher.match("粤海校区", "丽湖校区")  # False
    """

    def match(self, text: str, target: str, ignore_case: bool = False) -> bool:
        """
        判断text是否精确匹配target

        参数:
            text: 待匹配的文本
            target: 目标文本
            ignore_case: 是否忽略大小写

        返回:
            bool: 是否匹配
        """
        if ignore_case:
            return text.lower() == target.lower()
        return text == target


class ExactMatcher(TextMatcher):
    """精确匹配的别名，与TextMatcher等价"""
    pass
