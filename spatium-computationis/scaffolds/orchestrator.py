"""
Protocol Orchestrator — Unified Protocol Management  ⎔

The Orchestrator coordinates all protocols:
- Manages the flow: Ingressus → Compressio → Ordinatio → Actio → Reductus → Feedback
- Provides instrumentation and observability
- Handles errors and retries
- Emits events at each stage

Glyphs:
  ⎔ Orchestrator — coordinates all protocols
  ⇨ Flow         — directed sequence of operations
  ⟲ Loop         — feedback cycles
"""

from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..schemas import (
    ActionResult,
    IntelligenceObject,
    ProjectInput,
    RawInput,
    RoutingDecision,
)
from .event_bus import (
    Event,
    EventType,
    EventPriority,
    emit_event,
)


# ---------------------------------------------------------------------------
# Orchestrator Configuration
# ---------------------------------------------------------------------------

class OrchestratorConfig(BaseModel):
    """Configuration for the protocol orchestrator."""
    # Timeouts
    ingressus_timeout_seconds: float = 30.0
    compressio_timeout_seconds: float = 30.0
    ordinatio_timeout_seconds: float = 10.0
    actio_timeout_seconds: float = 120.0
    feedback_timeout_seconds: float = 10.0
    
    # Retries
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Feature flags
    emit_events: bool = True
    record_feedback: bool = True
    enable_learning: bool = True
    
    # Parallelism
    max_concurrent_requests: int = 50
    
    # Quality thresholds
    min_confidence_threshold: float = 0.3  # Below this, request human review


# ---------------------------------------------------------------------------
# Orchestration Results
# ---------------------------------------------------------------------------

class ProtocolStage(str, Enum):
    """Stages in the protocol pipeline."""
    RECEIVED = "received"
    INGRESSUS = "ingressus"
    COMPRESSIO = "compressio"
    ORDINATIO = "ordinatio"
    ACTIO = "actio"
    REDUCTUS = "reductus"
    FEEDBACK = "feedback"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageResult:
    """Result of a single protocol stage."""
    stage: ProtocolStage
    success: bool
    duration_ms: float
    output: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """Complete result of orchestrating a request."""
    request_id: str
    correlation_id: str
    
    # Inputs
    raw_input: RawInput
    
    # Stage results
    stages: list[StageResult] = field(default_factory=list)
    
    # Final outputs
    project_input: ProjectInput | None = None
    intelligence_object: IntelligenceObject | None = None
    routing_decision: RoutingDecision | None = None
    action_result: ActionResult | None = None
    
    # Timing
    total_duration_ms: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    
    # Status
    current_stage: ProtocolStage = ProtocolStage.RECEIVED
    success: bool = False
    error_message: str | None = None
    
    def add_stage(self, result: StageResult) -> None:
        """Add a stage result."""
        self.stages.append(result)
        self.current_stage = result.stage
        if not result.success:
            self.error_message = result.error


# ---------------------------------------------------------------------------
# Protocol Orchestrator
# ---------------------------------------------------------------------------

