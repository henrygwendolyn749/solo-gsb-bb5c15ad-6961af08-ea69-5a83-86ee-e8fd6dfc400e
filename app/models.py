"""Pydantic request/response models."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from .irt import THETA_MAX, THETA_MIN

# JSON booleans must not sneak in as quota values; strict ints reject them.
PositiveIntField = Annotated[int, Field(strict=True, gt=0)]


# ---- items ----------------------------------------------------------------

class OptionOut(BaseModel):
    key: str
    text: str


class ItemOut(BaseModel):
    """An item as served to an examinee (the correct answer is not exposed)."""

    id: str
    difficulty: float
    discrimination: float
    content_tag: str | None = None
    stem: str
    options: list[OptionOut]


class BankItemOut(BaseModel):
    """Item bank row for administration/inspection, including exposure."""

    id: str
    difficulty: float
    discrimination: float
    content_tag: str | None = None
    stem: str
    answer: str
    exposure_count: int


class ItemDetailOut(BankItemOut):
    options: list[OptionOut]


class ItemBankOut(BaseModel):
    count: int
    items: list[BankItemOut]


# ---- sessions -------------------------------------------------------------

class SessionCreate(BaseModel):
    initial_theta: float = Field(
        0.0, ge=THETA_MIN, le=THETA_MAX, description="初始能力值"
    )
    max_items: int = Field(
        10, ge=1, le=50, description="本次测验最多作答题目数"
    )
    exposure_limit: int | None = Field(
        None,
        ge=1,
        le=10_000,
        description="单题全局曝光上限；缺省取服务端 DEFAULT_EXPOSURE_LIMIT",
    )
    duration_seconds: int | None = Field(
        None,
        ge=60,
        le=86_400,
        description=(
            "可选测验时限（秒，60~86400）；"
            "服务端按 UTC 记录截止时间，到期后 /next 与提交答案返回 409"
        ),
    )
    tag_minimums: dict[str, PositiveIntField] = Field(
        default_factory=dict,
        description=(
            "可选内容标签最低答题配额：键须为题库现有非空 content_tag，"
            "值为正整数，所有配额之和不超过 max_items；不传则不设配额"
        ),
    )
    target_se: float | None = Field(
        None,
        gt=0.0,
        allow_inf_nan=False,
        description=(
            "可选能力估计精度停测目标标准误（正有限值，SE = 1/√Σ Fisher 信息）；"
            "须与 min_precision_items 同时提供，不传则不按精度停测"
        ),
    )
    min_precision_items: PositiveIntField | None = Field(
        None,
        ge=1,
        le=50,
        description=(
            "触发精度停测前至少需要作答的题数（1～max_items）；"
            "须与 target_se 同时提供"
        ),
    )

    @model_validator(mode="after")
    def _validate_precision_stop(self) -> SessionCreate:
        if (self.target_se is None) != (self.min_precision_items is None):
            raise ValueError(
                "target_se 与 min_precision_items 必须同时提供或同时省略"
            )
        if (
            self.min_precision_items is not None
            and self.min_precision_items > self.max_items
        ):
            raise ValueError("min_precision_items 不能大于 max_items")
        return self


class SessionOut(BaseModel):
    id: str
    theta: float
    current_item_id: str | None
    max_items: int
    exposure_limit: int
    duration_seconds: int | None = None
    expires_at: str | None = None
    tag_minimums: dict[str, int] = Field(default_factory=dict)
    target_se: float | None = Field(
        None, description="精度停测目标标准误；未启用时为 null"
    )
    min_precision_items: int | None = Field(
        None, description="精度停测最少作答题数；未启用时为 null"
    )
    standard_error: float | None = Field(
        None, description="当前 θ 下全部已答题的估计标准误 1/√Σ信息；无已答题为 null"
    )
    status: str
    finish_reason: str | None
    answered_count: int
    created_at: str
    updated_at: str


class NextItemOut(BaseModel):
    session_id: str
    status: str
    item: ItemOut | None = None
    information: float | None = None
    exposure_count: int | None = None
    exposure_limit: int
    answered_count: int
    max_items: int
    target_se: float | None = None
    min_precision_items: int | None = None
    standard_error: float | None = None
    finish_reason: str | None = None
    note: str | None = None


# ---- responses ------------------------------------------------------------

class ResponseCreate(BaseModel):
    response_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="客户端生成的幂等键，建议使用 UUID",
    )
    item_id: str = Field(..., description="刚从 /next 取得的题目 ID")
    response: str = Field(..., min_length=1, description="作答选项键，如 'A'")


class ResponseOut(BaseModel):
    id: str
    session_id: str
    item_id: str
    response: str
    correct: bool
    score: int
    correct_answer: str
    theta_before: float
    theta_after: float
    theta_change: float
    p_correct: float
    information_at_theta: float
    exposure_count: int
    created_at: str


class ResponseHistoryOut(BaseModel):
    session_id: str
    status: str
    theta: float
    count: int
    results: list[ResponseOut]


# ---- progress -------------------------------------------------------------

class ProgressOut(BaseModel):
    session_id: str
    status: str
    theta: float
    answered_count: int
    max_items: int
    bank_size: int
    percent_complete: float
    exposure_limit: int
    duration_seconds: int | None = None
    expires_at: str | None = None
    tag_minimums: dict[str, int] = Field(
        default_factory=dict, description="各内容标签的最低答题配额"
    )
    tag_answered: dict[str, int] = Field(
        default_factory=dict, description="各内容标签已答题数（按答题记录统计）"
    )
    target_se: float | None = Field(
        None, description="精度停测目标标准误；未启用时为 null"
    )
    min_precision_items: int | None = Field(
        None, description="精度停测最少作答题数；未启用时为 null"
    )
    standard_error: float | None = Field(
        None, description="当前 θ 下的能力估计标准误；无已答题或总信息为零时为 null"
    )
    finish_reason: str | None
    current_item: ItemOut | None
    answered_item_ids: list[str]


class HealthOut(BaseModel):
    status: str
    bank_size: int
