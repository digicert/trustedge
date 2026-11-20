# TrustEdge PKCS#11 Setup

### SoftHSM2 (PKCS#11 software token)

SoftHSM2 provides a software PKCS#11 token for development and testing. It does not provide the physical security properties of a hardware HSM. Use only disposable test credentials; do not use production PINs or other production credentials in this setup.

#### 1. Install prerequisites

On Ubuntu, install SoftHSM2 and OpenSC:

```bash
sudo apt install opensc softhsm2 libsofthsm2
```

`opensc` provides `pkcs11-tool`, which is used below to inspect the token.

The helper tools `smp_pkcs11_getslotdesc_bin` and `smp_pkcs11_getmoduleidstr_bin` are delivered in a separate helper-tools package, not with the TrustEdge package or this repository. Install `<HELPER-TOOLS-PACKAGE>` using the instructions supplied with it, then confirm the tools are available:

```bash
command -v smp_pkcs11_getslotdesc_bin smp_pkcs11_getmoduleidstr_bin
```

If the command prints nothing, run the tools from the directory where the package installed them.

#### 2. Configure SoftHSM2

The default SoftHSM2 configuration file is `/etc/softhsm/softhsm2.conf`. The user running `softhsm2-util` or `pkcs11-tool` must be able to read it (or the file selected by `SOFTHSM2_CONF`). The account running TrustEdge must also be able to read that file and access its configured token directory.

To use a different configuration file, select it for the current shell:

```bash
export SOFTHSM2_CONF=/path/to/softhsm2.conf
```

**Optional: use an isolated development token store**

To keep test tokens separate from the system-wide token store, create a dedicated token directory and SoftHSM2 configuration file. The heredoc expands `$HOME` when it writes the file. It replaces any existing configuration at this path:

```bash
mkdir -p "$HOME/softhsm-test/tokens"
chmod 700 "$HOME/softhsm-test/tokens"

cat > "$HOME/softhsm-test/softhsm2.conf" <<EOF
# SoftHSM v2 configuration file

directories.tokendir = $HOME/softhsm-test/tokens
objectstore.backend = file

# ERROR, WARNING, INFO, DEBUG
log.level = ERROR

# If CKF_REMOVABLE_DEVICE flag should be set
slots.removable = false

# Enable and disable PKCS#11 mechanisms using slots.mechanisms.
slots.mechanisms = ALL

# If the library should reset the state on fork
library.reset_on_fork = false
EOF

export SOFTHSM2_CONF="$HOME/softhsm-test/softhsm2.conf"
```

If TrustEdge runs as a different account, grant that account the access it needs to both the configuration file and the token directory. Do not make either world-writable.

#### 3. Initialize a token

List the available tokens and slots:

```bash
softhsm2-util --show-slots
```

Initialize a token in an available slot, replacing the placeholders with a test label and test-only PINs:

```bash
softhsm2-util --init-token --slot '<INITIAL_SLOT_ID>' \
  --label '<TEST_TOKEN_LABEL>' \
  --so-pin '<TEST_SO_PIN>' --pin '<TEST_USER_PIN>'
```

Use the slot ID reported by `softhsm2-util`; do not assume it is `0`. SoftHSM2 may assign a different slot ID after token initialization, so run `softhsm2-util --show-slots` again and note the initialized token's label.

This command supplies PINs as command-line arguments. Do not replace these placeholders with production PINs or store real PINs in shell history, scripts, or logs. Follow the input-protection guidance for the SoftHSM2 version in use.

#### 4. Locate the PKCS#11 library

Locate the installed library and set the environment variable used by the examples below:

```bash
dpkg -L libsofthsm2 | grep '/libsofthsm2\.so$'
export PKCS11_MODULE=/path/to/libsofthsm2.so
```

`PKCS11_MODULE` is used by `pkcs11-tool` and the helper tools in this guide. The TrustEdge documentation does not establish that TrustEdge reads this variable; TrustEdge uses the `modulelibpath` field in `/etc/digicert/pkcs11_smp.conf`.

#### 5. Get `modulename` and `moduleidstr`

Run the helper tools against the library:

```bash
smp_pkcs11_getslotdesc_bin -modulelibpath "$PKCS11_MODULE"
smp_pkcs11_getmoduleidstr_bin -modulelibpath "$PKCS11_MODULE"
```

Each tool prints one line per slot index. Example output (values differ on every installation):

```text
Slot[0] Module Id String: 0e46a6975aeb8065f0c71ec953f02cb105eabac2705a93341ddd284a3d2f5217
Slot[1] Module Id String: 38113c36d1f8eb3558d5868d285a7ddcba11128374fd2f13537255c351ea8c2f
Slot[0] description: SoftHSM slot ID 0x64043b77
Slot[1] description: SoftHSM slot ID 0x1
```

