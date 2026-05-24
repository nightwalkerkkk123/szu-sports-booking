# Matchers 模块

灵活的页面元素匹配器模块，支持多种匹配策略。

## 概述

Matchers 模块提供了一套可组合的匹配器，用于在浏览器自动化过程中精确匹配页面元素。

## 匹配器类型

### 1. TextMatcher - 精确文本匹配

```python
from booking.matchers import TextMatcher

matcher = TextMatcher()
matcher.match("粤海校区", "粤海校区")  # True
matcher.match("粤海校区", "丽湖校区")  # False
matcher.match("YUEHAI", "yuehai", ignore_case=True)  # True
```

### 2. RegexMatcher - 正则表达式匹配

```python
from booking.matchers import RegexMatcher

matcher = RegexMatcher()
# 匹配时间格式
matcher.match("19:00-20:00", r"\d{2}:\d{2}-\d{2}:\d{2}")  # True
# 匹配校区后缀
matcher.match("粤海校区", r"校区$")  # True
```

### 3. TimeSlotMatcher - 时间段专用匹配

```python
from booking.matchers import TimeSlotMatcher

matcher = TimeSlotMatcher()
# 完整匹配
matcher.match_time_slot("19:00-20:00", "19:00-20:00")  # True
# 开始时间匹配
matcher.match_time_slot("19:00-20:00", "19:00")  # True
# 部分匹配
matcher.match_time_slot("19:00-20:00", "19:")  # True
```

### 4. ContainsMatcher - 包含匹配

```python
from booking.matchers import ContainsMatcher

matcher = ContainsMatcher()
# 子字符串匹配
matcher.match("粤海校区网球", "粤海")  # True
matcher.match("粤海校区网球", "网球")  # True
# 多条件
matcher.match_any("粤海校区网球", ["粤海", "丽湖"])  # True
matcher.match_all("粤海校区网球", ["粤海", "校区"])  # True
```

### 5. PrefixMatcher / SuffixMatcher - 前缀/后缀匹配

```python
from booking.matchers import PrefixMatcher, SuffixMatcher

prefix = PrefixMatcher()
prefix.match("粤海校区", "粤海")  # True

suffix = SuffixMatcher()
suffix.match("粤海校区", "校区")  # True
```

## 组合匹配器

### CompositeMatcher - 加权组合

```python
from booking.matchers import CompositeMatcher, TextMatcher, ContainsMatcher

matcher = CompositeMatcher()
matcher.add(TextMatcher(), weight=1.0)      # 精确匹配权重最高
matcher.add(ContainsMatcher(), weight=0.8)  # 包含匹配权重较低

matcher.match("粤海校区网球", "粤海")  # True
```

### AnyOfMatcher - 任一匹配

```python
from booking.matchers import AnyOfMatcher, TextMatcher, ContainsMatcher

matcher = AnyOfMatcher([
    TextMatcher(),
    ContainsMatcher(),
])
matcher.match("粤海校区", "校区")  # True (ContainsMatcher匹配)
```

### AllOfMatcher - 全部匹配

```python
from booking.matchers import AllOfMatcher, ContainsMatcher, PrefixMatcher

matcher = AllOfMatcher([
    ContainsMatcher(),
    PrefixMatcher(),
])
matcher.match("粤海校区", "粤")  # True
```

## 工厂函数

```python
from booking.matchers import (
    create_flexible_matcher,
    create_time_slot_matcher,
    create_campus_matcher,
)

# 灵活的通用匹配器
flexible = create_flexible_matcher()

# 时间段专用匹配器
time_slot = create_time_slot_matcher()

# 校区专用匹配器
campus = create_campus_matcher()
```

## 使用场景

### 在 ChainBuilder 中使用

```python
from booking.chain_builder import Chain
from booking.matchers import TextMatcher

# Chain 已经内置了多种匹配方式
chain = Chain(page)
chain.click("粤海校区")  # 精确匹配
chain.click(contains="网球")  # 包含匹配
chain.click(regex=r"\d{2}:\d{2}")  # 正则匹配
```

### 在 SlotSelector 中使用

```python
from booking.selectors.slot_selector import FlexibleSlotSelector

selector = FlexibleSlotSelector(page)
selector.select("19:00-20:00")  # 自动使用 TimeSlotMatcher
```

## 架构设计

```
matchers/
├── __init__.py           # 公共接口
├── text_matcher.py       # 精确文本匹配
├── regex_matcher.py       # 正则表达式匹配
├── contains_matcher.py    # 包含匹配、前缀/后缀匹配
└── composite_matcher.py   # 组合匹配器
```

## 扩展指南

### 创建自定义匹配器

```python
class MyMatcher:
    def match(self, text: str, target: str) -> bool:
        # 自定义匹配逻辑
        return custom_logic(text, target)
```

### 创建自定义组合

```python
matcher = CompositeMatcher()
matcher.add(MyMatcher(), weight=1.0)
matcher.add(TextMatcher(), weight=0.5)
```