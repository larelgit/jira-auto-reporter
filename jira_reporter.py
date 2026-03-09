#!/usr/bin/env python3
"""
Jira Auto-Reporter — CLI utility for creating bug reports in Jira.

Usage examples:

  # Simple bug
  python jira_reporter.py --title "Player falls under the bridge" \\
                          --desc "Steps: 1. Go to the bridge. 2. Jump."

  # With priority and labels
  python jira_reporter.py --title "Crash when opening inventory" \\
                          --desc "Crashes every time." \\
                          --priority High \\
                          --labels crash regression

  # With an attached log file
  python jira_reporter.py --title "Crash to desktop" \\
                          --desc "See log." \\
                          --file crash.log

  # From a prepared file (template)
  python jira_reporter.py --from-file bug_template.txt

  # Batch bug creation from JSON
  python jira_reporter.py --batch bugs_batch.json
"""

import argparse
import json
import sys
from pathlib import Path

from jira_client import JiraClient, Colors
from config import JiraConfig


def parse_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        prog="jira_reporter",
        description="🐛 Jira Auto-Reporter — create bugs from the terminal!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --title "Bug" --desc "Bug description"
  %(prog)s --title "Bug" --desc "Description" --priority High --labels crash
  %(prog)s --title "Bug" --desc "Description" --file crash.log
  %(prog)s --from-file bug_template.txt
  %(prog)s --batch bugs_batch.json
        """,
    )

    # Group 1: Manual Input
    manual = parser.add_argument_group("Manual bug entry")
    manual.add_argument(
        "--title", "-t",
        type=str,
        help="Bug title (summary)",
    )
    manual.add_argument(
        "--desc", "-d",
        type=str,
        help="Bug description",
    )
    manual.add_argument(
        "--priority", "-p",
        type=str,
        choices=["Highest", "High", "Medium", "Low", "Lowest"],
        default=None,
        help="Priority (default — from project settings)",
    )
    manual.add_argument(
        "--labels", "-l",
        nargs="+",
        default=None,
        help="Labels separated by spaces (e.g., crash regression ui)",
    )
    manual.add_argument(
        "--components", "-c",
        nargs="+",
        default=None,
        help="Project components separated by spaces",
    )
    manual.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="Path to the file to attach to the ticket (log, screenshot, etc.)",
    )

    # Group 2: From file
    file_input = parser.add_argument_group("Create from file")
    file_input.add_argument(
        "--from-file",
        type=str,
        default=None,
        help="Path to the text file with the bug (format: Title\\nDescription)",
    )

    # Group 3: Batch mode
    batch_input = parser.add_argument_group("Batch creation")
    batch_input.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Path to a JSON file with a list of bugs",
    )

    # Additional options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show JSON without sending (for debugging)",
    )

    args = parser.parse_args()

    # Validation: at least one mode is required
    if not args.from_file and not args.batch and not args.title:
        parser.error(
            "Specify --title and --desc, or --from-file, or --batch. "
            "Use --help for more information."
        )

    # If manual mode is active, description is required
    if args.title and not args.desc and not args.from_file and not args.batch:
        parser.error("Along with --title, you must specify --desc.")

    return args


def parse_bug_from_file(file_path: str) -> dict:
    """
    Parses a bug from a text file.

    File format (bug_template.txt):
      Title: Bug title
      Priority: High
      Labels: crash, regression
      ---
      Everything below the separator is the bug description.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"{Colors.RED}❌ File not found: {file_path}{Colors.RESET}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    result = {
        "summary": "",
        "description": "",
        "priority": None,
        "labels": None,
    }

    # Split headers and body by "---"
    if "---" in content:
        header_part, body = content.split("---", 1)
        result["description"] = body.strip()

        for line in header_part.strip().splitlines():
            line = line.strip()
            if line.lower().startswith("title:"):
                result["summary"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("priority:"):
                result["priority"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("labels:"):
                labels_raw = line.split(":", 1)[1].strip()
                result["labels"] = [
                    lb.strip() for lb in labels_raw.split(",") if lb.strip()
                ]
    else:
        # Simple format: first line is title, the rest is description
        lines = content.strip().splitlines()
        result["summary"] = lines[0].strip()
        result["description"] = "\n".join(lines[1:]).strip()

    if not result["summary"]:
        print(f"{Colors.RED}❌ Bug title not found in the file.{Colors.RESET}")
        sys.exit(1)

    return result


def parse_batch_file(file_path: str) -> list:
    """Parses a JSON file with an array of bugs."""
    path = Path(file_path)
    if not path.exists():
        print(f"{Colors.RED}❌ File not found: {file_path}{Colors.RESET}")
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}❌ Invalid JSON: {e}{Colors.RESET}")
        sys.exit(1)

    if not isinstance(data, list):
        print(f"{Colors.RED}❌ JSON must contain an array of bugs.{Colors.RESET}")
        sys.exit(1)

    for i, bug in enumerate(data):
        if "summary" not in bug:
            print(
                f"{Colors.RED}❌ Bug #{i + 1} is missing the 'summary' field.{Colors.RESET}"
            )
            sys.exit(1)

    return data


def print_result(result: dict, attach_result: dict = None):
    """Nicely prints the result to the console."""
    if result["success"]:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Success! Bug created.{Colors.RESET}")
        print(f"   {Colors.CYAN}Key:   {result['key']}{Colors.RESET}")
        print(f"   {Colors.CYAN}Link:  {result['url']}{Colors.RESET}")

        if attach_result:
            if attach_result["success"]:
                print(
                    f"   {Colors.GREEN}📎 {attach_result['message']}{Colors.RESET}"
                )
            else:
                print(
                    f"   {Colors.YELLOW}⚠️  {attach_result['message']}{Colors.RESET}"
                )
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Error!{Colors.RESET}")
        print(f"   {Colors.RED}{result['message']}{Colors.RESET}")


def create_single_bug(
    client: JiraClient,
    summary: str,
    description: str,
    priority: str = None,
    labels: list = None,
    components: list = None,
    file_path: str = None,
    dry_run: bool = False,
) -> bool:
    """Creates a single bug and optionally attaches a file. Returns True on success."""

    if dry_run:
        payload = {
            "fields": {
                "project": {"key": client.config.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": client.config.issue_type},
            }
        }
        if priority:
            payload["fields"]["priority"] = {"name": priority}
        if labels:
            payload["fields"]["labels"] = labels

        print(f"\n{Colors.YELLOW}🔍 DRY RUN — request NOT sent:{Colors.RESET}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return True

    # Send the request
    print(f"{Colors.DIM}⏳ Sending bug to Jira...{Colors.RESET}", end="", flush=True)
    result = client.create_issue(
        summary=summary,
        description=description,
        priority=priority,
        labels=labels,
        components=components,
    )
    print("\r" + " " * 40 + "\r", end="")  # Clear the waiting string

    # Attach file if specified
    attach_result = None
    if result["success"] and file_path:
        print(f"{Colors.DIM}📎 Attaching file...{Colors.RESET}", end="", flush=True)
        attach_result = client.attach_file(result["key"], file_path)
        print("\r" + " " * 40 + "\r", end="")

    print_result(result, attach_result)
    return result["success"]


# ─── MAIN ────────────────────────────────────────────────────
def main():
    args = parse_args()

    # Load config (exits with error if .env is not configured)
    config = JiraConfig()
    client = JiraClient(config)

    print(f"{Colors.BOLD}🐛 Jira Auto-Reporter{Colors.RESET}")
    print(f"{Colors.DIM}   Project: {config.project_key} @ {config.domain}{Colors.RESET}")

    # ─── Mode 1: Batch creation from JSON ──────────────────────
    if args.batch:
        bugs = parse_batch_file(args.batch)
        print(f"\n📋 Found bugs: {len(bugs)}")

        success_count = 0
        fail_count = 0

        for i, bug in enumerate(bugs, 1):
            print(f"\n{'─' * 50}")
            print(f"   [{i}/{len(bugs)}] {bug['summary'][:60]}")
            ok = create_single_bug(
                client=client,
                summary=bug["summary"],
                description=bug.get("description", ""),
                priority=bug.get("priority"),
                labels=bug.get("labels"),
                dry_run=args.dry_run,
            )
            if ok:
                success_count += 1
            else:
                fail_count += 1

        print(f"\n{'═' * 50}")
        print(
            f"📊 Total: {Colors.GREEN}{success_count} created{Colors.RESET}, "
            f"{Colors.RED}{fail_count} errors{Colors.RESET}"
        )
        return

    # ─── Mode 2: From text file ──────────────────────────────
    if args.from_file:
        bug_data = parse_bug_from_file(args.from_file)
        create_single_bug(
            client=client,
            summary=bug_data["summary"],
            description=bug_data["description"],
            priority=bug_data.get("priority") or args.priority,
            labels=bug_data.get("labels") or args.labels,
            components=args.components,
            file_path=args.file,
            dry_run=args.dry_run,
        )
        return

    # ─── Mode 3: Manual input via arguments ──────────────────
    create_single_bug(
        client=client,
        summary=args.title,
        description=args.desc,
        priority=args.priority,
        labels=args.labels,
        components=args.components,
        file_path=args.file,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()