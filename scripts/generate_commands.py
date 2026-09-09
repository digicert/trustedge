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

# ── Local CLI reference (highest priority — actual binary help output) ─────────
# trustedge.txt is the output of running every `trustedge <cmd> --help`.
# It is the single source of truth for valid subcommands and flags.
CLI_REFERENCE_FILE = REPO_ROOT / "docs" / "data" / "trustedge.txt"

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


# ── TrustCore GitHub Markdown sources (raw content) ─────────────────────────
# TrustCore is TrustEdge's underlying SDK — its samples/BUILD_RUN.md contains
# the most accurate real-world command examples (build, run, configure).
GITHUB_MD_PAGES = [
    {
        "url":     "https://github.com/digicert/trustcore/blob/main/samples/trustedge/BUILD_RUN.md",
        "raw_url": "https://raw.githubusercontent.com/digicert/trustcore/main/samples/trustedge/BUILD_RUN.md",
        "title":   "TrustCore — TrustEdge Build & Run Guide (samples/trustedge/BUILD_RUN.md)",
    },
    {
        "url":     "https://github.com/digicert/trustcore",
        "raw_url": "https://raw.githubusercontent.com/digicert/trustcore/main/README.md",
        "title":   "TrustCore SDK — README",
    },
]

def fetch_markdown_page(entry: dict) -> dict | None:
    """Fetch a raw GitHub Markdown file and extract fenced shell code blocks."""
    try:
        resp = requests.get(entry["raw_url"], timeout=15,
                            headers={"User-Agent": "TrustEdge-CmdGen/1.0"})
        if resp.status_code == 404:
            print(f"  ⚠ 404: {entry['raw_url']}")
            return None
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠ Could not fetch {entry['raw_url']}: {e}")
        return None

    # Extract fenced code blocks: ```sh / ```bash / ```shell / plain ```
    raw = resp.text
    fenced = re.findall(
        r'```(?:sh|bash|shell|console|text)?\s*\n(.*?)```',
        raw, re.DOTALL | re.IGNORECASE
    )
    blocks = []
    for block in fenced:
        clean = block.strip()
        # Keep only blocks that reference trustedge or common install commands
        if re.search(r'\btrustedge\b|sudo\s+\w|wget\s+http|dpkg\s+-i|apt\s+install|git\s+clone|cmake\b|make\b', clean):
            if clean and len(clean) > 5:
                blocks.append(clean)

    return {"url": entry["url"], "title": entry["title"], "code_blocks": blocks}


# ── Load CLI reference first — used to seed the hallucination guard ───────────
print("── Step 0: Loading CLI reference (trustedge.txt) ──")
cli_reference_text = ""
try:
    cli_reference_text = CLI_REFERENCE_FILE.read_text(encoding="utf-8")
    print(f"  ✓ Loaded {CLI_REFERENCE_FILE} ({len(cli_reference_text)} chars)")
except FileNotFoundError:
    print(f"  ✗ {CLI_REFERENCE_FILE} not found — hallucination guard will rely on web sources only")

# Extract VALID top-level subcommands from the CLI reference.
# The help text lists them as bare words under "Commands:", so we extract those
# AND also match any "trustedge <word>" patterns.
VALID_SUBCOMMANDS = set(re.findall(r'trustedge\s+(\w[\w\-]*)', cli_reference_text))
# Also extract bare subcommand names from the "Commands:" section
_cmd_section = re.search(r'Commands:\s*(.*?)(?:\n\n|\Z)', cli_reference_text, re.DOTALL)
if _cmd_section:
    VALID_SUBCOMMANDS.update(re.findall(r'^\s{2}(\w[\w\-]+)', _cmd_section.group(1), re.MULTILINE))
# Also add bare trustedge flags
VALID_FLAGS_CLI = set(re.findall(r'--[\w\-]+', cli_reference_text))
print(f"  ✓ {len(VALID_SUBCOMMANDS)} valid subcommands, {len(VALID_FLAGS_CLI)} valid flags extracted")
print(f"  Valid subcommands: {sorted(VALID_SUBCOMMANDS)}")

