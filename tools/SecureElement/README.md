# DigiCert TrustEdge Secure Element Setup

## Introduction
This guide helps developers evaluate TrustEdge with a secure element. It covers the TrustEdge CLI provider selection for a PKCS#11 device (such as an NXP secure element) and a TPM 2.0 device, as well as the bundled TPM provisioning tools.

TrustEdge integrates with **Device Trust Manager** — a platform that establishes device identity and manages certificates issued throughout a device’s lifecycle, from **birth certificates** to **operational certificates**. The TrustEdge CLI can also be used to evaluate secure-element key generation and certificate workflows independently.

The TPM provisioning bundles below are for TPM 2.0 devices; they are not required for PKCS#11 devices.

---

## Directory Structure
The repository contains:

- **tpm2_tools-\<platform\>.zip** – Prebuilt TPM 2.0 tool bundles for different architectures. Extracting a bundle provides the helper scripts, configuration files, and binaries:
  - `tpm2_tools-aarch64-24.7.2-3262.zip`
  - `tpm2_tools-arm32-24.7.2-3262.zip`
  - `tpm2_tools-x86_64-24.7.2-3262.zip`

---

## Supported Platforms
The `tpm2_tools` package is available for multiple platforms to ensure portability and ease of integration:
- **aarch64 (ARM 64-bit)**
- **arm32 (ARM 32-bit)**
- **x86_64 (Intel/AMD 64-bit)**

---

## TrustEdge CLI Secure Element Quick Start

