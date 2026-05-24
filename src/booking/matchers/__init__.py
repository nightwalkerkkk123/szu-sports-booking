"""Matcher modules for flexible element matching."""
from booking.matchers.text_matcher import TextMatcher, ExactMatcher
from booking.matchers.regex_matcher import RegexMatcher, TimeSlotMatcher
from booking.matchers.contains_matcher import (
    ContainsMatcher,
    PrefixMatcher,
    SuffixMatcher,
)
from booking.matchers.composite_matcher import (
    CompositeMatcher,
    AnyOfMatcher,
    AllOfMatcher,
    create_flexible_matcher,
    create_time_slot_matcher,
    create_campus_matcher,
)

__all__ = [
    # Text matcher
    "TextMatcher",
    "ExactMatcher",
    # Regex matcher
    "RegexMatcher",
    "TimeSlotMatcher",
    # Contains matchers
    "ContainsMatcher",
    "PrefixMatcher",
    "SuffixMatcher",
    # Composite matchers
    "CompositeMatcher",
    "AnyOfMatcher",
    "AllOfMatcher",
    # Factory functions
    "create_flexible_matcher",
    "create_time_slot_matcher",
    "create_campus_matcher",
]