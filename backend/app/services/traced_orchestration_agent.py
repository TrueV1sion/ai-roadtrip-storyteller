"""
Enhanced Master Orchestration Agent with distributed tracing.

This module shows how to integrate OpenTelemetry tracing into the
existing orchestration system for complete observability.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.services.master_orchestration_agent import MasterOrchestrationAgent
from backend.app.core.tracing import (
    get_tracer, trace_method, add_span_attributes, 
    add_span_event, get_current_trace_id
)
from backend.app.core.logger import get_logger
from opentelemetry import trace

logger = get_logger(__name__)


class TracedMasterOrchestrationAgent(MasterOrchestrationAgent):
    """
    Enhanced orchestration agent with distributed tracing capabilities.
    
    This extends the existing MasterOrchestrationAgent to add:
    - Span creation for each agent interaction
    - Trace propagation across sub-agents
    - Performance metrics collection
    - Error tracking and correlation
    """
    
    def __init__(self):
        super().__init__()
        self.tracer = get_tracer()
    
    @trace_method(
        name="orchestration.process_request",
        attributes={"agent.type": "master_orchestrator"}
    )
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user request with full tracing across all sub-agents.
        """
        span = trace.get_current_span()
        trace_id = get_current_trace_id()
        
        # Add request metadata to span
        add_span_attributes({
            "user.id": request.get("user_id", "anonymous"),
            "request.type": request.get("type", "voice"),
            "journey.origin": request.get("context", {}).get("origin", ""),
            "journey.destination": request.get("context", {}).get("destination", ""),
            "trace.id": trace_id
        })
        
        # Log with trace ID for correlation
        logger.info(f"Processing request with trace_id={trace_id}")
        
        try:
            # Analyze intent with tracing
            with self.tracer.start_as_current_span("orchestration.analyze_intent") as intent_span:
                intent_result = await self._analyze_intent(request)
                intent_span.set_attribute("intent.primary", intent_result["primary_intent"])
                intent_span.set_attribute("intent.confidence", intent_result["confidence"])
                add_span_event("Intent analysis completed", {
                    "intents": str(intent_result["intents"])
                })
            
            # Route to sub-agents with parallel tracing
            with self.tracer.start_as_current_span("orchestration.route_to_agents") as routing_span:
                agent_tasks = self._create_agent_tasks(intent_result, request)
                routing_span.set_attribute("agent.count", len(agent_tasks))
                
                # Execute agents in parallel with individual spans
                agent_results = await self._execute_agents_with_tracing(agent_tasks)
                
                add_span_event("Agent routing completed", {
                    "successful_agents": len([r for r in agent_results if r.get("success")])
                })
            
            # Synthesize response with tracing
            with self.tracer.start_as_current_span("orchestration.synthesize_response") as synthesis_span:
                final_response = await self._synthesize_response(
                    intent_result, 
                    agent_results, 
                    request
                )
                synthesis_span.set_attribute("response.length", len(final_response.get("text", "")))
                synthesis_span.set_attribute("response.has_audio", bool(final_response.get("audio_url")))
            
            # Add final metrics
            span.set_attribute("processing.success", True)
            span.set_attribute("processing.duration_ms", 
                             (datetime.utcnow() - datetime.fromisoformat(
                                 request.get("timestamp", datetime.utcnow().isoformat())
                             )).total_seconds() * 1000)
            
            return {
                "success": True,
                "trace_id": trace_id,
                "request_id": request.get("request_id"),
                "response": final_response,
                "agent_results": agent_results,
                "processing_metrics": {
                    "intent_analysis_ms": intent_result.get("processing_time", 0),
                    "agent_execution_ms": sum(r.get("processing_time", 0) for r in agent_results),
                    "total_ms": (datetime.utcnow() - datetime.fromisoformat(
                        request.get("timestamp", datetime.utcnow().isoformat())
                    )).total_seconds() * 1000
                }
            }
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logger.error(f"Error in orchestration (trace_id={trace_id}): {str(e)}")
            raise
    
    async def _execute_agents_with_tracing(
        self, 
        agent_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute agent tasks with individual tracing spans."""
        
        async def execute_with_span(task: Dict[str, Any]) -> Dict[str, Any]:
            agent_name = task["agent"]
            
            with self.tracer.start_as_current_span(
                f"agent.{agent_name}",
                attributes={
                    "agent.name": agent_name,
                    "agent.priority": task.get("priority", 5)
                }
            ) as span:
                try:
                    start_time = datetime.utcnow()
                    
                    # Execute agent
                    result = await self._execute_agent(task)
                    
                    # Add metrics
                    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    span.set_attribute("agent.processing_time_ms", processing_time)
                    span.set_attribute("agent.success", result.get("success", False))
                    
                    if result.get("success"):
                        add_span_event(f"{agent_name} completed successfully")
                    else:
                        add_span_event(f"{agent_name} failed", {
                            "error": result.get("error", "Unknown error")
                        })
                    
                    result["processing_time"] = processing_time
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    return {
                        "agent": agent_name,
                        "success": False,
                        "error": str(e)
                    }
        
        # Execute all agents in parallel
        results = await asyncio.gather(
            *[execute_with_span(task) for task in agent_tasks],
            return_exceptions=True
        )
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "agent": agent_tasks[i]["agent"],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    @trace_method(name="orchestration.analyze_intent")
    async def _analyze_intent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent with tracing."""
        # This would normally use AI to analyze intent
        # For now, return a traced mock result
        
        add_span_event("Analyzing user input", {
            "input_length": len(request.get("user_input", ""))
        })
        
        # Simulate AI processing
        await asyncio.sleep(0.1)
        
        result = {
            "primary_intent": "navigation",
            "confidence": 0.95,
            "intents": ["navigation", "story", "booking"],
            "processing_time": 100
        }
        
        add_span_attributes({
            "intent.primary": result["primary_intent"],
            "intent.confidence": result["confidence"]
        })
        
        return result
    
    async def _execute_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single agent task with tracing context propagation."""
        agent_name = task["agent"]
        
        # Add trace context to agent request
        task["request"]["trace_id"] = get_current_trace_id()
        
        # This would call the actual agent
        # For demonstration, simulate agent execution
        await asyncio.sleep(0.2)
        
        return {
            "agent": agent_name,
            "success": True,
            "data": {
                "message": f"Response from {agent_name}",
                "recommendations": ["Sample recommendation"]
            }
        }
    
    @trace_method(name="orchestration.synthesize_response")
    async def _synthesize_response(
        self,
        intent_result: Dict[str, Any],
        agent_results: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize final response with tracing."""
        
        add_span_event("Synthesizing response from agents", {
            "agent_count": len(agent_results),
            "successful_agents": len([r for r in agent_results if r.get("success")])
        })
        
        # Simulate response synthesis
        await asyncio.sleep(0.05)
        
        response = {
            "text": "Based on your request, here's what I found...",
            "personality": request.get("context", {}).get("personality", "enthusiastic_guide"),
            "suggestions": [],
            "audio_url": None
        }
        
        # Aggregate suggestions from agents
        for result in agent_results:
            if result.get("success") and "recommendations" in result.get("data", {}):
                response["suggestions"].extend(result["data"]["recommendations"])
        
        add_span_attributes({
            "response.suggestion_count": len(response["suggestions"]),
            "response.has_audio": bool(response.get("audio_url"))
        })
        
        return response