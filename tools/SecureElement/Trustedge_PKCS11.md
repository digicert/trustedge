# TrustEdge PKCS#11 Setup

### SoftHSM2 (PKCS#11 software token)

SoftHSM2 provides a software PKCS#11 token for development and testing. It does not provide the physical security properties of a hardware HSM. The steps below describe the reference workflow; use the actual slot details and follow the credential-provisioning security notes before using it. Do not use production PINs or other production credentials for this test setup.

#### 1. Install SoftHSM2 and OpenSC

On Ubuntu, install the packages:

```bash
sudo apt install opensc softhsm2 libsofthsm2
```

`opensc` provides `pkcs11-tool`, which is used below to inspect the token. The default SoftHSM2 configuration file is `/etc/softhsm/softhsm2.conf`.

Ensure the user running `softhsm2-util` or `pkcs11-tool` can read `/etc/softhsm/softhsm2.conf` (or the file selected by `SOFTHSM2_CONF`). The account running TrustEdge must also be able to read that configuration file and access its configured token directory.

If using a different configuration file, select it for the current shell:

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

Run the SoftHSM2 commands and TrustEdge as a user that can read this configuration and access the token directory. If TrustEdge runs as a different account, grant that account the required access to both paths.

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

Use the slot ID reported by `softhsm2-util`; do not assume it is `0`. SoftHSM2 may assign a different slot ID after token initialization. Run `softhsm2-util --show-slots` again and note the initialized token's label and slot ID.

The reference command supplies PINs as command-line arguments. Do not replace these placeholders with production PINs or store real PINs in shell history, scripts, or logs. Use only disposable test credentials and follow the input-protection guidance for the SoftHSM2 version in use.

Locate the installed PKCS#11 library and set the environment variable used by the `pkcs11-tool` examples:

```bash
dpkg -L libsofthsm2 | grep '/libsofthsm2\.so$'
export PKCS11_MODULE=/path/to/libsofthsm2.so
```

`PKCS11_MODULE` is used by `pkcs11-tool` in this guide. The local TrustEdge documentation does not establish that TrustEdge reads this environment variable; its reference configuration instead has a `modulelibpath` field.

#### 2. Configure the TrustEdge PKCS#11 module

The reference workflow uses `/etc/digicert/pkcs11_smp.conf`. Run `softhsm2-util --show-slots` after initializing the token and select the intended token by its label and initialization status. For example, the reference output contains:

```text
Slot 507447823
  Slot info:
    Description:      SoftHSM slot ID 0x1e3f0a0f
  Token info:
    Initialized:      yes
    User PIN init.:   yes
    Label:            Mytoken
```

For this token, use `modulename=SoftHSM slot ID 0x1e3f0a0f`, not `Mytoken` or `507447823`.

**Multiple initialized slots:** TrustEdge uses the zeroth SoftHSM slot (slot index `0`) by default. Confirm that the intended token is in that slot using `softhsm2-util --show-slots` and `pkcs11-tool --module "$PKCS11_MODULE" --list-slots`. This slot index is distinct from the TrustEdge `modulenum` and from the SoftHSM slot ID.

Use this configuration template, replacing all angle-bracket placeholders with values for your installation before saving it as `/etc/digicert/pkcs11_smp.conf`:

```ini
providertype=13

[module]
modulenum=1
modulename=<SLOT-DESCRIPTION-FROM-SHOW-SLOTS>
modulelibpath=<ABSOLUTE-PATH-TO-libsofthsm2.so>
moduleidstr=<MODULE-ID-FOR-YOUR-TOKEN-AND-PROVIDER>
credfile=default_creds.pkcs11
```

For example, a configuration for the token shown above could contain the following values. Replace the sample `moduleidstr` and library path with values for your installation:

```ini
providertype=13

[module]
modulenum=1
modulename=SoftHSM slot ID 0x1e3f0a0f
modulelibpath=/usr/lib/softhsm/libsofthsm2.so
moduleidstr=f5e073310b951737496c41e1da51cdfc245894b3507c175840793964ec80da39
credfile=default_creds.pkcs11
```

After creating or updating `/etc/digicert/pkcs11_smp.conf`, set its owner and group to the TrustEdge runtime account:

```bash
sudo chown trustedge:trustedge /etc/digicert/pkcs11_smp.conf
```

This changes ownership but not file permissions. Ensure the `trustedge` user has read permission on the file; check its owner, group, and mode with:

```bash
ls -l /etc/digicert/pkcs11_smp.conf
```

The values in the sample are examples and must match your installation. In particular, verify the slot description and library path using the commands in step 1, and use the `moduleidstr` generated for your token and provider. The configuration fields are:

