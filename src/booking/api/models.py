"""Data models for API booking."""

from pydantic import BaseModel, Field


class TimeSlot(BaseModel):
    """时间段数据模型"""
    wid: str = Field(alias="WID")
    code: str = Field(alias="CODE")  # "08:00-09:00"
    name: str = Field(alias="NAME")
    state_explain: str | None = Field(default=None, alias="STATE_EXPLAIN")
    disabled: bool
    text: str  # "可预约" / "已满员"

    model_config = {"populate_by_name": True}

    @property
    def is_available(self) -> bool:
        """是否可预约"""
        if self.disabled:
            return False
        if not self.state_explain:
            return False
        return "SYS_OPEN" in self.state_explain and "PE_OCCUPY" not in self.state_explain


class Venue(BaseModel):
    """场地数据模型"""
    wid: str = Field(alias="WID")
    name: str = Field(alias="CDMC")  # "北区网球1号场"
    campus_code: str = Field(alias="XQDM")  # "1"
    campus_name: str = Field(alias="XQDM_DISPLAY")  # "粤海校区"
    sport_code: str = Field(alias="XMDM")  # "004"
    sport_name: str = Field(alias="XMDM_DISPLAY")  # "网球"
    venue_area_code: str = Field(alias="CGBM")  # "015"
    venue_area_name: str = Field(alias="CGBM_DISPLAY")  # "北区网球场"
    state_explain: str = Field(alias="STATE_EXPLAIN")
    disabled: bool
    text: str  # "可预约" / "体育课占用"
    dcfs: str = Field(alias="DCFS")  # "1.0" 包场
    bcrxz: str = Field(alias="BCRSXZ")  # "4" 可预约人数
    scwsdprs: str = Field(default="0", alias="SCWSDPRS")  # 已预约人数

    model_config = {"populate_by_name": True}

    @property
    def is_available(self) -> bool:
        """是否可预约"""
        if self.disabled:
            return False
        if self.state_explain != "SYS_OPEN":
            return False
        # 散场模式：检查是否已满（如 "50/50"）
        if "/" in self.text:
            try:
                current, capacity = self.text.split("/")
                if int(current) >= int(capacity):
                    return False
            except (ValueError, IndexError):
                pass
        return True


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
    message: str | None = None
    datas: dict | None = None

    @property
    def is_success(self) -> bool:
        """是否预约成功"""
        return self.code == "0"


class BookingRecord(BaseModel):
    """预约记录数据模型"""
    wid: str = Field(alias="WID")
    order_id: str = Field(default="", alias="DHID")  # 订单号
    sport_name: str = Field(default="", alias="XMDM_DISPLAY")  # "二楼有氧健身"
    sport_code: str = Field(default="", alias="XMDM")
    venue_name: str = Field(default="", alias="CDWID_DISPLAY")  # "二楼健身房"
    venue_area_name: str = Field(default="", alias="CGDM_DISPLAY")  # "运动广场西馆二楼健身房"
    campus_name: str = Field(default="", alias="XQWID_DISPLAY")  # "粤海校区"
    time_slot: str = Field(default="", alias="YYSJD")  # "2026-05-25 19:00~2026-05-25 20:00"
    status: str = Field(default="", alias="YYZT")  # "CG_DQR" 待确认 / "CG_WC" 已完成 / "CG_QX" 取消
    status_display: str = Field(default="", alias="YYZT_DISPLAY")  # "待确认" / "已完成" / "取消预约"
    booking_type: str = Field(default="", alias="YYLX")
    username: str = Field(default="", alias="YYRGH")
    created_at: str = Field(default="", alias="CJSJ")  # "2026-05-24 20:50:09"
    amount: str = Field(default="0.00", alias="TRANAMT")  # "5.00"
    is_paid: str = Field(default="0", alias="SFZF")  # "0" 未支付 / "1" 已支付

    model_config = {"populate_by_name": True}

    @property
    def is_active(self) -> bool:
        """是否为有效预约（未取消、未完成）"""
        return self.status not in ("CG_QX", "CG_WC")
