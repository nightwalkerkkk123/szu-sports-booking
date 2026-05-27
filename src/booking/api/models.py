"""Data models for API booking."""
from pydantic import BaseModel
from typing import Optional


class TimeSlot(BaseModel):
    """时间段数据模型"""
    wid: str
    code: str  # "08:00-09:00"
    name: str
    state_explain: str  # "PE_OCCUPY,SYS_OPEN" or "SYS_OPEN"
    disabled: bool
    text: str  # "可预约" / "已满员"

    @property
    def is_available(self) -> bool:
        """是否可预约"""
        return not self.disabled and "SYS_OPEN" in self.state_explain


class Venue(BaseModel):
    """场地数据模型"""
    wid: str
    cd_wid: str  # same as wid
    name: str  # "北区网球1号场"
    campus_code: str
    campus_name: str  # "粤海校区"
    sport_code: str
    sport_name: str  # "网球"
    venue_area_code: str  # "015"
    venue_area_name: str  # "北区网球场"
    state_explain: str
    disabled: bool
    text: str  # "可预约" / "体育课占用"
    dcfs: str  # "1.0" 包场
    bcrxz: str  # "4" 可预约人数

    @property
    def is_available(self) -> bool:
        """是否可预约"""
        return not self.disabled and self.state_explain == "SYS_OPEN"


class TimeSlotResponse(BaseModel):
    """获取时间段的API响应"""
    rows: list[TimeSlot]


class VenueResponse(BaseModel):
    """获取场地的API响应"""
    rows: list[Venue]
    page_number: int = 0
    page_size: int = 0
    total_size: int = 0


class BookingRequest(BaseModel):
    """预约请求数据模型"""
    dhid: str = ""  # 空
    yy_rgh: str  # 学号
    cyrs: str = ""  # 空
    yy_rxm: str  # 预约人姓名
    cgdm: str  # 场馆代码 e.g. "015"
    cd_wid: str  # 场地WID
    xmdm: str  # 项目代码 e.g. "004"
    xq_wid: str  # 校区ID e.g. "1"
    ky_ysjd: str  # 时间段 e.g. "12:00-13:00"
    yy_rq: str  # 日期 e.g. "2026-05-25"
    yy_lx: str = "1.0"  # 预约类型
    yy_ks: str  # 开始时间 e.g. "2026-05-25 12:00"
    yy_js: str  # 结束时间 e.g. "2026-05-25 13:00"
    pc_or_phone: str = "pc"


class BookingResponse(BaseModel):
    """预约响应数据模型"""
    code: str  # "0" 表示成功
    message: Optional[str] = None
    datas: Optional[dict] = None

    @property
    def is_success(self) -> bool:
        """是否预约成功"""
        return self.code == "0"