class ProtocolOrchestrator:
    """Orchestrates the flow of requests through all protocols."""
    
    def __init__(self, config: OrchestratorConfig | None = None):
        self.config = config or OrchestratorConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
    
    async def orchestrate(self, raw: RawInput) -> OrchestrationResult:
        """
        Orchestrate a request through all protocols.
        
        Flow: Ingressus → Compressio → Ordinatio → Actio → [Reductus] → Feedback
        """
        async with self._semaphore:
            return await self._execute_pipeline(raw)
    
    async def _execute_pipeline(self, raw: RawInput) -> OrchestrationResult:
        """Execute the full protocol pipeline."""
        request_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        
        result = OrchestrationResult(
            request_id=request_id,
            correlation_id=correlation_id,
            raw_input=raw,
        )
        
        # Emit start event
        if self.config.emit_events:
            await emit_event(
                EventType.INPUT_RECEIVED,
                payload={
                    "request_id": request_id,
                    "input_type": raw.input_type.value,
                    "project_id": raw.project_id,
                },
                source_module="orchestrator",
                correlation_id=correlation_id,
                project_id=raw.project_id,
            )
        
        try:
            # Stage 1: Ingressus
            stage_result = await self._run_stage(
                ProtocolStage.INGRESSUS,
                self._run_ingressus,
                raw,
                self.config.ingressus_timeout_seconds,
                correlation_id,
            )
            result.add_stage(stage_result)
            
            if not stage_result.success:
                return self._finalize_result(result, start_time, success=False)
            
            result.project_input = stage_result.output
            
            # Stage 2: Compressio
            stage_result = await self._run_stage(
                ProtocolStage.COMPRESSIO,
                self._run_compressio,
                result.project_input,
                self.config.compressio_timeout_seconds,
                correlation_id,
            )
            result.add_stage(stage_result)
            
            if not stage_result.success:
                return self._finalize_result(result, start_time, success=False)
            
            result.intelligence_object = stage_result.output
            
            # Stage 3: Ordinatio
            stage_result = await self._run_stage(
                ProtocolStage.ORDINATIO,
                self._run_ordinatio,
                result.intelligence_object,
                self.config.ordinatio_timeout_seconds,
                correlation_id,
            )
            result.add_stage(stage_result)
            
            if not stage_result.success:
                return self._finalize_result(result, start_time, success=False)
            
            result.routing_decision = stage_result.output
            
            # Emit routing event
            if self.config.emit_events:
                await emit_event(
                    EventType.ROUTING_DECIDED,
                    payload={
                        "request_id": request_id,
                        "target_agent": result.routing_decision.target_agent,
                        "action": result.routing_decision.action.value,
                        "priority": result.routing_decision.priority,
                    },
                    source_module="orchestrator",
                    correlation_id=correlation_id,
                    project_id=raw.project_id,
                )
            
            # Stage 4: Actio
            stage_result = await self._run_stage(
                ProtocolStage.ACTIO,
                self._run_actio,
                (result.routing_decision, result.intelligence_object),
                self.config.actio_timeout_seconds,
                correlation_id,
            )
            result.add_stage(stage_result)
            
            if not stage_result.success:
                return self._finalize_result(result, start_time, success=False)
            
            result.action_result = stage_result.output
            
            # Emit completion event
            if self.config.emit_events:
                await emit_event(
                    EventType.ACTION_COMPLETED,
                    payload={
                        "request_id": request_id,
                        "action_id": result.action_result.action_id,
                        "agent": result.action_result.agent,
                        "summary": result.action_result.result_summary,
                    },
                    source_module="orchestrator",
                    correlation_id=correlation_id,
                    project_id=raw.project_id,
                )
            
            # Stage 5: Feedback (if enabled)
            if self.config.record_feedback:
                await self._record_initial_feedback(result, correlation_id)
            
            return self._finalize_result(result, start_time, success=True)
            
        except Exception as e:
            result.error_message = str(e)
            
            if self.config.emit_events:
                await emit_event(
                    EventType.ACTION_FAILED,
                    payload={
                        "request_id": request_id,
                        "error": str(e),
                        "stage": result.current_stage.value,
                        "traceback": traceback.format_exc(),
                    },
                    source_module="orchestrator",
                    priority=EventPriority.HIGH,
                    correlation_id=correlation_id,
                    project_id=raw.project_id,
                )
            
            return self._finalize_result(result, start_time, success=False)
    
    async def _run_stage(
        self,
        stage: ProtocolStage,
        func,
        input_data: Any,
        timeout: float,
        correlation_id: str,
    ) -> StageResult:
        """Run a single protocol stage with timing and error handling."""
        start_time = time.perf_counter()
        
        try:
            output = await asyncio.wait_for(
                func(input_data),
                timeout=timeout,
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return StageResult(
                stage=stage,
                success=True,
                duration_ms=duration_ms,
                output=output,
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=f"Stage {stage.value} timed out after {timeout}s",
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
                metadata={"traceback": traceback.format_exc()},
            )
    
    async def _run_ingressus(self, raw: RawInput) -> ProjectInput:
        """Run Ingressus protocol."""
        from ..protocols import ingressus
        return await ingressus.process(raw)
    
    async def _run_compressio(self, project_input: ProjectInput) -> IntelligenceObject:
        """Run Compressio protocol."""
        from ..protocols import compressio
        return await compressio.compress(project_input)
    
    async def _run_ordinatio(self, intel: IntelligenceObject) -> RoutingDecision:
        """Run Ordinatio protocol."""
        from ..protocols import ordinatio
        return await ordinatio.route(intel)
    
    async def _run_actio(self, inputs: tuple) -> ActionResult:
        """Run Actio protocol."""
        decision, intel = inputs
        from ..protocols import actio
        return await actio.execute(decision, intel)
    
    def _finalize_result(
        self,
        result: OrchestrationResult,
        start_time: float,
        success: bool,
    ) -> OrchestrationResult:
        """Finalize the orchestration result."""
        result.total_duration_ms = (time.perf_counter() - start_time) * 1000
        result.completed_at = datetime.now(timezone.utc)
        result.success = success
        result.current_stage = ProtocolStage.COMPLETED if success else ProtocolStage.FAILED
        return result
    
    async def _record_initial_feedback(
        self,
        result: OrchestrationResult,
        correlation_id: str,
    ) -> None:
        """Record initial feedback for the completed action."""
        if not result.action_result or not result.routing_decision:
            return
        
        from ..protocols.feedback import record_outcome, OutcomeType
        
        # Initial outcome is "unknown" until human feedback or system verification
        record_outcome(
            action_id=result.action_result.action_id,
            agent=result.action_result.agent,
            action_type=result.action_result.action_type.value,
            outcome_type=OutcomeType.UNKNOWN,
            quality_score=result.intelligence_object.confidence if result.intelligence_object else 0.5,
            project_id=result.raw_input.project_id,
            input_features={
                "input_type": result.raw_input.input_type.value,
                "glyph": result.intelligence_object.glyph if result.intelligence_object else None,
                "region": result.intelligence_object.region.value if result.intelligence_object else None,
            },
            decision_features={
                "target_agent": result.routing_decision.target_agent,
                "action": result.routing_decision.action.value,
                "priority": result.routing_decision.priority,
                "reasoning": result.routing_decision.reasoning,
            },
        )


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

# Global orchestrator instance
_global_orchestrator: ProtocolOrchestrator | None = None


def get_orchestrator(config: OrchestratorConfig | None = None) -> ProtocolOrchestrator:
    """Get or create the global orchestrator."""
    global _global_orchestrator
    if _global_orchestrator is None or config is not None:
        _global_orchestrator = ProtocolOrchestrator(config)
    return _global_orchestrator


async def orchestrate_request(raw: RawInput) -> OrchestrationResult:
    """Convenience function to orchestrate a request."""
    return await get_orchestrator().orchestrate(raw)
