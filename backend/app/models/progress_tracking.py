"""
Database models for progress tracking system
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Enum, Float, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class NoteType(str, enum.Enum):
    """Types of progress notes"""
    UPDATE = "update"
    PROGRESS = "progress"
    BLOCKER = "blocker"
    COMPLETED = "completed"
    QUESTION = "question"
    INSIGHT = "insight"
    MILESTONE = "milestone"


class ProgressNote(Base):
    """Progress note model for tracking team updates"""
    __tablename__ = "progress_notes"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, nullable=True, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    note_type = Column(Enum(NoteType), default=NoteType.UPDATE)
    
    # Voice integration
    voice_transcript = Column(Text, nullable=True)
    emotion_state = Column(JSON, nullable=True)  # {primary: 'joy', intensity: 0.8, confidence: 0.9}
    audio_url = Column(String, nullable=True)
    
    # Metadata
    note_metadata = Column(JSON, default={})
    tags = Column(JSON, default=[])
    mentions = Column(JSON, default=[])  # [@user_id, @team_id]
    
    # Analytics
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    urgency_level = Column(Integer, default=0)  # 0-4 (normal to critical)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="progress_notes")
    task = relationship("Task", back_populates="progress_notes", foreign_keys=[task_id])
    team = relationship("Team", back_populates="progress_notes")
    reactions = relationship("ProgressReaction", back_populates="progress_note", cascade="all, delete-orphan")


class TeamMember(Base):
    """Team member model for collaboration tracking"""
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")  # member, lead, observer
    
    # Permissions
    can_create_notes = Column(JSON, default=True)
    can_edit_others = Column(JSON, default=False)
    can_delete = Column(JSON, default=False)
    
    # Activity tracking
    last_active = Column(DateTime, nullable=True)
    notes_created = Column(Integer, default=0)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class TaskProgress(Base):
    """Task progress tracking model"""
    __tablename__ = "task_progress"
    
    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    
    # Progress metrics
    completion_percentage = Column(Float, default=0.0)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, default=0.0)
    
    # Status tracking
    status = Column(String, default="not_started")  # not_started, in_progress, blocked, completed
    blockers = Column(JSON, default=[])
    
    # Milestones
    milestones = Column(JSON, default=[])  # [{name, target_date, completed_date, status}]
    
    # Quality metrics
    defects_found = Column(Integer, default=0)
    defects_resolved = Column(Integer, default=0)
    test_coverage = Column(Float, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="progress", uselist=False)
    updates = relationship("ProgressNote", secondary="task_progress_notes", back_populates="task_progress")


class ProgressReaction(Base):
    """Reactions to progress notes for team engagement"""
    __tablename__ = "progress_reactions"
    
    id = Column(String, primary_key=True, index=True)
    progress_note_id = Column(String, ForeignKey("progress_notes.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    reaction_type = Column(String, nullable=False)  # 👍, 🎉, 💪, ❓, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    progress_note = relationship("ProgressNote", back_populates="reactions")
    user = relationship("User")


class Team(Base):
    """Team model for grouping collaborators"""
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Team settings
    settings = Column(JSON, default={
        'daily_standup_time': None,
        'weekly_report_day': 'friday',
        'notification_preferences': {
            'new_notes': True,
            'mentions': True,
            'milestones': True
        }
    })
    
    # Analytics preferences
    track_velocity = Column(JSON, default=True)
    track_sentiment = Column(JSON, default=True)
    track_collaboration = Column(JSON, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    progress_notes = relationship("ProgressNote", back_populates="team")


class Task(Base):
    """Task model for tracking project tasks"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(String, nullable=False, index=True)
    assignee_id = Column(String, ForeignKey("users.id"), nullable=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    
    # Task attributes
    priority = Column(String, default="medium")  # low, medium, high, critical
    due_date = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    
    # Status and tracking
    status = Column(String, default="todo")  # todo, in_progress, review, done, cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    assignee = relationship("User", foreign_keys=[assignee_id])
    team = relationship("Team", foreign_keys=[team_id])
    progress_notes = relationship("ProgressNote", back_populates="task", foreign_keys="[ProgressNote.task_id]")
    progress = relationship("TaskProgress", back_populates="task", uselist=False)
    
    
# Association table for many-to-many relationship between TaskProgress and ProgressNote
from sqlalchemy import Table

task_progress_notes = Table(
    'task_progress_notes',
    Base.metadata,
    Column('task_progress_id', String, ForeignKey('task_progress.id')),
    Column('progress_note_id', String, ForeignKey('progress_notes.id'))
)