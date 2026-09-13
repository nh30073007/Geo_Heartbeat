import { Droplets, Flame, Wheat } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Panel } from './Panel';
export function ResourcePressure({score, supply = 70, economic = 70}:{score:number;supply?:number;economic?:number}){
 const factor=Math.max(.55,Math.min(1.45,score/55));
 const rows: Array<[string,number,LucideIcon]>=[['Oil',Math.round(62+factor*20),Flame],['Natural Gas',Math.round(50+factor*20),Flame],['Rare Earth',Math.round(55+factor*18),Wheat],['Water',Math.round(48+(100-supply)*.25),Droplets],['Food',Math.round(44+(100-economic)*.3),Wheat]];
 return <Panel eyebrow="SCARCITY MONITOR" title="Resource Pressure"><div className="resource-score"><div><small>GLOBAL PRESSURE</small><b>{Math.round(score)}</b><em>/100</em></div><span className={score>70?'danger':'warning'}>{score>70?'HIGH':'ELEVATED'}</span></div><div className="resource-list">{rows.map(([name,v,Icon])=><div key={name as string}><span><Icon size={14}/>{name as string}</span><div><i style={{width:`${Math.min(100,v as number)}%`}}/></div><b>{v}%</b></div>)}</div></Panel>
}
