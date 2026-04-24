# 🕵️‍♂️ SuperGrok OSINT Combined Search v4

**The ultimate cross-platform OSINT intelligence platform powered by xAI Grok-2**

Combines **Osint Industries**, **DeHashed**, and **Cypher Dynamics** with advanced filtering, beautiful reports, a modern web UI, **and now SuperGrok AI** for expert-level threat analysis and natural language insights.

![SuperGrok Banner](https://via.placeholder.com/1200x300/0d1117/58a6ff?text=SuperGrok+OSINT+v4+-+xAI+Powered)

## ✨ What's New in v4 (SuperGrok Edition)

- **🧠 SuperGrok AI Analysis** — Send combined results to Grok-2 for:
  - Executive threat summaries
  - Cross-source correlation detection
  - Risk scoring with justification
  - Actionable recommendations
  - Natural language Q&A chat about your results
- **Live Grok Chat** in the web app (context-aware follow-up questions)
- **One-command installer** with full PATH integration
- All v3 advanced filters preserved + enhanced
- Production-ready with retry logic, graceful fallbacks, and detailed logging

## 🚀 Quick Start (One Command)

```bash
curl -fsSL https://raw.githubusercontent.com/your-org/osint-combined/main/install.sh | bash
```

Then:

```bash
# Set keys (recommended)
export OSINT_INDUSTRIES_API_KEY="your_key"
export DEHASHED_API_KEY="your_key"
export CYPHER_DYNAMICS_API_KEY="your_key"
export GROK_API_KEY="sk-..."          # Get free at https://console.x.ai/

# CLI with AI
osint-search -q "ceo@target.com" --supergrok --pretty --report intel.md

# Web UI (http://localhost:5000)
osint-web
```

## 📋 Full Feature List

| Feature                    | Description                                                                 |
|---------------------------|-----------------------------------------------------------------------------|
| **3-Source Parallel Search** | Osint Industries + DeHashed + Cypher Dynamics (ThreadPoolExecutor)         |
| **Advanced Filters**       | `--min-count`, `--min-password-len`, `--only-passwords`, `--regex`, date ranges, source selection |
| **SuperGrok AI**           | `--supergrok` flag triggers expert Grok-2 analysis + live chat in web UI   |
| **Beautiful Output**       | Rich library colored panels, tables, syntax highlighting (graceful fallback) |
| **Markdown Reports**       | `--report report.md` with full AI section, overlaps, and recommendations   |
| **Web Interface**          | Modern Bootstrap 5 dark theme, tabs, real-time chat, one-click downloads   |
| **REST API**               | `POST /api/search` + `/api/grok_chat` for automation & integrations        |
| **Batch Mode**             | `--batch-file targets.txt` (add in future release)                         |
| **Config Support**         | `osint_config.json` + full `.env` support                                  |

## 🛠️ Configuration

Create `.env` or `osint_config.json`:

```json
{
  "osint_industries_api_key": "...",
  "dehashed_api_key": "...",
  "cypher_dynamics_api_key": "...",
  "grok_api_key": "sk-...",
  "cypher_dynamics_api_url": "https://api.cypherdynamics.com/search"
}
```

**DeHashed Note**: If you get 401 errors, also set `DEHASHED_EMAIL=your@email.com` (the script auto-falls back to Basic Auth).

## 📖 Usage Examples

### CLI
```bash
# High-value target with AI
osint-search -q "victim@company.com" \
  --min-count 5 \
  --min-password-len 10 \
  --only-passwords \
  --supergrok \
  --report ceo_high_value.md

# Focus on recent stealer logs + regex
osint-search -q "targetuser" -t username \
  --after-date 2025-01-01 \
  --regex "session|cookie|token" \
  --sources cypher_dynamics \
  --supergrok
```

### Web App Highlights
- Full filter support in sidebar
- **SuperGrok tab** shows beautiful markdown analysis from Grok-2
- Live chat: "What is the biggest risk?" / "Suggest mitigation steps"
- One-click JSON / Markdown download
- Responsive on mobile

### Programmatic (Python)
```python
from osint_combined_search import OSINTCombinedSearch

searcher = OSINTCombinedSearch()
results = searcher.run_search(
    query="target@corp.com",
    query_type="email",
    filters={"min_count": 3, "only_passwords": True},
    enable_grok=True
)

print(results["summary"]["risk_score"])
print(results["results"]["grok"]["analysis"])  # Full AI briefing
```

## 🧠 SuperGrok Prompt Engineering

The AI receives a carefully crafted prompt including:
- Full filtered results from all sources
- Applied filters
- Instructions for structured output (Executive Summary, Correlations, Risk Assessment, Recommendations, Caveats)

This produces **professional-grade** threat intelligence briefings in seconds.

## ⚖️ Legal & Ethical Notice

**This tool is for authorized security research, red teaming, and personal account monitoring only.**

- Do **not** use on systems or individuals without explicit permission.
- Respect all platform Terms of Service and rate limits.
- The authors are not responsible for misuse.
- Many jurisdictions require consent for OSINT on third parties.

Always operate ethically and within the law.

## 🗺️ Roadmap (v4.1+)

- [ ] Docker + docker-compose
- [ ] Persistent search history (SQLite)
- [ ] PDF export of reports
- [ ] Multi-user auth for web app
- [ ] Additional sources (HaveIBeenPwned, Intelligence X, etc.)
- [ ] Real-time streaming results in web UI
- [ ] Automated alert system for new leaks

## 🤝 Contributing

Pull requests welcome! Especially:
- New source integrations
- Improved Grok prompt engineering
- UI/UX enhancements

## 📄 License

MIT License — use responsibly.

---

**Built with ❤️ by Grok (xAI) • Inspired by the OSINT community**

*Upgrade to SuperGrok today and turn raw data into actionable intelligence.*