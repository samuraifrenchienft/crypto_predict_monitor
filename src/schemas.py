from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MarketEvent(BaseModel):
    market_id: str
    title: str | None = None
    timestamp: datetime
    probability: float
    source: str | None = None

    @field_validator("market_id")
    @classmethod
    def _market_id_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("market_id must be non-empty")
        return s

    @field_validator("probability")
    @classmethod
    def _probability_range(cls, v: float) -> float:
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("probability must be a number") from e
        if f < 0.0 or f > 1.0:
            raise ValueError("probability must be in [0, 1]")
        return f

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        if not isinstance(v, datetime):
            raise ValueError("timestamp must be a datetime")
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class AlertMessage(BaseModel):
    event: MarketEvent
    message: str
    severity: Literal["info", "warning", "critical"] = "info"

    @field_validator("message")
    @classmethod
    def _message_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("message must be non-empty")
        return s

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_lowercase(cls, v: str) -> str:
        return str(v).strip().lower()


class WebhookPayload(BaseModel):
    """
    Webhook payload schema.
    
    Schema Versioning Rules:
    ------------------------
    - schema_version starts at 1 and increments for breaking changes
    - Increment schema_version when:
      * Removing fields
      * Renaming fields
      * Changing field types in incompatible ways
      * Changing validation rules that reject previously valid data
    
    - Do NOT increment schema_version when:
      * Adding new optional fields (backward compatible)
      * Relaxing validation (accepting more data)
      * Adding new enum values
    
    Backward Compatibility:
    -----------------------
    - All new fields MUST be optional (have defaults)
    - Never remove or rename existing fields without incrementing schema_version
    - Consumers should ignore unknown fields (forward compatibility)
    - Producers should handle missing optional fields (backward compatibility)
    
    Current version: 1
    """
    schema_version: int = 1
    content: str
    embeds: list[dict] | None = None

    @field_validator("schema_version")
    @classmethod
    def _schema_version_valid(cls, v: int) -> int:
        try:
            i = int(v)
        except Exception as e:
            raise ValueError("schema_version must be an integer") from e
        if i < 1:
            raise ValueError("schema_version must be >= 1")
        return i

    @field_validator("content")
    @classmethod
    def _content_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("content must be non-empty")
        return s


def format_alert(event: MarketEvent, *, threshold: float | None = None) -> AlertMessage:
    title_part = f" — {event.title}" if event.title else ""
    prob_pct = event.probability * 100.0
    source_part = f" (source: {event.source})" if event.source else ""
    ts = event.timestamp.isoformat()

    threshold_part = ""
    if threshold is not None:
        try:
            threshold_part = f" (threshold: {float(threshold):.4f})"
        except Exception:
            threshold_part = " (threshold provided)"

    msg = (
        f"Market event{source_part}: {event.market_id}{title_part} | "
        f"p={prob_pct:.2f}% | t={ts}{threshold_part}"
    )

    return AlertMessage(event=event, message=msg, severity="info")


def parse_webhook_payload(data: dict) -> WebhookPayload:
    """
    Parse webhook payload with forward compatibility.
    
    This function safely parses webhook payloads, ignoring unknown fields
    to support forward compatibility with future schema versions.
    
    Args:
        data: Dictionary containing webhook payload data
        
    Returns:
        WebhookPayload instance
        
    Raises:
        ValueError: If required fields are missing or invalid
        
    Notes:
        - Accepts schema_version >= 1
        - Ignores unknown fields (forward compatibility)
        - Validates required fields for schema_version 1:
          * content (required, non-empty string)
          * schema_version (optional, defaults to 1, must be >= 1)
          * embeds (optional)
    """
    if not isinstance(data, dict):
        raise ValueError("data must be a dictionary")
    
    schema_version = data.get("schema_version", 1)
    try:
        schema_version = int(schema_version)
    except Exception as e:
        raise ValueError("schema_version must be an integer") from e
    
    if schema_version < 1:
        raise ValueError("schema_version must be >= 1")
    
    filtered_data = {}
    known_fields = {"schema_version", "content", "embeds"}
    
    for key in known_fields:
        if key in data:
            filtered_data[key] = data[key]
    
    try:
        return WebhookPayload.model_validate(filtered_data)
    except Exception as e:
        raise ValueError(f"Invalid webhook payload: {str(e)}") from e


class WebhookEventSnapshot(BaseModel):
    model_config = {"extra": "forbid"}

    market_id: str
    title: str | None = None
    probability: float
    timestamp: str
    source: str | None = None

    @field_validator("market_id")
    @classmethod
    def _market_id_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("market_id must be non-empty")
        return s

    @field_validator("probability")
    @classmethod
    def _probability_range(cls, v: float) -> float:
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("probability must be a number") from e
        if f < 0.0 or f > 1.0:
            raise ValueError("probability must be in [0, 1]")
        return f


class WebhookAlert(BaseModel):
    model_config = {"extra": "forbid"}

    market_id: str
    severity: Literal["info", "warning", "critical"]
    message: str
    current_probability: float
    prev_probability: float | None = None
    delta: float | None = None

    @field_validator("market_id")
    @classmethod
    def _market_id_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("market_id must be non-empty")
        return s

    @field_validator("message")
    @classmethod
    def _message_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("message must be non-empty")
        return s

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_lowercase(cls, v: str) -> str:
        return str(v).strip().lower()


class WebhookPayloadV2(BaseModel):
    model_config = {"extra": "forbid"}

    content: str
    embeds: list[dict] | None = None
    event_snapshot: WebhookEventSnapshot | None = None
    alert: WebhookAlert | None = None

    @field_validator("content")
    @classmethod
    def _content_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("content must be non-empty")
        return s