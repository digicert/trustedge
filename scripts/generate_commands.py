#!/usr/bin/env python3
"""
generate_commands.py
────────────────────
Fetches TrustEdge documentation from dev.digicert.com (live, authoritative),
extracts real code blocks with their source URLs, then calls GitHub Models API
to structure them into commands.json.

Every generated command carries a source_url field pointing to the exact doc
page it came from — wrong commands are immediately traceable and fixable.

Run locally:
  pip install openai requests beautifulsoup4
  export GITHUB_TOKEN=<PAT with models:read>
  export TRUSTEDGE_VERSION=v24.8.0
  python scripts/generate_commands.py
"""

import json
import os
import pathlib
import textwrap
import time
import datetime
import re
import sys
import requests
from bs4 import BeautifulSoup
from openai import APIConnectionError, OpenAI

REPO_ROOT = pathlib.Path(__file__).parent.parent
OUT_FILE  = REPO_ROOT / "docs" / "data" / "commands.json"

MODEL   = os.environ.get("AI_MODEL", "openai/gpt-4o")
VERSION = os.environ.get("TRUSTEDGE_VERSION", "latest")
TOKEN   = os.environ["GITHUB_TOKEN"]   # injected by the Action or set locally
MAX_API_ATTEMPTS = int(os.environ.get("AI_MAX_ATTEMPTS", "3"))

# ── Step 1: Define authoritative doc pages ────────────────────────────────────
# These are the DigiCert docs that contain real TrustEdge CLI commands.
# Add new pages here whenever DigiCert publishes new sections.

DOC_PAGES = [
    # Core reference — most important
    "https://dev.digicert.com/en/trustedge/trustedge-command-reference.html",
    # Install & configure
    "https://dev.digicert.com/en/trustedge/install-and-configure.html",
    "https://dev.digicert.com/en/trustedge/install-and-configure/install-trustedge-on-linux.html",
    "https://dev.digicert.com/en/trustedge/install-and-configure/install-and-run-trustedge-with-zephyr-rtos.html",
    "https://dev.digicert.com/en/trustedge/install-and-configure/manage-the-keystore.html",
    # Certificate operations
    "https://dev.digicert.com/en/trustedge/trustedge-command-reference/certificate-commands.html",
    "https://dev.digicert.com/en/trustedge/trustedge-command-reference/key-commands.html",
    "https://dev.digicert.com/en/trustedge/trustedge-command-reference/mqtt-commands.html",
    "https://dev.digicert.com/en/trustedge/trustedge-command-reference/est-commands.html",
    # System requirements
    "https://dev.digicert.com/en/trustedge/system-requirements.html",
    # Tutorials
    "https://dev.digicert.com/en/trustedge/tutorials.html",
]

# Also read the repo's own READMEs — useful for TPM provisioning commands
# that may only be documented there
REPO_DOCS = {
    "README":        REPO_ROOT / "README.md",
    "SecureElement": REPO_ROOT / "tools" / "SecureElement" / "README.md",
    "pqc_demo":      REPO_ROOT / "examples" / "pqc-demo" / "README.md",
}

# ── Step 2: Fetch and parse live documentation ────────────────────────────────

