import { Cpu } from 'lucide-react';
import { Panel } from './Panel';
export function TechnologyIndex({ score, ai = score, supply = 70, tension = 30 }: {score:number; ai?:number; supply?:number; tension?:number}){
 const vals=[['AI',ai],['Cyber',Math.min(100, score*.95+5)],['Space',Math.min(100, score*.78+10)],['Nuclear',Math.max(0,58+tension*.12)],['Defense',Math.min(100,81+tension*.08)]];
 return <Panel eyebrow="CAPABILITY" title="Technology Index"><div className="radar-wrap"><svg viewBox="0 0 240 190" className="radar-svg"><polygon points="120,20 192,72 165,154 75,154 48,72"/><polygon points="120,48 164,80 147,132 93,132 76,80"/><polygon points="120,76 136,88 129,111 111,111 104,88"/><polygon points="120,35 181,75 157,142 83,142 59,75" className="radar-data"/><line x1="120" y1="20" x2="120" y2="160"/><line x1="48" y1="72" x2="192" y2="72"/><line x1="75" y1="154" x2="165" y2="154"/></svg><div className="radar-labels">{vals.map(([n,v])=><span key={n}>{n}<b>{Math.round(v as number)}</b></span>)}</div></div><div className="tech-foot"><Cpu size={15}/> <span>AI capability</span><b>{Math.round(ai)}%</b><em>Supply {Math.round(supply)}%</em></div></Panel>
}
