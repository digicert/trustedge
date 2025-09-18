# Overview
This tutorial showcases the integration of Post-Quantum Cryptography (PQC) in IoT communications. It demonstrates a quantum-safe session between the TrustEdge MQTT client and the open-source Mosquitto MQTT broker. The MQTT session is secured using ML-DSA certificates to authenticate the MQTT client with the Mosquitto broker and employs hybrid key exchange (X25519 + ML-KEM-768) during the TLS 1.3 session.

> **Note:** PQC is only supported in TLS 1.3 as per IETF. TLS 1.2 is feature-frozen, making it essential for all TLS clients and servers to upgrade to TLS 1.3.

## Before you begin

- You need a [TrustEdge compatible device.](https://dev.digicert.com/en/trustedge/system-requirements.html)
- ```sudo``` (root) privileges on your device is needed.
- The user running TrustEdge CLI commands must be a member of the ```trustedge``` group
  -  Use ```groups "$(whoami)"``` to see group membership.
  -  Use ```sudo adduser "$(whoami)" trustedge``` to add your user to the ```trustedge``` group.
-  You have an understanding of the [TrustEdge keystore directory and permissions.](https://dev.digicert.com/en/trustedge/install-and-configure/manage-the-keystore.html)
-  [GitHub CLI](https://docs.github.com/en/github-cli/github-cli/about-github-cli) to clone the TrustEdge repository.

## Architecture

![Setup Architecture is as follows](https://github.com/user-attachments/assets/b2ffbc47-8925-493f-9705-ad4d3f4ac5f4)

## Ubuntu Package File Structure
The demo files are packaged in [here](https://github.com/digicert/trustedge/tree/master/examples/pqc-demo), which includes all necessary components for running the PQC demo. Both x86_64 and ARM64 binaries are provided.

## Key Files
- [start_broker.sh](https://github.com/digicert/trustedge/blob/master/examples/pqc-demo/start_broker.sh): Discovers the platform using `uname -m` and instructs the Mosquitto broker to start listening with an ML-DSA server certificate.
- [TrustEdge PQC Capable Binary](https://github.com/digicert/trustedge/releases/tag/trustedge_24.7.2-2187): Generate ML-DSA Certificates and Negotiate PQC exclusively.
- [TrustEdge Keystore Directory](https://dev.digicert.com/en/trustedge/install-and-configure/manage-the-keystore.html): Generates certificates and keys required for authentication. Using Default Keystore for the Demo at `/etc/digicert/keystore`

## Step 1: Install TrustEdge

1. Download the appropriate [TrustEdge release ```.deb``` package](https://github.com/digicert/trustedge/releases) for your CPU architecture:

    ```
    # 64-bit Intel/AMD (x86_64)
    wget https://github.com/digicert/trustedge/releases/download/trustedge_24.7.2-2187/trustedge_24.7.2-2187.x86_64.deb
    ```
    ```
    # 64-bit ARM (AArch64)
    wget https://github.com/digicert/trustedge/releases/download/trustedge_24.7.2-2187/trustedge_24.7.2-2187.aarch64.deb
    ```
    ```
    # 32-bit ARM
    wget https://github.com/digicert/trustedge/releases/download/trustedge_24.7.2-2187/trustedge_24.7.2-2187.arm.deb
    ```

2. Remove any previous TrustEdge installation:

    ```
    sudo apt remove --purge trustedge
    ```

3. Install the new package:

   ```
   sudo dpkg -i trustedge_24.7.2-2187.<cpu_arch>.deb
   ```

4. Verify version ≥ v24.7.2-2187:

   ```
   trustedge --version
   ```

## Step 2: Clone TrustEdge repository


### Step 3: Generate ML-DSA Certificates
Follow the command instructions to generate self-signed ML-DSA certificates. CSR content samples are [given below](#notes). The CSR files `ca_csr.cnf` and `server_csr.cnf` should be stored at '/etc/digicert/keystore/conf/' for command to generate ML-DSA certificates under '/etc/digicert/keystore/certs/' 

```bash
sudo trustedge certificate -a QS -g MLDSA_44 -o CA.key -x CA.crt -i ca_csr.cnf -da 3651 
sudo trustedge certificate -a QS -g MLDSA_44 -o server.key -x server.crt -i server_csr.cnf -da 3651 -sk CA.key -sc CA.crt
```

### Step 4: Update MQTT Broker Certificate Store
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

### MQTT Broker
- **Binds**: `0.0.0.0`
- **Port**: `8883 (MQTTS)`
- **Server Name**: `mqtt-pqc-broker`

Start Broker:
```bash
./start_broker.sh --cert ./keystore/server.crt --key ./keystore/server.key
```

### MQTT Subscriber (TrustEdge)
Listens to topic `pqc/secure/channel`:
```bash
./consumer.sh --broker mqtt-pqc-broker --port 8883 --ca-cert ./keystore/CA.crt
```

### MQTT Publisher (TrustEdge)
Publishes payloads to topic `pqc/secure/channel`:
```bash
./publisher.sh --broker mqtt-pqc-broker --port 8883 --ca-cert ./keystore/CA.crt
```

---

## Notes
- ML-DSA certificates are significantly larger than RSA/ECC certificates due to their larger signature sizes.
- TLS clients and servers must adhere to TLS 1.3 for PQC compatibility.
- Sample CA CSR to be stored `/etc/digicert/keystore/conf/ca_csr.cnf`
  ```bash
  ##Subject
  countryName=US
  commonName=DigiCert Broker
  stateOrProvinceName=California
  localityName=Sunnyvale
  organizationName=PM
  organizationalUnitName=BU
  ##Requested Extensions
  hasBasicConstraints=true
  isCA=true
  certPathLen=-1
  keyUsage=keyEncipherment, digitalSignature, keyCertSign
  ##subjectAltNames=numSANs; value1, type1; valueN, typeN
  subjectAltNames=1; broker.root.ca, 2
  ```
- Sample Server CSR to be stored `/etc/digicert/keystore/conf/server_csr.cnf`
  ```bash
  ##Subject
  countryName=US
  commonName=DigiCert Server
  stateOrProvinceName=California
  localityName=Sunnyvale
  organizationName=PM
  organizationalUnitName=BU
  ##Requested Extensions
  hasBasicConstraints=true
  isCA=false
  certPathLen=-1
  keyUsage=keyEncipherment, digitalSignature, keyCertSign
  ##subjectAltNames=numSANs; value1, type1; valueN, typeN
  subjectAltNames=1; mqtt-pqc-broker, 2
  ```

For additional details, refer to the appendix or visit [TrustEdge Documentation](https://dev.digicert.com/en/trustedge.html).



