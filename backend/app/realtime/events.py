"""
Advanced Event System with:
- Type-safe events
- Event validation
- Event history
- Event filtering
- Event persistence
"""
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid
import json
import logging

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """All supported event types"""
    # Simulation Events
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_COMPLETED = "simulation_completed"
    SIMULATION_PAUSED = "simulation_paused"
    SIMULATION_RESUMED = "simulation_resumed"
    SIMULATION_STOPPED = "simulation_stopped"
    SIMULATION_FAILED = "simulation_failed"
    
    # Round Events
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    ROUND_FAILED = "round_failed"
    
    # Agent Events
    AGENT_ACTION = "agent_action"
    AGENT_STRATEGY_CHANGED = "agent_strategy_changed"
    AGENT_UTILITY_UPDATED = "agent_utility_updated"
    
    # State Events
    STATE_UPDATED = "state_updated"
    STATE_TRANSITION = "state_transition"
    STATE_CHECKPOINT = "state_checkpoint"
    
    # Sentiment Events
    SENTIMENT_ANALYZED = "sentiment_analyzed"
    SENTIMENT_UPDATED = "sentiment_updated"
    SENTIMENT_THRESHOLD = "sentiment_threshold"
    
    # Environment Events
    ENVIRONMENT_CHANGED = "environment_changed"
    REGION_UPDATED = "region_updated"
    METRIC_THRESHOLD = "metric_threshold"
    
    # System Events
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_INFO = "system_info"
    SYSTEM_HEALTH = "system_health"
    
    # User Events
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"
    USER_ACTION = "user_action"
    
    # Custom Events
    CUSTOM = "custom"

