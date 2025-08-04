"""
OpenTelemetry instrumentation for backend services
"""

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    
    HAS_OPENTELEMETRY = True
    
    # Configure tracer
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint="otel-collector:4317",
        insecure=True
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Auto-instrument libraries
    FastAPIInstrumentor.instrument()
    RequestsInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    RedisInstrumentor.instrument()
    
except ImportError:
    HAS_OPENTELEMETRY = False
    tracer = None


def setup_tracing(app=None):
    """Setup tracing for the application."""
    if HAS_OPENTELEMETRY:
        # Tracing is already set up above
        pass
    else:
        # No-op when opentelemetry is not available
        pass


class TraceContextMiddleware:
    """Middleware to propagate trace context."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """Process the request."""
        # Simply pass through when opentelemetry is not available
        await self.app(scope, receive, send)