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

The help output should list `PKCS11` or `TPM2` for `--tap-provider`. The `--tap` option enables hardware-backed TAP key generation, `--tap-provider` selects the configured provider, and `--tap-modnum` selects the TAP module (default: `1`).

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