- `providertype=13` selects the PKCS#11 provider (`TAP_PROVIDER_PKCS11`).
- `modulename` must exactly match that slot's PKCS#11 slot description; it is not the SoftHSM2 token label or slot ID.
- `modulelibpath` is the absolute path to the PKCS#11 shared library used by the dynamic-load build. Use the actual path located in step 1 (the value assigned to `PKCS11_MODULE`), not the variable name itself.
- `moduleidstr` identifies the token and provider; use the value generated for your token rather than copying the sample value.
- TrustEdge resolves a relative `credfile` value relative to `/etc/digicert/pkcs11_smp.conf`. Thus the reference basename `default_creds.pkcs11` refers to `/etc/digicert/default_creds.pkcs11`.
- `modulenum` is the TrustEdge module identifier selected by `--tap-modnum`. This guide uses `modulenum=1` with `--tap-modnum 1` in the RSA and ECC commands below. This number is not a SoftHSM2 slot ID or a `pkcs11-tool` slot index; `modulenum=1` does not select the uninitialized SoftHSM2 `Slot 1`.

#### 3. Configure PKCS#11 credentials

TrustCore provides `projects/mocpkcs11_tools/provision/pkcs11_provision_linux.sh` and `projects/mocpkcs11_tools/provision/pkcs11_prov.conf.tmpl`. The script's `DEFAULT_CREDS` template is the source of the reference transformation: it represents entity credentials in the TrustCore credential-file format, and the token user PIN is substituted for the template value before the file is written.

The following example performs the reference's template substitution without putting the PIN in a shell command or printing the decoded credentials. Run it from the root of the matching TrustCore checkout. The example uses Python 3 and prompts for the SoftHSM2 **user PIN**, not the SO PIN. It accepts only ASCII letters and digits for this example; choose an appropriate test PIN when initializing the token.

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

The temporary file is private to the invoking user and removed on exit. The installed file is readable only by the specified owner. Check its permissions without displaying its contents:

```bash
ls -l /etc/digicert/default_creds.pkcs11
```

Base64 is encoding, not encryption. Do not put a real PIN in shell history, enable verbose provisioning with a real PIN, or print decoded credentials to a terminal or log.

#### 4. Build and install TrustEdge with PKCS#11 support

The reference build command is:

Run it from the root of the matching TrustCore checkout:

```bash
./scripts/ci/trustedge/ci_trustedge_build.sh \
  --monolithic --package \
  --cvc --proxy --pqc --pqc-composite \
  --enable-pc --pkcs11-dynamic
```

The TrustCore build script accepts the options above. `--pkcs11-dynamic` enables TAP and dynamic PKCS#11 loading; for this mode, configure the PKCS#11 shared-library path in `modulelibpath`. Use the standard build prerequisites documented for the matching TrustCore checkout. The script copies the generated Debian package to `dist/`; the reference's `trustedge_2.0.2.x86_64.deb` is only an example. List the package generated by your build and install that exact file:

```bash
ls -1 dist/*.deb
sudo dpkg -i dist/<GENERATED-TRUSTEDGE-PACKAGE>.deb
```

#### 5. Generate RSA and ECC keys

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

#### 6. Verify token objects

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
- **Token or slot not found:** Run `softhsm2-util --show-slots` and `pkcs11-tool --module "$PKCS11_MODULE" --list-slots`; check `SOFTHSM2_CONF` if using a nondefault configuration file.
- **Wrong module or slot selection:** Confirm `--tap-modnum` against the TrustEdge module configuration. Separately select the intended PKCS#11 slot index for `pkcs11-tool`; do not treat it as the TrustEdge module number or SoftHSM2 slot ID.
- **`moduleidstr` mismatch:** A debug build may report `PKCS11_createModuleList: Module ID string check failed` when the configured identifier does not match the module identifier. A non-debug build may omit the diagnostic and identifier values, even with `--log-level VERBOSE`; their absence does not prove that the configured identifier matches. A debug build may print the mismatch and still continue to generate a key, so verify that the intended token was used.

  In the debug output for the example in this guide, `Slot 0 moduleidstr` is `f5e073310b951737496c41e1da51cdfc245894b3507c175840793964ec80da39`, while `DeviceID string set to` reports `abcd73310b951737496c41e1da51cdfc245894b3507c175840793964ec80da39`. Use the `Slot 0 moduleidstr` value for `/etc/digicert/pkcs11_smp.conf`; do not substitute the separate `DeviceID` diagnostic.

  To inspect these values, rebuild from the matching TrustCore checkout with debug support:

  ```bash
  ./scripts/ci/trustedge/ci_trustedge_build.sh \
    --gdb --debug-all --monolithic --package \
    --cvc --proxy --pqc --pqc-composite \
    --enable-pc --pkcs11-dynamic
  ```

  Rerun the TrustEdge operation and inspect the debug output for `Slot 0 moduleidstr`; use the value reported for your token in `/etc/digicert/pkcs11_smp.conf`.
- **Login or credentials failure:** Recheck the initialized token and user PIN, the credentials file format and access for the TrustEdge runtime account, and the provider instructions for the installed build. Do not print PINs to logs or expose production PINs in command arguments.
- **Objects not visible:** Confirm `PKCS11_MODULE`, the selected token label/slot index, and `SOFTHSM2_CONF`; then rerun the object listing against that token. If key generation fails, verify the TrustEdge build and module configuration against the matching provider documentation rather than changing unverified identifiers.