For a fuller TPM2 local integration-test example, see the [NanoSSL TAP local integration workflow](https://github.com/digicert/trustcore/blob/main/.github/workflows/nanossl_tap_local_integration_test.yml). It uses an isolated software TPM, provisions it with the bundle in this repository, checks the resulting TPM configuration and device permissions, and then runs an EST/TAP integration test. The workflow's automated setup is for a disposable test TPM; do not copy its reset/clear steps onto a pre-owned device.

The CLI must be built or packaged with the provider required by the device. Provider support depends on the TrustEdge build; confirm it before testing:

```bash
trustedge certificate --help
```

The help output should list `PKCS11` or `TPM2` for `--tap-provider`. The `--tap` option enables TAP key generation through the selected provider, `--tap-provider` selects the configured provider, and `--tap-modnum` selects the TAP module (default: `1`). Key storage and protection depend on the provider and its configuration.

### PKCS#11 device (for example, NXP)

1. Install the secure-element vendor's PKCS#11 library and configure its token/slot and user credentials according to the vendor instructions.
2. Make the library available to the TrustEdge runtime, and confirm the TrustEdge package was built with PKCS#11 support.
3. Configure the module path, token/slot, and authentication using the PKCS#11/SMP configuration supplied for that TrustEdge build. These settings are build- and vendor-specific. Do not put a token PIN in shell history or a world-readable file.
4. Generate a test ECC signing key through the configured provider:

```bash
trustedge certificate \
  --algorithm ECC --curve P256 \
  --tap --tap-provider PKCS11 --tap-modnum 1 \
  --tap-key-usage TAP_KEY_USAGE_SIGNING \
  --tap-sig-scheme TAP_SIG_SCHEME_ECDSA_SHA256 \
  --output-file ./nxp-eval-key
```

Use the module number and supported curve/signature algorithms provided for your TrustEdge build and secure element. After generation, use the vendor's tooling or device policy to confirm the key is present and non-exportable as intended.

### SoftHSM2 (PKCS#11 software token)

SoftHSM2 provides a software PKCS#11 token for development and testing. It does not provide the physical security properties of a hardware HSM. The steps below describe the reference workflow; use the actual slot details and follow the credential-provisioning security notes before using it. Do not use production PINs or other production credentials for this test setup.

#### 1. Install SoftHSM2 and OpenSC

On Ubuntu, install the packages:

```bash
sudo apt install opensc softhsm2 libsofthsm2
```

`opensc` provides `pkcs11-tool`, which is used below to inspect the token. The default SoftHSM2 configuration file is `/etc/softhsm2.conf`. If using a different configuration file, select it for the current shell:

```bash
export SOFTHSM2_CONF=/path/to/softhsm2.conf
```

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

The reference workflow uses `/etc/digicert/pkcs11_smp.conf`. Its example values are specific to that test setup, so do not copy its slot name, library path, or module identifier as universal values. The following is a field template, not a verified configuration for every TrustEdge package:

```ini
providertype=13

[module]
modulenum=1
modulename=<SLOT-DESCRIPTION-FROM-HELPER>
modulelibpath=<ABSOLUTE-PATH-TO-libsofthsm2.so>
moduleidstr=<MODULE-ID-FROM-HELPER>
credfile=default_creds.pkcs11
```

TrustCore's PKCS#11 implementation verifies `providertype=13` as `TAP_PROVIDER_PKCS11`. It requires `modulenum`, `modulename`, `moduleidstr`, and, for a dynamic-load build, `modulelibpath`. Use the tools from the matching TrustCore/TAP tools installation to obtain the exact slot description and module ID string:

```bash
smp_pkcs11_getslotdesc_bin -modulelibpath "$PKCS11_MODULE"
smp_pkcs11_getmoduleidstr_bin -modulelibpath "$PKCS11_MODULE"
```

Each tool reports values by PKCS#11 slot index. Select the output for the initialized token:

- `modulename` must exactly match that slot's PKCS#11 slot description; it is not the SoftHSM2 token label or slot ID.
- `moduleidstr` is the module ID string reported for the slot. The helper computes it from the token's serial number; it can differ between tokens. Do not reuse the fixed identifier in the reference example.
- `modulelibpath` is the path to the PKCS#11 shared library used by the dynamic-load build.
- TrustEdge resolves a relative `credfile` value relative to `/etc/digicert/pkcs11_smp.conf`. Thus the reference basename `default_creds.pkcs11` refers to `/etc/digicert/default_creds.pkcs11`; an absolute path can also be used.
- `modulenum` is the TrustEdge module identifier selected by `--tap-modnum`. The reference config and CLI both use `1`. This number is not a SoftHSM2 slot ID or a `pkcs11-tool` slot index.

The local TrustCore implementation was used to verify these field meanings. The helper tools must come from the same compatible TrustCore/TrustEdge release as the runtime.

#### 3. Configure PKCS#11 credentials

TrustCore provides `projects/mocpkcs11_tools/provision/pkcs11_provision_linux.sh` and `projects/mocpkcs11_tools/provision/pkcs11_prov.conf.tmpl`. The script's `DEFAULT_CREDS` template is the source of the reference transformation: it represents entity credentials in the TrustCore credential-file format, and the token user PIN is substituted for the template value before the file is written.

The following example performs the reference's template substitution without putting the PIN in a shell command or printing the decoded credentials. Run it from the root of the matching TrustCore checkout. First replace `REPLACE_WITH_RUNTIME_ACCOUNT` with the account that will run the TrustEdge command. The example uses Python 3 and prompts for the SoftHSM2 **user PIN**, not the SO PIN. It accepts only ASCII letters and digits for this example; choose an appropriate test PIN when initializing the token.

**The install command overwrites an existing `default_creds.pkcs11`.** Back up or choose a different filename if the file is already in use, and update `credfile` to match. Verify that `/etc/digicert` exists and that the runtime account can traverse it and read the module configuration and SoftHSM2 token files.

```bash
TRUSTEDGE_USER=REPLACE_WITH_RUNTIME_ACCOUNT
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

  install -m 600 -o "$TRUSTEDGE_USER" \
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
  --gdb --debug-all --monolithic --package \
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

The CLI help describes `--tap-modnum` as the TAP module selector and lists `PKCS11` as a provider when enabled in the build. The reference uses module number `1`; the PKCS#11 implementation associates the configured module with a slot by matching its slot description and module ID string. The CLI help does not establish what the output file contains for a TAP key, or whether the private key is exportable or protected. Do not infer those properties; protect any generated output according to the provider documentation.

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
- **Login or credentials failure:** Recheck the initialized token and user PIN, the credentials file format and access for the TrustEdge runtime account, and the provider instructions for the installed build. Do not print PINs to logs or expose production PINs in command arguments.
- **Objects not visible:** Confirm `PKCS11_MODULE`, the selected token label/slot index, and `SOFTHSM2_CONF`; then rerun the object listing against that token. If key generation fails, verify the TrustEdge build and module configuration against the matching provider documentation rather than changing unverified identifiers.

### TPM 2.0 device

1. Verify the TPM device path and that the TrustEdge process has permission to access it (see [Important Assumption: TPM Device Path](#important-assumption-tpm-device-path)).
2. Make sure the TrustEdge runtime user can read and write the TPM device. For example, replace `trustedge` with the account that will run TrustEdge:

```bash
TPM_DEVICE=/dev/tpm0 # Replace with the device path found above, if different.
ls -l "$TPM_DEVICE"
getfacl "$TPM_DEVICE"
sudo -u trustedge test -r "$TPM_DEVICE" && sudo -u trustedge test -w "$TPM_DEVICE"
```

Do not solve access problems by making the device world-writable. Have the device administrator configure an appropriate group or ACL.

3. If the TPM is already owned/provisioned, do **not** clear or reprovision it just for evaluation. Obtain its authorized credentials and configuration from the owner, and confirm TrustEdge is configured for the correct TPM module.
4. For a new, dedicated test TPM only, use the bundled tools and follow [TPM2 Device Operations](#tpm2-device-operations) to provision it. Provisioning generates `/etc/digicert/tpm2.conf` and `/etc/digicert/creds.tpm2`; verify they exist and are readable by the TrustEdge runtime as required by the deployment. Do not copy the CI workflow's TPM state deletion or reset steps to pre-owned hardware.
5. Generate a test ECC signing key using the TPM2 provider:

```bash
trustedge certificate \
  --algorithm ECC --curve P256 \
  --tap --tap-provider TPM2 --tap-modnum 1 \
  --tap-key-usage TAP_KEY_USAGE_SIGNING \
  --tap-sig-scheme TAP_SIG_SCHEME_ECDSA_SHA256 \
  --output-file ./tpm2-eval-key
```

The tool bundle's `smp_tpm2_getidstr_bin --w` operation configures the TPM2 module identifier; use it only as part of the authorized provisioning workflow. If `TPM2` is absent from `--tap-provider`, use a TPM2-enabled TrustEdge package/build.

### Evaluate the certificate workflow

The key-generation command above is a smoke test, not a complete enrollment test. To evaluate the full workflow, run a test EST/SCEP enrollment or Device Trust Manager flow using the test CA/bootstrap configuration and integration harness for your deployment. The referenced NanoSSL workflow runs a TAP certificate/key integration test after TPM setup; its test scripts and credentials are supplied separately from this repository. Confirm enrollment and signing succeed and that the resulting certificate corresponds to the key held by the secure element. Use test credentials and follow the CA/device vendor's instructions.

Before running an integration test, check the device, access, and provisioning files using the same account that will execute the test:

```bash
TPM_DEVICE=/dev/tpm0 # Replace with the device path found above, if different.
ls -l "$TPM_DEVICE"
test -r "$TPM_DEVICE" && test -w "$TPM_DEVICE"
test -r /etc/digicert/tpm2.conf
test -r /etc/digicert/creds.tpm2
```

If a check fails, resolve the device path, permissions, or authorized credential/configuration issue before starting TrustEdge. Avoid printing credential file contents into logs or support output.

---

## Important Assumption: TPM Device Path

**This documentation assumes your TPM device is enumerated as `/dev/tpm0`.** Before proceeding, verify your actual TPM device path by running:

```bash
ls -la /dev/tpm*
```

Common TPM device paths include:
- `/dev/tpm0` – Standard TPM device  
- `/dev/tpmrm0` – TPM resource manager  

If your device has a **different path**, substitute it in all commands in this guide. For example, if your device is `/dev/tpmrm0`, replace `--sm=/dev/tpm0` with `--sm=/dev/tpmrm0` in tool commands, and set `TPM_DEVICE=/dev/tpmrm0` in the access checks.

---

## Usage Steps

### 1. Clone the TrustEdge Repository
```bash
git clone https://github.com/digicert/trustedge.git
cd trustedge/tools/SecureElement
```

### 2. Extract the Platform-Specific Package
Choose the archive matching the device architecture:
```bash
unzip tpm2_tools-aarch64-24.7.2-3262.zip
```
For 32-bit ARM or x86_64, use `tpm2_tools-arm32-24.7.2-3262.zip` or `tpm2_tools-x86_64-24.7.2-3262.zip` instead.

This inflates a secondary archive:
```text
inflating: tpm2_tools-aarch64.zip
```

### 3. Unpack the Tools Bundle
```bash
unzip tpm2_tools-aarch64.zip
```

This creates the following directory structure:
- `bin/`  
- `scripts/`  
- `conf/`  
- `provision_tpm2.sh`  
- `reset_tpm2.sh`  

---

## TPM2 Device Operations

### Understanding Credential Files

A **credential file** is a security configuration file used to manage access control and authentication for TPM devices. It stores:

- **Passwords/Secrets**: Hierarchical passwords for TPM ownership and authorization (Lockout Hierarchy Password, Endorsement Hierarchy Password, Storage Hierarchy Password)
- **Authorization Policies**: Access control rules that define who can use specific TPM keys and functions
- **Metadata**: Information about the TPM's security policies and authentication requirements

**Purpose of Credential Files:**
- **Security**: Enables password-protected and policy-based access to TPM resources
- **Audit & Control**: Ensures only authorized processes can perform TPM operations (key generation, signing, decryption)
- **Compliance**: Supports security requirements by restricting TPM access to authenticated users/applications
- **Persistence**: Stores authorization state so TPM security policies persist across device reboots

When you provision a TPM with a credential file (e.g., `/etc/digicert/creds.tpm2`), you're establishing it as the security policy for that device. Subsequent operations that use this credential file verify authorization before allowing access.

---

### Generate or Initialize a Credential File

Before you can use credential files with TPM operations, you need to obtain or generate a credential file. The credential file can be:

1. **Pre-provided by DigiCert**: If you have received a credential file from DigiCert as part of your TrustEdge deployment package, you can use it directly.

2. **Generated from Configuration Templates**: DigiCert provides configuration templates in the `conf/tap/tpm2/` directory:
   - `tpm2_prov.conf.tmpl` – Template configuration file for TPM provisioning
   
   You can use these templates as a basis to generate your credential file. Customize the template according to your security requirements (passwords, policies, hierarchy settings) and use the provisioning tools to initialize the TPM with these credentials.

3. **Created Interactively**: Some deployments may use provisioning scripts that prompt you to set passwords and policies, which are then compiled into a credential file.

**Important**: Guard credential files carefully as they contain sensitive authentication and authorization information. Store them securely (e.g., in `/etc/digicert/` with restricted permissions) and limit access to authorized users and processes only.

Once you have a credential file in place, you can reference it in all TPM operations (see below).

---

### Clear the TPM2 Device
> **Warning:** Clearing a TPM can destroy access to keys and data stored on it. Do not run these commands on a pre-owned or production TPM unless you are authorized to erase it and have confirmed the impact.

You can clear the TPM2 device using the reset script:
```bash
sudo ./reset_tpm2.sh
```

Alternatively, use the `digicert_tpm2_takeownership` tool:

- Without a credential file:
```bash
sudo ./bin/digicert_tpm2_takeownership --sm=/dev/tpm0 --c --force
```

- With a credential file:
```bash
sudo ./bin/digicert_tpm2_takeownership --sm=/dev/tpm0 --c --credfile=/etc/digicert/creds.tpm2
```

---

### Take Ownership and Provision the TPM2 Device
Ownership can be taken and provisioned using the script:
```bash
sudo ./provision_tpm2.sh
```

This script:
- Takes ownership of the TPM2 device  
- Provisions the device with required credentials  
- Configures the TPM2 Module Identifier with the correct `moduleidstr`  

Alternatively, use the `digicert_tpm2_takeownership` tool directly:
```bash
sudo ./bin/digicert_tpm2_takeownership --sm=/dev/tpm0 --lhpwd= --ehpwd= --shpwd= --credfile=creds.tpm2 --authfail=10 --rcytime=300 --lorcy=300
```

After ownership, provision the device:
```bash
sudo ./bin/digicert_tpm2_provision --sm=/dev/tpm0 --ekpwd= --ekalg=rsa --srkpwd= --srkalg=rsa --credfile=/etc/digicert/creds.tpm2
```

Configure TPM2 Module Identifier:
```bash
sudo ./bin/smp_tpm2_getidstr_bin --w
```

---

### Notes
- **TPM Device Path Verification**: The commands in this guide assume the TPM device is at `/dev/tpm0`. Verify your actual TPM device path with `ls -la /dev/tpm*` and adjust commands accordingly if needed.  
- If resetting or taking ownership of the TPM2 device fails, ensure that no processes are actively using the TPM2 device. Identify and terminate such processes before retrying.  
- Always verify configuration files under `conf/` before provisioning.    

---

## Certificate Lifecycle and Data Flow

The following diagram illustrates how TPM provisioning integrates with **Device Trust Manager (DTM)** and the **IoT Telemetry Platform**:

```
+---------------------------+
|   Device Trust Manager    |
|        (DTM)              |
|                           |
| - Birth Identity Cert     |
| - Operational Cert Mgmt   |
| - Device Management       |
+-----|--------------|------+
      |              |
      |              |
      v              v
+---------------------------+    +---------------------------+
|   TPM2 Device             |    |   IoT Platform            |
|                           |    |   (MQTT, HTTPS, etc.)     |
| - Operational Key Pair    |--->|                           |
| - Operational Certificate |    | - Secure Data Exchange    |
| - Reset TPM               |<---|                           |
| - Take Ownership          |    |                           |
| - Provision Certs         |    |                           |
+---------------------------+    +---------------------------+
```
