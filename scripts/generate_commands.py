#!/usr/bin/env python3
"""
generate_commands.py
────────────────────
Reads TrustEdge documentation from the repo, sends it to GitHub Models API
(GPT-4o or Claude), and writes docs/data/commands.json.

Runs inside the GitHub Action `generate-commands` job.
Can also be run locally:
  export GITHUB_TOKEN=<your-PAT-with-models:read>
  export TRUSTEDGE_VERSION=v24.7.2-3262
  python scripts/generate_commands.py
"""

import json
import os
import pathlib
import textwrap
from openai import OpenAI

REPO_ROOT = pathlib.Path(__file__).parent.parent
OUT_FILE  = REPO_ROOT / "docs" / "data" / "commands.json"

MODEL   = os.environ.get("AI_MODEL", "openai/gpt-4o")
VERSION = os.environ.get("TRUSTEDGE_VERSION", "latest")
TOKEN   = os.environ["GITHUB_TOKEN"]   # injected by the Action or set locally

# ── Collect documentation sources ──────────────────────────────────────────

def read_file(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

docs = {
    "README":          read_file(REPO_ROOT / "README.md"),
    "SecureElement":   read_file(REPO_ROOT / "tools" / "SecureElement" / "README.md"),
    "pqc_demo":        read_file(REPO_ROOT / "examples" / "pqc-demo" / "README.md"),
}

# ── Prompt ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
You are a technical writer for DigiCert TrustEdge — an IoT security agent.
Your job is to extract and synthesize exact shell commands from the provided
documentation, then output a single structured JSON object.

RULES:
1. Commands must be EXACT — copy from the docs verbatim where present.
   Never invent flags or paths not in the documentation.
2. Use {{VERSION}} as a placeholder wherever a release version appears
   (e.g. in .deb filenames). The caller substitutes the real version.
3. Organise by: arch (x86_64 | aarch64 | arm32 | zephyr),
   then by: step (prerequisites | install | tpm_provision | keygen |
                   cert_selfsigned | cert_est | run_cli | run_agent | pqc_demo | verify)
4. Each step has: title (string), commands (array of strings),
   notes (array of strings, optional), tpm_required (bool, optional).
5. Output ONLY valid JSON — no markdown fences, no commentary.
6. Include a top-level meta object with: version, generated_at (ISO-8601), source_files.
""").strip()

USER_PROMPT = textwrap.dedent(f"""
TrustEdge version: {VERSION}

=== README.md ===
{docs['README']}

=== tools/SecureElement/README.md ===
{docs['SecureElement']}

=== examples/pqc-demo/README.md ===
{docs['pqc_demo']}

Generate the commands.json now.
""").strip()

# ── Call GitHub Models API ──────────────────────────────────────────────────

print(f"Calling GitHub Models API — model: {MODEL}, version: {VERSION}")

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=TOKEN,
)

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": USER_PROMPT},
    ],
    temperature=0.1,      # low temp → deterministic, faithful to docs
    max_tokens=8192,
    response_format={"type": "json_object"},
)

raw = response.choices[0].message.content

# ── Validate & write ────────────────────────────────────────────────────────

try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    print("ERROR: AI returned invalid JSON")
    print(raw[:500])
    raise SystemExit(1) from exc

# Inject meta if AI omitted it
data.setdefault("meta", {})
data["meta"]["version"]      = VERSION
data["meta"]["model_used"]   = MODEL
data["meta"]["source_files"] = list(docs.keys())

import datetime
data["meta"]["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Written {OUT_FILE}  ({OUT_FILE.stat().st_size} bytes)")
