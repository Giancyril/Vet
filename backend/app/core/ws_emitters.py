"""
WebSocket telemetry emission helpers for the review pipeline.
Wraps ws_manager.broadcast_review_event with structured payloads.
"""
from app.core.websocket import ws_manager


async def emit_agent_started(review_id: str, agent: str, description: str):
    await ws_manager.broadcast_review_event(review_id, "agent_started", {
        "agent": agent,
        "description": description,
    })


async def emit_secret_scanned(review_id: str, secret_count: int, secrets_found: list):
    await ws_manager.broadcast_review_event(review_id, "secret_scanned", {
        "secrets_found": secrets_found,
        "count": secret_count,
    })


async def emit_ast_analyzed(review_id: str, breaking_changes: int, complexity_flags: int):
    await ws_manager.broadcast_review_event(review_id, "ast_analyzed", {
        "breaking_changes": breaking_changes,
        "complexity_flags": complexity_flags,
    })


async def emit_finding_discovered(review_id: str, severity: str, title: str, file: str):
    await ws_manager.broadcast_review_event(review_id, "finding_discovered", {
        "severity": severity,
        "title": title,
        "file": file,
    })


async def emit_health_calculated(review_id: str, score: float, grade: str):
    await ws_manager.broadcast_review_event(review_id, "health_calculated", {
        "score": score,
        "grade": grade,
    })


async def emit_review_finished(review_id: str, verdict: str, total_findings: int, duration_ms: float):
    await ws_manager.broadcast_review_event(review_id, "review_finished", {
        "verdict": verdict,
        "total_findings": total_findings,
        "duration_ms": duration_ms,
    })
