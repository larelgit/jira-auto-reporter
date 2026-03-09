"""
Jira REST API client.
Responsible for all communication with the server: creating tickets, attachments, etc.
"""

import json
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

from config import JiraConfig


# ─── ANSI colors for the terminal ────────────────────────────
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


class JiraClient:
    """Client for working with Jira REST API v2."""

    def __init__(self, config: JiraConfig):
        self.config = config
        self.auth = HTTPBasicAuth(config.email, config.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ─── Ticket creation ─────────────────────────────────────
    def create_issue(
        self,
        summary: str,
        description: str,
        priority: Optional[str] = None,
        labels: Optional[list] = None,
        components: Optional[list] = None,
    ) -> dict:
        """
        Creates a bug report in Jira.

        Args:
            summary: Bug title.
            description: Description (steps to reproduce, etc.).
            priority: Priority (Highest, High, Medium, Low, Lowest).
            labels: List of labels, e.g., ["crash", "regression"].
            components: Project components.

        Returns:
            dict with keys 'success', 'key', 'url', 'message'.
        """
        url = f"{self.config.base_url}/issue"

        # Form the JSON Payload according to the Jira API specification
        payload = {
            "fields": {
                "project": {
                    "key": self.config.project_key,
                },
                "summary": summary,
                "description": description,
                "issuetype": {
                    "name": self.config.issue_type,
                },
            }
        }

        # Optional fields
        if priority:
            payload["fields"]["priority"] = {"name": priority}

        if labels:
            payload["fields"]["labels"] = labels

        if components:
            payload["fields"]["components"] = [
                {"name": c} for c in components
            ]

        try:
            response = requests.post(
                url,
                data=json.dumps(payload),
                headers=self.headers,
                auth=self.auth,
                timeout=30,
            )

            return self._handle_response(response)

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": (
                    f"Failed to connect to {self.config.domain}. "
                    f"Check the domain and internet connection."
                ),
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": "Request timeout (30 sec). Try again later.",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": f"Network error: {e}",
            }

    # ─── File Attachment ──────────────────────────────────────
    def attach_file(self, issue_key: str, file_path: str) -> dict:
        """
        Attaches a file to an existing ticket (POST /issue/{key}/attachments).

        Args:
            issue_key: Ticket key, e.g., "UT-42".
            file_path: Path to the file (log, screenshot, etc.).

        Returns:
            dict with keys 'success' and 'message'.
        """
        url = f"{self.config.base_url}/issue/{issue_key}/attachments"

        # Jira requires a special header for attachments
        headers = {
            "Accept": "application/json",
            "X-Atlassian-Token": "no-check",  # XSRF protection
        }

        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    url,
                    headers=headers,
                    auth=self.auth,
                    files={"file": (file_path.split("/")[-1], f)},
                    timeout=60,
                )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"File '{file_path}' attached to {issue_key}.",
                }
            else:
                return {
                    "success": False,
                    "message": (
                        f"Failed to attach file. "
                        f"HTTP {response.status_code}: {response.text}"
                    ),
                }

        except FileNotFoundError:
            return {
                "success": False,
                "message": f"File not found: {file_path}",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Error uploading file: {e}",
            }

    # ─── HTTP Response Handling ───────────────────────────────
    def _handle_response(self, response: requests.Response) -> dict:
        """Parses the HTTP response from Jira and returns a human-readable result."""

        status = response.status_code

        # 201 Created — ticket successfully created
        if status == 201:
            data = response.json()
            issue_key = data["key"]
            issue_url = f"{self.config.browse_url}/{issue_key}"
            return {
                "success": True,
                "key": issue_key,
                "url": issue_url,
                "message": f"Bug created: {issue_key}",
            }

        # 400 Bad Request — invalid request format
        if status == 400:
            errors = self._extract_errors(response)
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": (
                    f"Bad request (400). Check the project key "
                    f"and issue type.\n   Details: {errors}"
                ),
            }

        # 401 Unauthorized — incorrect email or API token
        if status == 401:
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": (
                    "Authorization error (401). Check JIRA_EMAIL "
                    "and JIRA_API_TOKEN in the .env file."
                ),
            }

        # 403 Forbidden — no permissions
        if status == 403:
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": (
                    "Forbidden (403). Your account does not have permissions "
                    "to create issues in this project."
                ),
            }

        # 404 Not Found — incorrect URL or project does not exist
        if status == 404:
            return {
                "success": False,
                "key": None,
                "url": None,
                "message": (
                    f"Not found (404). Check JIRA_DOMAIN "
                    f"({self.config.domain}) and JIRA_PROJECT_KEY "
                    f"({self.config.project_key})."
                ),
            }

        # Any other code
        errors = self._extract_errors(response)
        return {
            "success": False,
            "key": None,
            "url": None,
            "message": f"Unexpected response HTTP {status}.\n   Details: {errors}",
        }

    @staticmethod
    def _extract_errors(response: requests.Response) -> str:
        """Tries to extract error details from the JSON response."""
        try:
            data = response.json()
            errors = data.get("errorMessages", [])
            field_errors = data.get("errors", {})
            parts = errors + [f"{k}: {v}" for k, v in field_errors.items()]
            return "; ".join(parts) if parts else response.text[:300]
        except (ValueError, KeyError):
            return response.text[:300]