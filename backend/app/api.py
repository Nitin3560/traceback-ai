from __future__ import annotations

from datetime import datetime,timedelta
from typing import Optional,Dict,Any

from fastapi import FastAPI,Query,Body
from fastapi.middleware.cors import CORSMiddleware

from .store import EventStore
from .ingest import load_scenario_events
from .graph import load_dependencies_yaml
from .anomaly import compute_anomalies
from .causal import rank_root_causes


app=FastAPI(title="Traceback AI",version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORE=EventStore()
GRAPH=None
DATA_LOADED=False


@app.get("/health")
def health()->Dict[str,Any]:
    return {"ok":True,"events":len(STORE.all())}


@app.post("/load_scenario")
def load_scenario(payload:dict=Body(...))->Dict[str,Any]:
    """
    payload:
      {
        "scenario_dir": "../data/scenario1",
        "dependencies_path": "../data/scenario1/dependencies.yaml"
      }
    """
    global GRAPH,DATA_LOADED
    scenario_dir=(payload.get("scenario_dir") or "").strip()
    dependencies_path=(payload.get("dependencies_path") or "").strip()

    events=load_scenario_events(scenario_dir)
    STORE.clear()
    STORE.add_many(events)
    GRAPH=load_dependencies_yaml(dependencies_path)
    DATA_LOADED=True

    if events:
        t0=events[0].timestamp.isoformat()
        t1=events[-1].timestamp.isoformat()
    else:
        t0=t1=None

    return {
        "loaded":True,
        "events":len(events),
        "services":STORE.services(),
        "time_range":{"start":t0,"end":t1},
        "graph_services":sorted(list(GRAPH.services())) if GRAPH else [],
    }


@app.get("/incident/suggest_window")
def suggest_window(minutes:int=Query(10,ge=1,le=120))->Dict[str,Any]:
    """
    Suggest an incident window at the end of the dataset (for quick demo).
    """
    events=STORE.all()
    if not events:
        return {"error":"No events loaded. Call /load_scenario first."}
    end=events[-1].timestamp
    start=end-timedelta(minutes=minutes)
    return {"start":start.isoformat(),"end":end.isoformat(),"minutes":minutes}


@app.get("/anomalies")
def anomalies(
    start:str=Query(...),
    end:str=Query(...),
    baseline_minutes:int=Query(10,ge=1,le=120),
)->Dict[str,Any]:
    if not DATA_LOADED:
        return {"error":"No data loaded. Call /load_scenario first."}

    incident_start=datetime.fromisoformat(start.replace("Z",""))
    incident_end=datetime.fromisoformat(end.replace("Z",""))

    events=STORE.all()
    anoms=compute_anomalies(
        events=events,
        incident_start=incident_start,
        incident_end=incident_end,
        baseline_minutes=baseline_minutes,
    )
    return {
        "incident_window":{"start":start,"end":end},
        "anomalies":{
            svc:{
                "overall":a.overall,
                "metric_z":a.metric_z,
                "first_anomaly_time":a.first_anomaly_time.isoformat() if a.first_anomaly_time else None,
            }
            for svc,a in anoms.items()
        },
    }


@app.get("/root_cause")
def root_cause(
    start:str=Query(...),
    end:str=Query(...),
    baseline_minutes:int=Query(10,ge=1,le=120),
)->Dict[str,Any]:
    if not DATA_LOADED or GRAPH is None:
        return {"error":"No data loaded. Call /load_scenario first."}

    incident_start=datetime.fromisoformat(start.replace("Z",""))
    incident_end=datetime.fromisoformat(end.replace("Z",""))

    events_all=STORE.all()
    events_incident=STORE.between(incident_start,incident_end)

    anoms=compute_anomalies(
        events=events_all,
        incident_start=incident_start,
        incident_end=incident_end,
        baseline_minutes=baseline_minutes,
    )

    ranked=rank_root_causes(
        events=events_incident,
        graph=GRAPH,
        anomalies=anoms,
        incident_start=incident_start,
        incident_end=incident_end,
    )

    return {
        "incident_window":{"start":start,"end":end},
        "ranked_causes":[
            {
                "service":h.service,
                "cause_event":h.cause_event.to_dict() if h.cause_event else None,
                "score":round(h.score,4),
                "cause_strength":round(h.cause_strength,4),
                "propagation_fit":round(h.propagation_fit,4),
                "temporal_priority":round(h.temporal_priority,4),
                "evidence":[ev.to_dict() for ev in h.evidence],
            }
            for h in ranked
        ],
    }
