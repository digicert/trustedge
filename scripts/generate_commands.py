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

VERSION = os.environ.get("TRUSTEDGE_VERSION", "latest")
MAX_API_ATTEMPTS = int(os.environ.get("AI_MAX_ATTEMPTS", "3"))

# ── Provider selection ────────────────────────────────────────────────────────
# Priority order (first key found wins):
#   1. HF_TOKEN         → Hugging Face router (free, no credit card)
#   2. OPENAI_API_KEY   → OpenAI direct (~$0.01/run)
# Override provider with: AI_PROVIDER=huggingface | openai
_provider_hint = os.environ.get("AI_PROVIDER", "").lower()
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")

if _provider_hint == "openai" or (OPENAI_KEY and not HF_TOKEN):
    AI_PROVIDER = "openai"
    AI_BASE_URL = "https://api.openai.com/v1"
    AI_API_KEY  = OPENAI_KEY
    MODEL       = os.environ.get("AI_MODEL", "gpt-4o")
elif HF_TOKEN or _provider_hint == "huggingface":
    AI_PROVIDER = "huggingface"
    AI_BASE_URL = "https://router.huggingface.co/v1"
    AI_API_KEY  = HF_TOKEN
    MODEL       = os.environ.get("AI_MODEL", "openai/gpt-oss-120b:fastest")
else:
    print("ERROR: No AI provider configured.")
    print("  Set HF_TOKEN  (Hugging Face — free at hf.co/settings/tokens)")
    print("  or OPENAI_API_KEY  (OpenAI — platform.openai.com/api-keys)")
    sys.exit(1)

print(f"  Provider : {AI_PROVIDER}  ({AI_BASE_URL})")
print(f"  Model    : {MODEL}")

# ── Step 1: Define authoritative doc pages ────────────────────────────────────
# These are the DigiCert docs that contain real TrustEdge CLI commands.
# Add new pages here whenever DigiCert publishes new sections.

DOC_PAGES = [
    # ── Install & configure ──
    "https://dev.digicert.com/trustedge/install-and-configure/install-trustedge-on-linux.html",
    "https://dev.digicert.com/trustedge/install-and-configure/install-and-run-trustedge-with-zephyr-rtos.html",
    "https://dev.digicert.com/trustedge/install-and-configure/configure-trustedge.html",
    "https://dev.digicert.com/trustedge/install-and-configure/manage-the-keystore.html",
    # ── CLI reference (authoritative command definitions) ──
    "https://dev.digicert.com/trustedge/cli-reference/trustedge.html",
    "https://dev.digicert.com/trustedge/cli-reference/trustedge-agent.html",
    "https://dev.digicert.com/trustedge/cli-reference/trustedge-certificate.html",
    "https://dev.digicert.com/trustedge/cli-reference/trustedge-certificate/trustedge-certificate-est.html",
    "https://dev.digicert.com/trustedge/cli-reference/trustedge-certificate/trustedge-certificate-scep.html",
    "https://dev.digicert.com/trustedge/cli-reference/trustedge-mqtt.html",
    # ── Tutorials (real worked examples) ──
    "https://dev.digicert.com/trustedge/tutorials/generate-software-based-private-key.html",
    "https://dev.digicert.com/trustedge/tutorials/generate-hardware-based-private-key-tpm2.html",
    "https://dev.digicert.com/trustedge/tutorials/generate-a-x-509-certificate.html",
    "https://dev.digicert.com/trustedge/tutorials/create-a-certificate-signing-request-csr.html",
    "https://dev.digicert.com/trustedge/tutorials/est-enrollment.html",
    "https://dev.digicert.com/trustedge/tutorials/take-ownership-of-a-tpm.html",
    "https://dev.digicert.com/trustedge/tutorials/using-pqc-to-secure-mqtt-with-trustedge.html",
    "https://dev.digicert.com/trustedge/tutorials/initialize-and-start-trustedge-trustedge-agent.html",
    # ── System requirements ──
    "https://dev.digicert.com/trustedge/system-requirements.html",
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

    # Extract every <pre> and (non-nested) <code> block — these are the real commands
    blocks = []
    for tag in soup.find_all(["pre", "code"]):
        if tag.name == "code" and tag.find_parent("pre") is not None:
            continue
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

client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)

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
