"""
Base agent class for code analysis agents
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
import json


@dataclass
class AgentMessage:
    """Message between agents"""
    id: str
    from_agent: str
    to_agent: Optional[str]  # None for broadcast
    message_type: str  # observation, question, answer, plan, warning
    content: Dict[str, Any]
    timestamp: datetime
    in_reply_to: Optional[str] = None


@dataclass
class AgentTask:
    """Task assigned to an agent"""
    id: str
    type: str
    priority: int  # 1-10, 10 highest
    assigned_to: str
    created_by: str
    status: str  # pending, in_progress, completed, failed
    data: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """Base class for all knowledge graph agents"""
    
    def __init__(self, agent_id: str, agent_type: str, knowledge_graph_db):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.db = knowledge_graph_db
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, AgentTask] = {}
        self.capabilities: List[str] = []
        self.state: Dict[str, Any] = {}
        self.running = False
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a specific task - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def analyze_node(self, node_id: str) -> Dict[str, Any]:
        """Analyze a specific node - must be implemented by subclasses"""
        pass
    
    async def start(self):
        """Start the agent"""
        self.running = True
        await asyncio.gather(
            self._process_messages(),
            self._process_tasks()
        )
    
    async def stop(self):
        """Stop the agent"""
        self.running = False
    
    async def _process_messages(self):
        """Process incoming messages"""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
    
    async def _process_tasks(self):
        """Process assigned tasks"""
        while self.running:
            try:
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # Update task status
                task.status = "in_progress"
                self.active_tasks[task.id] = task
                
                # Process the task
                try:
                    result = await self.process_task(task)
                    task.status = "completed"
                    task.result = result
                    task.completed_at = datetime.now()
                    
                    # Store result in knowledge graph
                    await self._store_task_result(task)
                    
                except Exception as e:
                    task.status = "failed"
                    task.result = {"error": str(e)}
                    await self._log_error(task, e)
                
                finally:
                    del self.active_tasks[task.id]
                    
            except asyncio.TimeoutError:
                continue
    
    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        if message.message_type == "question":
            # Answer if we can
            answer = await self._try_answer_question(message)
            if answer:
                await self.send_message(
                    to_agent=message.from_agent,
                    message_type="answer",
                    content=answer,
                    in_reply_to=message.id
                )
        
        elif message.message_type == "observation":
            # Store observation
            await self._store_observation(message)
        
        elif message.message_type == "plan":
            # Consider plan in our own planning
            self.state['peer_plans'] = self.state.get('peer_plans', [])
            self.state['peer_plans'].append(message)
    
    async def send_message(self, to_agent: Optional[str], message_type: str, 
                          content: Dict[str, Any], in_reply_to: Optional[str] = None):
        """Send message to another agent or broadcast"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(),
            in_reply_to=in_reply_to
        )
        
        # In real implementation, this would use a message broker
        # For now, we'll store in the knowledge graph
        await self._store_message(message)
    
    async def create_task(self, task_type: str, assigned_to: str, 
                         data: Dict[str, Any], priority: int = 5) -> AgentTask:
        """Create a task for another agent"""
        task = AgentTask(
            id=str(uuid.uuid4()),
            type=task_type,
            priority=priority,
            assigned_to=assigned_to,
            created_by=self.agent_id,
            status="pending",
            data=data,
            created_at=datetime.now()
        )
        
        # In real implementation, this would use a task queue
        # For now, we'll store in the knowledge graph
        await self._store_task(task)
        
        return task
    
    async def leave_note(self, node_id: str, note: str, note_type: str = "observation"):
        """Leave a note on a code node for other agents"""
        self.db.add_agent_note(
            agent_id=self.agent_id,
            node_id=node_id,
            note=note,
            note_type=note_type
        )
    
    async def get_peer_notes(self, node_id: str) -> List[Dict[str, Any]]:
        """Get notes from other agents about a node"""
        notes = self.db.get_agent_notes(node_id=node_id)
        return [note for note in notes if note['agent_id'] != self.agent_id]
    
    async def _try_answer_question(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """Try to answer a question based on our knowledge"""
        # Override in subclasses with specific expertise
        return None
    
    async def _store_observation(self, message: AgentMessage):
        """Store an observation in the knowledge graph"""
        # Implementation depends on message content
        pass
    
    async def _store_message(self, message: AgentMessage):
        """Store message in knowledge graph"""
        # In production, this would use a proper message queue
        pass
    
    async def _store_task(self, task: AgentTask):
        """Store task in knowledge graph"""
        # In production, this would use a proper task queue
        pass
    
    async def _store_task_result(self, task: AgentTask):
        """Store task result in knowledge graph"""
        # Implementation depends on task type and result
        pass
    
    async def _log_error(self, task: AgentTask, error: Exception):
        """Log error for failed task"""
        error_note = f"Task {task.id} failed: {str(error)}"
        # Store error in knowledge graph
        pass