# DigiCert TPM2 Tools

## Introduction
The **TrustEdge** includes a set of utilities under `tpm2_tools` that enable developers and integrators to take ownership, provision, and configure Trusted Platform Modules (TPMs) across different platforms. These tools simplify secure element management and provide a consistent workflow for TPM initialization, certificate provisioning, and device identity management.

TrustEdge integrates with **Device Trust Manager** — a platform that establishes device identity and enables visualization of certificates issued throughout a device’s lifecycle, from **birth certificates** to **operational certificates**. This ensures secure communication and data exchange backed by certificate-based trust.

TrustEdge is fully **TLS 1.3 compliant**, providing modern, standards-based security for sending and receiving data. It also supports **Post-Quantum Cryptography (PQC) algorithms**, ensuring long-term resilience against emerging cryptographic threats.

---

## Directory Structure
Within the `tools/SecureElement/` directory, you will find:

- **scripts/** – Helper scripts for TPM reset and provisioning workflows  
- **reset_tpm2.sh** – Script to reset TPM state  
- **provision_tpm2.sh** – Script to provision TPM with required credentials  
- **conf/** – Configuration files for TPM setup  
- **bin/** – Supporting binaries for TPM operations  
- **tpm2_tools-\<platform\>.zip** – Prebuilt tool bundles for different architectures:
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

## Important Assumption: TPM Device Path

**This documentation assumes your TPM device is enumerated as `/dev/tpm0`.** Before proceeding, verify your actual TPM device path by running:

```bash
ls -la /dev/tpm*
```

Common TPM device paths include:
- `/dev/tpm0` – Standard TPM device  
- `/dev/tpmrm0` – TPM resource manager  

If your device has a **different path**, substitute it in all commands below. For example, if your device is `/dev/tpmrm0`, replace `--sm=/dev/tpm0` with `--sm=/dev/tpmrm0` in all commands.

---

## Usage Steps

### 1. Clone the TrustEdge Repository
```bash
git clone https://github.com/digicert/trustedge.git
cd trustedge/tools/SecureElement
```

### 2. Extract the Platform-Specific Package
Unzip the archive for your platform:
```bash
unzip tpm2_tools-aarch64-XX.x.x-xxxx.zip
```

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
- Integrate with **Device Trust Manager** to visualize certificate lifecycle and enable secure TLS 1.3 + PQC-backed communication.  

---

## Certificate Lifecycle and Data Flow

The following diagram illustrates how TPM provisioning integrates with **Device Trust Manager (DTM)** and downstream IoT telemetry platforms:

```
+-------------------+        +-------------------+        +---------------------------+
|   TPM2 Device     |        | Device Trust      |        |   IoT Telemetry Platform  |
|                   |        | Manager (DTM)     |        | (MQTT, HTTPS, etc.)       |
| - Reset TPM       |        |                   |        |                           |
| - Take Ownership  | -----> | - Birth Identity  | -----> | - Operational Certificates|
| - Provision Certs |        | - Cert Lifecycle  |        | - Secure TLS 1.3 + PQC    |
+-------------------+        | - Integrated CA/ICA|       | - Data Exchange           |
                             | - External CA/ICA  |       |                           |
                             +-------------------+        +---------------------------+
```

### Flow Description
1. **TPM2 Device Initialization**  
   - Reset TPM (`reset_tpm2.sh`)  
   - Take ownership and provision (`provision_tpm2.sh` or `digicert_tpm2_takeownership`)  

2. **Device Trust Manager (DTM)**  
   - Issues a **Birth Identity Certificate** at device onboarding  
   - Manages lifecycle of certificates (renewal, revocation, operational certs)  
   - Supports integration with internal CA/ICA or external third-party CA/ICA  

3. **IoT Telemetry Platform**  
   - Uses **Operational Certificates** issued via DTM  
   - Ensures secure communication over **TLS 1.3**  
   - Supports **Post-Quantum Cryptography (PQC)** algorithms for long-term resilience  
   - Enables secure telemetry data exchange (e.g., MQTT, HTTPS, WSS)  

