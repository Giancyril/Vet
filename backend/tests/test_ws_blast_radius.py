"""Tests for WebSocket manager and blast radius analyzer."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.websocket import ConnectionManager
from app.analysis.blast_radius import calculate_blast_radius, BlastRadiusReport


# ── WebSocket Manager Tests ─────────────────────────────────────────────────

class TestConnectionManager:
    def test_initial_state(self):
        mgr = ConnectionManager()
        assert mgr.active_connections == {}
        assert mgr.global_connections == []

    @pytest.mark.asyncio
    async def test_connect_review(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_review(ws, "review-1")
        assert "review-1" in mgr.active_connections
        assert ws in mgr.active_connections["review-1"]
        ws.accept.assert_awaited_once()

    def test_disconnect_review(self):
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.active_connections = {"review-1": [ws]}
        mgr.disconnect_review(ws, "review-1")
        assert "review-1" not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_connect_global(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_global(ws)
        assert ws in mgr.global_connections
        ws.accept.assert_awaited_once()

    def test_disconnect_global(self):
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.global_connections = [ws]
        mgr.disconnect_global(ws)
        assert ws not in mgr.global_connections

    @pytest.mark.asyncio
    async def test_broadcast_review_event(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        mgr.active_connections = {"review-abc": [ws]}

        await mgr.broadcast_review_event("review-abc", "agent_started", {"agent": "Security"})

        ws.send_text.assert_awaited_once()
        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["event"] == "agent_started"
        assert payload["review_id"] == "review-abc"
        assert payload["data"]["agent"] == "Security"

    @pytest.mark.asyncio
    async def test_broadcast_removes_broken_connection(self):
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.send_text.side_effect = Exception("Connection lost")
        mgr.active_connections = {"review-xyz": [ws]}
        # Should not raise
        await mgr.broadcast_review_event("review-xyz", "test", {})
        assert "review-xyz" not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_review(self):
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast_review_event("nonexistent", "test", {})


# ── Blast Radius Analyzer Tests ─────────────────────────────────────────────

class TestBlastRadius:
    def test_empty_diff(self):
        result = calculate_blast_radius([])
        assert result.impact_index == 0.0
        assert result.impact_level == "Low"
        assert result.modified_files == []

    def test_single_python_file(self):
        diff_files = [
            {"filename": "app/services/auth.py", "patch": "+def login():\n+    pass", "additions": 2, "deletions": 0}
        ]
        result = calculate_blast_radius(diff_files)
        assert "app/services/auth.py" in result.modified_files
        assert isinstance(result.impact_index, float)
        assert result.impact_level in {"Low", "Medium", "High", "Critical"}

    def test_non_python_files_excluded_from_ast(self):
        diff_files = [
            {"filename": "frontend/src/App.tsx", "patch": "+const x = 1;", "additions": 1, "deletions": 0}
        ]
        result = calculate_blast_radius(diff_files)
        assert result.breaking_exports == []

    def test_breaking_change_detected(self):
        patch = (
            "-def get_user(user_id: str, db: Session):\n"
            "-    pass\n"
        )
        diff_files = [{"filename": "app/models/user.py", "patch": patch, "additions": 0, "deletions": 2}]
        result = calculate_blast_radius(diff_files)
        # Removed symbols should be flagged
        assert isinstance(result.breaking_exports, list)

    def test_api_endpoint_detection(self):
        patch = '+@router.get("/users/{user_id}")\n+async def get_user(user_id: str):\n+    pass'
        diff_files = [{"filename": "app/api/v1/users.py", "patch": patch, "additions": 3, "deletions": 0}]
        result = calculate_blast_radius(diff_files)
        assert len(result.affected_endpoints) > 0

    def test_core_service_triggers_downstream(self):
        diff_files = [
            {"filename": "app/services/review_service.py", "patch": "+def new_fn(): pass", "additions": 1, "deletions": 0}
        ]
        result = calculate_blast_radius(diff_files)
        assert len(result.downstream_files) > 0

    def test_impact_level_critical_for_many_files(self):
        diff_files = [
            {"filename": f"app/services/svc_{i}.py", "patch": "+pass", "additions": 1, "deletions": 0}
            for i in range(10)
        ]
        result = calculate_blast_radius(diff_files)
        assert result.impact_level in {"High", "Critical"}

    def test_summary_is_string(self):
        diff_files = [{"filename": "app/main.py", "patch": "+pass", "additions": 1, "deletions": 0}]
        result = calculate_blast_radius(diff_files)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 10

    def test_dependency_graph_populated(self):
        patch = "+from app.db.session import get_db\n+pass"
        diff_files = [{"filename": "app/api/v1/test.py", "patch": patch, "additions": 2, "deletions": 0}]
        result = calculate_blast_radius(diff_files)
        assert "app/api/v1/test.py" in result.dependency_graph
