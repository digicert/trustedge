```markdown
# Post-Quantum Cryptography (PQC) Demo Using TrustEdge and Mosquitto MQTT Broker
```

## Overview
This demo showcases the integration of Post-Quantum Cryptography (PQC) in action. It demonstrates a TLS 1.3 session between the TrustEdge MQTT client and the open-source Mosquitto MQTT broker. The MQTT session is secured using ML-DSA certificates (issued by Device Trust Manager) and employs ML-KEM for key exchange during the TLS 1.3 session.

> **Note:** PQC is only supported in TLS 1.3 as per IETF. TLS 1.2 is feature-frozen, making it essential for all TLS clients and servers to upgrade to TLS 1.3.

---

## Linux Package File Structure
The demo files are packaged in [here](https://github.com/digicert/trustedge/tree/master/examples/pqc-demo), which includes all necessary components for running the PQC demo. Both x86_64 and ARM64 binaries are provided.

### Key Files
- [start_broker.sh](https://github.com/digicert/trustedge/blob/master/examples/pqc-demo/start_broker.sh): Discovers the platform using `uname -m` and starts ML-DSA Certificates Compliant MQTT BROKER.
- [TrustEdge TLS stack](https://github.com/digicert/trustedge/releases/tag/trustedge_24.7.2-2187): Generate ML-DSA Certificates and Negotiate PQC exclusively.
- [TrustEdge Keystore Directory](https://dev.digicert.com/en/trustedge/install-and-configure/manage-the-keystore.html): Generates certificates and keys required for authentication.

---

## Installation Guide

### Step 1: Download TrustEdge Binary
Download the latest version of TrustEdge binary from the [TrustEdge GitHub Repository](https://github.com/digicert/trustedge).

Example (ARM64):
```bash
wget https://github.com/digicert/trustedge/releases/download/trustedge_24.7.2-2187/trustedge_24.7.2-2187.arm.deb
```

### Step 2: Update TrustEdge Binary
Ensure you use TrustEdge v24.7.2 Build 2187 or above:
1. Uninstall the old version.
2. Install the binary downloaded in Step 1.

### Step 3: Generate ML-DSA Certificates
Follow the instructions in the appendix to generate self-signed ML-DSA certificates.

```bash
suod trustedge certificate -a QS -g MLDSA_44 -o CA.key -x CA.crt -i ca_csr.cnf -da 3651 
sudo trustedge certificate -a QS -g MLDSA_44 -o server.key -x server.crt -i server_csr.cnf -da 3651 -sk CA.key -sc CA.crt
```

### Step 4: Update Certificate Store
Copy the newly generated ML-DSA certificates to the MQTT Broker certificate store using:
```bash
sudo cp /etc/digicert/keystore/keys/server.key ./keystore/server.key
sudo cp /etc/digicert/keystore/certs/server.crt ./keystore/server.crt
sudo cp /etc/digicert/keystore/keys/CA.key ./keystore/CA.key
sudo cp /etc/digicert/keystore/certs/CA.crt ./keystore/CA.crt
```

### Step 5: Verify ML-DSA Certificate
```bash
trustedge certificate -pc keystore/server.crt
```

---

## Configuration Details

### MQTT Broker (Mosquitto)
- **Binds**: `0.0.0.0`
- **Port**: `8883 (MQTTS)`
- **Server Name**: `mosquitto-service-01`

Start Broker:
```bash
./start_broker.sh --cert ./keystore/server.crt --key ./keystore/server.key
```

### MQTT Subscriber (TrustEdge)
Listens to topic `pqc/secure/channel`:
```bash
./consumer.sh --broker mosquitto-service-01 --port 8883 --ca-cert ./keystore/CA.crt
```

### MQTT Publisher (TrustEdge)
Publishes payloads to topic `pqc/secure/channel`:
```bash
./publisher.sh --broker mosquitto-service-01 --port 8883 --ca-cert ./keystore/CA.crt
```

---

## Notes
- ML-DSA certificates are significantly larger than RSA/ECC certificates due to their larger signature sizes.
- TLS clients and servers must adhere to TLS 1.3 for PQC compatibility.

For additional details, refer to the appendix or visit [TrustEdge Documentation](https://dev.digicert.com/en/trustedge.html).