def fetch_page(url: str) -> dict | None:
    """Fetch a doc page, return { url, title, code_blocks: [str] } or None."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "TrustEdge-CmdGen/1.0"})
        if resp.status_code == 404:
            print(f"  ⚠ 404 (page may not exist yet): {url}")
            return None
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠ Could not fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.find("title")
    title = title.get_text(strip=True) if title else url

    # Extract every <code> and <pre> block — these are the real commands
    blocks = []
    for tag in soup.find_all(["pre", "code"]):
        text = tag.get_text()
        # Only keep blocks that look like shell commands (contain trustedge, sudo, wget, etc.)
        if re.search(r'\btrustedge\b|sudo\s+\w|wget\s+http|dpkg\s+-i|apt\s+install|git\s+clone', text):
            clean = text.strip()
            if clean and len(clean) > 5:
                blocks.append(clean)

    return {"url": url, "title": title, "code_blocks": blocks}

print("── Step 1: Fetching authoritative docs from dev.digicert.com ──")
fetched_pages = []
all_code_blocks = []   # flat list of { url, block } for the hallucination guard

for url in DOC_PAGES:
    print(f"  → {url}")
    page = fetch_page(url)
    time.sleep(0.5)   # be polite to the server
    if page and page["code_blocks"]:
        fetched_pages.append(page)
        for block in page["code_blocks"]:
            all_code_blocks.append({"url": url, "block": block})
        print(f"     ✓ {len(page['code_blocks'])} command blocks found")
    elif page:
        print(f"     – no command blocks found (page may be overview only)")

if not all_code_blocks:
    print("✗ FAIL — No command blocks fetched from any doc page.")
    print("  Check network access and that the URLs above are correct.")
    sys.exit(1)

# Read repo docs for TPM / PQC commands not on the web portal
print("\n── Step 2: Reading repo documentation ──")
repo_doc_text = {}
for name, path in REPO_DOCS.items():
    try:
        repo_doc_text[name] = path.read_text(encoding="utf-8")
        print(f"  ✓ {path.name}")
    except FileNotFoundError:
        print(f"  – {path.name} not found, skipping")

# ── Step 3: Build the AI prompt from real sources only ───────────────────────

def format_fetched_pages(pages: list[dict]) -> str:
    parts = []
    for p in pages:
        if not p["code_blocks"]:
            continue
        parts.append(f"=== SOURCE: {p['url']} ===\nTitle: {p['title']}")
        for block in p["code_blocks"]:
            parts.append(f"```\n{block}\n```")
    return "\n\n".join(parts)

SYSTEM_PROMPT = textwrap.dedent("""
You are a technical documentation assistant for DigiCert TrustEdge.
Your ONLY job is to structure commands that already exist in the provided sources.

CRITICAL RULES — any violation causes automated rejection:
1. USE ONLY commands from the provided source pages. Do NOT invent any command,
   flag, argument, or path. If a command is not in the sources, omit it entirely.
2. Every step entry MUST include a source_url field identifying where the commands came from:
   - If the source is a dev.digicert.com page, use the exact page URL.
   - If the source is repo documentation included below, use the repo path shown in the SOURCE header.
3. Use {{VERSION}} wherever a version number appears (e.g. in .deb filenames).
4. Structure:
   Top-level arch keys: x86_64, aarch64, arm32, zephyr
   Each arch has step keys: prerequisites, install, tpm_provision,
     cert_selfsigned, cert_est, run_cli, run_agent, pqc_demo, verify
   Each step: {
     "title": "string",
     "commands": ["string"],
     "source_url": "string",
     "notes": ["string"]            ← optional, from the docs
   }
5. Output ONLY valid JSON. No markdown fences. No explanation outside JSON.
6. If you cannot find a real command for a step from the sources, omit that step.
   An omitted step is far better than an invented command.
""").strip()

USER_PROMPT = f"""TrustEdge version: {VERSION}

── AUTHORITATIVE SOURCES (dev.digicert.com) ──
Use ONLY the commands found in these pages:

{format_fetched_pages(fetched_pages)}

── REPO DOCS (TPM provisioning and PQC demo — repo-only content) ──
{repo_doc_text.get('SecureElement', '')}
{repo_doc_text.get('pqc_demo', '')}

