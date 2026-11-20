import sys

sys.path.insert(0, "/app")

from src.rag.monitoring import record

record(
    component="demo_setup",
    model_name="none",
    model_version="1",
    prompt_version="none",
    latency_ms=0,
    status="ready"
)

print("Telemetry initialized successfully")
