from __future__ import annotations

import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from src.schemas import AlertMessage, MarketEvent

logger = logging.getLogger("crypto_predict_monitor")


class EscalationRule(BaseModel):
    """Escalation rule for adjusting alert severity based on conditions."""
    min_probability: float | None = None
    min_delta: float | None = None
    severity: Literal["info", "warning", "critical"]

    @field_validator("min_probability")
    @classmethod
    def _probability_range(cls, v: float | None) -> float | None:
        if v is None:
            return None
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("min_probability must be a number") from e
        if f < 0.0 or f > 1.0:
            raise ValueError("min_probability must be in [0, 1]")
        return f

    @field_validator("min_delta")
    @classmethod
    def _min_delta_positive(cls, v: float | None) -> float | None:
        if v is None:
            return None
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("min_delta must be a number") from e
        if f <= 0.0:
            raise ValueError("min_delta must be > 0")
        return f

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_lowercase(cls, v: str) -> str:
        return str(v).strip().lower()


class AlertRule(BaseModel):
    market_id: str
    min_probability: float | None = None
    max_probability: float | None = None
    min_delta: float | None = None
    cooldown_seconds: int = 0
    once: bool = False
    severity: Literal["info", "warning", "critical"] = "warning"
    escalate: list[EscalationRule] = []
    reason_template: str | None = None

    @field_validator("market_id")
    @classmethod
    def _market_id_non_empty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("market_id must be non-empty")
        return s

    @field_validator("min_probability", "max_probability")
    @classmethod
    def _probability_range(cls, v: float | None) -> float | None:
        if v is None:
            return None
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("probability must be a number") from e
        if f < 0.0 or f > 1.0:
            raise ValueError("probability must be in [0, 1]")
        return f

    @field_validator("min_delta")
    @classmethod
    def _min_delta_positive(cls, v: float | None) -> float | None:
        if v is None:
            return None
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("min_delta must be a number") from e
        if f <= 0.0:
            raise ValueError("min_delta must be > 0")
        return f

    @field_validator("cooldown_seconds")
    @classmethod
    def _cooldown_non_negative(cls, v: int) -> int:
        try:
            i = int(v)
        except Exception as e:
            raise ValueError("cooldown_seconds must be an integer") from e
        if i < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        return i

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_lowercase(cls, v: str) -> str:
        return str(v).strip().lower()

    def model_post_init(self, __context: Any) -> None:
        if self.min_probability is not None and self.max_probability is not None:
            if self.min_probability > self.max_probability:
                raise ValueError("min_probability must be <= max_probability")


class AlertState:
    def __init__(self) -> None:
        self.last_prob_by_market_id: dict[str, float] = {}
        self.rule_state: dict[str, dict[str, Any]] = {}

    def get_prev(self, market_id: str) -> float | None:
        return self.last_prob_by_market_id.get(market_id)

    def set_current(self, market_id: str, prob: float) -> None:
        self.last_prob_by_market_id[market_id] = float(prob)

    def _rule_key(self, rule: AlertRule) -> str:
        return f"{rule.market_id}:{id(rule)}"

    def get_rule_state(self, rule: AlertRule) -> dict[str, Any]:
        key = self._rule_key(rule)
        if key not in self.rule_state:
            self.rule_state[key] = {
                "last_fired_at": None,
                "active": True,
                "condition_met": False,
                "ever_fired": False,
            }
        return self.rule_state[key]

    def mark_fired(self, rule: AlertRule) -> None:
        state = self.get_rule_state(rule)
        state["last_fired_at"] = time.time()
        state["condition_met"] = True
        state["ever_fired"] = True
        if rule.once:
            state["active"] = False

    def clear_condition(self, rule: AlertRule) -> None:
        state = self.get_rule_state(rule)
        state["condition_met"] = False


def evaluate_event(
    event: MarketEvent,
    rule: AlertRule,
    prev_prob: float | None,
    state: AlertState | None = None,
) -> AlertMessage | None:
    if event.market_id != rule.market_id:
        return None

    triggered = False
    trigger_reason = ""

    min_prob_triggered = False
    max_prob_triggered = False
    delta_triggered = False

    if rule.min_probability is not None and event.probability >= rule.min_probability:
        triggered = True
        min_prob_triggered = True
        trigger_reason = f"probability {event.probability:.4f} >= min {rule.min_probability:.4f}"

    if rule.max_probability is not None and event.probability <= rule.max_probability:
        triggered = True
        max_prob_triggered = True
        trigger_reason = f"probability {event.probability:.4f} <= max {rule.max_probability:.4f}"

    delta_val: float | None = None
    if rule.min_delta is not None and prev_prob is not None:
        delta_val = abs(event.probability - prev_prob)
        if delta_val >= rule.min_delta:
            triggered = True
            delta_triggered = True
            trigger_reason = f"delta {delta_val:.4f} >= min {rule.min_delta:.4f}"

    if state is not None:
        rule_state = state.get_rule_state(rule)
        
        if not triggered:
            state.clear_condition(rule)
            return None
        
        if not rule_state["active"]:
            return None
        
        if rule.once and rule_state["ever_fired"]:
            return None
        
        if rule_state["condition_met"]:
            return None
        
        last_fired = rule_state["last_fired_at"]
        if last_fired is not None and rule.cooldown_seconds > 0:
            elapsed = time.time() - last_fired
            if elapsed < rule.cooldown_seconds:
                return None
    else:
        if not triggered:
            return None

    # Determine severity: start with rule base severity, then check escalations
    severity: str = rule.severity
    
    # Severity priority: info < warning < critical
    severity_priority = {"info": 0, "warning": 1, "critical": 2}
    current_priority = severity_priority.get(severity, 1)
    
    # Evaluate escalation rules
    for escalation in rule.escalate:
        escalation_matches = False
        
        # Check if escalation conditions are met
        if escalation.min_probability is not None:
            if event.probability >= escalation.min_probability:
                escalation_matches = True
        
        if escalation.min_delta is not None and delta_val is not None:
            if delta_val >= escalation.min_delta:
                escalation_matches = True
        
        # If escalation matches, use highest severity
        if escalation_matches:
            escalation_priority = severity_priority.get(escalation.severity, 1)
            if escalation_priority > current_priority:
                severity = escalation.severity
                current_priority = escalation_priority

    msg_parts = [
        f"Alert for market_id={event.market_id}",
        f"current_probability={event.probability:.4f}",
    ]

    if prev_prob is not None:
        msg_parts.append(f"prev_probability={prev_prob:.4f}")
        if delta_val is not None:
            msg_parts.append(f"delta={delta_val:.4f}")

    # Apply custom reason template if provided
    final_reason = trigger_reason
    if rule.reason_template:
        try:
            template_vars = {
                "market_id": event.market_id,
                "probability": event.probability,
                "delta": delta_val if delta_val is not None else 0.0,
                "min_probability": rule.min_probability if rule.min_probability is not None else 0.0,
                "min_delta": rule.min_delta if rule.min_delta is not None else 0.0,
                "severity": severity,
            }
            final_reason = rule.reason_template.format(**template_vars)
        except Exception:
            # Fall back to default reason if formatting fails
            final_reason = trigger_reason

    msg_parts.append(f"reason: {final_reason}")

    message = " | ".join(msg_parts)

    if state is not None:
        state.mark_fired(rule)

    return AlertMessage(event=event, message=message, severity=severity)