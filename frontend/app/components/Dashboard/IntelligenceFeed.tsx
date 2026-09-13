import { Activity, CircleAlert, CircleCheck, Info, Radio } from 'lucide-react';
import { Panel } from './Panel';
import type { SimulationState } from '../../types';

function toneFor(type:string, priority?:string){if(priority==='critical'||type.includes('fail')||type.includes('termination'))return 'critical';if(type.includes('action')||type.includes('resum')||type.includes('start'))return 'success';if(type.includes('pause')||type.includes('threshold'))return 'warning';return 'info';}
export function IntelligenceFeed({ state, round, events = [] }: { state?: SimulationState; round?: number; events?: any[] }) {
 const live={time:new Date().toISOString().slice(11,19)+' UTC',text:`Round ${round??0}: stability ${Math.round(state?.economic_stability??0)} · tension ${Math.round(state?.strategic_tension??0)}`,tone:'success'};
 const feed=events.length?events.slice(0,5).map((e:any)=>({time:String(e.timestamp||'').slice(11,19)+' UTC',text:`${String(e.type||'event').replaceAll('_',' ')} · round ${e.data?.round??round??0}`,tone:toneFor(String(e.type||''),e.priority)})):[live];
 return <Panel eyebrow="SENTIMENT + SIGNAL INGESTION" title="Intelligence Feed" action={<span className="feed-live"><Radio size={12}/> LIVE</span>}><div className="intel-list">{feed.map((item:any,i)=><div className="intel" key={`${item.time}-${item.text}-${i}`}><div className={`intel-dot ${item.tone}`}>{item.tone==='critical'?<CircleAlert size={10}/>:item.tone==='success'?<CircleCheck size={10}/>:<Info size={10}/>}</div><div><time>{item.time}</time><b>{item.text}</b></div></div>)}</div><div className="feed-footer"><Activity size={14}/> <span>Backend event stream</span><b>{events.length || 1} recent</b></div></Panel>;
}
