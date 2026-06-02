"""
Protocol: Synchronizatio — State Synchronization  🔄

Manages state synchronization between agents, services, and clients.
Ensures eventual consistency across distributed components.

Glyph: 🔄
Latin: Synchronizatio
Meaning: bringing into alignment

Features:
  - State versioning with vector clocks
  - Conflict detection and resolution strategies
  - Incremental sync (delta-only transfers)
  - Snapshot creation and restoration
  - Multi-party state reconciliation
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ConflictStrategy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"


class SyncStatus(str, Enum):
    IN_SYNC = "in_sync"
    PENDING = "pending"
    CONFLICTED = "conflicted"
    SYNCING = "syncing"


class VectorClock(BaseModel):
    """Vector clock for causality tracking."""
    clocks: dict[str, int] = Field(default_factory=dict)

    def increment(self, node_id: str):
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1

    def merge(self, other: "VectorClock"):
        for node_id, count in other.clocks.items():
            self.clocks[node_id] = max(self.clocks.get(node_id, 0), count)

    def is_concurrent_with(self, other: "VectorClock") -> bool:
        """Check if two vector clocks are concurrent (neither dominates)."""
        self_dominates = False
        other_dominates = False
        all_keys = set(self.clocks.keys()) | set(other.clocks.keys())
        for key in all_keys:
            s = self.clocks.get(key, 0)
            o = other.clocks.get(key, 0)
            if s > o:
                self_dominates = True
            elif o > s:
                other_dominates = True
        return self_dominates and other_dominates

    def dominates(self, other: "VectorClock") -> bool:
        """Check if this clock dominates (happened after) another."""
        dominated = False
        for key in set(self.clocks.keys()) | set(other.clocks.keys()):
            s = self.clocks.get(key, 0)
            o = other.clocks.get(key, 0)
            if s < o:
                return False
            if s > o:
                dominated = True
        return dominated


class StateDelta(BaseModel):
    """A change delta between two state versions."""
    delta_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node: str
    path: str
    operation: str  # "set", "delete", "append", "remove"
    value: Any = None
    version: int
    vector_clock: VectorClock
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StateSnapshot(BaseModel):
    """A full snapshot of state at a point in time."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str
    state: dict[str, Any]
    version: int
    vector_clock: VectorClock
    checksum: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncConflict(BaseModel):
    """A detected synchronization conflict."""
    conflict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str
    path: str
    local_value: Any = None
    remote_value: Any = None
    local_clock: VectorClock
    remote_clock: VectorClock
    resolved: bool = False
    resolution: Any = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncState(BaseModel):
    """Synchronization state for a resource."""
    resource_id: str
    state: dict[str, Any] = Field(default_factory=dict)
    version: int = 0
    vector_clock: VectorClock = Field(default_factory=VectorClock)
    status: SyncStatus = SyncStatus.IN_SYNC
    pending_deltas: list[StateDelta] = Field(default_factory=list)
    conflicts: list[SyncConflict] = Field(default_factory=list)
    last_sync: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

