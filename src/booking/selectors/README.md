# selectors

本目录集中维护页面选择器。

## 规则

1. **业务代码中不要直接硬编码 selector**
2. 新增页面元素选择器时，应放入本目录
3. 选择器命名应描述业务含义，而不是页面实现细节
4. 如果页面结构变化，只应优先修改本目录

## 文件说明

| 文件 | 作用 |
|------|------|
| `venue_selector.py` | 场馆相关选择器（校区、运动项目） |
| `slot_selector.py` | 时间段相关选择器（日期、时间） |

## 架构

```
selectors/
├── venue_selector.py   # FlexibleVenueSelector
│   └── select_campus(), select_sport()
└── slot_selector.py    # FlexibleSlotSelector
    └── select_date(), select_slot()
```

## 使用示例

```python
from booking.selectors.venue_selector import FlexibleVenueSelector
from booking.selectors.slot_selector import FlexibleSlotSelector

# 选择校区
venue_selector = FlexibleVenueSelector(page)
venue_selector.select_campus("粤海校区")

# 选择时间段
slot_selector = FlexibleSlotSelector(page)
slot_selector.select_slot("19:00-20:00")
```

## 选择器常量

CSS 选择器以字符串常量形式直接定义在各模块内部（如 `client.py` 中的 `"#username"`、`".bh-btn"` 等），确保修改时只需改动一处。