- `smp_pkcs11_getslotdesc_bin` provides the value for `modulename`: the text after `description: `.
- `smp_pkcs11_getmoduleidstr_bin` provides the value for `moduleidstr`.
- Use the lines for the same slot index from both tools.

TrustEdge uses slot index `0` by default. Confirm that slot index `0` is the intended token by matching the token label from `softhsm2-util --show-slots` with the output of:

```bash
pkcs11-tool --module "$PKCS11_MODULE" --list-slots
```

The slot index is distinct from the SoftHSM2 slot ID and from the TrustEdge `modulenum`.

#### 6. Write `/etc/digicert/pkcs11_smp.conf`

Verify that `/etc/digicert` exists, then create or edit the file with an editor run as root, for example `sudoedit /etc/digicert/pkcs11_smp.conf`. Replace every angle-bracket placeholder with your own values:

```ini
providertype=13

[module]
modulenum=1
modulename=<SLOT-DESCRIPTION-FROM-STEP-5>
modulelibpath=<ABSOLUTE-PATH-TO-libsofthsm2.so>
moduleidstr=<MODULE-ID-STRING-FROM-STEP-5>
credfile=default_creds.pkcs11
```

An example using the sample output from step 5 (replace the sample values with your own):

```ini
providertype=13

[module]
modulenum=1
modulename=SoftHSM slot ID 0x64043b77
modulelibpath=/usr/lib/softhsm/libsofthsm2.so
moduleidstr=0e46a6975aeb8065f0c71ec953f02cb105eabac2705a93341ddd284a3d2f5217
credfile=default_creds.pkcs11
```

Set the owner and group to the TrustEdge runtime account, then check the result:

```bash
sudo chown trustedge:trustedge /etc/digicert/pkcs11_smp.conf
ls -l /etc/digicert/pkcs11_smp.conf
```

`chown` changes ownership but not permissions; make sure the `trustedge` user can read the file.

The configuration fields are:

- `providertype=13` selects the PKCS#11 provider (`TAP_PROVIDER_PKCS11`).
- `modulename` must exactly match the slot description printed by `smp_pkcs11_getslotdesc_bin`. It is not the token label or slot ID.
- `modulelibpath` is the absolute path to the PKCS#11 shared library (the value assigned to `PKCS11_MODULE`), not the variable name itself.
- `moduleidstr` is the module ID string printed by `smp_pkcs11_getmoduleidstr_bin` for the same slot. Do not copy a value from another token or installation.
- A relative `credfile` is resolved relative to `/etc/digicert/pkcs11_smp.conf`, so `default_creds.pkcs11` refers to `/etc/digicert/default_creds.pkcs11`.
- `modulenum` is the TrustEdge module identifier selected by `--tap-modnum`. This guide uses `modulenum=1` with `--tap-modnum 1`. It is not a SoftHSM2 slot ID or a `pkcs11-tool` slot index.

#### 7. Configure PKCS#11 credentials

TrustCore provides `projects/mocpkcs11_tools/provision/pkcs11_provision_linux.sh` and `projects/mocpkcs11_tools/provision/pkcs11_prov.conf.tmpl`. The script's `DEFAULT_CREDS` template represents entity credentials in the TrustCore credential-file format; the token user PIN is substituted into it before the file is written.

The following example performs that substitution without putting the PIN in a shell command or printing the decoded credentials. Run it from the root of the matching TrustCore checkout. The example uses Python 3 and prompts for the SoftHSM2 **user PIN**, not the SO PIN. It accepts only ASCII letters and digits for this example; choose an appropriate test PIN when initializing the token.

**The install command overwrites an existing `default_creds.pkcs11`.** Back up or choose a different filename if the file is already in use, and update `credfile` to match. Verify that `/etc/digicert` exists and that the runtime account can traverse it and read the module configuration and SoftHSM2 token files.

```bash
(
  set -euo pipefail
  umask 077
  tmp_creds=$(mktemp)
  trap 'rm -f -- "$tmp_creds"' EXIT

  python3 - "$tmp_creds" <<'PY'
import base64
import getpass
import re
import sys
from pathlib import Path

script = Path("projects/mocpkcs11_tools/provision/pkcs11_provision_linux.sh")
match = re.search(rb'^DEFAULT_CREDS="([A-Za-z0-9+/=]+)"$', script.read_bytes(), re.MULTILINE)
if not match:
    raise SystemExit("DEFAULT_CREDS template not found")
template = base64.b64decode(match.group(1), validate=True)
placeholder = b"[ 0000 ]"
if placeholder not in template:
    raise SystemExit("Expected PIN placeholder not found in credentials template")
pin = getpass.getpass("SoftHSM2 user PIN: ")
if not re.fullmatch(r"[A-Za-z0-9]{4,255}", pin):
    raise SystemExit("Use a test PIN of 4-255 ASCII letters or digits for this example")
credentials = template.replace(placeholder, b"[ " + pin.encode("ascii") + b" ]")
Path(sys.argv[1]).write_bytes(base64.b64encode(credentials))
PY

  sudo install -m 640 -o trustedge -g trustedge \
    "$tmp_creds" /etc/digicert/default_creds.pkcs11
)
```