print("\n── Step 1: Fetching authoritative docs from dev.digicert.com ──")
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

# ── Step 1b: Fetch TrustCore GitHub Markdown sources ─────────────────────────
print("\n── Step 1b: Fetching TrustCore SDK sources (GitHub Markdown) ──")
for entry in GITHUB_MD_PAGES:
    print(f"  → {entry['raw_url']}")
    page = fetch_markdown_page(entry)
    time.sleep(0.5)
    if page and page["code_blocks"]:
        fetched_pages.append(page)
        for block in page["code_blocks"]:
            all_code_blocks.append({"url": page["url"], "block": block})
        print(f"     ✓ {len(page['code_blocks'])} command blocks found")
    elif page:
        print(f"     – no command blocks found in {entry['title']}")

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

═══ VALID TRUSTEDGE COMMANDS (the COMPLETE list — do not add any others) ═══
  trustedge --version
  trustedge --help
  trustedge --daemon                    ← run as Linux daemon/service
  trustedge agent [options]             ← Device Trust Manager agent mode
  trustedge mqtt [options]              ← MQTT pub/sub client
  trustedge certificate [options]       ← key gen + cert gen (self-signed, CSR)
  trustedge certificate est [options]   ← EST enrollment
  trustedge certificate scep [options]  ← SCEP enrollment

═══ COMMANDS THAT DO NOT EXIST — NEVER generate these ═══
  trustedge key     ← DOES NOT EXIST  (key gen is done via trustedge certificate -a ... -o ...)
  trustedge csr     ← DOES NOT EXIST  (CSR is done via trustedge certificate -csr ...)
  trustedge keystore← DOES NOT EXIST
  trustedge cert    ← DOES NOT EXIST  (use: trustedge certificate)
  trustedge enroll  ← DOES NOT EXIST
  trustedge provision ← DOES NOT EXIST

═══ CORRECT FLAG NAMES (copy exactly) ═══
  Key generation flags on `trustedge certificate`:
    -a ECC | RSA | QS | HYBRID   (algorithm)
    -c P256 | P384 | P521         (curve, required for ECC)
    -g MLDSA_44 | MLDSA_65 | MLDSA_87  (PQC algorithm, required for QS/HYBRID)
    -o <name>                     (output key/cert name)
    -x <file>                     (x509 cert output path)
    -i <conf-file>                (CSR config file in keystore/conf/)
    -da <days>                    (validity days)
    -sc <signing-cert>            (signing cert for non-self-signed)
    -sk <signing-key>             (signing key for non-self-signed)
    -t                            (generate TPM2 hardware key)
    -tpr TPM2                     (TAP provider)
    -pc <cert-file>               (print/verify certificate)
  MQTT flags:
    --mqtt_servername <host>
    --mqtt_port <port>
    --mqtt_transport SSL | TCP
    --ssl_cert_file <file>
    --ssl_key_file <file>
    --ssl_ca_file <file>
    --mqtt_pub_topic <topic>
    --mqtt_pub_message <msg>
    --mqtt_sub_topic <topic>
  Agent flags:
    --configure | --download | --reset
    --bootstrap-zip <file>
    --devtm-bootstrap-uri <url>
    --log-level DEBUG | INFO | ERROR
    --require-pqc

CRITICAL RULES:
1. USE ONLY commands from the CLI reference and provided doc sources.
2. Every step MUST include a source_url.
3. Use {{VERSION}} wherever a version number appears in filenames.
4. Structure:
   Top-level arch keys: x86_64, aarch64, arm32, zephyr
   Each arch has step keys: prerequisites, install, tpm_provision,
     cert_selfsigned, cert_est, cert_scep, run_cli, run_agent, pqc_demo, verify
   Each step: {
     "title": "string",
     "commands": ["string"],
     "source_url": "string",
     "notes": ["string"]
   }
