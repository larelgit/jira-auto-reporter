"""
Module for loading configuration from the .env file.
No hardcoded secrets — everything is handled via environment variables.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


class JiraConfig:
    """Configuration container for connecting to Jira."""

    def __init__(self):
        # Search for the .env file next to the script
        env_path = Path(__file__).resolve().parent / ".env"
        load_dotenv(dotenv_path=env_path)

        self.domain = os.getenv("JIRA_DOMAIN")
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY")
        self.issue_type = os.getenv("JIRA_ISSUE_TYPE", "Bug")

        self._validate()

    def _validate(self):
        """Check that all required variables are set."""
        missing = []
        if not self.domain:
            missing.append("JIRA_DOMAIN")
        if not self.email:
            missing.append("JIRA_EMAIL")
        if not self.api_token:
            missing.append("JIRA_API_TOKEN")
        if not self.project_key:
            missing.append("JIRA_PROJECT_KEY")

        if missing:
            print(f"\033[91m❌ Configuration Error!\033[0m")
            print(f"   Environment variables not set: {', '.join(missing)}")
            print(f"   Copy .env.example to .env and fill in the values:")
            print(f"   cp .env.example .env")
            sys.exit(1)

    @property
    def base_url(self) -> str:
        """Base URL for Jira REST API v2."""
        return f"https://{self.domain}/rest/api/2"

    @property
    def browse_url(self) -> str:
        """URL for browsing tickets in the browser."""
        return f"https://{self.domain}/browse"

    def __repr__(self) -> str:
        return (
            f"JiraConfig(domain={self.domain}, "
            f"email={self.email}, "
            f"project={self.project_key})"
        )