"""
Distributed Tracing Configuration
Production setup for OpenTelemetry with Jaeger
"""

import os
from typing import Optional

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    trace = None
    TracerProvider = None
    Resource = None
    SERVICE_NAME = None
    SERVICE_VERSION = None
    JaegerExporter = None
    OTLPSpanExporter = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None
    FastAPIInstrumentor = None
    SQLAlchemyInstrumentor = None
    RedisInstrumentor = None
    CeleryInstrumentor = None
    RequestsInstrumentor = None
    HTTPXClientInstrumentor = None
    AsyncioInstrumentor = None
    TraceContextTextMapPropagator = None
    set_global_textmap = None

if HAS_OPENTELEMETRY:
    from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.propagate import set_global_textmap

from app.core.logger import get_logger

logger = get_logger(__name__)


class TracingConfig:
    """Manages distributed tracing configuration."""
    
    def __init__(self):
        self.enabled = os.environ.get('TRACING_ENABLED', 'true').lower() == 'true'
        self.service_name = os.environ.get('SERVICE_NAME', 'roadtrip-api')
        self.service_version = os.environ.get('SERVICE_VERSION', '1.0.0')
        self.environment = os.environ.get('ENVIRONMENT', 'development')
        self.jaeger_endpoint = os.environ.get('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces')
        self.otlp_endpoint = os.environ.get('OTLP_ENDPOINT', 'http://localhost:4317')
        self.export_type = os.environ.get('TRACE_EXPORT_TYPE', 'jaeger')  # jaeger, otlp, console
        self.sample_rate = float(os.environ.get('TRACE_SAMPLE_RATE', '1.0'))  # 1.0 = 100%
        
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
    
    def setup_tracing(self, app=None):
        """Initialize distributed tracing."""
        if not self.enabled:
            logger.info("Tracing disabled")
            return
        
        try:
            # Create resource with service information
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "service.environment": self.environment,
                "service.instance.id": os.environ.get('HOSTNAME', 'unknown'),
                "telemetry.sdk.name": "opentelemetry",
                "telemetry.sdk.language": "python",
                "worker.id": str(os.getpid())
            })
            
            # Create tracer provider
            self.tracer_provider = TracerProvider(
                resource=resource,
                active_span_processor=None  # Will add processors
            )
            
            # Configure exporter based on type
            if self.export_type == 'jaeger':
                exporter = JaegerExporter(
                    agent_host_name=self._extract_host(self.jaeger_endpoint),
                    agent_port=6831,  # UDP port
                    collector_endpoint=self.jaeger_endpoint,
                )
            elif self.export_type == 'otlp':
                exporter = OTLPSpanExporter(
                    endpoint=self.otlp_endpoint,
                    insecure=True  # For local development
                )
            else:
                # Console exporter for debugging
                exporter = ConsoleSpanExporter()
            
            # Add span processor
            span_processor = BatchSpanProcessor(
                exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                max_export_interval_millis=5000,
            )
            self.tracer_provider.add_span_processor(span_processor)
            
            # Set as global tracer provider
            trace.set_tracer_provider(self.tracer_provider)
            
            # Set up propagator
            set_global_textmap(TraceContextTextMapPropagator())
            
            # Get tracer
            self.tracer = trace.get_tracer(
                self.service_name,
                self.service_version
            )
            
            # Auto-instrument libraries
            self._setup_auto_instrumentation(app)
            
            logger.info(
                f"Tracing initialized: {self.export_type} exporter, "
                f"sample rate: {self.sample_rate * 100}%"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            self.enabled = False
    
    def _setup_auto_instrumentation(self, app=None):
        """Set up automatic instrumentation for libraries."""
        try:
            # FastAPI instrumentation
            if app:
                FastAPIInstrumentor.instrument_app(
                    app,
                    excluded_urls="/metrics,/health.*,/docs,/openapi.json"
                )
            
            # SQLAlchemy instrumentation
            SQLAlchemyInstrumentor().instrument(
                enable_commenter=True,
                commenter_options={}
            )
            
            # Redis instrumentation
            RedisInstrumentor().instrument(
                trace_provider=self.tracer_provider
            )
            
            # Celery instrumentation
            CeleryInstrumentor().instrument(
                trace_provider=self.tracer_provider
            )
            
            # HTTP client instrumentation
            RequestsInstrumentor().instrument(
                trace_provider=self.tracer_provider
            )
            
            HTTPXClientInstrumentor().instrument(
                trace_provider=self.tracer_provider
            )
            
            # Asyncio instrumentation (optional - can be noisy)
            if os.environ.get('TRACE_ASYNCIO', 'false').lower() == 'true':
                AsyncioInstrumentor().instrument(
                    trace_provider=self.tracer_provider
                )
            
            logger.info("Auto-instrumentation completed")
            
        except Exception as e:
            logger.error(f"Auto-instrumentation failed: {e}")
    
    def _extract_host(self, url: str) -> str:
        """Extract host from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.hostname or 'localhost'
        except Exception as e:
            return 'localhost'
    
    def create_span(self, name: str, kind=None):
        """Create a new span."""
        if kind is None and HAS_OPENTELEMETRY:
            kind = trace.SpanKind.INTERNAL
            
        if not self.enabled or not self.tracer:
            if HAS_OPENTELEMETRY:
                return trace.get_tracer(__name__).start_span(name)  # No-op span
            else:
                from contextlib import nullcontext
                return nullcontext()
        
        return self.tracer.start_span(name, kind=kind)
    
    def get_current_span(self):
        """Get the current active span."""
        return trace.get_current_span()
    
    def shutdown(self):
        """Shutdown tracing and flush remaining spans."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Tracing shutdown complete")


# Global tracing configuration
if HAS_OPENTELEMETRY:
    tracing_config = TracingConfig()
else:
    tracing_config = None


# Convenience functions
def init_tracing(app=None):
    """Initialize tracing system."""
    if HAS_OPENTELEMETRY and tracing_config:
        tracing_config.setup_tracing(app)
    else:
        logger.info("OpenTelemetry not available, tracing disabled")


def create_span(name: str, kind=None):
    """Create a new span."""
    if HAS_OPENTELEMETRY and tracing_config:
        if kind is None:
            kind = trace.SpanKind.INTERNAL
        return tracing_config.create_span(name, kind)
    else:
        # Return a no-op context manager
        from contextlib import nullcontext
        return nullcontext()


def get_current_span():
    """Get current span."""
    if HAS_OPENTELEMETRY and tracing_config:
        return tracing_config.get_current_span()
    else:
        return None


# Export components
__all__ = [
    'tracing_config',
    'init_tracing',
    'create_span',
    'get_current_span'
]