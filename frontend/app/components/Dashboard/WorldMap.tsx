// frontend/app/components/Dashboard/WorldMap.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { Maximize2, Layers, Locate, Globe2 } from 'lucide-react';
import type { SimulationState } from '../../types';

// Minimal country geo data — replace with real ISO dataset if available
const COUNTRY_NODES: { id: string; name: string; x: number; y: number; weight: number }[] = [
  { id: 'us', name: 'United States', x: 22, y: 38, weight: 0.95 },
  { id: 'ca', name: 'Canada', x: 20, y: 28, weight: 0.72 },
  { id: 'mx', name: 'Mexico', x: 20, y: 48, weight: 0.52 },
  { id: 'br', name: 'Brazil', x: 32, y: 65, weight: 0.55 },
  { id: 'ar', name: 'Argentina', x: 31, y: 78, weight: 0.47 },
  { id: 'uk', name: 'United Kingdom', x: 47, y: 30, weight: 0.80 },
  { id: 'fr', name: 'France', x: 49, y: 36, weight: 0.75 },
  { id: 'de', name: 'Germany', x: 52, y: 33, weight: 0.78 },
  { id: 'ru', name: 'Russia', x: 62, y: 28, weight: 0.62 },
  { id: 'cn', name: 'China', x: 74, y: 42, weight: 0.85 },
  { id: 'in', name: 'India', x: 68, y: 52, weight: 0.60 },
  { id: 'bd', name: 'Bangladesh', x: 71, y: 55, weight: 0.42 },
  { id: 'pk', name: 'Pakistan', x: 66, y: 52, weight: 0.40 },
  { id: 'ir', name: 'Iran', x: 62, y: 48, weight: 0.50 },
  { id: 'sa', name: 'Saudi Arabia', x: 58, y: 55, weight: 0.65 },
  { id: 'il', name: 'Israel', x: 55, y: 50, weight: 0.68 },
  { id: 'jp', name: 'Japan', x: 85, y: 42, weight: 0.77 },
  { id: 'kr', name: 'South Korea', x: 83, y: 45, weight: 0.70 },
  { id: 'id', name: 'Indonesia', x: 78, y: 62, weight: 0.48 },
  { id: 'au', name: 'Australia', x: 84, y: 72, weight: 0.70 },
  { id: 'za', name: 'South Africa', x: 53, y: 75, weight: 0.45 },
  { id: 'ng', name: 'Nigeria', x: 49, y: 58, weight: 0.35 },
  { id: 'ke', name: 'Kenya', x: 56, y: 64, weight: 0.30 },
];

interface WorldMapProps {
  state: SimulationState;
  selectedId?: string | null;
  onTool?: (tool: string) => void;
  onSelectCountry?: (countryId: string) => void;
}

export const WorldMap: React.FC<WorldMapProps> = ({ state, selectedId, onTool, onSelectCountry }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Subtle pulse animation
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1500);
    return () => clearInterval(id);
  }, []);

  const tensionFactor = Math.max(0, Math.min(1, state.strategic_tension / 100));

  const nodeColor = (weight: number) => {
    const risk = weight * tensionFactor + (1 - weight) * 0.2;
    if (risk > 0.55) return 'bg-red-500';
    if (risk > 0.35) return 'bg-amber-400';
    return 'bg-emerald-400';
  };

  const handleClick = (id: string) => {
    onSelectCountry?.(id);
  };

  return (
    <div ref={containerRef} className="worldmap" id="section-world">
      <div className="worldmap-head">
        <div className="worldmap-title">
          <Globe2 size={14} />
          <span>Interactive World Map</span>
          <small>{COUNTRY_NODES.length} countries · click to inspect</small>
        </div>
        <div className="worldmap-tools">
          <button onClick={() => onTool?.('layers')} title="Layers"><Layers size={14} /></button>
          <button onClick={() => onTool?.('locate')} title="Recenter"><Locate size={14} /></button>
          <button onClick={() => onTool?.('fullscreen')} title="Fullscreen"><Maximize2 size={14} /></button>
        </div>
      </div>

      <div className="worldmap-canvas">
        {/* Faint grid */}
        <div className="worldmap-grid" />

        {/* Country nodes */}
        {COUNTRY_NODES.map(node => {
          const isHovered = hovered === node.id;
          const isSelected = selectedId === node.id;
          const pulse = Math.sin((tick + node.x) / 3) * 0.5 + 0.5;
          const size = 10 + node.weight * 18 + pulse * 4;
          return (
            <button
              key={node.id}
              className={`worldmap-node ${nodeColor(node.weight)} ${isSelected ? 'selected' : ''}`}
              style={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                width: `${size}px`,
                height: `${size}px`,
              }}
              onMouseEnter={() => setHovered(node.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => handleClick(node.id)}
              aria-label={node.name}
            >
              {(isHovered || isSelected) && (
                <span className="worldmap-label">
                  {node.name}
                  {isSelected && <em> · SELECTED</em>}
                </span>
              )}
            </button>
          );
        })}

        {/* Legend */}
        <div className="worldmap-legend">
          <span><i className="dot emerald" /> Stable</span>
          <span><i className="dot amber" /> Unstable</span>
          <span><i className="dot red" /> Critical</span>
        </div>
      </div>
    </div>
  );
};