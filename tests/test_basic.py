"""
Basic unit tests for jira-auto-reporter.
Run:  pytest tests/ -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Config Tests ────────────────────────────────────────────


class TestJiraConfig:
    """Tests for config.py."""

    def test_config_loads_env_vars(self):
        """Config should read from environment variables."""
        env = {
            "JIRA_DOMAIN": "test.atlassian.net",
            "JIRA_EMAIL": "user@test.com",
            "JIRA_API_TOKEN": "secret-token",
            "JIRA_PROJECT_KEY": "PROJ",
        }
        with patch.dict(os.environ, env, clear=False):
            from config import JiraConfig
            cfg = JiraConfig()

            assert cfg.domain == "test.atlassian.net"
            assert cfg.email == "user@test.com"
            assert cfg.api_token == "secret-token"
            assert cfg.project_key == "PROJ"

    def test_base_url_format(self):
        """base_url should follow Jira REST API v2 format."""
        env = {
            "JIRA_DOMAIN": "myorg.atlassian.net",
            "JIRA_EMAIL": "a@b.com",
            "JIRA_API_TOKEN": "tok",
            "JIRA_PROJECT_KEY": "TST",
        }
        with patch.dict(os.environ, env, clear=False):
            from config import JiraConfig
            cfg = JiraConfig()

            assert cfg.base_url == "https://myorg.atlassian.net/rest/api/2"

    def test_browse_url_format(self):
        """browse_url should point to the issue browser."""
        env = {
            "JIRA_DOMAIN": "myorg.atlassian.net",
            "JIRA_EMAIL": "a@b.com",
            "JIRA_API_TOKEN": "tok",
            "JIRA_PROJECT_KEY": "TST",
        }
        with patch.dict(os.environ, env, clear=False):
            from config import JiraConfig
            cfg = JiraConfig()

            assert cfg.browse_url == "https://myorg.atlassian.net/browse"

    def test_default_issue_type(self):
        """Default issue type should be 'Bug'."""
        env = {
            "JIRA_DOMAIN": "x.atlassian.net",
            "JIRA_EMAIL": "a@b.com",
            "JIRA_API_TOKEN": "tok",
            "JIRA_PROJECT_KEY": "X",
        }
        with patch.dict(os.environ, env, clear=False):
            from config import JiraConfig
            cfg = JiraConfig()

            assert cfg.issue_type == "Bug"

    def test_missing_env_exits(self):
        """Config should exit if required vars are missing."""
        env = {
            "JIRA_DOMAIN": "",
            "JIRA_EMAIL": "",
            "JIRA_API_TOKEN": "",
            "JIRA_PROJECT_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit):
                # Force reimport to re-run __init__
                if "config" in sys.modules:
                    del sys.modules["config"]
                from config import JiraConfig
                JiraConfig()


# ─── JiraClient Tests ───────────────────────────────────────


class TestJiraClient:
    """Tests for jira_client.py."""

    @pytest.fixture
    def client(self):
        """Create a JiraClient with fake config."""
        env = {
            "JIRA_DOMAIN": "test.atlassian.net",
            "JIRA_EMAIL": "user@test.com",
            "JIRA_API_TOKEN": "fake-token",
            "JIRA_PROJECT_KEY": "TEST",
        }
        with patch.dict(os.environ, env, clear=False):
            from config import JiraConfig
            from jira_client import JiraClient
            cfg = JiraConfig()
            return JiraClient(cfg)

    def test_handle_201_success(self, client):
        """201 response should be parsed as success."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"key": "TEST-42"}

        result = client._handle_response(mock_response)

        assert result["success"] is True
        assert result["key"] == "TEST-42"
        assert "TEST-42" in result["url"]

    def test_handle_401_unauthorized(self, client):
        """401 response should report auth error."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        result = client._handle_response(mock_response)

        assert result["success"] is False
        assert "401" in result["message"]

    def test_handle_403_forbidden(self, client):
        """403 response should report permission error."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        result = client._handle_response(mock_response)

        assert result["success"] is False
        assert "403" in result["message"]

    def test_handle_404_not_found(self, client):
        """404 response should report not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        result = client._handle_response(mock_response)

        assert result["success"] is False
        assert "404" in result["message"]

    def test_handle_400_bad_request(self, client):
        """400 response should include error details."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errorMessages": ["Field 'summary' is required"],
            "errors": {},
        }

        result = client._handle_response(mock_response)

        assert result["success"] is False
        assert "400" in result["message"]

    @patch("jira_client.requests.post")
    def test_create_issue_connection_error(self, mock_post, client):
        """Connection errors should be handled gracefully."""
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("No connection")

        result = client.create_issue("Title", "Desc")

        assert result["success"] is False
        assert "connect" in result["message"].lower()

    @patch("jira_client.requests.post")
    def test_create_issue_timeout(self, mock_post, client):
        """Timeout errors should be handled gracefully."""
        import requests as req
        mock_post.side_effect = req.exceptions.Timeout("Timed out")

        result = client.create_issue("Title", "Desc")

        assert result["success"] is False
        assert "timeout" in result["message"].lower()


