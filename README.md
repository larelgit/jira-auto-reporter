# 🐛 Jira Auto-Reporter

> CLI utility for creating bug reports in Jira right from the terminal.  
> Without opening a browser. With a single line.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Jira](https://img.shields.io/badge/Jira-REST%20API%20v2-0052CC?logo=jira)

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

## 📁 Project structure

```
├── jira_reporter.py      # CLI interface (argparse)
├── jira_client.py        # HTTP client (requests + Jira API)
├── config.py             # Load .env config
├── .env.example          # Configuration template
├── .gitignore            # Secret protection
├── requirements.txt      # Dependencies
├── bug_template.txt      # Example template
└── bugs_batch.json       # Example batch file
```

---

## 🛡️ Security

- API token is **never** stored in the code
- `.env` file is added to `.gitignore`
- Uses Basic Auth via `HTTPBasicAuth`

---

## 📜 License

MIT
