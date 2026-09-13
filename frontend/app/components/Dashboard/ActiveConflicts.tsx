import { AlertTriangle, ChevronRight, Radio } from 'lucide-react';
import { Panel } from './Panel';
import type { Conflict, SimulationState } from '../../types';

const BASE:Conflict[]=[{id:'c1',name:'Russia vs Ukraine',type:'Military',severity:'High',region:'Eastern Europe',momentum:82},{id:'c2',name:'Israel–Hamas',type:'Proxy War',severity:'High',region:'Middle East',momentum:76},{id:'c3',name:'South China Sea',type:'Territorial',severity:'Medium',region:'Indo-Pacific',momentum:59},{id:'c4',name:'India–Pakistan',type:'Border Tension',severity:'High',region:'South Asia',momentum:68},{id:'c5',name:'Ethiopia Internal',type:'Civil War',severity:'Medium',region:'East Africa',momentum:51}];

function severityFor(m:number):Conflict['severity']{ return m>=70?'High':m>=45?'Medium':'Low'; }

export function ActiveConflicts({ state, onViewAll }: { state?: SimulationState; onViewAll?: () => void }) {
  const tension = state?.strategic_tension ?? 31;
  // Momentum breathes with global strategic tension so the "live" threat
  // monitor actually reflects the running simulation instead of frozen demo
  // numbers.
  const delta = (tension - 31) * 0.6;
  const conflicts = BASE.map(c => {
    const momentum = Math.max(5, Math.min(99, Math.round(c.momentum + delta)));
    return { ...c, momentum, severity: severityFor(momentum) };
  });
  return <Panel eyebrow="THREAT MONITOR" title="Active Conflicts" action={<span className="live-count"><Radio size={12}/> {conflicts.length} ACTIVE</span>}><div className="conflict-list">{conflicts.map(c=><div className="conflict" key={c.id}><div className={`conflict-icon ${c.severity.toLowerCase()}`}><AlertTriangle size={14}/></div><div className="conflict-main"><b>{c.name}</b><span>{c.type} · {c.region}</span><div className="mini-progress"><i style={{width:`${c.momentum}%`}}/></div></div><strong className={c.severity.toLowerCase()}>{c.severity}</strong><ChevronRight size={14}/></div>)}</div><button className="panel-link" onClick={onViewAll}>View all conflicts <ChevronRight size={14}/></button></Panel>;
}
