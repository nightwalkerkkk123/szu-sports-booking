"""Contains matcher for substring matching."""


class ContainsMatcher:
    """
    包含匹配器 - 检查文本是否包含子字符串

    示例:
        matcher = ContainsMatcher()
        matcher.match("粤海校区网球", "粤海")  # True
        matcher.match("粤海校区网球", "网球")  # True
        matcher.match("粤海校区", "丽湖")      # False
    """

    def match(self, text: str, substring: str, ignore_case: bool = False) -> bool:
        """
        判断text是否包含substring

        参数:
            text: 待匹配的文本
            substring: 子字符串
            ignore_case: 是否忽略大小写

        返回:
            bool: 是否包含
        """
        if ignore_case:
            return substring.lower() in text.lower()
        return substring in text

    def match_any(self, text: str, substrings: list[str], ignore_case: bool = False) -> bool:
        """
        判断text是否包含任一子字符串

        参数:
            text: 待匹配的文本
            substrings: 子字符串列表
            ignore_case: 是否忽略大小写

        返回:
            bool: 是否包含任一
        """
        return any(self.match(text, s, ignore_case) for s in substrings)

    def match_all(self, text: str, substrings: list[str], ignore_case: bool = False) -> bool:
        """
        判断text是否包含所有子字符串

        参数:
            text: 待匹配的文本
            substrings: 子字符串列表
            ignore_case: 是否忽略大小写

        返回:
            bool: 是否包含所有
        """
        return all(self.match(text, s, ignore_case) for s in substrings)


class PrefixMatcher:
    """
    前缀匹配器 - 检查文本是否以指定前缀开头

    示例:
        matcher = PrefixMatcher()
        matcher.match("粤海校区", "粤海")  # True
        matcher.match("丽湖校区", "粤海")  # False
    """

    def match(self, text: str, prefix: str, ignore_case: bool = False) -> bool:
        """
        判断text是否以prefix开头

        参数:
            text: 待匹配的文本
            prefix: 前缀
            ignore_case: 是否忽略大小写

        返回:
            bool: 是否匹配
        """
        if ignore_case:
            return text.lower().startswith(prefix.lower())
        return text.startswith(prefix)


class SuffixMatcher:
    """
    后缀匹配器 - 检查文本是否以指定后缀结尾

    示例:
        matcher = SuffixMatcher()
        matcher.match("粤海校区", "校区")  # True
        matcher.match("粤海校区", "粤海")  # False
    """

    def match(self, text: str, suffix: str, ignore_case: bool = False) -> bool:
        """
        判断text是否以suffix结尾

        参数:
            text: 待匹配的文本
            suffix: 后缀
            ignore_case: 是否忽略大小写

        返回:
            bool: 是否匹配
        """
        if ignore_case:
            return text.lower().endswith(suffix.lower())
        return text.endswith(suffix)