5. Output ONLY valid JSON. No markdown fences. No explanation outside JSON.
6. Omit a step entirely if you cannot find real commands for it.
   An omitted step is far better than an invented command.
""").strip()

USER_PROMPT = f"""TrustEdge version: {VERSION}

══ PRIMARY SOURCE: CLI REFERENCE (trustedge --help output — highest authority) ══
This is the actual output of running trustedge --help for every command.
It defines ALL valid commands, flags and arguments. Do not use any command
or flag not shown here.

{cli_reference_text}

══ SECONDARY SOURCES: TrustCore SDK (GitHub) — build & run examples ══
TrustCore is the underlying SDK for TrustEdge. The BUILD_RUN.md and README
below are the most accurate real-world examples of how TrustEdge is built,
configured and run. Treat these as high-authority examples alongside the CLI reference.

{format_fetched_pages([p for p in fetched_pages if 'github.com' in p['url']])}

══ TERTIARY SOURCES: dev.digicert.com documentation ══
These pages provide usage examples and context for the CLI commands above.

{format_fetched_pages([p for p in fetched_pages if 'github.com' not in p['url']])}

══ REPO DOCS (TPM provisioning and PQC demo) ══
{repo_doc_text.get('SecureElement', '')}
{repo_doc_text.get('pqc_demo', '')}

Generate commands.json now. Every command must appear verbatim in the CLI reference above.
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

# ── Build allow-list: CLI reference is primary, web sources are secondary ─────
real_command_tokens = set()

# 1. CLI reference — highest authority (flags and subcommands from actual binary)
if cli_reference_text:
    real_command_tokens.update(re.findall(r'trustedge\s+\w[\w\-]*', cli_reference_text))
    real_command_tokens.update(re.findall(r'--[\w\-]+', cli_reference_text))
    real_command_tokens.update(re.findall(r'-\w[\w\-]*', cli_reference_text))

# 2. Web doc pages
for item in all_code_blocks:
    real_command_tokens.update(re.findall(r'trustedge\s+\w[\w\-]*', item["block"]))
    real_command_tokens.update(re.findall(r'--[\w\-]+', item["block"]))

# 3. Repo docs (TPM/PQC)
for text in repo_doc_text.values():
    real_command_tokens.update(re.findall(r'trustedge\s+\w[\w\-]*', text))
    real_command_tokens.update(re.findall(r'--[\w\-]+', text))

# Hard-block known hallucinated commands (not in binary regardless of docs)
BLOCKED_SUBCOMMANDS = {'key', 'csr', 'keystore', 'cert', 'enroll', 'provision'}
print(f"  Blocked subcommands: {sorted(BLOCKED_SUBCOMMANDS)}")
def check_hallucinations(data: dict) -> list[str]:
    issues = []
    for arch, steps in data.items():
        if arch == "meta" or not isinstance(steps, dict):
            continue
        for step_name, content in steps.items():
            if not isinstance(content, dict):
                continue
            for cmd in content.get("commands", []):
                # Hard-block known non-existent subcommands
                for subcmd in re.findall(r'trustedge\s+(\w[\w\-]*)', cmd):
                    if subcmd in BLOCKED_SUBCOMMANDS:
                        issues.append(
                            f"  [{arch}/{step_name}] BLOCKED subcommand: "
                            f"`trustedge {subcmd}` — this command does not exist in the binary"
                        )
                    elif f"trustedge {subcmd}" not in real_command_tokens:
                        issues.append(
                            f"  [{arch}/{step_name}] Unverified subcommand: "
                            f"`trustedge {subcmd}` — not found in CLI reference or docs"
                        )
                # Check flags (only long-form -- flags; short flags are harder to verify)
                for flag in re.findall(r'--[\w\-]+', cmd):
                    if flag not in real_command_tokens:
                        issues.append(
                            f"  [{arch}/{step_name}] Unverified flag: "
                            f"`{flag}` — not found in CLI reference or docs"
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
