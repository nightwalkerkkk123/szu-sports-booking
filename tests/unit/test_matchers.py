"""Tests for matchers module."""

from booking.matchers import (
    AllOfMatcher,
    AnyOfMatcher,
    CompositeMatcher,
    ContainsMatcher,
    ExactMatcher,
    PrefixMatcher,
    RegexMatcher,
    SuffixMatcher,
    TextMatcher,
    TimeSlotMatcher,
    create_campus_matcher,
    create_flexible_matcher,
    create_time_slot_matcher,
)


class TestTextMatcher:
    """Tests for TextMatcher."""

    def test_match_exact_success(self):
        """精确匹配成功"""
        matcher = TextMatcher()
        assert matcher.match("粤海校区", "粤海校区") is True

    def test_match_exact_failure(self):
        """精确匹配失败"""
        matcher = TextMatcher()
        assert matcher.match("粤海校区", "丽湖校区") is False

    def test_match_empty_strings(self):
        """空字符串匹配"""
        matcher = TextMatcher()
        assert matcher.match("", "") is True
        assert matcher.match("text", "") is False

    def test_match_ignore_case(self):
        """忽略大小写匹配"""
        matcher = TextMatcher()
        assert matcher.match("YUEHAI", "yuehai", ignore_case=True) is True
        assert matcher.match("YUEHAI", "yuehai", ignore_case=False) is False

    def test_match_chinese(self):
        """中文匹配"""
        matcher = TextMatcher()
        assert matcher.match("网球场地", "网球场地") is True
        assert matcher.match("网球场地", "羽毛球场地") is False


class TestExactMatcher:
    """Tests for ExactMatcher (alias of TextMatcher)."""

    def test_is_text_matcher(self):
        """ExactMatcher 是 TextMatcher 的别名"""
        matcher = ExactMatcher()
        assert matcher.match("test", "test") is True
        assert matcher.match("test", "Test") is False


class TestRegexMatcher:
    """Tests for RegexMatcher."""

    def test_match_time_format(self):
        """匹配时间格式"""
        matcher = RegexMatcher()
        assert matcher.match("19:00-20:00", r"\d{2}:\d{2}-\d{2}:\d{2}") is True
        assert matcher.match("19:00", r"\d{2}:\d{2}") is True
        assert matcher.match("invalid", r"\d{2}:\d{2}") is False

    def test_match_campus_suffix(self):
        """匹配校区后缀"""
        matcher = RegexMatcher()
        assert matcher.match("粤海校区", r"校区$") is True
        assert matcher.match("丽湖校区", r"校区$") is True
        assert matcher.match("粤海", r"校区$") is False

    def test_match_invalid_regex(self):
        """无效正则返回 False"""
        matcher = RegexMatcher()
        assert matcher.match("text", r"[invalid") is False

    def test_extract(self):
        """提取匹配分组"""
        matcher = RegexMatcher()
        result = matcher.extract("19:00-20:00", r"(\d{2}:\d{2})")
        assert result == "19:00"

    def test_extract_no_group(self):
        """无分组时返回 None"""
        matcher = RegexMatcher()
        result = matcher.extract("19:00-20:00", r"\d{2}:\d{2}")
        assert result is None


class TestTimeSlotMatcher:
    """Tests for TimeSlotMatcher."""

    def test_match_full_match(self):
        """完整时间段匹配"""
        matcher = TimeSlotMatcher()
        assert matcher.match_time_slot("19:00-20:00", "19:00-20:00") is True

    def test_match_start_time(self):
        """开始时间匹配"""
        matcher = TimeSlotMatcher()
        assert matcher.match_time_slot("19:00-20:00", "19:00") is True

    def test_match_partial(self):
        """部分匹配"""
        matcher = TimeSlotMatcher()
        assert matcher.match_time_slot("19:00-20:00", "19:") is True

    def test_match_no_match(self):
        """不匹配"""
        matcher = TimeSlotMatcher()
        # "20:00" 包含在 "19:00-20:00" 中，所以 contains 匹配返回 True
        assert matcher.match_time_slot("19:00-20:00", "20:00") is True
        # 完全不同的时间
        assert matcher.match_time_slot("19:00-20:00", "21:00") is False

    def test_match_whitespace(self):
        """空白字符处理"""
        matcher = TimeSlotMatcher()
        assert matcher.match_time_slot(" 19:00-20:00 ", " 19:00 ") is True


