# 🐛 Jira Auto-Reporter

> CLI utility for creating bug reports in Jira right from the terminal.
> Without opening a browser. With a single line.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Jira](https://img.shields.io/badge/Jira-REST%20API%20v2-0052CC?logo=jira)
[![CI](https://github.com/larelgit/jira-auto-reporter/actions/workflows/ci.yml/badge.svg)](https://github.com/larelgit/jira-auto-reporter/actions/workflows/ci.yml)
[![Dry Run CLI](https://github.com/larelgit/jira-auto-reporter/actions/workflows/dry-run.yml/badge.svg)](https://github.com/larelgit/jira-auto-reporter/actions/workflows/dry-run.yml)

---

## 🚀 Quick start

### 1. Clone the repository

```bash
git clone https://github.com/larelgit/jira-auto-reporter.git
cd jira-auto-reporter
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Jira connection

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable           | What to write                           |
|--------------------|----------------------------------------|
| `JIRA_DOMAIN`      | `your-org.atlassian.net`               |
| `JIRA_EMAIL`       | Your Atlassian account email           |
| `JIRA_API_TOKEN`   | [Create here](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Project key (e.g., `UT`)               |

### 4. Create your first bug!

```bash
python jira_reporter.py --title "Test bug" --desc "Testing the script"
```

---

## 📖 Usage

### Basic bug report

```bash
python jira_reporter.py \
  --title "Player falls under the bridge" \
  --desc "Steps: 1. Go to the bridge. 2. Jump."
```

### With priority and labels

```bash
python jira_reporter.py \
  --title "Crash when opening inventory" \
  --desc "Crashes every time I press I" \
  --priority High \
  --labels crash inventory blocker
```

### With an attached file

```bash
python jira_reporter.py \
  --title "Crash to Desktop" \
  --desc "See log" \
  --file crash.log
```

### From a template (text file)

```bash
python jira_reporter.py --from-file bug_template.txt
```

### Batch creation (JSON)

```bash
python jira_reporter.py --batch bugs_batch.json
```

### Debug mode (without sending)

```bash
python jira_reporter.py \
  --title "Test" --desc "Test" \
  --dry-run
```

---

## ⚙️ CI/CD — GitHub Actions

The project includes three automated workflows that run on GitHub Actions.

### Pipeline overview

```
Push / PR to main
       │
       ▼
┌──────────────────────────────────────────────┐
│                CI Workflow                     │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐ │
│  │   Lint   │  │   Syntax   │  │   Tests   │ │
│  │ flake8   │  │ py_compile │  │  pytest   │ │
│  │ ruff     │  │            │  │ 3.8—3.12  │ │
│  └──────────┘  └────────────┘  └───────────┘ │
└──────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│           Dry Run Workflow                    │
│  --title/--desc  │ --from-file  │  --batch   │
│         All 3 CLI modes verified             │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  📝  Report Bug to Jira  (manual trigger)    │
│  Fill a form in GitHub UI → real Jira API    │
│  Uses repository secrets                     │
└──────────────────────────────────────────────┘
```

### Workflow details

| Workflow | File | Trigger | What it does |
|----------|------|---------|--------------|
| **CI** | `ci.yml` | Push to `main`, any PR | Linting (flake8 + ruff), syntax compilation, unit tests across Python 3.8 — 3.12 |
| **Dry Run CLI** | `dry-run.yml` | Push to `main` (when `*.py` changed), manual | Runs the CLI in `--dry-run` mode for all three input modes (manual, template, batch) |
| **Report Bug to Jira** | `jira-report.yml` | Manual (`workflow_dispatch`) | Creates a real bug in Jira through the GitHub UI form |

### Running tests locally

```bash
pip install pytest
pytest tests/ -v
```

### Creating a bug from GitHub UI

1. Go to **Actions → 📝 Report Bug to Jira**
2. Click **Run workflow**
3. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| Bug title | ✅ | Summary for the Jira issue |
| Bug description | ✅ | Steps to reproduce, expected/actual results |
| Priority | ✅ | `Highest` / `High` / `Medium` / `Low` / `Lowest` |
| Labels | ❌ | Comma-separated list (e.g., `crash,regression,ui`) |
| Dry run | ❌ | Check to preview JSON without creating the issue |

4. Click **Run workflow** and check the job output

### Setting up repository secrets

For the **Report Bug to Jira** workflow to work, add these secrets in
**Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|--------|-------|
| `JIRA_DOMAIN` | `your-org.atlassian.net` |
| `JIRA_EMAIL` | Your Atlassian account email |
| `JIRA_API_TOKEN` | Your Jira API token |
| `JIRA_PROJECT_KEY` | Project key (e.g., `UT`) |

> **Note:** CI and Dry Run workflows use fake environment variables and do **not** require secrets.

---

## 📁 Project structure

```
├── .github/
│   └── workflows/
│       ├── ci.yml                # CI: lint + syntax + tests
│       ├── dry-run.yml           # Dry-run verification of all CLI modes
│       └── jira-report.yml       # Manual bug creation via GitHub UI
├── tests/
│   ├── __init__.py
│   └── test_basic.py            # Unit tests (config, client, parsers)
├── jira_reporter.py              # CLI interface (argparse)
├── jira_client.py                # HTTP client (requests + Jira API)
├── config.py                     # Load .env config
├── .env.example                  # Configuration template
├── .gitignore                    # Secret & artifact protection
├── requirements.txt              # Dependencies
├── bug_template.txt              # Example template
└── bugs_batch.json               # Example batch file
```

---

## 🛡️ Security

- API token is **never** stored in the code
- `.env` file is added to `.gitignore`
- Uses Basic Auth via `HTTPBasicAuth`
- GitHub Actions secrets are encrypted and never exposed in logs

---

## 📜 License

MIT
