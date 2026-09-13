"use client";
import { Crosshair, Handshake, Landmark, MessageSquare, ShieldPlus } from 'lucide-react';
import { Panel } from './Panel';
const actions=[['Create Crisis',Crosshair,'red'],['Diplomatic Meeting',Handshake,'blue'],['Economic Sanction',Landmark,'amber'],['Peace Negotiation',MessageSquare,'green'],['Deploy Peacekeeping',ShieldPlus,'violet']];
export function QuickActions({onAction}:{onAction?:(a:string)=>void}){return <Panel eyebrow="COMMAND LAYER" title="Quick Actions"><div className="quick-grid">{actions.map(([name,Icon,tone])=><button key={name as string} className={`quick ${tone}`} onClick={()=>onAction?.(name as string)}><Icon size={16}/><span>{name as string}</span></button>)}</div></Panel>}
