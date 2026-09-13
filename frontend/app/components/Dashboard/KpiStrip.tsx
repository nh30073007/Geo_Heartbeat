"use client";
import { Activity, Cpu, DollarSign, Gauge, Globe2, Package } from 'lucide-react';
import type { SimulationHistoryPoint } from '../../types';
import type { LucideIcon } from 'lucide-react';

function Sparkline({ values = [], tone = 'blue' }: { values?: number[]; tone?: string }) {
  const nums = values.length ? values.slice(-18) : [50, 51, 49, 52];
  const min = Math.min(...nums), max = Math.max(...nums), range = Math.max(1, max - min);
  const pts = nums.map((v, i) => `${(i / Math.max(1, nums.length - 1)) * 100},${21 - ((v - min) / range) * 17}`).join(' ');
  return <svg className={`spark ${tone}`} viewBox="0 0 100 24" preserveAspectRatio="none"><polyline points={pts} fill="none" vectorEffect="non-scaling-stroke"/></svg>;
}

export function KpiStrip({ stability, tension, tech, economic, history = [], conflicts = 5 }: { stability:number; tension:number; tech:number; economic:number; history?:SimulationHistoryPoint[]; conflicts?:number }) {
 const values=(key:keyof SimulationHistoryPoint['state'])=>history.map(p=>Number(p.state[key])).filter(Number.isFinite);
 const cards: Array<[string,string,string,string,string,LucideIcon,number,number[]]>=[
  ['GLOBAL STABILITY', `${Math.round(stability)}`, '/100', stability>70?'Stable':'Watch', 'red', Globe2, stability, [...history.map(p=>Number(p.state.economic_stability))]],
  ['POWER BALANCE', 'MULTI', 'POLAR', 'Dynamic', 'amber', Activity, 64, [...history.map(p=>100-Number(p.state.strategic_tension))]],
  ['ECONOMIC HEALTH', `$${(100 + economic * .063).toFixed(1)}`, 'T', economic>=74?'+2.3%':'-0.4%', 'green', DollarSign, economic, values('economic_stability')],
  ['TECHNOLOGY INDEX', `${(tech/10).toFixed(1)}`, '/10', tech>=70?'+0.8%':'-0.2%', 'blue', Cpu, tech, values('technology_independence')],
  ['RESOURCE PRESSURE', `${Math.round(tension)}`, '/100', tension>70?'High':'Moderate', 'red', Package, tension, [...history.map(p=>Number(p.state.strategic_tension))]],
  ['ACTIVE CONFLICTS', String(conflicts).padStart(2,'0'), '', conflicts>5?'Elevated':'Active', 'red', Gauge, Math.min(100, conflicts*16), [...history.map(p=>Number(p.state.strategic_tension))]],
 ];
 return <div className="kpi-grid">{cards.map(([label,value,unit,delta,tone,Icon,progress,series])=><div className={`kpi-card ${tone}`} key={label as string}><div className="kpi-top"><span>{label as string}</span><div className="kpi-icon"><Icon size={17}/></div></div><div className="kpi-value">{value as string}<em>{unit as string}</em></div><div className="kpi-bottom"><b>{delta as string}</b><span>live</span></div><Sparkline tone={tone as string} values={series as number[]}/><div className="kpi-bar"><span style={{width:`${Math.min(100, Math.max(0, Number(progress)))}%`}}/></div></div>)}</div>;
}
