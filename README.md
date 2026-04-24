# OSINT Combined Search v4

A modular, cross-platform Open Source Intelligence (OSINT) aggregation tool that queries **OSINT Industries**, **DeHashed**, and **Cypher Dynamics** in parallel with advanced filtering, risk scoring, and professional reporting.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [CLI Usage](#cli-usage)
7. [Example Input & Output](#example-input--output)
8. [Web Application](#web-application)
9. [Advanced Features](#advanced-features)
10. [Troubleshooting](#troubleshooting)
11. [Legal & Ethical Notice](#legal--ethical-notice)

---

## Overview

OSINT Combined Search v4 unifies three major intelligence sources into a single command-line and web interface. It runs searches in parallel using `ThreadPoolExecutor`, applies client-side intelligent filtering, calculates a risk score, and generates Markdown intelligence reports.

### Supported Query Types

| Type | Description | Example |
|------|-------------|---------|
| `email` | Email address | `target@example.com` |
| `username` | Username / handle | `targetuser` |
| `domain` | Domain name | `example.com` |
| `ip` | IP address | `192.0.2.1` |
| `password` | Plaintext password | `password123` |
| `hashed_password` | Password hash | `5f4dcc3b5aa765d61d8327deb882cf99` |
| `phone` | Phone number | `+14155551234` |
| `name` | Full name | `John Doe` |
| `wallet` | Crypto wallet address | `0x71C7656EC7ab88b098defB751B7401B5f6d8976F` |

---

## Features

- **3-Source Parallel Search** — Query OSINT Industries, DeHashed, and Cypher Dynamics simultaneously
- **Advanced Filters** — Min count, min password length, regex matching, date ranges, password-only mode
- **Cascade Search** — Search a domain, automatically extract all emails found, then search each email individually
- **Bulk Search** — Run up to 50 queries in a single batch with concurrency control
- **Risk Scoring** — Automatic LOW / MEDIUM / HIGH risk classification based on cross-source exposure
- **Beautiful CLI Output** — Rich-powered colored panels, tables, and syntax highlighting (graceful fallback to plain JSON)
- **Markdown Reports** — Export professional intelligence reports with executive summary, findings, and recommendations
- **Web UI** — Modern Bootstrap 5 dark-themed Flask app with tabs, stats, and one-click downloads
- **Result Caching** — In-memory cache with 5-minute TTL to avoid redundant API calls
- **Graceful Degradation** — Falls back to basic auth for DeHashed if Bearer token fails
- **Raw JSON Export** — Save per-source raw responses for further analysis

---

## Project Structure

```
osint/
├── osint_combined_search.py          # Legacy monolithic CLI (standalone)
├── osint_web_app.py                  # Flask web application
├── osint_config.json                 # JSON configuration template
├── requirements.txt                  # Python dependencies
├── install.sh                        # One-command installer
├── README.md                         # This file
├── README-2.md                       # Previous version docs
├── TODO.md                           # Development roadmap
└── osint_utility/                    # Modular package (preferred)
    ├── __init__.py
    ├── __main__.py                   # python -m osint_utility entry point
    ├── main.py                       # Modular CLI entry point
    ├── orchestrator.py               # Core search orchestrator
    ├── clients/
    │   ├── __init__.py
    │   ├── osint_industries.py      # OSINT Industries API client
    │   ├── dehashed.py              # DeHashed API client
    │   └── cypher_dynamics.py       # Cypher Dynamics API client
    └── utils/
        ├── __init__.py
        ├── config.py                # Configuration loader & validator
        ├── filters.py               # Client-side filtering engine
        └── formatter.py             # Output formatting & reports
```

---

## Installation

### Prerequisites

- Python 3.9+
- API keys for the sources you plan to use

### Step 1: Clone / Download

```bash
git clone https://github.com/your-org/osint-combined.git
cd osint-combined
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or use the provided installer:

```bash
bash install.sh
```

### Step 3: Configure API Keys

Create a `.env` file in the project root:

```bash
export OSINT_INDUSTRIES_API_KEY="your_osint_industries_key"
export DEHASHED_API_KEY="your_dehashed_key"
export DEHASHED_EMAIL="your_email@example.com"
export CYPHER_DYNAMICS_API_KEY="your_cypher_dynamics_key"
export CYPHER_DYNAMICS_API_URL="https://api.cypherdynamics.com/search"
export FLASK_SECRET_KEY="change-me-in-production"
```

Or edit `osint_config.json`:

```json
{
  "osint_industries_api_key": "your_key",
  "dehashed_api_key": "your_key",
  "dehashed_email": "your@email.com",
  "cypher_dynamics_api_key": "your_key",
  "cypher_dynamics_api_url": "https://api.cypherdynamics.com/search",
  "timeout": 30,
  "premium": true
}
```

---

## CLI Usage

### Basic Search

```bash
python osint_combined_search.py -q "target@example.com" --pretty
```

### Using the Modular CLI

```bash
python -m osint_utility --type email --value target@example.com --report intel.md
```

### Common Options

| Flag | Description |
|------|-------------|
| `-q, --query` | Search query value |
| `-t, --type` | Query type (email, username, domain, ip, password, hashed_password, name, phone, wallet) |
| `--sources` | Comma-separated sources (default: all) |
| `--min-count N` | Minimum breach occurrence count |
| `--min-password-len N` | Minimum password length |
| `--only-passwords` | Only return entries with cleartext passwords |
| `--regex PATTERN` | Regex filter applied to all fields |
| `--after-date YYYY-MM-DD` | Only results after this date |
| `--before-date YYYY-MM-DD` | Only results before this date |
| `--cascade` | For domain searches: extract emails and search each one |
| `--pretty` | Enable rich colored terminal output |
| `--report FILE.md` | Generate Markdown intelligence report |
| `--save-raw DIR` | Save individual raw JSON per source |
| `--config FILE` | Path to custom config JSON |
| `--no-rich` | Disable rich terminal output |
| `--timeout N` | API timeout in seconds |

---

## Example Input & Output

### Example 1: Basic Email Search

**Input (Command):**

```bash
python osint_combined_search.py \
  -q "ceo@targetcorp.com" \
  -t email \
  --pretty \
  --report report.md
```

**Output (Terminal — Rich):**

```
┌─────────────────────────────────────────────────────────────┐
│ OSINT COMBINED SEARCH v4 | Query: ceo@targetcorp.com | Type: email │
└─────────────────────────────────────────────────────────────┘
┌────────────────────────────┐
│ ✅ Search Complete in 2.34s │
└────────────────────────────┘
┌──────────────┬──────────────────────────────────────────────────┐
│ Metric       │ Value                                            │
├──────────────┼──────────────────────────────────────────────────┤
│ query        │ ceo@targetcorp.com                               │
│ sources_searched │ ['osint_industries', 'dehashed', 'cypher_dynamics'] │
│ total_sources_with_results │ 2                                            │
│ key_findings │ DeHashed: 47 breach entries                      │
│              │ Cypher Dynamics: 12 credential hits              │
│ risk_score   │ HIGH                                             │
│ recommendations │ Rotate all exposed passwords immediately      │
│              │ Enable 2FA/MFA everywhere                        │
│              │ Monitor for further leaks using this tool regularly │
│              │ Consider professional incident response if corporate account │
└──────────────┴──────────────────────────────────────────────────┘
```

**Output (JSON — truncated):**

```json
{
  "query": "ceo@targetcorp.com",
  "type": "email",
  "timestamp": "2025-01-15T09:23:17.843210",
  "execution_time_seconds": 2.34,
  "version": "4.0",
  "results": {
    "osint_industries": {
      "source": "osint_industries",
      "results": {
        "profiles": [...],
        "accounts": [...]
      },
      "status": "success"
    },
    "dehashed": {
      "source": "dehashed",
      "results": {
        "entries": [
          {
            "email": "ceo@targetcorp.com",
            "username": "ceouser",
            "password": "Winter2024!",
            "hashed_password": "",
            "breach": "MegaBreach2023",
            "breach_date": "2023-08-14",
            "domain": "targetcorp.com"
          }
        ]
      },
      "entries_found": 47,
      "status": "success"
    },
    "cypher_dynamics": {
      "source": "cypher_dynamics",
      "results": {
        "credentials": [
          {
            "email": "ceo@targetcorp.com",
            "password": "Winter2024!",
            "url": "https://portal.targetcorp.com",
            "date": "2024-11-02",
            "user_agent": "Mozilla/5.0 ...",
            "ip": "203.0.113.45"
          }
        ]
      },
      "status": "success"
    }
  },
  "summary": {
    "query": "ceo@targetcorp.com",
    "sources_searched": ["osint_industries", "dehashed", "cypher_dynamics"],
    "total_sources_with_results": 2,
    "key_findings": [
      "DeHashed: 47 breach entries",
      "Cypher Dynamics: 12 credential hits"
    ],
    "risk_score": "HIGH",
    "recommendations": [
      "Rotate all exposed passwords immediately",
      "Enable 2FA/MFA everywhere",
      "Monitor for further leaks using this tool regularly",
      "Consider professional incident response if corporate account"
    ],
    "filters_used": {}
  }
}
```

---

### Example 2: Advanced Filtering

**Input (Command):**

```bash
python -m osint_utility \
  --type email \
  --value "admin@targetcorp.com" \
  --min-count 5 \
  --min-password-len 10 \
  --only-passwords \
  --after-date 2024-01-01 \
  --regex "session|cookie|token" \
  --sources dehashed cypher_dynamics \
  --report filtered_intel.md
```

**Output (Terminal):**

```
Configuration validated for: dehashed, cypher_dynamics

OSINT Combined Search v4 (Modular) | Query: admin@targetcorp.com | Type: email

┌─────────────────────────────────────────────────────────────┐
│ ✅ Search Complete in 1.89s                                 │
└─────────────────────────────────────────────────────────────┘

Risk Score: HIGH
Sources with Data: 2 / 2

Key Findings:
  • DeHashed: 8 breach entries (filtered from 34)
  • Cypher Dynamics: 3 credential hits (filtered from 15)

Filters Applied:
  • min_count: 5
  • min_password_len: 10
  • only_passwords: True
  • after_date: 2024-01-01
  • regex: session|cookie|token

✅ Report saved to: filtered_intel.md
```

---

### Example 3: Domain Cascade Search

**Input (Command):**

```bash
python osint_combined_search.py \
  -q "targetcorp.com" \
  -t domain \
  --cascade \
  --pretty \
  --min-password-len 8 \
  --report cascade_report.md
```

**Output (Terminal — Rich):**

```
┌─────────────────────────────────────────────────────────────┐
│ OSINT COMBINED SEARCH v4 | Query: targetcorp.com | Type: domain │
└─────────────────────────────────────────────────────────────┘

🌊 CASCADE MODE ENABLED
Domain search complete. Extracting emails...
Found 127 unique emails.
Searching top 50 emails (77 skipped due to limit)...

Progress: 50/50 emails searched

┌────────────────────────────┐
│ ✅ Cascade Complete in 45.2s │
└────────────────────────────┘

📊 Cascade Summary:
┌────────────────────────┬────────┐
│ Metric                 │ Value  │
├────────────────────────┼────────┤
│ Emails Found           │ 127    │
│ Emails Searched        │ 50     │
│ Emails Skipped         │ 77     │
│ Successful Searches    │ 48     │
│ Failed Searches        │ 2      │
│ HIGH Risk Emails       │ 23     │
│ MEDIUM Risk Emails     │ 18     │
│ LOW Risk Emails        │ 9      │
└────────────────────────┴────────┘
```

**Output (JSON — cascade structure):**

```json
{
  "cascade_search": true,
  "domain": "targetcorp.com",
  "timestamp": "2025-01-15T10:45:22.123456",
  "execution_time_seconds": 45.2,
  "version": "4.0",
  "emails_found": 127,
  "emails_searched": 50,
  "emails_skipped": 77,
  "all_emails": [
    "ceo@targetcorp.com",
    "admin@targetcorp.com",
    "hr@targetcorp.com",
    "it-support@targetcorp.com",
    ...
  ],
  "domain_results": {
    "query": "targetcorp.com",
    "type": "domain",
    "results": { ... },
    "summary": { ... }
  },
  "email_results": {
    "ceo@targetcorp.com": {
      "query": "ceo@targetcorp.com",
      "type": "email",
      "results": { ... },
      "summary": {
        "risk_score": "HIGH",
        ...
      },
      "status": "success"
    },
    "admin@targetcorp.com": {
      "query": "admin@targetcorp.com",
      "type": "email",
      "results": { ... },
      "summary": {
        "risk_score": "HIGH",
        ...
      },
      "status": "success"
    }
  },
  "summary": {
    "domain_search_success": 3,
    "email_searches_successful": 48,
    "email_searches_failed": 2,
    "total_risk_high": 23,
    "total_risk_medium": 18,
    "total_risk_low": 9
  }
}
```

---

### Example 4: Bulk Search

**Input (Command):**

```bash
cat targets.txt
# Contents:
# user1@example.com
# user2@example.com
# user3@example.com

python -c "
from osint_utility.orchestrator import OSINTOrchestrator
orch = OSINTOrchestrator()
results = orch.run_bulk_search(
    queries=['user1@example.com', 'user2@example.com', 'user3@example.com'],
    query_type='email',
    max_concurrent=2
)
print(results['summary'])
"
```

**Output:**

```json
{
  "bulk_search": true,
  "total_queries": 3,
  "query_type": "email",
  "timestamp": "2025-01-15T11:00:00.000000",
  "execution_time_seconds": 8.45,
  "results": {
    "user1@example.com": { ... },
    "user2@example.com": { ... },
    "user3@example.com": { ... }
  },
  "summary": {
    "successful": 3,
    "failed": 0,
    "total_risk_high": 1,
    "total_risk_medium": 1,
    "total_risk_low": 1
  }
}
```

---

### Example 5: Markdown Report Output

When using `--report report.md`, the following Markdown file is generated:

```markdown
# OSINT Combined Intelligence Report

**Query:** `ceo@targetcorp.com`
**Type:** email
**Generated:** 2025-01-15T09:23:17.843210
**Execution Time:** 2.34s
**Version:** 4.0

---

## Executive Summary

**Risk Score:** HIGH
**Sources with Data:** 2 / 3

### Key Findings
- DeHashed: 47 breach entries
- Cypher Dynamics: 12 credential hits

### Recommendations
1. Rotate all exposed passwords immediately
2. Enable 2FA/MFA everywhere
3. Monitor for further leaks using this tool regularly
4. Consider professional incident response if corporate account

## Detailed Source Results

### OSINT INDUSTRIES
**Status:** success

```json
{ "profiles": [...], "accounts": [...] }
```

### DEHASHED
**Status:** success

```json
{ "entries": [...], "total": 47 }
```

### CYPHER DYNAMICS
**Status:** success

```json
{ "credentials": [...], "total": 12 }
```

---
*Report generated by OSINT Combined Search v4*
```

---

## Web Application

Launch the web UI:

```bash
python osint_web_app.py
```

Then open `http://localhost:5000` in your browser.

### Web UI Features

- **Dark Theme** — Modern Bootstrap 5 cyber-themed interface
- **Sidebar Controls** — Query input, type selector, source selection, advanced filters
- **Cascade Toggle** — Enable domain-to-email cascade search (domain queries only)
- **Bulk Search Modal** — Run up to 50 queries at once with concurrency control
- **Tabbed Results** — Summary, Sources, Report, and Emails (cascade only)
- **Live Stats** — Search count and threat counter (persisted in localStorage)
- **One-Click Downloads** — Export results as JSON or Markdown
- **Responsive Design** — Works on desktop and mobile

### Web UI Screenshot Description

```
┌─────────────────────────────────────────────────────────────┐
│  🔒 OSINT Combined Search v4                    [Modular]   │
├─────────────────┬───────────────────────────────────────────┤
│                 │                                           │
│  🔍 New Search  │         Ready for OSINT Search            │
│  ─────────────  │         🛡️                                │
│  Query: [____]  │                                           │
│  Type:  [Email▼]│      Enter a query on the left to begin   │
│  Sources: [☑☑☑] │         cross-platform intelligence       │
│                 │              gathering.                   │
│  [🌊 Cascade]   │                                           │
│                 │                                           │
│  [⚙️ Advanced]  │                                           │
│                 │                                           │
│  [🚀 Launch     │                                           │
│   Search]       │                                           │
│                 │                                           │
│  ⚡ Quick Stats │                                           │
│  ┌─────┬─────┐  │                                           │
│  │  12 │  7  │  │                                           │
│  │Srch │Thrts│  │                                           │
│  └─────┴─────┘  │                                           │
│                 │                                           │
└─────────────────┴───────────────────────────────────────────┘
```

---

## Advanced Features

### Cascade Domain-to-Email Search

When searching a domain with `--cascade`, the tool:

1. Performs an initial domain search across all sources
2. Extracts all unique email addresses from the results using regex
3. Searches each discovered email individually (up to 50 by default)
4. Compiles a comprehensive report with per-email risk scores

Use case: Reconnaissance on a corporate domain to discover and assess all exposed employee accounts.

### Client-Side Filtering

Filters are applied after API responses are received:

| Filter | Behavior |
|--------|----------|
| `min_count` | Requires entry to appear in at least N breaches |
| `min_password_len` | Rejects passwords shorter than N characters |
| `only_passwords` | Drops entries without a cleartext password field |
| `regex` | Keeps only entries matching the pattern anywhere in JSON |
| `after_date` / `before_date` | Filters by breach_date or date fields |

### Risk Scoring Logic

| Score | Condition |
|-------|-----------|
| **HIGH** | 2+ sources returned results AND password-related data detected |
| **MEDIUM** | 2+ sources returned results but no password data |
| **LOW** | Only 1 source returned results |
| **UNKNOWN** | No sources returned usable data |

---

## Troubleshooting

### DeHashed 401 Unauthorized

DeHashed may require Basic Auth instead of Bearer. Set both:

```bash
export DEHASHED_API_KEY="your_key"
export DEHASHED_EMAIL="your_registered_email@example.com"
```

The tool automatically falls back to Basic Auth if Bearer fails.

### Missing Rich Output

Install the `rich` package:

```bash
pip install rich
```

The tool gracefully falls back to plain JSON if Rich is unavailable.

### API Timeouts

Increase the timeout:

```bash
python osint_combined_search.py -q "target@example.com" --config osint_config.json
```

Or set environment variable:

```bash
export OSINT_TIMEOUT=60
```

### No Results from a Source

- Verify the API key is correct and active
- Check the source's status page for outages
- Ensure your query type is supported by that source
- Review rate limits (the tool does not yet handle rate-limit retries)

---

## Legal & Ethical Notice

**This tool is for authorized security research, red teaming, and personal account monitoring only.**

- Do **not** use on systems or individuals without explicit permission.
- Respect all platform Terms of Service and rate limits.
- The authors are not responsible for misuse.
- Many jurisdictions require consent for OSINT on third parties.

Always operate ethically and within the law.

---

## License

MIT License — use responsibly.

---

**OSINT Combined Search v4** — Built for the security community.