# ─── File Parser Tests ───────────────────────────────────────


class TestFileParser:
    """Tests for parse_bug_from_file in jira_reporter.py."""

    def test_parse_template_with_headers(self, tmp_path):
        """Should parse Title, Priority, Labels from header section."""
        template = tmp_path / "bug.txt"
        template.write_text(
            "Title: Test Bug\n"
            "Priority: High\n"
            "Labels: crash, ui\n"
            "---\n"
            "Steps to reproduce:\n"
            "1. Do something.\n",
            encoding="utf-8",
        )

        from jira_reporter import parse_bug_from_file
        result = parse_bug_from_file(str(template))

        assert result["summary"] == "Test Bug"
        assert result["priority"] == "High"
        assert result["labels"] == ["crash", "ui"]
        assert "Steps to reproduce" in result["description"]

    def test_parse_simple_format(self, tmp_path):
        """First line = title, rest = description (no --- separator)."""
        template = tmp_path / "simple.txt"
        template.write_text(
            "Simple Bug Title\n"
            "This is the description.\n"
            "More details here.\n",
            encoding="utf-8",
        )

        from jira_reporter import parse_bug_from_file
        result = parse_bug_from_file(str(template))

        assert result["summary"] == "Simple Bug Title"
        assert "This is the description" in result["description"]

    def test_parse_missing_file_exits(self):
        """Should exit if file doesn't exist."""
        from jira_reporter import parse_bug_from_file

        with pytest.raises(SystemExit):
            parse_bug_from_file("/nonexistent/file.txt")


# ─── Batch Parser Tests ─────────────────────────────────────


class TestBatchParser:
    """Tests for parse_batch_file in jira_reporter.py."""

    def test_parse_valid_batch(self, tmp_path):
        """Should parse a valid JSON array of bugs."""
        batch = tmp_path / "bugs.json"
        data = [
            {"summary": "Bug 1", "description": "Desc 1", "priority": "High"},
            {"summary": "Bug 2", "description": "Desc 2"},
        ]
        batch.write_text(json.dumps(data), encoding="utf-8")

        from jira_reporter import parse_batch_file
        result = parse_batch_file(str(batch))

        assert len(result) == 2
        assert result[0]["summary"] == "Bug 1"

    def test_parse_invalid_json_exits(self, tmp_path):
        """Should exit on malformed JSON."""
        batch = tmp_path / "bad.json"
        batch.write_text("{not valid json", encoding="utf-8")

        from jira_reporter import parse_batch_file

        with pytest.raises(SystemExit):
            parse_batch_file(str(batch))

    def test_parse_missing_summary_exits(self, tmp_path):
        """Should exit if a bug doesn't have 'summary'."""
        batch = tmp_path / "no_sum.json"
        data = [{"description": "no summary here"}]
        batch.write_text(json.dumps(data), encoding="utf-8")

        from jira_reporter import parse_batch_file

        with pytest.raises(SystemExit):
            parse_batch_file(str(batch))

    def test_parse_not_array_exits(self, tmp_path):
        """Should exit if JSON root is not an array."""
        batch = tmp_path / "obj.json"
        batch.write_text('{"summary": "single object"}', encoding="utf-8")

        from jira_reporter import parse_batch_file

        with pytest.raises(SystemExit):
            parse_batch_file(str(batch))
