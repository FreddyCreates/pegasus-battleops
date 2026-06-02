"""
Protocol: Collaboratio — Real-Time Collaboration  🤝

Enables multiple users and agents to collaborate on projects simultaneously.
Manages presence, shared editing, conflict resolution, and live cursors.

Glyph: 🤝
Latin: Collaboratio
Meaning: working together in real-time

Features:
  - Session management (join/leave/presence)
  - Shared state with conflict resolution (last-write-wins + CRDT)
  - Broadcast changes to all participants
  - Role-based collaboration (viewer, editor, admin)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CollaborationRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class Participant(BaseModel):
    """A participant in a collaboration session."""
    participant_id: str
    user_id: str
    display_name: str
    role: CollaborationRole = CollaborationRole.EDITOR
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cursor_position: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollaborationSession(BaseModel):
    """A real-time collaboration session."""
    session_id: str
    project_id: str
    resource_type: str  # e.g., "estimate", "document", "punch_list"
    resource_id: str
    participants: list[Participant] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: dict[str, Any] = Field(default_factory=dict)
    version: int = 0
    locked_by: str | None = None


class ChangeOperation(BaseModel):
    """An atomic change operation for conflict resolution."""
    operation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    participant_id: str
    operation_type: str  # "set", "delete", "append", "increment"
    path: str  # JSON path to the changed field
    value: Any = None
    previous_value: Any = None
    version: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CollaborationEvent(BaseModel):
    """Event broadcast to all session participants."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    event_type: str  # "join", "leave", "change", "cursor", "lock", "unlock"
    participant_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Session Store
# ---------------------------------------------------------------------------

_sessions: dict[str, CollaborationSession] = {}
_event_queues: dict[str, list[asyncio.Queue]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_session(
    project_id: str,
    resource_type: str,
    resource_id: str,
    initial_state: dict[str, Any] | None = None,
) -> CollaborationSession:
    """Create a new collaboration session for a resource."""
    session = CollaborationSession(
        session_id=str(uuid.uuid4()),
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        state=initial_state or {},
    )
    _sessions[session.session_id] = session
    _event_queues[session.session_id] = []
    return session


def join_session(
    session_id: str,
    user_id: str,
    display_name: str,
    role: CollaborationRole = CollaborationRole.EDITOR,
) -> Participant:
    """Join an existing collaboration session."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found")

    participant = Participant(
        participant_id=str(uuid.uuid4()),
        user_id=user_id,
        display_name=display_name,
        role=role,
    )
    session.participants.append(participant)
    return participant


def leave_session(session_id: str, participant_id: str) -> bool:
    """Remove a participant from a session."""
    session = _sessions.get(session_id)
    if not session:
        return False

    session.participants = [
        p for p in session.participants if p.participant_id != participant_id
    ]

    # Clean up empty sessions
    if not session.participants:
        del _sessions[session_id]
        _event_queues.pop(session_id, None)

    return True


def apply_change(
    session_id: str,
    participant_id: str,
    operation_type: str,
    path: str,
    value: Any = None,
) -> ChangeOperation:
    """Apply a change operation to the shared state."""
    session = _sessions.get(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found")

    # Check lock
    if session.locked_by and session.locked_by != participant_id:
        raise PermissionError(f"Session locked by another participant")

    # Check permission
    participant = next(
        (p for p in session.participants if p.participant_id == participant_id),
        None,
    )
    if not participant:
        raise ValueError("Participant not in session")
    if participant.role == CollaborationRole.VIEWER:
        raise PermissionError("Viewers cannot make changes")

    # Get previous value
    keys = path.split(".")
    current = session.state
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    previous_value = current.get(keys[-1])

    # Apply operation
    if operation_type == "set":
        current[keys[-1]] = value
    elif operation_type == "delete":
        current.pop(keys[-1], None)
    elif operation_type == "append":
        if keys[-1] not in current:
            current[keys[-1]] = []
        current[keys[-1]].append(value)
    elif operation_type == "increment":
        current[keys[-1]] = current.get(keys[-1], 0) + (value or 1)

    session.version += 1

    operation = ChangeOperation(
        session_id=session_id,
        participant_id=participant_id,
        operation_type=operation_type,
        path=path,
        value=value,
        previous_value=previous_value,
        version=session.version,
    )

    return operation


def get_session(session_id: str) -> CollaborationSession | None:
    """Get session details."""
    return _sessions.get(session_id)


def get_active_sessions(project_id: str | None = None) -> list[CollaborationSession]:
    """List active collaboration sessions."""
    sessions = list(_sessions.values())
    if project_id:
        sessions = [s for s in sessions if s.project_id == project_id]
    return sessions


def lock_session(session_id: str, participant_id: str) -> bool:
    """Lock a session for exclusive editing."""
    session = _sessions.get(session_id)
    if not session:
        return False
    if session.locked_by:
        return False
    session.locked_by = participant_id
    return True


def unlock_session(session_id: str, participant_id: str) -> bool:
    """Unlock a session."""
    session = _sessions.get(session_id)
    if not session:
        return False
    if session.locked_by != participant_id:
        return False
    session.locked_by = None
    return True


def update_cursor(
    session_id: str,
    participant_id: str,
    position: dict[str, Any],
) -> bool:
    """Update a participant's cursor position for live cursors."""
    session = _sessions.get(session_id)
    if not session:
        return False

    for p in session.participants:
        if p.participant_id == participant_id:
            p.cursor_position = position
            p.last_active = datetime.now(timezone.utc)
            return True
    return False
