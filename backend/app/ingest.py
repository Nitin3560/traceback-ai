from __future__ import annotations
import json
from pathlib import Path
from typing import List,Dict,Any

from .normalize import normalize_log,normalize_metric,normalize_deploy
from .store import Event


def _read_jsonl(path:Path)->List[Dict[str,Any]]:
    if not path.exists():
        return []
    rows:List[Dict[str,Any]]=[]
    with path.open("r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_scenario_events(scenario_dir:str)->List[Event]:
    """
    Reads:
      logs.jsonl, metrics.jsonl, deploy.jsonl
    """
    p=Path(scenario_dir)
    logs=_read_jsonl(p/"logs.jsonl")
    metrics=_read_jsonl(p/"metrics.jsonl")
    deploys=_read_jsonl(p/"deploy.jsonl")

    events:List[Event]=[]
    for r in logs:
        events.append(normalize_log(r))
    for r in metrics:
        events.append(normalize_metric(r))
    for r in deploys:
        events.append(normalize_deploy(r))

    events.sort(key=lambda e:e.timestamp)
    return events
