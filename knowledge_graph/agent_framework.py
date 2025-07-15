"""
Knowledge Graph Agent Orchestration Framework
Implements autonomous agents for proactive code analysis and integration
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentPriority(Enum):
    """Priority levels for agent tasks"""
    CRITICAL = 1  # Blocking issues
    HIGH = 2      # Important but not blocking
    MEDIUM = 3    # Should be addressed
    LOW = 4       # Nice to have


class AgentStatus(Enum):
    """Agent lifecycle status"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    ALERTING = "alerting"
    LEARNING = "learning"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Standard message format for inter-agent communication"""
    sender: str
    recipient: str
    message_type: str
    payload: Dict[str, Any]
    priority: AgentPriority
    timestamp: datetime = None
    correlation_id: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now()


@dataclass
class AnalysisResult:
    """Standard result format for agent analysis"""
    agent_name: str
    analysis_type: str
    severity: str  # critical, high, medium, low
    findings: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class BaseAgent(ABC):
    """Base class for all Knowledge Graph agents"""
    
    def __init__(self, name: str, kg_server):
        self.name = name
        self.kg_server = kg_server
        self.status = AgentStatus.IDLE
        self.message_queue = asyncio.Queue()
        self.running = False
        self.logger = logging.getLogger(f"Agent.{name}")
        
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Perform agent-specific analysis"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages from other agents"""
        pass
    
    async def start(self):
        """Start the agent's main loop"""
        self.running = True
        self.logger.info(f"Starting agent: {self.name}")
        
        # Start message handler
        asyncio.create_task(self._message_handler())
        
        # Start agent-specific tasks
        await self._start_tasks()
    
    async def stop(self):
        """Stop the agent"""
        self.running = False
        self.logger.info(f"Stopping agent: {self.name}")
    
    async def send_message(self, recipient: str, message_type: str, 
                          payload: Dict[str, Any], priority: AgentPriority = AgentPriority.MEDIUM):
        """Send message to another agent"""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            priority=priority
        )
        
        # Route through orchestrator
        await self.kg_server.agent_orchestrator.route_message(message)
    
    async def _message_handler(self):
        """Process incoming messages"""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                await self.handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error handling message: {e}")
    
    async def _start_tasks(self):
        """Override to start agent-specific background tasks"""
        pass


