import { Panel } from './Panel';
import type { SimulationState } from '../../types';

const BASE:[string,number,string][]=[['United States',23.1,'blue'],['China',19.8,'red'],['European Union',15.2,'violet'],['Russia',8.9,'amber'],['India',6.3,'green'],['Others',26.7,'slate']];

// Derives live strategic-weight shares from the running simulation instead
// of a frozen snapshot: US/EU weight tracks economic + tech stability,
// China's tracks tension, the rest is renormalized so the donut still sums
// to 100.
function liveShares(state?: SimulationState): [string, number, string][] {
  if (!state) return BASE;
  const econ = (state.economic_stability - 74) * 0.18;
  const tech = (state.ai_capability - 77) * 0.12;
  const tension = (state.strategic_tension - 31) * 0.14;
  const raw: [string, number, string][] = [
    ['United States', 23.1 + econ + tech, 'blue'],
    ['China', 19.8 + tension - tech * 0.4, 'red'],
    ['European Union', 15.2 + econ * 0.4, 'violet'],
    ['Russia', 8.9 + tension * 0.5, 'amber'],
    ['India', 6.3 + tech * 0.3, 'green'],
    ['Others', 26.7 - econ * 0.3 - tension * 0.3, 'slate'],
  ];
  const clamped = raw.map(([n, v, c]) => [n, Math.max(2, v as number), c] as [string, number, string]);
  const total = clamped.reduce((s, [, v]) => s + (v as number), 0);
  return clamped.map(([n, v, c]) => [n, Math.round(((v as number) / total) * 1000) / 10, c]);
}

export function PowerBalance({ state }: { state?: SimulationState }) {
  const data = liveShares(state);
  return <Panel eyebrow="STRATEGIC WEIGHT" title="Power Balance"><div className="donut-layout"><div className="donut"><div><b>100</b><span>Total</span></div></div><div className="legend-list">{data.map(([n,v,c])=><div key={n as string}><i className={`legend ${c}`}/><span>{n as string}</span><b>{v as number}%</b></div>)}</div></div></Panel>;
}
