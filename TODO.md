# TODO: Remove AI Integration + Add Domain-to-Email Cascade Search

## Remove AI Integration
- [x] 1. Delete `osint_utility/utils/grok_analyzer.py` (no file exists, nothing to do)
- [x] 2. Edit `osint_utility/utils/config.py` (no file exists, nothing to do)
- [x] 3. Edit `osint_utility/orchestrator.py` (no file exists, nothing to do)
- [x] 4. Edit `osint_utility/main.py` (no file exists, nothing to do)
- [x] 5. Edit `osint_combined_search.py` — no grok/AI code found, already clean
- [ ] 6. Edit `osint_web_app.py` — complete the file, add cascade checkbox support
- [ ] 7. Edit `osint_utility/utils/formatter.py` (no file exists, nothing to do)
- [x] 8. Edit `requirements.txt` — remove `openai` dependency
- [x] 9. Edit `osint_config.json` — remove `grok_api_key` field

## Complete osint_web_app.py
- [ ] 10. Add Flask routes (`/`, `/api/search`, `/api/health`, `/api/download/json`, `/api/download/markdown`)
- [ ] 11. Complete HTML template with results display, tabs, risk badges, downloads
- [ ] 12. Add JavaScript for localStorage stats, loading spinner, copy-to-clipboard

## Testing
- [ ] 13. Verify imports work and no grok references remain

