"""Tests for the prototype code updater agent."""

import json
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.agents.prototype_updater_tools import build_tools, execute_tool
from app.agents.prototype_updater_types import UpdatePlan, UpdateResult, UpdateTask


@pytest.fixture
def mock_git():
    """Mock GitManager."""
    git = MagicMock()
    git.read_file.return_value = "export default function App() { return <div>Hello</div>; }"
    git.write_file.return_value = None
    git.commit.return_value = "abc1234567890"
    return git


@pytest.fixture
def sample_plan():
    """Sample update plan."""
    return UpdatePlan(
        tasks=[
            UpdateTask(
                file_path="src/Login.tsx",
                change_description="Add MFA toggle to login form",
                reason="Client feedback: MFA required for enterprise users",
                feature_id=str(uuid4()),
                risk="medium",
                depends_on=[],
            ),
            UpdateTask(
                file_path="src/Dashboard.tsx",
                change_description="Add stats refresh button",
                reason="Consultant observation: no manual refresh option",
                feature_id=str(uuid4()),
                risk="low",
                depends_on=[],
            ),
        ],
        execution_order=[0, 1],
        estimated_files_changed=2,
        risk_assessment="Low overall risk — UI additions only",
    )


class TestBuildTools:
    """Tests for tool definition builder."""

    def test_returns_correct_tool_count(self, mock_git):
        """Should return all 6 tools."""
        tools = build_tools(mock_git, "/tmp/test", "proj-123")
        assert len(tools) == 6

    def test_tool_names(self, mock_git):
        """All expected tools should be present."""
        tools = build_tools(mock_git, "/tmp/test", "proj-123")
        names = {t["name"] for t in tools}
        assert names == {"read_file", "write_file", "list_directory", "search_code", "get_feature_context", "run_build"}

    def test_tools_have_input_schemas(self, mock_git):
        """Each tool should have an input_schema."""
        tools = build_tools(mock_git, "/tmp/test", "proj-123")
        for tool in tools:
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"


