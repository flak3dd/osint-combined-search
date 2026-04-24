#!/usr/bin/env python3
"""
OSINT Combined Search Utility v4
================================
Combines Osint Industries, DeHashed, and Cypher Dynamics with advanced filters,
cross-source intelligence, beautiful reports, and web UI support.

Author: Enhanced iteratively based on user feedback
License: MIT (for ethical OSINT use only)
"""

import os
import sys
import json
import time
import argparse
import hashlib
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
import requests
from dotenv import load_dotenv

# Optional rich for beautiful CLI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

load_dotenv()

console = Console() if RICH_AVAILABLE else None

class OSINTCombinedSearch:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_keys = {
            "osint_industries": os.getenv("OSINT_INDUSTRIES_API_KEY") or self.config.get("osint_industries_api_key"),
            "dehashed": os.getenv("DEHASHED_API_KEY") or self.config.get("dehashed_api_key"),
            "cypher_dynamics": os.getenv("CYPHER_DYNAMICS_API_KEY") or self.config.get("cypher_dynamics_api_key"),
        }
        self.cypher_url = os.getenv("CYPHER_DYNAMICS_API_URL", "https://api.cypherdynamics.com/search")
        self.timeout = int(os.getenv("OSINT_TIMEOUT", 30))
        self.max_workers = 3
        self.results_cache = {}

    # ==================== CORE SEARCH METHODS (v3 preserved + improved) ====================

    def search_osint_industries(self, query: str, query_type: str, filters: Dict) -> Dict:
        """Osint Industries v2 API"""
        if not self.api_keys["osint_industries"]:
            return {"error": "No OSINT Industries API key", "source": "osint_industries"}

        url = "https://api.osint.industries/v2/request"
        headers = {
            "Authorization": f"Bearer {self.api_keys['osint_industries']}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "type": query_type,
            "premium": filters.get("premium", True),
            "include_raw": True
        }
        if filters.get("min_count"):
            payload["min_count"] = filters["min_count"]

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return {"source": "osint_industries", "results": data, "status": "success"}
        except Exception as e:
            return {"source": "osint_industries", "error": str(e), "status": "failed"}

    def search_dehashed(self, query: str, query_type: str, filters: Dict) -> Dict:
        """DeHashed v2 API with smart auth fallback"""
        if not self.api_keys["dehashed"]:
            return {"error": "No DeHashed API key", "source": "dehashed"}

        url = "https://api.dehashed.com/v2/search"
        headers = {"Content-Type": "application/json"}

        # Try common auth patterns
        auth_header = f"Bearer {self.api_keys['dehashed']}"
        headers["Authorization"] = auth_header

        payload = {
            "query": query,
            "type": query_type if query_type in ["email", "username", "password", "hashed_password", "domain", "ip"] else "email",
            "page": 1,
            "size": 100
        }

        # Apply date filters if supported
        if filters.get("after_date"):
            payload["after"] = filters["after_date"]
        if filters.get("before_date"):
            payload["before"] = filters["before_date"]
        if filters.get("min_count"):
            payload["min_count"] = filters["min_count"]

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 401:
                # Fallback to Basic Auth (email:apikey) - user should set DEHASHED_EMAIL
                email = os.getenv("DEHASHED_EMAIL", "user@example.com")
                import base64
                basic = base64.b64encode(f"{email}:{self.api_keys['dehashed']}".encode()).decode()
                headers["Authorization"] = f"Basic {basic}"
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return {"source": "dehashed", "results": data, "entries_found": len(data.get("entries", [])), "status": "success"}
        except Exception as e:
            return {"source": "dehashed", "error": str(e), "status": "failed"}

    def search_cypher_dynamics(self, query: str, query_type: str, filters: Dict) -> Dict:
        """Cypher Dynamics Stealer Log / Credential Search"""
        if not self.api_keys["cypher_dynamics"]:
            return {"error": "No Cypher Dynamics API key", "source": "cypher_dynamics"}

        headers = {
            "Authorization": f"Bearer {self.api_keys['cypher_dynamics']}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "query_type": query_type,
            "include_cookies": True,
            "include_sessions": True,
            "min_password_length": filters.get("min_password_len", 0)
        }
        if filters.get("regex"):
            payload["regex_filter"] = filters["regex"]
        if filters.get("after_date"):
            payload["after_date"] = filters["after_date"]

        try:
            resp = requests.post(self.cypher_url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return {"source": "cypher_dynamics", "results": data, "status": "success"}
        except Exception as e:
            return {"source": "cypher_dynamics", "error": str(e), "status": "failed"}

    # ==================== FILTERING & POST-PROCESSING (v3) ====================

    def apply_advanced_filters(self, raw_results: Dict, filters: Dict) -> Dict:
        """Client-side intelligent filtering + source-aware processing"""
        filtered = {"sources": {}, "summary": {}}
        total_filtered = 0

        for source, data in raw_results.get("results", {}).items():
            source_results = data.get("results", {})
            filtered_entries = []

            # DeHashed specific
            if source == "dehashed" and "entries" in source_results:
                for entry in source_results["entries"]:
                    if self._passes_filters(entry, filters):
                        filtered_entries.append(entry)
                filtered["sources"][source] = {
                    **data,
                    "results": {"entries": filtered_entries},
                    "entries_found": len(filtered_entries)
                }

            # Cypher Dynamics
            elif source == "cypher_dynamics" and "credentials" in source_results:
                for cred in source_results.get("credentials", []):
                    if self._passes_filters(cred, filters):
                        filtered_entries.append(cred)
                filtered["sources"][source] = {
                    **data,
                    "results": {"credentials": filtered_entries, **{k: v for k, v in source_results.items() if k != "credentials"}}
                }

            # Osint Industries (rich profile - keep most)
            else:
                filtered["sources"][source] = data

            total_filtered += len(filtered_entries) if filtered_entries else 1

        filtered["summary"] = {
            "total_filtered_entries": total_filtered,
            "filters_applied": filters
        }
        return filtered

    def _passes_filters(self, entry: Dict, filters: Dict) -> bool:
        """Universal filter checker"""
        if filters.get("only_passwords") and not entry.get("password") and not entry.get("cleartext_password"):
            return False

        pwd = entry.get("password") or entry.get("cleartext_password") or ""
        if filters.get("min_password_len") and len(pwd) < filters["min_password_len"]:
            return False

        if filters.get("min_count") and entry.get("count", 0) < filters["min_count"]:
            return False

        if filters.get("regex"):
            regex = re.compile(filters["regex"], re.IGNORECASE)
            text = json.dumps(entry)
            if not regex.search(text):
                return False

        # Date filters (simplified)
        breach_date = entry.get("breach_date") or entry.get("date")
        if breach_date and filters.get("after_date"):
            if breach_date < filters["after_date"]:
                return False
        if breach_date and filters.get("before_date"):
            if breach_date > filters["before_date"]:
                return False

        return True

    # ==================== EMAIL EXTRACTION & CASCADE ====================

    def extract_emails_from_results(self, results: Dict) -> List[str]:
        """Extract email addresses from search results."""
        emails = set()
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        for source, data in results.get("results", {}).items():
            source_results = data.get("results", {})
            
            if isinstance(source_results, dict):
                if "entries" in source_results:
                    for entry in source_results["entries"]:
                        if isinstance(entry, dict):
                            for field in ["email", "username", "name"]:
                                if field in entry:
                                    text = str(entry[field])
                                    found = re.findall(email_pattern, text, re.IGNORECASE)
                                    emails.update(found)
                            text = json.dumps(entry)
                            found = re.findall(email_pattern, text, re.IGNORECASE)
                            emails.update(found)
                elif "credentials" in source_results:
                    for cred in source_results["credentials"]:
                        if isinstance(cred, dict):
                            text = json.dumps(cred)
                            found = re.findall(email_pattern, text, re.IGNORECASE)
                            emails.update(found)
                else:
                    text = json.dumps(source_results)
                    found = re.findall(email_pattern, text, re.IGNORECASE)
                    emails.update(found)
            elif isinstance(source_results, list):
                for item in source_results:
                    if isinstance(item, dict):
                        text = json.dumps(item)
                        found = re.findall(email_pattern, text, re.IGNORECASE)
                        emails.update(found)
                    else:
                        text = str(item)
                        found = re.findall(email_pattern, text, re.IGNORECASE)
                        emails.update(found)
        
        return sorted(list(emails))

    def cascade_domain_to_emails(self, domain: str, filters: Optional[Dict] = None,
                                 sources: Optional[List[str]] = None,
                                 max_email_searches: int = 50) -> Dict:
        """Search for a domain, then search for all emails found in the results."""
        start_time = time.time()
        filters = filters or {}
        sources = sources or ["osint_industries", "dehashed", "cypher_dynamics"]
        
        # First, search for the domain
        domain_results = self.run_search(
            query=domain,
            query_type="domain",
            filters={},
            sources=sources,
            enable_rich_output=False
        )
        
        # Extract emails from domain results
        emails = self.extract_emails_from_results(domain_results)
        
        # Limit the number of emails to search
        emails_to_search = emails[:max_email_searches] if len(emails) > max_email_searches else emails
        
        # Search for each email
        email_results = {}
        if emails_to_search:
            for email in emails_to_search:
                try:
                    email_result = self.run_search(
                        query=email,
                        query_type="email",
                        filters=filters,
                        sources=sources,
                        enable_rich_output=False
                    )
                    email_results[email] = email_result
                except Exception as e:
                    email_results[email] = {
                        "error": str(e),
                        "status": "failed"
                    }
        
        # Compile comprehensive results
        cascade_results = {
            "cascade_search": True,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "domain_results": domain_results,
            "emails_found": len(emails),
            "emails_searched": len(emails_to_search),
            "emails_skipped": len(emails) - len(emails_to_search),
            "email_results": email_results,
            "all_emails": emails,
            "summary": {
                "domain_search_success": domain_results.get("summary", {}).get("total_sources_with_results", 0),
                "email_searches_successful": sum(1 for r in email_results.values() if r.get("status") != "failed"),
                "email_searches_failed": sum(1 for r in email_results.values() if r.get("status") == "failed"),
                "total_risk_high": sum(1 for r in email_results.values() if r.get("summary", {}).get("risk_score") == "HIGH"),
                "total_risk_medium": sum(1 for r in email_results.values() if r.get("summary", {}).get("risk_score") == "MEDIUM"),
                "total_risk_low": sum(1 for r in email_results.values() if r.get("summary", {}).get("risk_score") == "LOW"),
            },
            "execution_time_seconds": round(time.time() - start_time, 2),
            "version": "4.0"
        }
        
        return cascade_results

    # ==================== MAIN ORCHESTRATION ====================

    def run_search(self, query: str, query_type: str = "email", filters: Optional[Dict] = None,
                   sources: Optional[List[str]] = None, enable_rich_output: bool = True) -> Dict:
        """Main entry point - runs everything in parallel"""
        start_time = time.time()
        filters = filters or {}
        sources = sources or ["osint_industries", "dehashed", "cypher_dynamics"]

        if RICH_AVAILABLE:
            rprint(Panel(f"[bold cyan]OSINT COMBINED SEARCH v4[/bold cyan] | Query: [yellow]{query}[/yellow] | Type: {query_type}", border_style="blue"))

        raw_results = {"query": query, "type": query_type, "timestamp": datetime.now().isoformat(), "results": {}}

        # Parallel execution
        search_funcs = {
            "osint_industries": self.search_osint_industries,
            "dehashed": self.search_dehashed,
            "cypher_dynamics": self.search_cypher_dynamics
        }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {}
            for src in sources:
                if src in search_funcs:
                    future = executor.submit(search_funcs[src], query, query_type, filters)
                    future_to_source[future] = src

            for future in as_completed(future_to_source):
                src = future_to_source[future]
                try:
                    result = future.result()
                    raw_results["results"][src] = result
                except Exception as e:
                    raw_results["results"][src] = {"error": str(e), "status": "failed"}

        # Apply filters
        filtered_results = self.apply_advanced_filters(raw_results, filters)

        # Final summary
        filtered_results["summary"] = self._generate_enhanced_summary(filtered_results, query, filters)
        filtered_results["execution_time_seconds"] = round(time.time() - start_time, 2)
        filtered_results["version"] = "4.0"

        return filtered_results

    def _generate_enhanced_summary(self, results: Dict, query: str, filters: Dict) -> Dict:
        """Build rich summary"""
        summary = {
            "query": query,
            "sources_searched": list(results.get("results", {}).keys()),
            "total_sources_with_results": sum(1 for r in results.get("results", {}).values() if r.get("status") == "success"),
            "key_findings": [],
            "risk_score": "UNKNOWN",
            "recommendations": [],
            "filters_used": filters,
        }

        # Extract key stats
        for src, data in results.get("results", {}).items():
            if data.get("status") == "success":
                if src == "dehashed":
                    count = data.get("entries_found", 0)
                    summary["key_findings"].append(f"DeHashed: {count} breach entries")
                elif src == "cypher_dynamics":
                    creds = len(data.get("results", {}).get("credentials", []))
                    summary["key_findings"].append(f"Cypher Dynamics: {creds} credential hits")
                elif src == "osint_industries":
                    summary["key_findings"].append("OSINT Industries: Rich profile data retrieved")

        # Simple risk scoring
        total_hits = len([k for k in results.get("results", {}) if results["results"][k].get("status") == "success"])
        if total_hits >= 2:
            summary["risk_score"] = "HIGH" if any("password" in str(v).lower() for v in results.get("results", {}).values()) else "MEDIUM"
        else:
            summary["risk_score"] = "LOW"

        summary["recommendations"] = [
            "Rotate all exposed passwords immediately",
            "Enable 2FA/MFA everywhere",
            "Monitor for further leaks using this tool regularly",
            "Consider professional incident response if corporate account"
        ]

        return summary

    # ==================== OUTPUT FORMATTING ====================

    def pretty_print(self, results: Dict):
        """Beautiful terminal output"""
        if not RICH_AVAILABLE:
            print(json.dumps(results, indent=2))
            return

        rprint(Panel(f"[bold green]✅ Search Complete in {results.get('execution_time_seconds', 0)}s[/bold green]", border_style="green"))

        # Summary table
        table = Table(title="Quick Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        for k, v in results.get("summary", {}).items():
            if isinstance(v, (str, int, float, bool)):
                table.add_row(str(k), str(v)[:80])
        rprint(table)

        # Per source panels
        for source, data in results.get("results", {}).items():
            status = data.get("status", "unknown")
            color = "green" if status == "success" else "red"
            rprint(Panel(f"Status: [{color}]{status}[/{color}]\n{json.dumps(data.get('results', {}), indent=2)[:1500]}...",
                         title=f"[bold]{source.upper()}[/bold]", border_style=color))

    def generate_markdown_report(self, results: Dict, output_path: str):
        """Professional Markdown intelligence report"""
        md = f"""# OSINT Combined Intelligence Report

**Query:** `{results['query']}`  
**Type:** {results.get('type', 'N/A')}  
**Generated:** {results.get('timestamp')}  
**Execution Time:** {results.get('execution_time_seconds')}s  
**Version:** {results.get('version')}

---

## Executive Summary

**Risk Score:** {results.get('summary', {}).get('risk_score', 'UNKNOWN')}  
**Sources with Data:** {results.get('summary', {}).get('total_sources_with_results', 0)} / {len(results.get('summary', {}).get('sources_searched', []))}

### Key Findings
"""
        for finding in results.get("summary", {}).get("key_findings", []):
            md += f"- {finding}\n"

        md += "\n### Recommendations\n"
        for rec in results.get("summary", {}).get("recommendations", []):
            md += f"1. {rec}\n"

        # Per source
        md += "\n## Detailed Source Results\n\n"
        for source, data in results.get("results", {}).items():
            md += f"### {source.upper()}\n"
            md += f"**Status:** {data.get('status')}\n\n"
            md += "```json\n" + json.dumps(data.get("results", {}), indent=2)[:4000] + "\n```\n\n"

        md += "\n---\n*Report generated by OSINT Combined Search v4*\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)

        if RICH_AVAILABLE:
            rprint(f"[green]📄 Markdown report saved to {output_path}[/green]")


def main():
    parser = argparse.ArgumentParser(description="OSINT Combined Search v4")
    parser.add_argument("-q", "--query", required=True, help="Search query (email, username, domain, etc.)")
    parser.add_argument("-t", "--type", default="email", choices=["email", "username", "password", "hashed_password", "domain", "ip", "name", "phone", "wallet"])
    parser.add_argument("--sources", default="osint_industries,dehashed,cypher_dynamics", help="Comma-separated sources")
    parser.add_argument("--min-count", type=int, help="Minimum appearances in breaches")
    parser.add_argument("--min-password-len", type=int, help="Minimum password length")
    parser.add_argument("--only-passwords", action="store_true", help="Only return entries with cleartext passwords")
    parser.add_argument("--regex", help="Regex filter on any field")
    parser.add_argument("--after-date", help="YYYY-MM-DD - only after this date")
    parser.add_argument("--before-date", help="YYYY-MM-DD")
    parser.add_argument("--cascade", action="store_true", help="For domain searches: extract emails and search each one")
    parser.add_argument("--pretty", action="store_true", help="Beautiful colored output")
    parser.add_argument("--report", metavar="FILE.md", help="Generate full Markdown intelligence report")
    parser.add_argument("--save-raw", metavar="DIR", help="Save individual JSON per source")
    parser.add_argument("--config", help="Path to osint_config.json")

    args = parser.parse_args()

    # Load config if provided
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)

    filters = {
        "min_count": args.min_count,
        "min_password_len": args.min_password_len,
        "only_passwords": args.only_passwords,
        "regex": args.regex,
        "after_date": args.after_date,
        "before_date": args.before_date
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    sources = [s.strip() for s in args.sources.split(",")]

    searcher = OSINTCombinedSearch(config)
    
    if args.type == "domain" and args.cascade:
        results = searcher.cascade_domain_to_emails(
            domain=args.query,
            filters=filters,
            sources=sources
        )
    else:
        results = searcher.run_search(
            query=args.query,
            query_type=args.type,
            filters=filters,
            sources=sources
        )

    if args.pretty:
        searcher.pretty_print(results)
    else:
        print(json.dumps(results, indent=2))

    if args.report:
        searcher.generate_markdown_report(results, args.report)

    if args.save_raw:
        os.makedirs(args.save_raw, exist_ok=True)
        for src, data in results.get("results", {}).items():
            with open(os.path.join(args.save_raw, f"{src}.json"), "w") as f:
                json.dump(data, f, indent=2)
        if RICH_AVAILABLE:
            rprint(f"[green]Raw files saved to {args.save_raw}/[/green]")

    # Exit code based on success
    success = any(r.get("status") == "success" for r in results.get("results", {}).values())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

