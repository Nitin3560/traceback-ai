from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict,List,Optional,Tuple

from .store import Event
from .graph import DependencyGraph
from .anomaly import ServiceAnomaly


@dataclass
class RootCauseHypothesis:
    service:str
    cause_event:Optional[Event]
    score:float
    cause_strength:float
    propagation_fit:float
    temporal_priority:float
    evidence:List[Event]


def _find_candidate_cause_events(events:List[Event],start:datetime,end:datetime)->List[Event]:
    """
    Candidates are: deploy events + error-ish log events in the incident window.
    """
    candidates:List[Event]=[]
    for e in events:
        if not (start<=e.timestamp<=end):
            continue
        if e.type=="deploy":
            candidates.append(e)
        elif e.type=="log":
            sev=(e.severity or "").upper()
            if sev in ("ERROR","FATAL","CRITICAL"):
                candidates.append(e)
    candidates.sort(key=lambda x:x.timestamp)
    return candidates

def _cause_strength(e:Optional[Event],anomalies:Dict[str,ServiceAnomaly])->float:
    if e is None:
        return 0.0
    base=0.3
    if e.type=="deploy":
        base=0.9
    elif e.type=="log":
        base=0.7 if (e.severity or "").upper() in ("ERROR","FATAL","CRITICAL") else 0.4
    a=anomalies.get(e.service)
    if a:
        base*=(1.0+min(a.overall/10.0,0.5))  
    return float(min(base,1.5))


def _temporal_priority(e:Optional[Event],incident_start:datetime,incident_end:datetime)->float:
    if e is None:
        return 0.0
    total=(incident_end-incident_start).total_seconds() or 1.0
    pos=(e.timestamp-incident_start).total_seconds()
    return float(max(0.0,1.0-(pos/total)))


def _propagation_fit(
    origin_service:str,
    origin_time:datetime,
    graph:DependencyGraph,
    anomalies:Dict[str,ServiceAnomaly],
    max_lag_seconds:int=180,
)->Tuple[float,List[str]]:
    """
    Check how many downstream services show first_anomaly_time after origin_time within lag.
    """
    downstream=list(graph.reachable_downstream(origin_service))
    if not downstream:
        return 0.0,[]

    explained:List[str]=[]
    for svc in downstream:
        a=anomalies.get(svc)
        if not a or not a.first_anomaly_time:
            continue
        dt=(a.first_anomaly_time-origin_time).total_seconds()
        if 0<=dt<=max_lag_seconds:
            explained.append(svc)

    fit=len(explained)/max(len(downstream),1)
    return float(fit),explained


def rank_root_causes(
    events:List[Event],
    graph:DependencyGraph,
    anomalies:Dict[str,ServiceAnomaly],
    incident_start:datetime,
    incident_end:datetime,
)->List[RootCauseHypothesis]:
    candidates=_find_candidate_cause_events(events,incident_start,incident_end)

    if not candidates:
        earliest=None
        for a in anomalies.values():
            if a.first_anomaly_time:
                if earliest is None or a.first_anomaly_time<earliest[1]:
                    earliest=(a.service,a.first_anomaly_time)
        if earliest:
            svc,ts=earliest
            fake=Event(timestamp=ts,service=svc,type="metric",name="anomaly_spike",value=None,attrs={})
            candidates=[fake]

    hyps:List[RootCauseHypothesis]=[]

    for e in candidates:
        cs=_cause_strength(e,anomalies)
        tp=_temporal_priority(e,incident_start,incident_end)
        pf,explained=_propagation_fit(e.service,e.timestamp,graph,anomalies)
        score=0.45*cs+0.35*pf+0.20*tp
        evidence:List[Event]=[e]
        for svc in explained:
            t=anomalies[svc].first_anomaly_time
            if t:
                evidence.append(Event(timestamp=t,service=svc,type="metric",name="first_anomaly",attrs={},value=None))
        evidence.sort(key=lambda x:x.timestamp)

        hyps.append(
            RootCauseHypothesis(
                service=e.service,
                cause_event=e,
                score=float(score),
                cause_strength=float(cs),
                propagation_fit=float(pf),
                temporal_priority=float(tp),
                evidence=evidence,
            )
        )

    best:Dict[str,RootCauseHypothesis]={}
    for h in hyps:
        if h.service not in best or h.score>best[h.service].score:
            best[h.service]=h

    ranked=sorted(best.values(),key=lambda x:x.score,reverse=True)
    return ranked[:5]
