from datetime import date, datetime
from pydantic import BaseModel, Field


from pydantic import BaseModel

class BatchDelete(BaseModel):
    ids: list[int]


# ----- Account -----
class AccountCreate(BaseModel):
    account_name: str = ""
    password: str = ""
    email: str = ""
    server: str = ""
    region: str = ""
    class_name: str = Field(default="", alias="class")
    pin_code: str = ""
    phone: str = ""
    cloud_device: str = ""
    location: str = ""
    verify_code_url: str = ""
    recovery_code: str = ""


class AccountUpdate(BaseModel):
    account_name: str | None = None
    password: str | None = None
    email: str | None = None
    server: str | None = None
    region: str | None = None
    class_name: str | None = Field(default=None, alias="class")
    pin_code: str | None = None
    phone: str | None = None
    cloud_device: str | None = None
    location: str | None = None
    verify_code_url: str | None = None
    recovery_code: str | None = None


class AccountResponse(BaseModel):
    id: int
    account_name: str
    password: str
    email: str
    server: str
    region: str
    class_name: str = Field(alias="class")
    pin_code: str
    phone: str
    cloud_device: str
    location: str
    current_diamonds: int = 0
    verify_code_url: str
    recovery_code: str
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ----- DiamondRecord -----
class DiamondRecordCreate(BaseModel):
    account_id: int
    amount: int
    location: str = ""
    recorded_at: date


class DiamondRecordBatch(BaseModel):
    records: list[DiamondRecordCreate]


class DiamondRecordResponse(BaseModel):
    id: int
    account_id: int
    amount: int
    location: str
    recorded_at: date
    account: AccountResponse | None = None

    model_config = {"from_attributes": True}


# ----- Analytics -----
class OverviewResponse(BaseModel):
    total_diamonds: int
    total_records: int
    entry_count: int
    top_location: str | None


class ComparisonResponse(BaseModel):
    current_amount: int
    previous_amount: int
    change: int
    change_rate: float


class TrendPoint(BaseModel):
    date: date
    amount: int
    change_rate: float | None


class AccountTrendResponse(BaseModel):
    account_id: int
    account_name: str
    trend: list[TrendPoint]


class LocationDistribution(BaseModel):
    location: str
    total_amount: int


class GroupStat(BaseModel):
    name: str
    total_amount: int


class AccountRanking(BaseModel):
    account_id: int
    account_name: str
    cloud_device: str
    total_amount: int
    record_count: int


class CalendarEntry(BaseModel):
    date: date
    amount: int


class CrossStat(BaseModel):
    server: str
    region: str
    total_amount: int


class LowPerformer(BaseModel):
    account_id: int
    account_name: str
    cloud_device: str
    total_amount: int
    average: float
    ratio: float


# ----- Diamond Sync -----
class DiamondSyncItem(BaseModel):
    cloud_device: str
    diamonds: int


class DiamondSyncRequest(BaseModel):
    updates: list[DiamondSyncItem]


class DiamondSyncResponse(BaseModel):
    updated_count: int
    snapshot_count: int


# ----- Diamond Sell -----
class DiamondSellRequest(BaseModel):
    account_ids: list[int]


class DiamondSellResponse(BaseModel):
    sold_count: int
    total_diamonds_sold: int


class DiamondSaleResponse(BaseModel):
    id: int
    account_id: int
    account_name: str
    cloud_device: str
    phone: str
    diamonds_sold: int
    sale_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ----- Diamond Snapshot -----
class DiamondSnapshotResponse(BaseModel):
    id: int
    account_id: int
    date: date
    diamonds: int
    change: int

    model_config = {"from_attributes": True}
