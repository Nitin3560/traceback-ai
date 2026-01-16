from __future__ import annotations
from datetime import datetime
from typing import Any,Dict,Optional
from .store import Event

def _parse_ts(ts:Any)->datetime:
    """
    Accepts ISO strings like '2026-01-13T12:00:00Z' or without Z.
    """
    if isinstance(ts,datetime):
        return ts
    s=str(ts).strip()
    if s.endswith("Z"):
        s=s[:-1]
    return datetime.fromisoformat(s)

def normalize_log(raw:Dict[str,Any])->Event:
    # { "timestamp": "...", "service": "api", "level": "ERROR", "message": "...", "name": "timeout" }
    ts=_parse_ts(raw.get("timestamp"))
    service=str(raw.get("service","unknown"))
    level=str(raw.get("level",raw.get("severity","INFO")))
    name=str(raw.get("name") or raw.get("event") or "log_event")
    msg=raw.get("message") or raw.get("msg") or ""
    attrs=dict(raw)
    attrs.pop("timestamp",None)
    attrs.pop("service",None)
    return Event(
        timestamp=ts,
        service=service,
        type="log",
        name=name,
        severity=level,
        value=None,
        attrs={**attrs,"message":msg},
    )

def normalize_metric(raw:Dict[str,Any])->Event:
    # { "timestamp": "...", "service": "api", "metric": "latency_p95", "value": 123.4 }
    ts=_parse_ts(raw.get("timestamp"))
    service=str(raw.get("service","unknown"))
    metric=str(raw.get("metric") or raw.get("name") or "metric")
    value=raw.get("value")
    try:
        value_f:Optional[float]=float(value) if value is not None else None
    except Exception:
        value_f=None
    attrs=dict(raw)
    attrs.pop("timestamp",None)
    attrs.pop("service",None)
    return Event(
        timestamp=ts,
        service=service,
        type="metric",
        name=metric,
        severity=None,
        value=value_f,
        attrs=attrs,
    )

def normalize_deploy(raw:Dict[str,Any])->Event:
    # { "timestamp": "...", "service": "api", "version": "v3", "change": "deploy" }
    ts=_parse_ts(raw.get("timestamp"))
    service=str(raw.get("service","unknown"))
    version=str(raw.get("version") or raw.get("name") or "deploy")
    change=str(raw.get("change") or "deploy")
    attrs=dict(raw)
    attrs.pop("timestamp",None)
    attrs.pop("service",None)
    return Event(
        timestamp=ts,
        service=service,
        type="deploy",
        name=f"{change}_{version}",
        severity="INFO",
        value=None,
        attrs=attrs,
    )
