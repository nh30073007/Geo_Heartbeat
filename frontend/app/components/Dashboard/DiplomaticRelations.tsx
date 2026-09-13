import { ArrowDown, ArrowUp, Network } from 'lucide-react';
import { Panel } from './Panel';
import type { SimulationState } from '../../types';

const rel=[['US','CN','rival'],['US','EU','ally'],['US','IN','ally'],['CN','IN','neutral'],['RU','CN','ally'],['EU','IN','ally']];

export function DiplomaticRelations({ state }: { state?: SimulationState }) {
  const tension = state?.strategic_tension ?? 31;
  const sentiment = state?.public_sentiment ?? 0.18;
  // Risk score rises with tension and falls with positive public sentiment.
  const risk = Math.round(Math.max(5, Math.min(95, tension * 1.3 - sentiment * 20)));
  const level = risk >= 70 ? 'High Risk' : risk >= 40 ? 'Elevated Risk' : 'Low Risk';
  const litBars = Math.max(1, Math.min(4, Math.round(risk / 25)));
  return <Panel eyebrow="NETWORK MODEL" title="Diplomatic Relations" action={<Network size={16}/>}><div className="relation-score"><div><b>{risk}%</b><span>{level}</span></div><div className="relation-bars">{[0,1,2,3].map(i=><i key={i} style={{background:i<litBars?'#ef4444':'#27384c'}}/>)}</div></div><div className="network"><svg viewBox="0 0 330 170">{rel.map(([a,b,t],i)=><line key={i} x1={['55','145','55','145','225','225'][i]} y1={['45','45','120','120','45','120'][i]} x2={['225','225','145','55','145','55'][i]} y2={['120','120','120','45','120','45'][i]} className={t}/>) }<circle cx="55" cy="45" r="22"/><circle cx="145" cy="45" r="22"/><circle cx="225" cy="120" r="22"/><circle cx="55" cy="120" r="22"/><circle cx="225" cy="45" r="22"/><text x="55" y="49">US</text><text x="145" y="49">EU</text><text x="225" y="124">CN</text><text x="55" y="124">IN</text><text x="225" y="49">RU</text></svg></div><div className="network-legend"><span><i className="legend green"/>Ally</span><span><i className="legend slate"/>Neutral</span><span><i className="legend red"/>Rival</span></div></Panel>;
}
