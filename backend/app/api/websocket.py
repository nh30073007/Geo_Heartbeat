"""
Advanced WebSocket Manager with:
- Connection lifecycle management
- Authentication
- Room management
- Message queuing
- Heartbeat monitoring
- Broadcast with filtering
- ✅ FIXED: JSON serialization errors
"""
from typing import Dict, Any, Optional, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
import logging
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, Field

from .events import EventManager, BaseEvent, EventType, EventCategory, EventPriority

logger = logging.getLogger(__name__)

class ConnectionStatus(str, Enum):
    """Connection status"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"

class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    sender: Optional[str] = None
    room: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'data': self._json_safe(self.data),
            'timestamp': self.timestamp.isoformat(),
            'sender': self.sender,
            'room': self.room
        }
    
    def _json_safe(self, obj: Any) -> Any:
        """Convert objects to JSON-safe format"""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, dict):
            return {str(k): self._json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._json_safe(v) for v in obj]
        if hasattr(obj, 'dict'):
            return self._json_safe(obj.dict())
        if hasattr(obj, '__dict__'):
            return self._json_safe({k: v for k, v in obj.__dict__.items() if not k.startswith('_')})
        # For any other object, convert to string
        return str(obj)

class WebSocketConnection:
    """WebSocket connection wrapper"""
    
    def __init__(
        self,
        websocket: WebSocket,
        client_id: str,
        room: Optional[str] = None
    ):
        self.websocket = websocket
        self.client_id = client_id
        self.room = room or 'global'
        self.status = ConnectionStatus.CONNECTING
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.user_id: Optional[str] = None
        self.user_info: Dict[str, Any] = {}
        self.message_queue: List[WebSocketMessage] = []
        self.subscriptions: Set[EventType] = set()
        
    async def send(self, message: WebSocketMessage):
        """Send message to client"""
        try:
            # ✅ FIX: Use to_dict() which handles JSON serialization
            await self.websocket.send_json(message.to_dict())
            logger.debug(f"📤 Sent to {self.client_id}: {message.type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send to {self.client_id}: {e}")
            return False
    
    async def send_event(self, event: BaseEvent):
        """Send event as message"""
        message = WebSocketMessage(
            type='event',
            data=event.to_dict() if hasattr(event, 'to_dict') else event.__dict__,
            sender='server'
        )
        await self.send(message)
    
    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = datetime.now()

class WebSocketManager:
    """
    Advanced WebSocket Manager with:
    1. Connection lifecycle management
    2. Authentication
    3. Room management
    4. Message queuing
    5. Heartbeat monitoring
    6. Broadcast with filtering
    """
    
    def __init__(self, event_manager: Optional[EventManager] = None):
        self.event_manager = event_manager or EventManager()
        
        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.rooms: Dict[str, List[str]] = {'global': []}
        
        # Authentication
        self.auth_tokens: Dict[str, Dict[str, Any]] = {}
        
        # Heartbeat
        self.heartbeat_interval = 45  # seconds
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Message queue
        self.message_buffer: List[WebSocketMessage] = []
        self.buffer_size = 1000
        
        # Event subscription
        self.event_subscribers: Dict[EventType, List[str]] = {}
        
        logger.info("🔌 WebSocket Manager initialized")
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        token: Optional[str] = None,
        room: str = 'global'
    ) -> Dict[str, Any]:
        """
        Handle new WebSocket connection
        """
        client_id = client_id or str(uuid.uuid4())
        
        # Start heartbeat lazily once an event loop is running.
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._start_heartbeat()

        # Accept connection
        await websocket.accept()
        
        # Create connection
        connection = WebSocketConnection(websocket, client_id, room)
        connection.status = ConnectionStatus.CONNECTED
        
        # Store connection
        self.connections[client_id] = connection
        
        # Add to room
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(client_id)
        
        # Authenticate if token provided
        if token:
            await self._authenticate(client_id, token)
        
        # Send connection success
        await connection.send(WebSocketMessage(
            type='connection_established',
            data={
                'client_id': client_id,
                'room': room,
                'status': connection.status.value,
                'timestamp': datetime.now().isoformat()
            }
        ))
        
        # Broadcast connection event
        await self.broadcast(WebSocketMessage(
            type='user_connected',
            data={'client_id': client_id, 'room': room},
            sender='system'
        ), room=room)
        
        logger.info(f"🔗 Client {client_id} connected to room {room}")
        
        return {
            'client_id': client_id,
            'room': room,
            'status': connection.status.value
        }
    
    async def disconnect(self, client_id: str, code: int = 1000, reason: str = "Disconnected"):
        """
        Handle disconnection
        """
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        
        # Update status
        connection.status = ConnectionStatus.DISCONNECTED
        
        # Remove from room
        room = connection.room
        if room in self.rooms and client_id in self.rooms[room]:
            self.rooms[room].remove(client_id)
        
        # Remove from connections
        del self.connections[client_id]
        
        # Close the socket
        try:
            await connection.websocket.close(code=code, reason=reason)
        except Exception:
            pass
        
        # Broadcast disconnection
        await self.broadcast(WebSocketMessage(
            type='user_disconnected',
            data={'client_id': client_id, 'room': room},
            sender='system'
        ), room=room)
        
        logger.info(f"🔌 Client {client_id} disconnected")
    
    async def handle_message(self, client_id: str, message_data: Dict[str, Any]):
        """
        Handle incoming message
        """
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        
        # Any inbound traffic proves the client is alive
        connection.update_heartbeat()

        try:
            # Parse message
            message = WebSocketMessage(**message_data)
            message.sender = client_id
            
            # Process based on type
            if message.type == 'heartbeat':
                await self._handle_heartbeat(client_id, message)
            
            elif message.type == 'subscribe':
                await self._handle_subscribe(client_id, message)
            
            elif message.type == 'unsubscribe':
                await self._handle_unsubscribe(client_id, message)
            
            elif message.type == 'event':
                await self._handle_event(client_id, message)
            
            elif message.type == 'broadcast':
                await self._handle_broadcast(client_id, message)
            
            else:
                # Unknown message type
                await connection.send(WebSocketMessage(
                    type='error',
                    data={'message': f'Unknown message type: {message.type}'},
                    sender='system'
                ))
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await connection.send(WebSocketMessage(
                type='error',
                data={'message': str(e)},
                sender='system'
            ))
    
    async def broadcast(
        self,
        message: WebSocketMessage,
        room: Optional[str] = None,
        exclude: Optional[List[str]] = None
    ):
        """
        Broadcast message to room or all clients
        """
        exclude = exclude or []
        
        if room:
            # Broadcast to specific room
            if room in self.rooms:
                tasks = []
                for client_id in self.rooms[room]:
                    if client_id not in exclude and client_id in self.connections:
                        tasks.append(
                            self.connections[client_id].send(message)
                        )
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Broadcast to all clients
            tasks = []
            for client_id, connection in self.connections.items():
                if client_id not in exclude:
                    tasks.append(connection.send(message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_event(self, event: BaseEvent, room: Optional[str] = None):
        """
        Broadcast event to room
        """
        message = WebSocketMessage(
            type='event',
            data=event.to_dict() if hasattr(event, 'to_dict') else event.__dict__,
            sender='system'
        )
        await self.broadcast(message, room)
    
    async def send_event_to_client(self, client_id: str, event: BaseEvent):
        """
        Send event to specific client
        """
        if client_id in self.connections:
            await self.connections[client_id].send_event(event)
    
    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IDs"""
        return list(self.connections.keys())
    
    def get_clients_in_room(self, room: str) -> List[str]:
        """Get clients in a room"""
        return self.rooms.get(room, [])
    
    def get_connection_status(self, client_id: str) -> Optional[str]:
        """Get connection status"""
        if client_id in self.connections:
            return self.connections[client_id].status.value
        return None
    
    async def authenticate_client(
        self,
        client_id: str,
        user_id: str,
        token: str
    ) -> bool:
        """
        Authenticate client
        """
        if client_id not in self.connections:
            return False
        
        # Validate token (in production, use proper JWT validation)
        if token in self.auth_tokens:
            self.connections[client_id].user_id = user_id
            self.connections[client_id].user_info = self.auth_tokens[token]
            self.connections[client_id].status = ConnectionStatus.AUTHENTICATED
            
            await self.connections[client_id].send(WebSocketMessage(
                type='authenticated',
                data={'user_id': user_id, 'status': 'authenticated'},
                sender='system'
            ))
            
            logger.info(f"🔐 Client {client_id} authenticated as {user_id}")
            return True
        
        return False
    
    async def _authenticate(self, client_id: str, token: str):
        """
        Internal authentication
        """
        # Simple token validation
        if token.startswith('valid_token_'):
            user_id = token.split('_')[2]
            self.auth_tokens[token] = {'user_id': user_id, 'valid': True}
            await self.authenticate_client(client_id, user_id, token)
    
    async def _handle_heartbeat(self, client_id: str, message: WebSocketMessage):
        """
        Handle heartbeat message
        """
        if client_id in self.connections:
            self.connections[client_id].update_heartbeat()
            
            # Send heartbeat response
            await self.connections[client_id].send(WebSocketMessage(
                type='heartbeat_ack',
                data={'timestamp': datetime.now().isoformat()},
                sender='system'
            ))
    
    async def _handle_subscribe(self, client_id: str, message: WebSocketMessage):
        """
        Handle subscription
        """
        if client_id not in self.connections:
            return
        
        event_types = message.data.get('event_types', [])
        
        for event_type in event_types:
            try:
                event_enum = EventType(event_type)
                if event_type not in self.event_subscribers:
                    self.event_subscribers[event_type] = []
                self.event_subscribers[event_type].append(client_id)
                self.connections[client_id].subscriptions.add(event_enum)
            except ValueError:
                await self.connections[client_id].send(WebSocketMessage(
                    type='error',
                    data={'message': f'Invalid event type: {event_type}'},
                    sender='system'
                ))
        
        await self.connections[client_id].send(WebSocketMessage(
            type='subscribed',
            data={'event_types': event_types},
            sender='system'
        ))
    
    async def _handle_unsubscribe(self, client_id: str, message: WebSocketMessage):
        """
        Handle unsubscription
        """
        if client_id not in self.connections:
            return
        
        event_types = message.data.get('event_types', [])
        
        for event_type in event_types:
            try:
                event_enum = EventType(event_type)
                if event_type in self.event_subscribers:
                    if client_id in self.event_subscribers[event_type]:
                        self.event_subscribers[event_type].remove(client_id)
                self.connections[client_id].subscriptions.discard(event_enum)
            except ValueError:
                pass
        
        await self.connections[client_id].send(WebSocketMessage(
            type='unsubscribed',
            data={'event_types': event_types},
            sender='system'
        ))
    
    async def _handle_event(self, client_id: str, message: WebSocketMessage):
        """
        Handle custom event
        """
        # Create event
        event = BaseEvent(
            type=EventType.CUSTOM,
            category=EventCategory.USER,
            source=client_id,
            data=message.data,
            priority=EventPriority.NORMAL,
            metadata={'client_id': client_id}
        )
        
        # Emit event
        self.event_manager.emit(event)
    
    async def _handle_broadcast(self, client_id: str, message: WebSocketMessage):
        """
        Handle broadcast request
        """
        room = message.data.get('room')
        broadcast_message = WebSocketMessage(
            type=message.data.get('message_type', 'broadcast'),
            data=message.data.get('data', {}),
            sender=client_id,
            room=room
        )
        
        await self.broadcast(broadcast_message, room, exclude=[client_id])
    
    def _start_heartbeat(self):
        """Start heartbeat monitoring"""
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("💓 Heartbeat monitoring started")
    
    async def _heartbeat_loop(self):
        """Heartbeat monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = datetime.now()
                disconnected = []
                
                # Check all connections
                for client_id, connection in self.connections.items():
                    elapsed = (current_time - connection.last_heartbeat).total_seconds()
                    
                    # Disconnect if no heartbeat for 2 intervals
                    if elapsed > self.heartbeat_interval * 2:
                        disconnected.append(client_id)
                
                # Disconnect stale connections
                for client_id in disconnected:
                    try:
                        await self.disconnect(client_id, code=1001, reason="Heartbeat timeout")
                        logger.warning(f"💀 Client {client_id} disconnected due to heartbeat timeout")
                    except Exception as e:
                        logger.error(f"Failed to disconnect {client_id}: {e}")
                
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    def get_room_stats(self) -> Dict[str, Any]:
        """Get room statistics"""
        return {
            'total_connections': len(self.connections),
            'total_rooms': len(self.rooms),
            'rooms': {
                room: len(clients)
                for room, clients in self.rooms.items()
            }
        }
    
    def get_event_stats(self) -> Dict[str, Any]:
        """Get event statistics"""
        return {
            'total_events': self.event_manager.stats.total_events,
            'events_by_type': self.event_manager.stats.events_by_type,
            'events_by_priority': self.event_manager.stats.events_by_priority,
            'events_per_second': self.event_manager.stats.events_per_second
        }