class EventPriority(str, Enum):
    """Event priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    DEBUG = "debug"

class EventCategory(str, Enum):
    """Event categories"""
    SIMULATION = "simulation"
    AGENT = "agent"
    STATE = "state"
    SENTIMENT = "sentiment"
    ENVIRONMENT = "environment"
    SYSTEM = "system"
    USER = "user"

class BaseEvent(BaseModel):
    """Base event model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    category: EventCategory
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('data')
    def validate_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError('Data must be a dictionary')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'type': self.type.value,
            'category': self.category.value,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'data': self.data,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEvent':
        """Create event from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=EventType(data['type']),
            category=EventCategory(data['category']),
            priority=EventPriority(data.get('priority', 'normal')),
            timestamp=datetime.fromisoformat(data['timestamp']) if 'timestamp' in data else datetime.now(),
            source=data['source'],
            data=data.get('data', {}),
            metadata=data.get('metadata', {})
        )

class EventFilter(BaseModel):
    """Filter for events"""
    types: Optional[List[EventType]] = None
    categories: Optional[List[EventCategory]] = None
    priorities: Optional[List[EventPriority]] = None
    sources: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search_text: Optional[str] = None
    limit: int = 100
    
    def matches(self, event: BaseEvent) -> bool:
        """Check if event matches filter"""
        if self.types and event.type not in self.types:
            return False
        
        if self.categories and event.category not in self.categories:
            return False
        
        if self.priorities and event.priority not in self.priorities:
            return False
        
        if self.sources and event.source not in self.sources:
            return False
        
        if self.start_time and event.timestamp < self.start_time:
            return False
        
        if self.end_time and event.timestamp > self.end_time:
            return False
        
        if self.search_text:
            search_lower = self.search_text.lower()
            event_str = json.dumps(event.to_dict()).lower()
            if search_lower not in event_str:
                return False
        
        return True

class EventStats(BaseModel):
    """Event statistics"""
    total_events: int = 0
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_category: Dict[str, int] = Field(default_factory=dict)
    events_by_priority: Dict[str, int] = Field(default_factory=dict)
    events_per_second: float = 0.0
    oldest_event: Optional[datetime] = None
    newest_event: Optional[datetime] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class EventManager:
    """
    Advanced Event Manager with:
    1. Event creation and validation
    2. Event storage and history
    3. Event filtering and search
    4. Event statistics
    5. Event persistence
    """
    
    def __init__(self, max_history: int = 10000):
        self.events: List[BaseEvent] = []
        self.max_history = max_history
        self.subscribers: Dict[EventType, List[callable]] = {}
        self.event_handlers: Dict[EventType, List[callable]] = {}
        
        # Statistics
        self.stats = EventStats()
        
        logger.info("📡 Event Manager initialized")
    
    def create_event(
        self,
        event_type: EventType,
        category: EventCategory,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BaseEvent:
        """
        Create a new event
        """
        event = BaseEvent(
            type=event_type,
            category=category,
            source=source,
            data=data or {},
            priority=priority,
            metadata=metadata or {}
        )
        
        # Add to history
        self.events.append(event)
        if len(self.events) > self.max_history:
            self.events = self.events[-self.max_history:]
        
        # Update stats
        self._update_stats(event)
        
        logger.debug(f"📢 Event created: {event_type.value} from {source}")
        
        return event
    
    def emit(self, event: BaseEvent):
        """
        Emit event to all subscribers
        """
        # Call handlers
        if event.type in self.event_handlers:
            for handler in self.event_handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")
        
        # Call global subscribers
        if event.type in self.subscribers:
            for callback in self.subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Event subscriber failed: {e}")
    
    def subscribe(self, event_type: EventType, callback: callable):
        """
        Subscribe to event type
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.info(f"📡 Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: callable):
        """
        Unsubscribe from event type
        """
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
            logger.info(f"📡 Unsubscribed from {event_type.value}")
    
    def register_handler(self, event_type: EventType, handler: callable):
        """
        Register event handler
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"📡 Registered handler for {event_type.value}")
    
    def get_events(
        self,
        filter: Optional[EventFilter] = None,
        limit: int = 100
    ) -> List[BaseEvent]:
        """
        Get events with optional filter
        """
        events = self.events[-limit:]
        
        if filter:
            events = [e for e in events if filter.matches(e)]
        
        return events[-limit:]
    
    def get_events_by_type(
        self,
        event_type: EventType,
        limit: int = 100
    ) -> List[BaseEvent]:
        """
        Get events by type
        """
        return [e for e in self.events[-limit:] if e.type == event_type][-limit:]
    
    def get_events_by_category(
        self,
        category: EventCategory,
        limit: int = 100
    ) -> List[BaseEvent]:
        """
        Get events by category
        """
        return [e for e in self.events[-limit:] if e.category == category][-limit:]
    
    def get_events_by_source(
        self,
        source: str,
        limit: int = 100
    ) -> List[BaseEvent]:
        """
        Get events by source
        """
        return [e for e in self.events[-limit:] if e.source == source][-limit:]
    
    def get_latest_events(self, limit: int = 10) -> List[BaseEvent]:
        """
        Get latest events
        """
        return self.events[-limit:]
    
    def get_stats(self) -> EventStats:
        """
        Get event statistics
        """
        return self.stats
    
    def clear_history(self):
        """
        Clear event history
        """
        self.events = []
        self.stats = EventStats()
        logger.info("🧹 Event history cleared")
    
    def _update_stats(self, event: BaseEvent):
        """
        Update statistics
        """
        self.stats.total_events += 1
        
        # By type
        event_type = event.type.value
        self.stats.events_by_type[event_type] = self.stats.events_by_type.get(event_type, 0) + 1
        
        # By category
        category = event.category.value
        self.stats.events_by_category[category] = self.stats.events_by_category.get(category, 0) + 1
        
        # By priority
        priority = event.priority.value
        self.stats.events_by_priority[priority] = self.stats.events_by_priority.get(priority, 0) + 1
        
        # Timestamps
        if not self.stats.oldest_event or event.timestamp < self.stats.oldest_event:
            self.stats.oldest_event = event.timestamp
        if not self.stats.newest_event or event.timestamp > self.stats.newest_event:
            self.stats.newest_event = event.timestamp
        
        # Calculate events per second
        if self.stats.oldest_event and self.stats.newest_event:
            duration = (self.stats.newest_event - self.stats.oldest_event).total_seconds()
            if duration > 0:
                self.stats.events_per_second = self.stats.total_events / duration