class TestExecuteTool:
    """Tests for tool execution."""

    def test_read_file(self, mock_git):
        """read_file should delegate to git.read_file."""
        result = execute_tool("read_file", {"path": "src/App.tsx"}, mock_git, "/tmp/test", "proj-123")
        assert result["success"] is True
        mock_git.read_file.assert_called_once_with("/tmp/test", "src/App.tsx")

    def test_write_file(self, mock_git):
        """write_file should delegate to git.write_file."""
        result = execute_tool(
            "write_file",
            {"path": "src/App.tsx", "content": "new content"},
            mock_git,
            "/tmp/test",
            "proj-123",
        )
        assert result["success"] is True
        mock_git.write_file.assert_called_once_with("/tmp/test", "src/App.tsx", "new content")

    def test_list_directory(self, mock_git, tmp_path):
        """list_directory should list files in a real directory."""
        # Create temp files
        (tmp_path / "app.tsx").touch()
        (tmp_path / "utils.ts").touch()
        (tmp_path / "readme.md").touch()

        result = execute_tool(
            "list_directory",
            {"path": "", "pattern": "*.ts*"},
            mock_git,
            str(tmp_path),
            "proj-123",
        )
        assert result["success"] is True
        assert "app.tsx" in result["data"]
        assert "utils.ts" in result["data"]
        assert "readme.md" not in result["data"]

    def test_list_directory_not_found(self, mock_git):
        """list_directory should fail for non-existent directory."""
        result = execute_tool(
            "list_directory",
            {"path": "nonexistent"},
            mock_git,
            "/tmp/definitely-not-real",
            "proj-123",
        )
        assert result["success"] is False

    def test_search_code(self, mock_git, tmp_path):
        """search_code should find pattern in files."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "Login.tsx").write_text("export function Login() { return <div>Login Form</div>; }")
        (src / "App.tsx").write_text("export function App() { return <Login />; }")

        result = execute_tool(
            "search_code",
            {"pattern": "Login"},
            mock_git,
            str(tmp_path),
            "proj-123",
        )
        assert result["success"] is True
        assert len(result["data"]) >= 1

    def test_run_build(self, mock_git):
        """run_build should call npm run build."""
        with patch("app.agents.prototype_updater_tools.subprocess") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Build successful"
            mock_proc.stderr = ""
            mock_subprocess.run.return_value = mock_proc

            result = execute_tool("run_build", {}, mock_git, "/tmp/test", "proj-123")
            assert result["success"] is True
            mock_subprocess.run.assert_called_once()

    def test_run_build_failure(self, mock_git):
        """run_build should report failure on non-zero exit."""
        with patch("app.agents.prototype_updater_tools.subprocess") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "Error: Module not found"
            mock_subprocess.run.return_value = mock_proc

            result = execute_tool("run_build", {}, mock_git, "/tmp/test", "proj-123")
            assert result["success"] is False

    def test_unknown_tool(self, mock_git):
        """Unknown tool names should return an error."""
        result = execute_tool("unknown_tool", {}, mock_git, "/tmp/test", "proj-123")
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_tool_exception_handling(self, mock_git):
        """Tool exceptions should be caught and returned as errors."""
        mock_git.read_file.side_effect = FileNotFoundError("File not found")
        result = execute_tool("read_file", {"path": "missing.tsx"}, mock_git, "/tmp/test", "proj-123")
        assert result["success"] is False
        assert "File not found" in result["error"]

    def test_get_feature_context(self, mock_git):
        """get_feature_context should fetch feature and overlay data."""
        feature_id = str(uuid4())
        project_id = str(uuid4())
        mock_feature = {"id": feature_id, "name": "Login"}
        mock_prototype = {"id": str(uuid4())}
        mock_overlay = {"id": str(uuid4()), "status": "partial"}

        with (
            patch("app.db.features.get_feature", return_value=mock_feature),
            patch("app.db.prototypes.get_prototype_for_project", return_value=mock_prototype),
            patch("app.db.prototypes.get_overlay_for_feature", return_value=mock_overlay),
        ):
            result = execute_tool(
                "get_feature_context",
                {"feature_id": feature_id},
                mock_git,
                "/tmp/test",
                project_id,
            )
            assert result["success"] is True
            assert result["data"]["feature"]["name"] == "Login"
            assert result["data"]["overlay"]["status"] == "partial"


class TestUpdatePlan:
    """Tests for UpdatePlan schema."""

    def test_empty_plan(self):
        """Empty plan should have sensible defaults."""
        plan = UpdatePlan()
        assert plan.tasks == []
        assert plan.execution_order == []
        assert plan.estimated_files_changed == 0

    def test_plan_with_tasks(self, sample_plan):
        """Plan with tasks should serialize correctly."""
        assert len(sample_plan.tasks) == 2
        assert sample_plan.execution_order == [0, 1]
        assert sample_plan.estimated_files_changed == 2

    def test_task_defaults(self):
        """Task with minimal fields should use defaults."""
        task = UpdateTask(
            file_path="src/App.tsx",
            change_description="Add header",
            reason="Feedback",
        )
        assert task.risk == "low"
        assert task.feature_id == ""
        assert task.depends_on == []


class TestUpdateResult:
    """Tests for UpdateResult schema."""

    def test_successful_result(self):
        """Successful result with all fields."""
        result = UpdateResult(
            files_changed=["src/Login.tsx", "src/Dashboard.tsx"],
            build_passed=True,
            commit_sha="abc123",
            errors=[],
            summary="Updated 2 files. Build: PASS.",
        )
        assert len(result.files_changed) == 2
        assert result.build_passed is True
        assert result.commit_sha == "abc123"

    def test_failed_result(self):
        """Failed result with errors."""
        result = UpdateResult(
            files_changed=["src/Login.tsx"],
            build_passed=False,
            commit_sha=None,
            errors=["Build failed: syntax error"],
            summary="Updated 1 file. Build: FAIL.",
        )
        assert result.build_passed is False
        assert len(result.errors) == 1
        assert result.commit_sha is None

    def test_default_result(self):
        """Default result should be valid."""
        result = UpdateResult()
        assert result.files_changed == []
        assert result.build_passed is True
        assert result.tests_passed is None
        assert result.errors == []


class TestPlanUpdates:
    """Tests for the plan_updates function."""

    @pytest.mark.asyncio
    async def test_generates_plan_from_synthesis(self):
        """Should generate an UpdatePlan from feedback synthesis."""
        from app.agents.prototype_updater import plan_updates

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "tasks": [
                            {
                                "file_path": "src/Login.tsx",
                                "change_description": "Add MFA toggle",
                                "reason": "Client feedback",
                                "feature_id": "feat-1",
                                "risk": "medium",
                                "depends_on": [],
                            }
                        ],
                        "execution_order": [0],
                        "estimated_files_changed": 1,
                        "risk_assessment": "Low risk",
                    }
                )
            )
        ]

        with patch("app.agents.prototype_updater.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            MockAnthropic.return_value = mock_client

            with patch("app.agents.prototype_updater.get_settings") as mock_settings:
                settings = MagicMock()
                settings.PROTOTYPE_UPDATER_PLAN_MODEL = "claude-opus-4-5-20251101"
                settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.return_value = settings

                plan = await plan_updates(
                    synthesis={"by_feature": {}, "session_summary": "test"},
                    file_tree=["src/Login.tsx", "src/App.tsx"],
                    features=[{"id": "feat-1", "name": "Login"}],
                )

                assert isinstance(plan, UpdatePlan)
                assert len(plan.tasks) == 1
                assert plan.tasks[0].file_path == "src/Login.tsx"