class FileWatcherAgent(BaseAgent):
    """Monitors file changes and triggers impact analysis"""
    
    def __init__(self, kg_server):
        super().__init__("FileWatcher", kg_server)
        self.watched_files: Set[str] = set()
        self.file_hashes: Dict[str, str] = {}
        
    async def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze file change impact"""
        file_path = data.get("file_path")
        change_type = data.get("change_type", "modified")
        
        # Get impact analysis from KG
        impact = await self._get_impact_analysis(file_path)
        
        # Determine severity
        severity = self._calculate_severity(impact)
        
        # Generate findings
        findings = []
        if impact["dependencies"]:
            findings.append({
                "type": "dependencies",
                "message": f"This change affects {len(impact['dependencies'])} dependent files",
                "files": impact["dependencies"]
            })
        
        # Generate suggestions
        suggestions = []
        if severity in ["critical", "high"]:
            suggestions.append({
                "type": "test",
                "message": "Run comprehensive tests before committing",
                "commands": ["pytest -xvs tests/"]
            })
        
        return AnalysisResult(
            agent_name=self.name,
            analysis_type="file_change_impact",
            severity=severity,
            findings=findings,
            suggestions=suggestions,
            metadata={"file_path": file_path, "change_type": change_type}
        )
    
    async def handle_message(self, message: AgentMessage):
        """Handle file monitoring requests"""
        if message.message_type == "watch_file":
            file_path = message.payload.get("file_path")
            self.watched_files.add(file_path)
            self.logger.info(f"Now watching: {file_path}")
            
        elif message.message_type == "file_changed":
            result = await self.analyze(message.payload)
            
            # Notify other agents based on severity
            if result.severity in ["critical", "high"]:
                await self.send_message(
                    "ImpactAnalyzer",
                    "deep_analysis_required",
                    {"file_path": message.payload["file_path"], "result": result},
                    AgentPriority.HIGH
                )
    
    async def _get_impact_analysis(self, file_path: str) -> Dict[str, Any]:
        """Get impact analysis from Knowledge Graph"""
        # Query the KG for dependencies
        response = await self.kg_server.analyze_impact({"node_id": file_path})
        return response
    
    def _calculate_severity(self, impact: Dict[str, Any]) -> str:
        """Calculate severity based on impact"""
        dep_count = len(impact.get("dependencies", []))
        
        if dep_count > 20:
            return "critical"
        elif dep_count > 10:
            return "high"
        elif dep_count > 5:
            return "medium"
        else:
            return "low"


class CommitGuardAgent(BaseAgent):
    """Validates commits before they're allowed"""
    
    def __init__(self, kg_server):
        super().__init__("CommitGuard", kg_server)
        self.blocked_patterns = []
        self.validation_rules = []
        
    async def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze commit for issues"""
        changed_files = data.get("changed_files", [])
        commit_message = data.get("commit_message", "")
        
        findings = []
        suggestions = []
        
        # Check each file
        for file_path in changed_files:
            # Check for breaking changes
            breaking = await self._check_breaking_changes(file_path)
            if breaking:
                findings.extend(breaking)
            
            # Check for pattern violations
            violations = await self._check_pattern_violations(file_path)
            if violations:
                findings.extend(violations)
        
        # Determine severity
        severity = "low"
        if any(f.get("type") == "breaking_change" for f in findings):
            severity = "critical"
        elif findings:
            severity = "high"
        
        # Generate suggestions
        if severity == "critical":
            suggestions.append({
                "type": "block_commit",
                "message": "This commit contains breaking changes and should be reviewed",
                "action": "Request code review before proceeding"
            })
        
        return AnalysisResult(
            agent_name=self.name,
            analysis_type="commit_validation",
            severity=severity,
            findings=findings,
            suggestions=suggestions,
            metadata={"file_count": len(changed_files)}
        )
    
    async def handle_message(self, message: AgentMessage):
        """Handle commit validation requests"""
        if message.message_type == "validate_commit":
            result = await self.analyze(message.payload)
            
            # Send result back
            await self.send_message(
                message.sender,
                "validation_result",
                {"result": result, "correlation_id": message.correlation_id}
            )
            
            # If critical, alert other agents
            if result.severity == "critical":
                await self.send_message(
                    "AlertManager",
                    "critical_issue",
                    {"issue": "Breaking changes detected", "details": result},
                    AgentPriority.CRITICAL
                )
    
    async def _check_breaking_changes(self, file_path: str) -> List[Dict[str, Any]]:
        """Check if changes break dependencies"""
        findings = []
        
        # Get dependencies from KG
        impact = await self.kg_server.analyze_impact({"node_id": file_path})
        
        # Check if any critical dependencies
        critical_deps = [d for d in impact.get("dependencies", []) 
                        if "test" in d or "core" in d or "main" in d]
        
        if critical_deps:
            findings.append({
                "type": "breaking_change",
                "message": f"Changes to {file_path} may break {len(critical_deps)} critical dependencies",
                "dependencies": critical_deps
            })
        
        return findings
    
    async def _check_pattern_violations(self, file_path: str) -> List[Dict[str, Any]]:
        """Check for pattern violations"""
        findings = []
        
        # Get similar files to check patterns
        similar = await self.kg_server.search_similar(file_path)
        
        # Analyze patterns (simplified for now)
        if similar and len(similar) > 3:
            # Check if this file follows established patterns
            # This is a simplified check - real implementation would be more sophisticated
            findings.append({
                "type": "pattern_check",
                "message": "Verify this follows established patterns",
                "similar_files": similar[:3]
            })
        
        return findings


class PatternEnforcerAgent(BaseAgent):
    """Ensures code follows established patterns"""
    
    def __init__(self, kg_server):
        super().__init__("PatternEnforcer", kg_server)
        self.learned_patterns = {}
        
    async def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze code for pattern compliance"""
        file_path = data.get("file_path")
        code_content = data.get("content", "")
        
        findings = []
        suggestions = []
        
        # Find similar files
        similar_files = await self.kg_server.search_similar(file_path)
        
        if similar_files:
            # Check for pattern deviations
            patterns = await self._extract_patterns(similar_files)
            violations = self._check_pattern_compliance(code_content, patterns)
            
            if violations:
                findings.extend(violations)
                suggestions.append({
                    "type": "pattern_fix",
                    "message": "Consider following established patterns",
                    "examples": similar_files[:2]
                })
        
        severity = "medium" if findings else "low"
        
        return AnalysisResult(
            agent_name=self.name,
            analysis_type="pattern_compliance",
            severity=severity,
            findings=findings,
            suggestions=suggestions,
            metadata={"similar_files_found": len(similar_files)}
        )
    
    async def handle_message(self, message: AgentMessage):
        """Handle pattern analysis requests"""
        if message.message_type == "check_patterns":
            result = await self.analyze(message.payload)
            
            await self.send_message(
                message.sender,
                "pattern_analysis_result",
                {"result": result}
            )
        
        elif message.message_type == "learn_pattern":
            # Learn new pattern from good code
            await self._learn_pattern(message.payload)
    
    async def _extract_patterns(self, files: List[str]) -> Dict[str, Any]:
        """Extract common patterns from files"""
        # Simplified pattern extraction
        patterns = {
            "imports": [],
            "class_structure": [],
            "function_patterns": []
        }
        
        # In real implementation, would analyze AST of files
        return patterns
    
    def _check_pattern_compliance(self, content: str, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if content follows patterns"""
        violations = []
        
        # Simplified check - real implementation would use AST analysis
        if "import" in content and not any("import" in p for p in patterns.get("imports", [])):
            violations.append({
                "type": "pattern_violation",
                "message": "Import style differs from established patterns",
                "severity": "low"
            })
        
        return violations
    
    async def _learn_pattern(self, data: Dict[str, Any]):
        """Learn new pattern from example"""
        pattern_type = data.get("type")
        pattern_data = data.get("pattern")
        
        if pattern_type not in self.learned_patterns:
            self.learned_patterns[pattern_type] = []
        
        self.learned_patterns[pattern_type].append(pattern_data)
        self.logger.info(f"Learned new {pattern_type} pattern")


class SuggestionEngine(BaseAgent):
    """Provides intelligent code suggestions"""
    
    def __init__(self, kg_server):
        super().__init__("SuggestionEngine", kg_server)
        
    async def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Generate suggestions for code improvement"""
        context = data.get("context", {})
        request_type = data.get("type", "general")
        
        suggestions = []
        
        if request_type == "similar_implementation":
            # Find similar implementations
            similar = await self.kg_server.search_similar(context.get("current_file"))
            if similar:
                suggestions.append({
                    "type": "reference",
                    "message": "Similar implementations found",
                    "files": similar[:3]
                })
        
        elif request_type == "pattern_match":
            # Suggest patterns
            suggestions.append({
                "type": "pattern",
                "message": "Consider using established patterns",
                "pattern": "Repository pattern for data access"
            })
        
        return AnalysisResult(
            agent_name=self.name,
            analysis_type="suggestions",
            severity="low",
            findings=[],
            suggestions=suggestions,
            metadata={"request_type": request_type}
        )
    
    async def handle_message(self, message: AgentMessage):
        """Handle suggestion requests"""
        if message.message_type == "get_suggestions":
            result = await self.analyze(message.payload)
            
            await self.send_message(
                message.sender,
                "suggestions",
                {"result": result}
            )


class AgentOrchestrator:
    """Orchestrates all Knowledge Graph agents"""
    
    def __init__(self, kg_server):
        self.kg_server = kg_server
        self.agents: Dict[str, BaseAgent] = {}
        self.message_bus = asyncio.Queue()
        self.running = False
        self.logger = logging.getLogger("AgentOrchestrator")
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agents"""
        self.agents["FileWatcher"] = FileWatcherAgent(self.kg_server)
        self.agents["CommitGuard"] = CommitGuardAgent(self.kg_server)
        self.agents["PatternEnforcer"] = PatternEnforcerAgent(self.kg_server)
        self.agents["SuggestionEngine"] = SuggestionEngine(self.kg_server)
        
        self.logger.info(f"Initialized {len(self.agents)} agents")
    
    async def start(self):
        """Start all agents"""
        self.running = True
        self.logger.info("Starting Agent Orchestrator")
        
        # Start message router
        asyncio.create_task(self._message_router())
        
        # Start all agents
        for agent in self.agents.values():
            await agent.start()
        
        self.logger.info("All agents started")
    
    async def stop(self):
        """Stop all agents"""
        self.running = False
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        self.logger.info("All agents stopped")
    
    async def route_message(self, message: AgentMessage):
        """Route message to appropriate agent"""
        await self.message_bus.put(message)
    
    async def _message_router(self):
        """Route messages between agents"""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_bus.get(),
                    timeout=1.0
                )
                
                # Route to recipient
                if message.recipient in self.agents:
                    await self.agents[message.recipient].message_queue.put(message)
                elif message.recipient == "broadcast":
                    # Send to all agents
                    for agent in self.agents.values():
                        if agent.name != message.sender:
                            await agent.message_queue.put(message)
                else:
                    self.logger.warning(f"Unknown recipient: {message.recipient}")
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error routing message: {e}")
    
    async def request_analysis(self, analysis_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Request analysis from appropriate agents"""
        results = []
        
        if analysis_type == "file_change":
            # File change analysis
            agent = self.agents["FileWatcher"]
            result = await agent.analyze(data)
            results.append(result)
            
            # Also check patterns
            pattern_result = await self.agents["PatternEnforcer"].analyze(data)
            results.append(pattern_result)
            
        elif analysis_type == "pre_commit":
            # Pre-commit validation
            result = await self.agents["CommitGuard"].analyze(data)
            results.append(result)
        
        # Aggregate results
        max_severity = max(results, key=lambda r: ["low", "medium", "high", "critical"].index(r.severity))
        
        return {
            "analysis_type": analysis_type,
            "severity": max_severity.severity,
            "results": [r.__dict__ for r in results],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            agent_name: {
                "status": agent.status.value,
                "running": agent.running
            }
            for agent_name, agent in self.agents.items()
        }