class TestContainsMatcher:
    """Tests for ContainsMatcher."""

    def test_match_contains(self):
        """包含匹配"""
        matcher = ContainsMatcher()
        assert matcher.match("粤海校区网球", "粤海") is True
        assert matcher.match("粤海校区网球", "网球") is True
        assert matcher.match("粤海校区网球", "羽毛球") is False

    def test_match_ignore_case(self):
        """忽略大小写"""
        matcher = ContainsMatcher()
        assert matcher.match("TENNIS", "ten", ignore_case=True) is True

    def test_match_any(self):
        """任一匹配"""
        matcher = ContainsMatcher()
        assert matcher.match_any("粤海校区", ["粤海", "丽湖"]) is True
        assert matcher.match_any("粤海校区", ["丽湖", "深圳"]) is False

    def test_match_all(self):
        """全部匹配"""
        matcher = ContainsMatcher()
        assert matcher.match_all("粤海校区", ["粤海", "校区"]) is True
        assert matcher.match_all("粤海校区", ["粤海", "深圳"]) is False


class TestPrefixMatcher:
    """Tests for PrefixMatcher."""

    def test_match_prefix(self):
        """前缀匹配"""
        matcher = PrefixMatcher()
        assert matcher.match("粤海校区", "粤海") is True
        assert matcher.match("粤海校区", "校区") is False

    def test_match_ignore_case(self):
        """忽略大小写"""
        matcher = PrefixMatcher()
        assert matcher.match("YUEHAI", "yue", ignore_case=True) is True


class TestSuffixMatcher:
    """Tests for SuffixMatcher."""

    def test_match_suffix(self):
        """后缀匹配"""
        matcher = SuffixMatcher()
        assert matcher.match("粤海校区", "校区") is True
        assert matcher.match("粤海校区", "粤海") is False

    def test_match_ignore_case(self):
        """忽略大小写"""
        matcher = SuffixMatcher()
        assert matcher.match("CAMPUS", "pus", ignore_case=True) is True


class TestCompositeMatcher:
    """Tests for CompositeMatcher."""

    def test_add_and_match(self):
        """添加匹配器并匹配"""
        matcher = CompositeMatcher()
        matcher.add(TextMatcher(), weight=1.0)
        matcher.add(ContainsMatcher(), weight=0.8)

        assert matcher.match("粤海校区", "粤海") is True

    def test_match_with_zero_weight(self):
        """零权重不匹配"""
        matcher = CompositeMatcher()
        matcher.add(TextMatcher(), weight=0.0)

        assert matcher.match("粤海校区", "粤海") is False

    def test_match_score(self):
        """匹配得分"""
        matcher = CompositeMatcher()
        matcher.add(TextMatcher(), weight=1.0)  # 精确匹配 "粤海校区" vs "粤海" -> False
        matcher.add(ContainsMatcher(), weight=0.5)  # 包含匹配 -> True

        matched, score = matcher.match_with_score("粤海校区", "粤海")
        assert matched is True
        # TextMatcher 不匹配(0)，ContainsMatcher 匹配(+0.5)
        assert score == 0.5

    def test_chain_api(self):
        """链式 API"""
        matcher = CompositeMatcher()
        matcher.add(TextMatcher()).add(ContainsMatcher())

        assert matcher.match("text", "ext") is True


class TestAnyOfMatcher:
    """Tests for AnyOfMatcher."""

    def test_match_any_success(self):
        """任一匹配成功"""
        matcher = AnyOfMatcher(
            [
                TextMatcher(),
                ContainsMatcher(),
            ]
        )
        assert matcher.match("粤海校区", "校区") is True

    def test_match_all_fail(self):
        """全部失败"""
        matcher = AnyOfMatcher(
            [
                TextMatcher(),
                ContainsMatcher(),
            ]
        )
        assert matcher.match("粤海校区", "深圳") is False

    def test_add(self):
        """添加匹配器"""
        matcher = AnyOfMatcher()
        matcher.add(TextMatcher())
        matcher.add(ContainsMatcher())

        assert matcher.match("test", "es") is True


class TestAllOfMatcher:
    """Tests for AllOfMatcher."""

    def test_match_all_success(self):
        """全部匹配成功"""
        matcher = AllOfMatcher(
            [
                ContainsMatcher(),
                PrefixMatcher(),
            ]
        )
        assert matcher.match("粤海校区", "粤") is True

    def test_match_partial_fail(self):
        """部分匹配失败"""
        matcher = AllOfMatcher(
            [
                ContainsMatcher(),
                PrefixMatcher(),
            ]
        )
        assert matcher.match("粤海校区", "校") is False

    def test_add(self):
        """添加匹配器"""
        matcher = AllOfMatcher()
        matcher.add(ContainsMatcher())
        matcher.add(PrefixMatcher())

        assert matcher.match("test", "t") is True


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_flexible_matcher(self):
        """创建灵活匹配器"""
        matcher = create_flexible_matcher()
        assert matcher.match("粤海校区网球", "粤海") is True

    def test_create_time_slot_matcher(self):
        """创建时间段匹配器"""
        matcher = create_time_slot_matcher()
        assert matcher.match_time_slot("19:00-20:00", "19:00") is True

    def test_create_campus_matcher(self):
        """创建校区匹配器"""
        matcher = create_campus_matcher()
        assert matcher.match("粤海校区", "粤海") is True
        assert matcher.match("粤海校区", "校区") is True