_sync_states: dict[str, SyncState] = {}
_snapshots: dict[str, list[StateSnapshot]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_sync_state(
    resource_id: str,
    initial_state: dict[str, Any] | None = None,
    strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS,
) -> SyncState:
    """Create a new synchronization state for a resource."""
    sync = SyncState(
        resource_id=resource_id,
        state=initial_state or {},
        strategy=strategy,
    )
    _sync_states[resource_id] = sync
    return sync


def apply_delta(
    resource_id: str,
    source_node: str,
    path: str,
    operation: str,
    value: Any = None,
) -> StateDelta:
    """Apply a state change delta."""
    sync = _sync_states.get(resource_id)
    if not sync:
        raise ValueError(f"No sync state for resource '{resource_id}'")

    sync.vector_clock.increment(source_node)
    sync.version += 1

    # Apply to state
    keys = path.split(".")
    current = sync.state
    for key in keys[:-1]:
        current = current.setdefault(key, {})

    if operation == "set":
        current[keys[-1]] = value
    elif operation == "delete":
        current.pop(keys[-1], None)
    elif operation == "append":
        if keys[-1] not in current:
            current[keys[-1]] = []
        current[keys[-1]].append(value)
    elif operation == "remove":
        if keys[-1] in current and isinstance(current[keys[-1]], list):
            try:
                current[keys[-1]].remove(value)
            except ValueError:
                pass

    delta = StateDelta(
        source_node=source_node,
        path=path,
        operation=operation,
        value=value,
        version=sync.version,
        vector_clock=copy.deepcopy(sync.vector_clock),
    )

    sync.pending_deltas.append(delta)
    sync.last_sync = datetime.now(timezone.utc)

    return delta


def receive_delta(resource_id: str, delta: StateDelta) -> SyncConflict | None:
    """Receive a delta from a remote node and detect conflicts."""
    sync = _sync_states.get(resource_id)
    if not sync:
        raise ValueError(f"No sync state for resource '{resource_id}'")

    # Check for conflict
    if sync.vector_clock.is_concurrent_with(delta.vector_clock):
        conflict = SyncConflict(
            resource_id=resource_id,
            path=delta.path,
            local_value=_get_value_at_path(sync.state, delta.path),
            remote_value=delta.value,
            local_clock=copy.deepcopy(sync.vector_clock),
            remote_clock=copy.deepcopy(delta.vector_clock),
        )
        sync.conflicts.append(conflict)
        sync.status = SyncStatus.CONFLICTED

        # Auto-resolve if strategy allows
        if sync.strategy == ConflictStrategy.LAST_WRITE_WINS:
            _resolve_lww(sync, conflict, delta)
        elif sync.strategy == ConflictStrategy.FIRST_WRITE_WINS:
            conflict.resolved = True
            conflict.resolution = conflict.local_value

        return conflict

    # No conflict — apply directly
    _apply_delta_to_state(sync, delta)
    sync.vector_clock.merge(delta.vector_clock)
    sync.version = max(sync.version, delta.version)
    sync.last_sync = datetime.now(timezone.utc)
    sync.status = SyncStatus.IN_SYNC

    return None


def create_snapshot(resource_id: str) -> StateSnapshot:
    """Create a snapshot of the current state."""
    sync = _sync_states.get(resource_id)
    if not sync:
        raise ValueError(f"No sync state for resource '{resource_id}'")

    checksum = hashlib.sha256(
        json.dumps(sync.state, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    snapshot = StateSnapshot(
        resource_id=resource_id,
        state=copy.deepcopy(sync.state),
        version=sync.version,
        vector_clock=copy.deepcopy(sync.vector_clock),
        checksum=checksum,
    )

    if resource_id not in _snapshots:
        _snapshots[resource_id] = []
    _snapshots[resource_id].append(snapshot)

    # Clear pending deltas after snapshot
    sync.pending_deltas = []

    return snapshot


def restore_snapshot(resource_id: str, snapshot_id: str) -> bool:
    """Restore state from a snapshot."""
    snapshots = _snapshots.get(resource_id, [])
    snapshot = next((s for s in snapshots if s.snapshot_id == snapshot_id), None)
    if not snapshot:
        return False

    sync = _sync_states.get(resource_id)
    if not sync:
        return False

    sync.state = copy.deepcopy(snapshot.state)
    sync.version = snapshot.version
    sync.vector_clock = copy.deepcopy(snapshot.vector_clock)
    sync.pending_deltas = []
    sync.conflicts = []
    sync.status = SyncStatus.IN_SYNC

    return True


def get_sync_state(resource_id: str) -> SyncState | None:
    """Get current sync state for a resource."""
    return _sync_states.get(resource_id)


def get_pending_deltas(resource_id: str) -> list[StateDelta]:
    """Get pending deltas that haven't been acknowledged."""
    sync = _sync_states.get(resource_id)
    if not sync:
        return []
    return sync.pending_deltas


def get_conflicts(resource_id: str) -> list[SyncConflict]:
    """Get unresolved conflicts."""
    sync = _sync_states.get(resource_id)
    if not sync:
        return []
    return [c for c in sync.conflicts if not c.resolved]


def resolve_conflict(
    resource_id: str,
    conflict_id: str,
    resolution: Any,
) -> bool:
    """Manually resolve a conflict."""
    sync = _sync_states.get(resource_id)
    if not sync:
        return False

    for conflict in sync.conflicts:
        if conflict.conflict_id == conflict_id and not conflict.resolved:
            conflict.resolved = True
            conflict.resolution = resolution
            # Apply resolution to state
            keys = conflict.path.split(".")
            current = sync.state
            for key in keys[:-1]:
                current = current.setdefault(key, {})
            current[keys[-1]] = resolution

            # Check if all conflicts resolved
            if not any(not c.resolved for c in sync.conflicts):
                sync.status = SyncStatus.IN_SYNC

            return True
    return False


def get_snapshots(resource_id: str) -> list[StateSnapshot]:
    """Get all snapshots for a resource."""
    return _snapshots.get(resource_id, [])


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _get_value_at_path(state: dict, path: str) -> Any:
    """Get a value at a dotted path."""
    keys = path.split(".")
    current = state
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _apply_delta_to_state(sync: SyncState, delta: StateDelta):
    """Apply a delta to the state."""
    keys = delta.path.split(".")
    current = sync.state
    for key in keys[:-1]:
        current = current.setdefault(key, {})

    if delta.operation == "set":
        current[keys[-1]] = delta.value
    elif delta.operation == "delete":
        current.pop(keys[-1], None)
    elif delta.operation == "append":
        if keys[-1] not in current:
            current[keys[-1]] = []
        current[keys[-1]].append(delta.value)
    elif delta.operation == "remove":
        if keys[-1] in current and isinstance(current[keys[-1]], list):
            try:
                current[keys[-1]].remove(delta.value)
            except ValueError:
                pass


def _resolve_lww(sync: SyncState, conflict: SyncConflict, delta: StateDelta):
    """Resolve conflict using last-write-wins strategy."""
    # Remote timestamp wins if later
    if delta.timestamp >= sync.last_sync:
        _apply_delta_to_state(sync, delta)
        conflict.resolved = True
        conflict.resolution = delta.value
    else:
        conflict.resolved = True
        conflict.resolution = conflict.local_value
