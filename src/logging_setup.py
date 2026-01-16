import logging
import re
from typing import Any, Mapping

from rich.logging import RichHandler


_LOGGER_NAME = "crypto_predict_monitor"

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "secret",
    "authorization",
    "cookie",
    "set-cookie",
    "webhook",
}

_BEARER_RE = re.compile(r"\bbearer\s+[^\s]+", re.IGNORECASE)
_JWT_RE = re.compile(r"\b[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")
_SENSITIVE_IN_URL_RE = re.compile(r"(?i)[?&](?:token|api[_-]?key|key|secret|sig|signature)=")
_DISCORD_WEBHOOK_RE = re.compile(r"(?i)discord(?:app)?\.com/api/webhooks/")


def redact_value(value: str) -> str:
    s = str(value)
    if not s:
        return s

    if _BEARER_RE.search(s):
        return "[REDACTED]"
    if _JWT_RE.search(s):
        return "[REDACTED]"
    if _DISCORD_WEBHOOK_RE.search(s):
        return "[REDACTED]"

    s_lower = s.lower()
    if ("authorization" in s_lower) or ("set-cookie" in s_lower) or ("cookie" in s_lower):
        return "[REDACTED]"

    if s_lower.startswith("http://") or s_lower.startswith("https://"):
        if _SENSITIVE_IN_URL_RE.search(s):
            return "[REDACTED]"

    if _LONG_TOKEN_RE.search(s.strip()):
        return "[REDACTED]"

    return s


def redact_dict(d: Mapping[str, Any]) -> dict:
    sensitive_norm = {s.replace("_", "").replace("-", "") for s in _SENSITIVE_KEYS}
    out: dict = {}
    for k, v in d.items():
        k_str = str(k)
        k_norm = k_str.strip().lower().replace("_", "").replace("-", "")

        if k_norm in sensitive_norm:
            out[k_str] = "[REDACTED]"
            continue

        if isinstance(v, Mapping):
            out[k_str] = redact_dict(v)
        elif isinstance(v, list):
            redacted_list = []
            for item in v:
                if isinstance(item, Mapping):
                    redacted_list.append(redact_dict(item))
                elif isinstance(item, str):
                    redacted_list.append(redact_value(item))
                else:
                    redacted_list.append(item)
            out[k_str] = redacted_list
        elif isinstance(v, tuple):
            redacted_items = []
            for item in v:
                if isinstance(item, Mapping):
                    redacted_items.append(redact_dict(item))
                elif isinstance(item, str):
                    redacted_items.append(redact_value(item))
                else:
                    redacted_items.append(item)
            out[k_str] = tuple(redacted_items)
        elif isinstance(v, str):
            out[k_str] = redact_value(v)
        else:
            out[k_str] = v
    return out


class _RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact_value(record.msg)

            args = record.args
            if isinstance(args, Mapping):
                record.args = redact_dict(args)
            elif isinstance(args, tuple):
                redacted = []
                for a in args:
                    if isinstance(a, Mapping):
                        redacted.append(redact_dict(a))
                    elif isinstance(a, str):
                        redacted.append(redact_value(a))
                    else:
                        redacted.append(a)
                record.args = tuple(redacted)
            elif isinstance(args, list):
                redacted = []
                for a in args:
                    if isinstance(a, Mapping):
                        redacted.append(redact_dict(a))
                    elif isinstance(a, str):
                        redacted.append(redact_value(a))
                    else:
                        redacted.append(a)
                record.args = redacted
            elif isinstance(args, str):
                record.args = redact_value(args)
        except Exception:
            return True
        return True


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.propagate = False

    try:
        logger.setLevel(getattr(logging, str(level).upper()))
    except Exception:
        logger.setLevel(logging.INFO)

    fmt = "%(message)s"
    formatter = logging.Formatter(fmt=fmt)

    has_rich = False
    for h in list(logger.handlers):
        if isinstance(h, RichHandler):
            has_rich = True
            h.setLevel(logger.level)
            h.setFormatter(formatter)
            try:
                h.show_time = True
                h.show_level = True
                h.show_path = False
            except Exception:
                pass
            if not any(isinstance(f, _RedactionFilter) for f in h.filters):
                h.addFilter(_RedactionFilter())

    if not has_rich:
        handler = RichHandler(show_time=True, show_level=True, show_path=False, rich_tracebacks=True)
        handler.setLevel(logger.level)
        handler.setFormatter(formatter)
        handler.addFilter(_RedactionFilter())
        logger.addHandler(handler)

    if not any(isinstance(f, _RedactionFilter) for f in logger.filters):
        logger.addFilter(_RedactionFilter())

    return logger
