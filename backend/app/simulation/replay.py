"""
Simulation Replay System with:
- Frame-by-frame playback
- Speed control
- Analytics overlay
- Export capabilities
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging
import asyncio
from pathlib import Path
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)

class PlaybackSpeed(Enum):
    """Playback speed options"""
    SLOW = 0.1
    NORMAL = 1.0
    FAST = 2.0
    VERY_FAST = 5.0
    MAX = 10.0

class ReplayMode(Enum):
    """Replay mode"""
    LINEAR = "linear"      # Normal playback
    LOOP = "loop"         # Loop continuously
    RANDOM = "random"     # Random access
    ANALYTICS = "analytics"  # Analytics mode

@dataclass
class ReplayFrame:
    """Single frame in replay"""
    round: int
    timestamp: datetime
    state: Dict[str, float]
    hegemon_strategy: str
    sovereign_strategy: str
    hegemon_utility: float
    sovereign_utility: float
    events: List[Dict[str, Any]] = field(default_factory=list)
    annotations: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReplayStats:
    """Statistics from replay"""
    total_frames: int
    duration: timedelta
    state_transitions: Dict[str, List[Tuple[float, float]]]
    strategy_distribution: Dict[str, Dict[str, int]]
    utility_trends: Dict[str, List[float]]
    equilibrium_points: List[Dict[str, Any]]
    key_events: List[Dict[str, Any]]

class SimulationReplay:
    """
    Advanced simulation replay system
    """
    
    def __init__(self):
        self.frames: List[ReplayFrame] = []
        self.current_frame: int = 0
        self.speed: PlaybackSpeed = PlaybackSpeed.NORMAL
        self.mode: ReplayMode = ReplayMode.LINEAR
        self.is_playing: bool = False
        self._play_task: Optional[asyncio.Task] = None
        
        # Analytics
        self.stats: Optional[ReplayStats] = None
        
        # Callbacks
        self._frame_callbacks: List = []
        
        logger.info("🎬 Simulation Replay initialized")
    
    def load_from_simulation(self, simulation_result: Any) -> int:
        """
        Load frames from simulation result
        """
        self.frames = []
        
        # Extract frames from simulation history
        if hasattr(simulation_result, 'events'):
            for event in simulation_result.events:
                if event.get('type') == 'round_completed':
                    data = event.get('data', {})
                    frame = ReplayFrame(
                        round=data.get('round', 0),
                        timestamp=datetime.now(),
                        state=data.get('state', {}),
                        hegemon_strategy=data.get('hegemon_strategy', ''),
                        sovereign_strategy=data.get('sovereign_strategy', ''),
                        hegemon_utility=data.get('hegemon_utility', 0.0),
                        sovereign_utility=data.get('sovereign_utility', 0.0),
                        events=[event]
                    )
                    self.frames.append(frame)
        
        self.current_frame = 0
        self._calculate_stats()
        
        logger.info(f"📂 Loaded {len(self.frames)} frames from simulation")
        return len(self.frames)
    
    def load_from_history(self, history: List[Dict[str, Any]]) -> int:
        """
        Load frames from state history
        """
        self.frames = []
        
        for entry in history:
            frame = ReplayFrame(
                round=entry.get('round', 0),
                timestamp=datetime.fromisoformat(entry.get('timestamp', datetime.now().isoformat())),
                state=entry.get('state', {}),
                hegemon_strategy=entry.get('hegemon_strategy', ''),
                sovereign_strategy=entry.get('sovereign_strategy', ''),
                hegemon_utility=entry.get('hegemon_utility', 0.0),
                sovereign_utility=entry.get('sovereign_utility', 0.0),
                events=entry.get('events', [])
            )
            self.frames.append(frame)
        
        self.current_frame = 0
        self._calculate_stats()
        
        logger.info(f"📂 Loaded {len(self.frames)} frames from history")
        return len(self.frames)
    
    def load_from_file(self, filepath: str) -> int:
        """
        Load replay from JSON file
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.frames = []
        for frame_data in data.get('frames', []):
            frame = ReplayFrame(
                round=frame_data['round'],
                timestamp=datetime.fromisoformat(frame_data['timestamp']),
                state=frame_data['state'],
                hegemon_strategy=frame_data.get('hegemon_strategy', ''),
                sovereign_strategy=frame_data.get('sovereign_strategy', ''),
                hegemon_utility=frame_data.get('hegemon_utility', 0.0),
                sovereign_utility=frame_data.get('sovereign_utility', 0.0),
                events=frame_data.get('events', []),
                annotations=frame_data.get('annotations', {})
            )
            self.frames.append(frame)
        
        self.current_frame = 0
        self._calculate_stats()
        
        logger.info(f"📂 Loaded {len(self.frames)} frames from file: {filepath}")
        return len(self.frames)
    
    def save_to_file(self, filepath: str):
        """
        Save replay to JSON file
        """
        data = {
            'total_frames': len(self.frames),
            'timestamp': datetime.now().isoformat(),
            'frames': [
                {
                    'round': f.round,
                    'timestamp': f.timestamp.isoformat(),
                    'state': f.state,
                    'hegemon_strategy': f.hegemon_strategy,
                    'sovereign_strategy': f.sovereign_strategy,
                    'hegemon_utility': f.hegemon_utility,
                    'sovereign_utility': f.sovereign_utility,
                    'events': f.events,
                    'annotations': f.annotations
                }
                for f in self.frames
            ],
            'stats': self._stats_to_dict() if self.stats else None
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"💾 Saved replay to: {filepath}")
    
    async def play(
        self,
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        callback: Optional[callable] = None
    ):
        """
        Play the replay
        """
        if not self.frames:
            logger.warning("No frames to play")
            return
        
        if callback:
            self._frame_callbacks.append(callback)
        
        self.is_playing = True
        self.current_frame = start_frame
        end_frame = end_frame or len(self.frames)
        
        try:
            while self.is_playing and self.current_frame < end_frame:
                frame = self.frames[self.current_frame]
                
                # Notify callbacks
                for cb in self._frame_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(cb):
                            await cb(frame)
                        else:
                            cb(frame)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                # Determine next frame based on mode
                if self.mode == ReplayMode.LINEAR:
                    self.current_frame += 1
                elif self.mode == ReplayMode.LOOP:
                    self.current_frame = (self.current_frame + 1) % len(self.frames)
                    if self.current_frame == 0 and end_frame == len(self.frames):
                        break
                elif self.mode == ReplayMode.RANDOM:
                    self.current_frame = np.random.randint(0, len(self.frames))
                elif self.mode == ReplayMode.ANALYTICS:
                    # Jump to key events
                    key_frames = self._get_key_frames()
                    if key_frames:
                        self.current_frame = np.random.choice(key_frames)
                    else:
                        self.current_frame += 1
                
                # Sleep based on speed
                await asyncio.sleep(0.1 / self.speed.value)
                
        except asyncio.CancelledError:
            logger.info("Playback cancelled")
        finally:
            self.is_playing = False
    
    def stop(self):
        """Stop playback"""
        self.is_playing = False
        if self._play_task:
            self._play_task.cancel()
    
    def pause(self):
        """Pause playback"""
        self.is_playing = False
    
    def resume(self):
        """Resume playback"""
        if not self.is_playing:
            self.is_playing = True
            asyncio.create_task(self.play(self.current_frame))
    
    def set_speed(self, speed: PlaybackSpeed):
        """Set playback speed"""
        self.speed = speed
        logger.info(f"⏩ Speed set to: {speed.name}")
    
    def set_mode(self, mode: ReplayMode):
        """Set replay mode"""
        self.mode = mode
        logger.info(f"🔄 Mode set to: {mode.name}")
    
    def goto_frame(self, frame_index: int):
        """Go to specific frame"""
        if 0 <= frame_index < len(self.frames):
            self.current_frame = frame_index
            return self.frames[frame_index]
        return None
    
    def get_current_frame(self) -> Optional[ReplayFrame]:
        """Get current frame"""
        if 0 <= self.current_frame < len(self.frames):
            return self.frames[self.current_frame]
        return None
    
    def get_frame(self, frame_index: int) -> Optional[ReplayFrame]:
        """Get frame by index"""
        if 0 <= frame_index < len(self.frames):
            return self.frames[frame_index]
        return None
    
    def get_frames_range(
        self,
        start: int = 0,
        end: Optional[int] = None
    ) -> List[ReplayFrame]:
        """Get range of frames"""
        end = end or len(self.frames)
        return self.frames[start:end]
    
    def search_frames(
        self,
        criteria: Dict[str, Any],
        max_results: int = 10
    ) -> List[Tuple[int, ReplayFrame]]:
        """Search frames by criteria"""
        results = []
        
        for i, frame in enumerate(self.frames):
            match = True
            for key, value in criteria.items():
                if key == 'hegemon_strategy':
                    if frame.hegemon_strategy != value:
                        match = False
                        break
                elif key == 'sovereign_strategy':
                    if frame.sovereign_strategy != value:
                        match = False
                        break
                elif key == 'state_min':
                    for state_key, min_val in value.items():
                        if frame.state.get(state_key, 0) < min_val:
                            match = False
                            break
                elif key == 'state_max':
                    for state_key, max_val in value.items():
                        if frame.state.get(state_key, 0) > max_val:
                            match = False
                            break
                elif key == 'utility_min':
                    if frame.hegemon_utility < value and frame.sovereign_utility < value:
                        match = False
                        break
                elif key == 'round':
                    if frame.round != value:
                        match = False
                        break
            
            if match:
                results.append((i, frame))
                if len(results) >= max_results:
                    break
        
        return results
    
    def _calculate_stats(self):
        """Calculate replay statistics"""
        if not self.frames:
            self.stats = None
            return
        
        # State transitions
        state_transitions = {
            'economic_stability': [],
            'technology_independence': [],
            'trade_stability': [],
            'strategic_tension': [],
            'public_sentiment': []
        }
        
        for frame in self.frames:
            state = frame.state
            for key in state_transitions:
                if key in state:
                    state_transitions[key].append((frame.round, state[key]))
        
        # Strategy distribution
        strategy_dist = {
            'hegemon': {},
            'sovereign': {}
        }
        
        for frame in self.frames:
            h_strat = frame.hegemon_strategy
            s_strat = frame.sovereign_strategy
            
            strategy_dist['hegemon'][h_strat] = strategy_dist['hegemon'].get(h_strat, 0) + 1
            strategy_dist['sovereign'][s_strat] = strategy_dist['sovereign'].get(s_strat, 0) + 1
        
        # Utility trends
        utility_trends = {
            'hegemon': [f.hegemon_utility for f in self.frames],
            'sovereign': [f.sovereign_utility for f in self.frames]
        }
        
        # Key events
        key_events = []
        for i, frame in enumerate(self.frames):
            if i > 0:
                prev = self.frames[i-1]
                # Detect significant changes
                if abs(frame.state.get('economic_stability', 0) - 
                       prev.state.get('economic_stability', 0)) > 10:
                    key_events.append({
                        'round': frame.round,
                        'type': 'economic_shift',
                        'value': frame.state.get('economic_stability', 0),
                        'change': frame.state.get('economic_stability', 0) - 
                                 prev.state.get('economic_stability', 0)
                    })
                
                if abs(frame.state.get('strategic_tension', 0) - 
                       prev.state.get('strategic_tension', 0)) > 10:
                    key_events.append({
                        'round': frame.round,
                        'type': 'tension_shift',
                        'value': frame.state.get('strategic_tension', 0),
                        'change': frame.state.get('strategic_tension', 0) - 
                                 prev.state.get('strategic_tension', 0)
                    })
                
                if frame.hegemon_strategy != prev.hegemon_strategy:
                    key_events.append({
                        'round': frame.round,
                        'type': 'hegemon_switch',
                        'from': prev.hegemon_strategy,
                        'to': frame.hegemon_strategy
                    })
                
                if frame.sovereign_strategy != prev.sovereign_strategy:
                    key_events.append({
                        'round': frame.round,
                        'type': 'sovereign_switch',
                        'from': prev.sovereign_strategy,
                        'to': frame.sovereign_strategy
                    })
        
        self.stats = ReplayStats(
            total_frames=len(self.frames),
            duration=timedelta(seconds=len(self.frames) * 0.1),
            state_transitions=state_transitions,
            strategy_distribution=strategy_dist,
            utility_trends=utility_trends,
            equilibrium_points=[],  # Can be filled from game theory analysis
            key_events=key_events
        )
    
    def _stats_to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        if not self.stats:
            return {}
        
        return {
            'total_frames': self.stats.total_frames,
            'duration': self.stats.duration.total_seconds(),
            'strategy_distribution': self.stats.strategy_distribution,
            'key_events': self.stats.key_events
        }
    
    def _get_key_frames(self) -> List[int]:
        """Get indices of key frames"""
        key_indices = []
        
        for i, frame in enumerate(self.frames):
            if i > 0 and i < len(self.frames) - 1:
                prev = self.frames[i-1]
                next_frame = self.frames[i+1]
                
                # Local maxima/minima
                if (frame.state.get('economic_stability', 0) > prev.state.get('economic_stability', 0) and
                    frame.state.get('economic_stability', 0) > next_frame.state.get('economic_stability', 0)):
                    key_indices.append(i)
                
                if (frame.state.get('strategic_tension', 0) > prev.state.get('strategic_tension', 0) and
                    frame.state.get('strategic_tension', 0) > next_frame.state.get('strategic_tension', 0)):
                    key_indices.append(i)
        
        return key_indices
    
    def get_export_data(self) -> Dict[str, Any]:
        """Get data for export"""
        return {
            'metadata': {
                'total_frames': len(self.frames),
                'timestamp': datetime.now().isoformat(),
                'speed': self.speed.name,
                'mode': self.mode.name
            },
            'frames': [
                {
                    'round': f.round,
                    'state': f.state,
                    'hegemon_strategy': f.hegemon_strategy,
                    'sovereign_strategy': f.sovereign_strategy,
                    'hegemon_utility': f.hegemon_utility,
                    'sovereign_utility': f.sovereign_utility
                }
                for f in self.frames
            ],
            'stats': self._stats_to_dict() if self.stats else None
        }
    
    def export_to_csv(self, filepath: str):
        """Export replay to CSV"""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            if not self.frames:
                return
            
            # Get all state keys
            state_keys = set()
            for frame in self.frames:
                state_keys.update(frame.state.keys())
            state_keys = sorted(list(state_keys))
            
            # Write header
            writer = csv.writer(f)
            header = ['round', 'timestamp', 'hegemon_strategy', 'sovereign_strategy',
                     'hegemon_utility', 'sovereign_utility'] + state_keys
            writer.writerow(header)
            
            # Write data
            for frame in self.frames:
                row = [
                    frame.round,
                    frame.timestamp.isoformat(),
                    frame.hegemon_strategy,
                    frame.sovereign_strategy,
                    frame.hegemon_utility,
                    frame.sovereign_utility
                ]
                for key in state_keys:
                    row.append(frame.state.get(key, ''))
                writer.writerow(row)
        
        logger.info(f"📊 Exported replay to CSV: {filepath}")
    
    def add_annotation(
        self,
        frame_index: int,
        annotation_key: str,
        annotation_value: Any
    ):
        """Add annotation to a frame"""
        if 0 <= frame_index < len(self.frames):
            self.frames[frame_index].annotations[annotation_key] = annotation_value
            logger.info(f"✏️ Added annotation to frame {frame_index}")
    
    def get_annotation(
        self,
        frame_index: int,
        annotation_key: str
    ) -> Optional[Any]:
        """Get annotation from a frame"""
        if 0 <= frame_index < len(self.frames):
            return self.frames[frame_index].annotations.get(annotation_key)
        return None
    
    def clear_annotations(self, frame_index: Optional[int] = None):
        """Clear annotations"""
        if frame_index is not None:
            if 0 <= frame_index < len(self.frames):
                self.frames[frame_index].annotations = {}
        else:
            for frame in self.frames:
                frame.annotations = {}
        
        logger.info("🧹 Annotations cleared")