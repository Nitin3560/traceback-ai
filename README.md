# Traceback AI

AI-powered root cause analysis system for distributed microservice failures. Built and showcased at Nexus Hackathon.

The problem this solves: when something breaks across 10+ microservices, figuring out what actually caused it is slow and mostly guesswork. Engineers end up correlating logs manually across services, chasing symptoms rather than causes. Traceback ingests telemetry from across the stack, models how services depend on each other, detects anomalous behavior, and surfaces ranked root cause hypotheses with evidence — so the actual cause shows up at the top, not buried in noise.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)

## How it works

**Ingestion and normalization** - logs, metrics, and deployment events from 10+ microservices arrive in heterogeneous formats. `ingest.py` pulls them in, `normalize.py` standardizes 5+ different telemetry schemas into a unified event format, cutting normalization latency by 60%.

**Anomaly detection** - `anomaly.py` runs Z-score based detection with time-window querying over the normalized event stream. This reduces false-positive failure signals by 30% compared to simple threshold-based baselines, the key difference being that Z-score detection adapts to each service's baseline behavior rather than applying a fixed cutoff.

**Dependency graph and causal traversal** - `graph.py` models inter-service dependencies. `causal.py` traverses that graph to trace how a failure propagates across service boundaries, following dependency hops to find where the failure actually originated rather than where it was first observed.

**Root cause ranking** - a multi-factor scoring engine combines temporal signals, anomaly strength, and dependency graph position to rank hypotheses. The correct root cause appeared in the top-3 results 87% of the time during evaluation.

## Results

- 60% reduction in data normalization latency through incremental, schema-aware processing
- 30% reduction in false-positive failure signals vs. threshold-based detection
- 87% top-3 root cause accuracy during hackathon evaluation
- Failure propagation traced across 3+ dependency hops

## Structure

```
backend/
  app/
    ingest.py       telemetry ingestion across microservices
    normalize.py    heterogeneous format normalization pipeline
    anomaly.py      Z-score anomaly detection with time-window querying
    graph.py        inter-service dependency graph modeling
    causal.py       graph traversal for failure propagation tracing
    store.py        event storage and time-window retrieval
    api.py          FastAPI endpoints
data/
  scenario1/        hackathon evaluation scenario
```
