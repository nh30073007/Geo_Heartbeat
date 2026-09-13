import { Crosshair, Plane, Shield, Users } from 'lucide-react';
import { Panel } from './Panel';
import type { SimulationState } from '../../types';

const BASE_B:[string,number,string][]=[['United States',801,'blue'],['China',606,'red'],['Russia',309,'amber'],['India',202,'green']];

export function MilitaryOverview({ state }: { state?: SimulationState }) {
  const tension = state?.strategic_tension ?? 31;
  // Spending scales with strategic tension: escalating simulations show
  // budgets climbing, cooling scenarios show them easing off.
  const factor = 1 + (tension - 31) * 0.01;
  const rows = BASE_B.map(([n, v, c]) => [n, `$${Math.round((v as number) * factor)}B`, c] as [string, string, string]);
  const totalT = (BASE_B.reduce((s, [, v]) => s + (v as number), 0) * factor / 1000).toFixed(2);
  const growth = ((factor - 1) * 100);
  return <Panel eyebrow="FORCE POSTURE" title="Military Overview"><div className="military-top"><div><small>Total spending</small><b>${totalT}T</b><em>{growth>=0?'+':''}{growth.toFixed(1)}%</em></div><div className="mini-donut"><span>4</span></div></div><div className="stat-list military">{rows.map(([n,v,c])=><div key={n as string}><span><i className={`legend ${c}`}/>{n as string}</span><b>{v as string}</b><em>{growth>=0?'+':''}{(c==='red'?growth+1.4:growth+0.3).toFixed(1)}%</em></div>)}</div><div className="military-facts"><span><Users size={14}/>21.7M <small>personnel</small></span><span><Shield size={14}/>12,512 <small>warheads</small></span><span><Plane size={14}/>21 <small>carriers</small></span><span><Crosshair size={14}/>{tension>=60?'Critical':tension>=40?'High':'Standard'} <small>readiness</small></span></div></Panel>;
}