The temporary file is private to the invoking user and removed on exit. The installed file is owned by `trustedge:trustedge` with mode `640`, so only that user and group can read it. Check its permissions without displaying its contents:

```bash
ls -l /etc/digicert/default_creds.pkcs11
```

Base64 is encoding, not encryption. Do not put a real PIN in shell history, enable verbose provisioning with a real PIN, or print decoded credentials to a terminal or log.

#### 8. Build and install TrustEdge with PKCS#11 support

Run the build from the root of the matching TrustCore checkout:

```bash
./scripts/ci/trustedge/ci_trustedge_build.sh \
  --monolithic --package \
  --cvc --proxy --pqc --pqc-composite \
  --enable-pc --pkcs11-dynamic
```

The TrustCore build script accepts the options above. `--pkcs11-dynamic` enables TAP and dynamic PKCS#11 loading; for this mode, configure the PKCS#11 shared-library path in `modulelibpath`. Use the standard build prerequisites documented for the matching TrustCore checkout. The script copies the generated Debian package to `dist/`. List the package generated by your build and install that exact file:

```bash
ls -1 dist/*.deb
sudo dpkg -i dist/<GENERATED-TRUSTEDGE-PACKAGE>.deb
```

#### 9. Generate RSA and ECC keys

The checked-in CLI help documents `--tap`, `--tap-provider`, `--tap-modnum`, `--algorithm`, `--size`, `--curve`, and `--output-file`. The following commands use the algorithm and curve capitalization shown by that help:

RSA:

```bash
trustedge certificate \
  --algorithm RSA --size 2048 \
  --output-file rsa_key_2048 \
  --tap --tap-provider PKCS11 --tap-modnum 1 \
  --log-level VERBOSE
```

ECC:

```bash
trustedge certificate \
  --algorithm ECC --curve P256 \
  --output-file ecc_key_p256 \
  --tap --tap-provider PKCS11 --tap-modnum 1 \
  --log-level VERBOSE
```

#### 10. Verify token objects

List slots with OpenSC and identify the slot **index** corresponding to the initialized token label. This index is not necessarily the slot ID shown by SoftHSM2:

```bash
pkcs11-tool --module "$PKCS11_MODULE" --list-slots
```

Then list objects for the intended slot. With `--login` and no `--pin` argument, `pkcs11-tool` can request the token PIN interactively:

```bash
pkcs11-tool --module "$PKCS11_MODULE" \
  --slot-index 0 --login --list-objects
```

Replace the example slot index `0` with the index for the intended token from `--list-slots`. Review the listed object types and labels/IDs to identify the expected RSA and ECC objects. Public-key objects contain public key data; private-key objects represent private keys; certificate objects represent certificates. Listing objects reports metadata and does not require exporting private-key material. Confirm the slot belongs to the intended token by matching the token label from `--list-slots` with the label from `softhsm2-util --show-slots`. Object presence confirms only that objects are listed in that token; it does not by itself prove persistence across restarts, non-exportability, or hardware protection.

#### Troubleshooting

- **Library not found:** Check the package's installed files with `dpkg -L libsofthsm2 | grep '/libsofthsm2\.so$'`, then use the resolved path for `PKCS11_MODULE` and `modulelibpath`.
- **Helper tools not found:** Confirm `<HELPER-TOOLS-PACKAGE>` is installed and run `command -v smp_pkcs11_getslotdesc_bin smp_pkcs11_getmoduleidstr_bin`; otherwise run the tools from their installed location.
- **Token or slot not found:** Run `softhsm2-util --show-slots` and `pkcs11-tool --module "$PKCS11_MODULE" --list-slots`; check `SOFTHSM2_CONF` if using a nondefault configuration file.
- **Wrong module or slot selection:** Confirm `--tap-modnum` matches `modulenum` in `/etc/digicert/pkcs11_smp.conf`. Separately, confirm the intended token is at slot index `0`, which TrustEdge uses by default; do not treat the slot index as the TrustEdge module number or SoftHSM2 slot ID.
- **`modulename` or `moduleidstr` mismatch:** Re-run both helper tools from step 5 and compare their output for the intended slot with `/etc/digicert/pkcs11_smp.conf`. Values from another token or installation will not match.
- **Login or credentials failure:** Recheck the initialized token and user PIN, the credentials file format and access for the TrustEdge runtime account, and the provider instructions for the installed build. Do not print PINs to logs or expose production PINs in command arguments.
- **Objects not visible:** Confirm `PKCS11_MODULE`, the selected token label/slot index, and `SOFTHSM2_CONF`; then rerun the object listing against that token. If key generation fails, verify the TrustEdge build and module configuration against the matching provider documentation rather than changing unverified identifiers.
