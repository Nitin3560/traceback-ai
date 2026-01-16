from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timedelta
from typing import Dict,List,Tuple,Optional

from .store import Event


@dataclass
class ServiceAnomaly:
    service:str
    metric_z:Dict[str,float]        
    overall:float                  
    first_anomaly_time:Optional[datetime]

def _mean_std(values:List[float])->Tuple[float,float]:
    n=len(values)
    if n==0:
        return 0.0,1.0
    mean=sum(values)/n
    var=sum((x-mean)**2 for x in values)/max(n,1)
    std=(var**0.5) if var>1e-12 else 1.0
    return mean,std

def compute_anomalies(
    events:List[Event],
    incident_start:datetime,
    incident_end:datetime,
    baseline_minutes:int=10,
    z_threshold:float=2.0,
)->Dict[str,ServiceAnomaly]:
    """
    For each service + metric, compute baseline mean/std from [incident_start - baseline_minutes, incident_start)
    and compute max z-score during incident window.
    """
    baseline_start=incident_start-timedelta(minutes=baseline_minutes)
    baseline:Dict[Tuple[str,str],List[float]]={}
    incident_vals:Dict[Tuple[str,str],List[Tuple[datetime,float]]]={}

    for e in events:
        if e.type!="metric" or e.value is None:
            continue
        key=(e.service,e.name)
        if baseline_start<=e.timestamp<incident_start:
            baseline.setdefault(key,[]).append(float(e.value))
        if incident_start<=e.timestamp<=incident_end:
            incident_vals.setdefault(key,[]).append((e.timestamp,float(e.value)))

    result:Dict[str,ServiceAnomaly]={}
    services=set([s for (s,_m) in set(list(baseline.keys())+list(incident_vals.keys()))])

    for svc in services:
        metric_z:Dict[str,float]={}
        first_anom:Optional[datetime]=None
        max_z=0.0

        metrics_for_service=set([m for (s,m) in incident_vals.keys() if s==svc])
        for m in metrics_for_service:
            base_vals=baseline.get((svc,m),[])
            inc=incident_vals.get((svc,m),[])
            if not inc:
                continue

            mu,sd=_mean_std(base_vals)
            z_list:List[Tuple[datetime,float]]=[]
            for ts,val in inc:
                z=(val-mu)/sd
                z_list.append((ts,z))
            ts_z=max(z_list,key=lambda x:abs(x[1]))
            metric_z[m]=float(ts_z[1])

            cur_abs=abs(ts_z[1])
            if cur_abs>max_z:
                max_z=cur_abs

            over=[ts for ts,z in z_list if abs(z)>=z_threshold]
            if over:
                cand=min(over)
                if first_anom is None or cand<first_anom:
                    first_anom=cand

        result[svc]=ServiceAnomaly(
            service=svc,
            metric_z=metric_z,
            overall=float(max_z),
            first_anomaly_time=first_anom,
        )

    return result
