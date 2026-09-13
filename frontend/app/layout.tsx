import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata={title:'Strategic AI Nexus | GeoPolis Simulation',description:'Real-time multi-agent geopolitical simulation dashboard'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
