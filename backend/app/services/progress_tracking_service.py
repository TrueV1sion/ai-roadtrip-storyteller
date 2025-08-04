"""
Progress Tracking Service with Voice Integration
Implements Six Sigma methodology for team progress tracking
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import json
import asyncio
from uuid import uuid4

from ..models.progress_tracking import ProgressNote, TeamMember, TaskProgress
from ..schemas.progress_tracking import (
    ProgressNoteCreate,
    ProgressNoteUpdate,
    ProgressNoteResponse,
    TeamMemberCreate,
    TaskProgressCreate,
    ProgressAnalytics
)
from ..core.logging_config import logger
from ..integrations.knowledge_graph import KnowledgeGraphClient
from ..services.voice_services import VoiceServices
from ..services.master_orchestration_agent import MasterOrchestrationAgent


class ProgressTrackingService:
    """
    FAANG-level progress tracking service with voice integration
    
    Features:
    - Voice-activated progress notes
    - Real-time team collaboration
    - Knowledge graph integration
    - Analytics and insights
    - Six Sigma metrics tracking
    """
    
    def __init__(self):
        self.kg_client = KnowledgeGraphClient()
        self.voice_service = VoiceServices()
        self.orchestrator = MasterOrchestrationAgent()
        self.websocket_connections: Dict[str, Any] = {}
        
    async def create_progress_note(
        self,
        db: Session,
        note_data: ProgressNoteCreate,
        user_id: str
    ) -> ProgressNoteResponse:
        """Create a new progress note with knowledge graph integration"""
        try:
            # Create progress note
            progress_note = ProgressNote(
                id=str(uuid4()),
                user_id=user_id,
                task_id=note_data.task_id,
                content=note_data.content,
                note_type=note_data.note_type,
                metadata=note_data.metadata or {},
                voice_transcript=note_data.voice_transcript,
                emotion_state=note_data.emotion_state,
                created_at=datetime.utcnow()
            )
            
            db.add(progress_note)
            db.commit()
            db.refresh(progress_note)
            
            # Store in knowledge graph
            await self._store_in_knowledge_graph(progress_note)
            
            # Broadcast to team members
            await self._broadcast_progress_update(progress_note)
            
            # Analyze for insights
            insights = await self._analyze_progress_note(progress_note)
            
            logger.info(f"Created progress note: {progress_note.id}")
            
            return ProgressNoteResponse(
                **progress_note.__dict__,
                insights=insights
            )
            
        except Exception as e:
            logger.error(f"Error creating progress note: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create progress note: {str(e)}"
            )
    
    async def create_voice_progress_note(
        self,
        db: Session,
        audio_data: bytes,
        user_id: str,
        task_id: Optional[str] = None
    ) -> ProgressNoteResponse:
        """Create progress note from voice input"""
        try:
            # Transcribe audio
            transcript = await self.voice_service.transcribe_audio(audio_data)
            
            # Extract emotion from voice
            emotion_analysis = await self.voice_service.analyze_emotion(audio_data)
            
            # Parse intent and extract task context
            intent_data = await self._parse_voice_intent(transcript)
            
            # Create progress note
            note_data = ProgressNoteCreate(
                task_id=task_id or intent_data.get('task_id'),
                content=transcript,
                note_type=intent_data.get('type', 'update'),
                voice_transcript=transcript,
                emotion_state=emotion_analysis,
                metadata={
                    'voice_generated': True,
                    'intent': intent_data,
                    'confidence': emotion_analysis.get('confidence', 0.0)
                }
            )
            
            return await self.create_progress_note(db, note_data, user_id)
            
        except Exception as e:
            logger.error(f"Error creating voice progress note: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process voice input: {str(e)}"
            )
    
    async def get_progress_notes(
        self,
        db: Session,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProgressNoteResponse]:
        """Get progress notes with filtering"""
        try:
            query = db.query(ProgressNote)
            
            if task_id:
                query = query.filter(ProgressNote.task_id == task_id)
            if user_id:
                query = query.filter(ProgressNote.user_id == user_id)
            
            notes = query.order_by(
                ProgressNote.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            # Enrich with insights
            enriched_notes = []
            for note in notes:
                insights = await self._get_cached_insights(note.id)
                enriched_notes.append(
                    ProgressNoteResponse(
                        **note.__dict__,
                        insights=insights
                    )
                )
            
            return enriched_notes
            
        except Exception as e:
            logger.error(f"Error fetching progress notes: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch progress notes: {str(e)}"
            )
    
    async def get_team_progress_analytics(
        self,
        db: Session,
        team_id: str,
        days: int = 7
    ) -> ProgressAnalytics:
        """Get team progress analytics with Six Sigma metrics"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Get team members
            team_members = db.query(TeamMember).filter(
                TeamMember.team_id == team_id
            ).all()
            
            member_ids = [member.user_id for member in team_members]
            
            # Get progress notes
            notes = db.query(ProgressNote).filter(
                ProgressNote.user_id.in_(member_ids),
                ProgressNote.created_at >= since_date
            ).all()
            
            # Calculate metrics
            analytics = {
                'total_notes': len(notes),
                'notes_per_day': len(notes) / days if days > 0 else 0,
                'active_contributors': len(set(note.user_id for note in notes)),
                'task_coverage': len(set(note.task_id for note in notes if note.task_id)),
                'sentiment_analysis': await self._analyze_team_sentiment(notes),
                'velocity_trend': await self._calculate_velocity_trend(notes, days),
                'collaboration_score': await self._calculate_collaboration_score(notes),
                'six_sigma_metrics': {
                    'dpmo': self._calculate_dpmo(notes),  # Defects per million opportunities
                    'cycle_time': self._calculate_cycle_time(notes),
                    'yield': self._calculate_yield(notes),
                    'sigma_level': self._calculate_sigma_level(notes)
                }
            }
            
            return ProgressAnalytics(**analytics)
            
        except Exception as e:
            logger.error(f"Error calculating analytics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate analytics: {str(e)}"
            )
    
    async def _store_in_knowledge_graph(self, note: ProgressNote):
        """Store progress note in knowledge graph"""
        try:
            # Create node for progress note
            node_data = {
                'id': note.id,
                'type': 'progress_note',
                'content': note.content,
                'user_id': note.user_id,
                'task_id': note.task_id,
                'timestamp': note.created_at.isoformat(),
                'metadata': note.metadata
            }
            
            await self.kg_client.create_node(node_data)
            
            # Link to task if exists
            if note.task_id:
                await self.kg_client.create_edge(
                    source_id=note.id,
                    target_id=note.task_id,
                    edge_type='updates_task'
                )
            
            # Link to user
            await self.kg_client.create_edge(
                source_id=note.user_id,
                target_id=note.id,
                edge_type='created_note'
            )
            
        except Exception as e:
            logger.error(f"Error storing in knowledge graph: {str(e)}")
    
    async def _broadcast_progress_update(self, note: ProgressNote):
        """Broadcast progress update to connected team members"""
        try:
            update_message = {
                'type': 'progress_update',
                'data': {
                    'note_id': note.id,
                    'user_id': note.user_id,
                    'task_id': note.task_id,
                    'content': note.content,
                    'timestamp': note.created_at.isoformat()
                }
            }
            
            # Send to all connected websockets
            for connection_id, websocket in self.websocket_connections.items():
                try:
                    await websocket.send_json(update_message)
                except Exception as e:
                    # Remove disconnected clients
                    del self.websocket_connections[connection_id]
                    
        except Exception as e:
            logger.error(f"Error broadcasting update: {str(e)}")
    
    async def _analyze_progress_note(self, note: ProgressNote) -> Dict[str, Any]:
        """Analyze progress note for insights"""
        try:
            insights = {
                'sentiment': 'neutral',
                'urgency': 'normal',
                'categories': [],
                'suggested_actions': [],
                'related_tasks': []
            }
            
            # Use orchestrator for analysis
            analysis_prompt = f"""
            Analyze this progress note and provide insights:
            Content: {note.content}
            
            Extract:
            1. Sentiment (positive/neutral/negative)
            2. Urgency level (low/normal/high/critical)
            3. Categories/tags
            4. Suggested follow-up actions
            5. Related tasks mentioned
            """
            
            response = await self.orchestrator.process_request(
                user_input=analysis_prompt,
                context={'note_type': 'progress_analysis'}
            )
            
            # Parse response and update insights
            if response.get('analysis'):
                insights.update(response['analysis'])
            
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing progress note: {str(e)}")
            return {}
    
    async def _parse_voice_intent(self, transcript: str) -> Dict[str, Any]:
        """Parse voice transcript to extract intent and context"""
        try:
            intent_prompt = f"""
            Parse this voice transcript for progress tracking:
            "{transcript}"
            
            Extract:
            1. Type of update (progress/blocker/completed/question)
            2. Task reference if mentioned
            3. Key entities (people, features, issues)
            4. Action items if any
            
            Return as structured data.
            """
            
            response = await self.orchestrator.process_request(
                user_input=intent_prompt,
                context={'note_type': 'voice_intent_parsing'}
            )
            
            return response.get('intent_data', {
                'type': 'update',
                'entities': [],
                'actions': []
            })
            
        except Exception as e:
            logger.error(f"Error parsing voice intent: {str(e)}")
            return {'type': 'update'}
    
    async def _analyze_team_sentiment(self, notes: List[ProgressNote]) -> Dict[str, float]:
        """Analyze overall team sentiment from notes"""
        sentiments = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        for note in notes:
            if note.emotion_state:
                emotion = note.emotion_state.get('primary', 'neutral')
                if emotion in ['joy', 'excitement', 'satisfaction']:
                    sentiments['positive'] += 1
                elif emotion in ['frustration', 'concern', 'stress']:
                    sentiments['negative'] += 1
                else:
                    sentiments['neutral'] += 1
        
        total = sum(sentiments.values()) or 1
        return {k: v / total for k, v in sentiments.items()}
    
    async def _calculate_velocity_trend(self, notes: List[ProgressNote], days: int) -> List[float]:
        """Calculate velocity trend over time"""
        daily_counts = {}
        
        for note in notes:
            date_key = note.created_at.date()
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        # Create trend for each day
        trend = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            trend.append(daily_counts.get(date, 0))
        
        trend.reverse()  # Oldest to newest
        return trend
    
    async def _calculate_collaboration_score(self, notes: List[ProgressNote]) -> float:
        """Calculate team collaboration score (0-100)"""
        if not notes:
            return 0.0
        
        # Factors: unique contributors, cross-references, response time
        unique_users = len(set(note.user_id for note in notes))
        total_notes = len(notes)
        
        # Basic collaboration score
        score = min(100, (unique_users / max(total_notes * 0.3, 1)) * 100)
        
        # Boost for notes referencing other tasks/people
        cross_references = sum(
            1 for note in notes 
            if '@' in note.content or 'task:' in note.content
        )
        score += min(20, (cross_references / total_notes) * 20)
        
        return min(100, score)
    
    def _calculate_dpmo(self, notes: List[ProgressNote]) -> float:
        """Calculate Defects Per Million Opportunities"""
        # Define defect as negative sentiment or blocker type
        defects = sum(
            1 for note in notes 
            if note.note_type == 'blocker' or 
            (note.emotion_state and note.emotion_state.get('primary') in ['frustration', 'stress'])
        )
        
        opportunities = len(notes) * 5  # 5 quality criteria per note
        
        if opportunities == 0:
            return 0.0
        
        return (defects / opportunities) * 1_000_000
    
    def _calculate_cycle_time(self, notes: List[ProgressNote]) -> float:
        """Calculate average cycle time between updates"""
        if len(notes) < 2:
            return 0.0
        
        sorted_notes = sorted(notes, key=lambda x: x.created_at)
        time_gaps = []
        
        for i in range(1, len(sorted_notes)):
            gap = (sorted_notes[i].created_at - sorted_notes[i-1].created_at).total_seconds() / 3600
            time_gaps.append(gap)
        
        return sum(time_gaps) / len(time_gaps) if time_gaps else 0.0
    
    def _calculate_yield(self, notes: List[ProgressNote]) -> float:
        """Calculate process yield (successful updates)"""
        if not notes:
            return 0.0
        
        successful = sum(
            1 for note in notes 
            if note.note_type in ['completed', 'progress'] and
            (not note.emotion_state or note.emotion_state.get('primary') not in ['frustration', 'stress'])
        )
        
        return (successful / len(notes)) * 100
    
    def _calculate_sigma_level(self, notes: List[ProgressNote]) -> float:
        """Calculate Six Sigma level based on DPMO"""
        dpmo = self._calculate_dpmo(notes)
        
        # Simplified sigma level calculation
        if dpmo <= 3.4:
            return 6.0
        elif dpmo <= 233:
            return 5.0
        elif dpmo <= 6210:
            return 4.0
        elif dpmo <= 66807:
            return 3.0
        elif dpmo <= 308537:
            return 2.0
        else:
            return 1.0
    
    async def _get_cached_insights(self, note_id: str) -> Dict[str, Any]:
        """Get cached insights for a note"""
        # In production, implement Redis caching
        return {}