import { CalendarClock, ChevronRight } from 'lucide-react';
import { Panel } from './Panel';
export function UpcomingEvents({events=[],onOpen}:{events?:any[];onOpen?:()=>void}){return <Panel eyebrow="FORECAST CALENDAR" title="Upcoming Events"><div className="event-list">{events.slice(0,4).map((e:any)=><div className="event" key={e.id}><div className="event-icon"><CalendarClock size={14}/></div><div><b>{e.name}</b><span>{e.type}</span></div><time>R{e.round}</time></div>)}</div><button className="panel-link" onClick={onOpen}>View calendar <ChevronRight size={14}/></button></Panel>}
