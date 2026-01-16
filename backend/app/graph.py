from __future__ import annotations
from dataclasses import dataclass,field
from typing import Dict,List,Set,Iterable
from pathlib import Path
import yaml

@dataclass
class DependencyGraph:
    edges:Dict[str,List[str]]=field(default_factory=dict)

    def downstream(self,service:str)->List[str]:
        return list(self.edges.get(service,[]))

    def services(self)->Set[str]:
        s:Set[str]=set(self.edges.keys())
        for k,v in self.edges.items():
            s.add(k)
            for x in v:
                s.add(x)
        return s

    def reachable_downstream(self,start:str)->Set[str]:
        visited:Set[str]=set()
        stack:List[str]=[start]
        while stack:
            cur=stack.pop()
            for nxt in self.edges.get(cur,[]):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        return visited

    def topo_hint(self,start:str)->List[str]:
        order:List[str]=[]
        q:List[str]=[start]
        seen:Set[str]=set([start])
        while q:
            cur=q.pop(0)
            for nxt in self.edges.get(cur,[]):
                if nxt not in seen:
                    seen.add(nxt)
                    order.append(nxt)
                    q.append(nxt)
        return order

def load_dependencies_yaml(path:str)->DependencyGraph:
    """
    dependencies.yaml expected shape (simple):
    services:
      frontend: [api]
      api: [worker]
      worker: [db]
      db: []
    """
    p=Path(path)
    if not p.exists():
        return DependencyGraph(edges={})

    data=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    services=data.get("services") or data.get("dependencies") or {}
    edges:Dict[str,List[str]]={}
    for k,v in services.items():
        if v is None:
            edges[str(k)]=[]
        elif isinstance(v,list):
            edges[str(k)]=[str(x) for x in v]
        else:
            edges[str(k)]=[str(v)]
    return DependencyGraph(edges=edges)