Generate commands.json now. Only include commands from the above sources.
"""

# ── Step 4: Call GitHub Models API ───────────────────────────────────────────

print(f"\n── Step 3: Calling GitHub Models API  model={MODEL} ──")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=TOKEN,
)

response = None
for attempt in range(1, MAX_API_ATTEMPTS + 1):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": USER_PROMPT},
            ],
            temperature=0.0,      # zero temp = maximally faithful, no creativity
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        break
    except APIConnectionError as exc:
        if attempt == MAX_API_ATTEMPTS:
            print(f"WARNING: GitHub Models API unreachable after {attempt} attempts: {exc}")
            break
        wait_seconds = min(10, attempt * 2)
        print(
            f"WARNING: API connection failed (attempt {attempt}/{MAX_API_ATTEMPTS}): {exc}. "
            f"Retrying in {wait_seconds}s..."
        )
        time.sleep(wait_seconds)

if response is None:
    if OUT_FILE.exists():
        print(f"Keeping existing {OUT_FILE}; skipping regeneration for this run.")
        raise SystemExit(0)
    print("ERROR: Unable to generate commands.json and no existing file is available.")
    raise SystemExit(1)

raw = response.choices[0].message.content

# ── Step 5: Validate JSON ─────────────────────────────────────────────────────

try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    print("✗ FAIL — AI returned invalid JSON. commands.json NOT updated.")
    print(raw[:800])
    sys.exit(1)

# ── Step 6: Hallucination guard using real fetched blocks ─────────────────────
# Build a set of all real command tokens from the fetched pages

real_command_tokens = set()
for item in all_code_blocks:
    real_command_tokens.update(re.findall(r'trustedge\s+\w[\w\-]*', item["block"]))
    # Also capture flags like --cert, --broker etc.
    real_command_tokens.update(re.findall(r'--[\w\-]+', item["block"]))

# Include repo-doc content in the allow-list too (repo-only TPM/PQC commands)
for text in repo_doc_text.values():
    real_command_tokens.update(re.findall(r'trustedge\s+\w[\w\-]*', text))
    real_command_tokens.update(re.findall(r'--[\w\-]+', text))
def check_hallucinations(data: dict) -> list[str]:
    issues = []
    for arch, steps in data.items():
        if arch == "meta" or not isinstance(steps, dict):
            continue
        for step_name, content in steps.items():
            if not isinstance(content, dict):
                continue
            for cmd in content.get("commands", []):
                # Check trustedge subcommands
                for subcmd in re.findall(r'trustedge\s+(\w[\w\-]*)', cmd):
                    candidate = f"trustedge {subcmd}"
                    if candidate not in real_command_tokens:
                        issues.append(
                            f"  [{arch}/{step_name}] Unverified subcommand: "
                            f"`{candidate}` — not found in any fetched doc page"
                        )
                # Check flags
                for flag in re.findall(r'--[\w\-]+', cmd):
                    if flag not in real_command_tokens:
                        issues.append(
                            f"  [{arch}/{step_name}] Unverified flag: "
                            f"`{flag}` — not found in any fetched doc page"
                        )
    return issues

issues = check_hallucinations(data)

print(f"\n── Step 4: Hallucination check ──")
if issues:
    print(f"  ⚠ {len(issues)} potential issue(s) found:")
    for i in issues:
        print(i)
    if len(issues) > 8:
        print(f"✗ Too many unverified tokens ({len(issues)}). commands.json NOT updated.")
        sys.exit(1)
    print("  → Will open a PR — review these before merging.")
else:
    print("  ✓ All commands verified against fetched doc pages.")

# ── Step 7: Add meta + sources consulted ─────────────────────────────────────

data.setdefault("meta", {})
data["meta"].update({
    "version":                 VERSION,
    "model_used":              MODEL,
    "generated_at":            datetime.datetime.utcnow().isoformat() + "Z",
    "hallucination_warnings":  len(issues),
    "sources_consulted": [     # shown in the compatibility page UI
        {"url": p["url"], "title": p["title"], "blocks_found": len(p["code_blocks"])}
        for p in fetched_pages
    ],
})

# ── Step 8: Write output ──────────────────────────────────────────────────────

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"\n✓ Written {OUT_FILE}  ({OUT_FILE.stat().st_size} bytes)")
print(f"  Sources consulted: {len(fetched_pages)} pages")
print(f"  Command blocks:    {len(all_code_blocks)}")
print(f"  Warnings:          {len(issues)}")

if os.environ.get("CI"):
    gh_output = os.environ.get("GITHUB_OUTPUT", "")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"warnings={len(issues)}\n")
