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

1. Clone the TrustEdge repository for the PQC demo tools:

    ```
    git clone https://github.com/digicert/trustedge.git
    ```

2. Go to the pqc-demo directory:

    ```
    cd trustedge/examples/pqc-demo
    ```


## Step 3: Generate ML-DSA certificates

1. Copy the PQC demo CSR configuration files to the ```/etc/digicert/keystore/conf``` directory:

    ```
    sudo cp ca_csr.cnf /etc/digicert/keystore/conf
    sudo cp server_csr.cnf /etc/digicert/keystore/conf
    ```
> [!NOTE]
> You can automate the next steps by running the PQC demo script ```certGeneration.sh```. If you decide to automate this process, skip to [Step 4: Configure and start the MQTT broker](#step-4-configure-and-start-the-mqtt-broker).

2. Generate root CA key and certificate:

    ```
    sudo trustedge certificate -a QS -g MLDSA_44 -o CA.key -x CA.crt -i ca_csr.cnf -da 3651
    ```

3. Generate server key and certificate signed by the root CA:

    ```
    sudo trustedge certificate -a QS -g MLDSA_44 -o server.key -x server.crt -i server_csr.cnf -da 3651 -sk CA.key -sc CA.crt
    ```

4. Verify server and CA certificates:

    ```
    sudo trustedge certificate -pc /etc/digicert/keystore/certs/server.crt
    sudo trustedge certificate -pc /etc/digicert/keystore/certs/CA.crt
    ```

5. Copy server certificate and key to the PQC demo ```keystore/``` directory:

    ```
    sudo cp /etc/digicert/keystore/keys/server.key ./keystore/server.key
    sudo cp /etc/digicert/keystore/certs/server.crt ./keystore/server.crt
    ```

6. Copy CA certificate and key to the PQC demo ```keystore/``` directory:

    ```
    sudo cp /etc/digicert/keystore/keys/CA.key ./keystore/CA.key
    sudo cp /etc/digicert/keystore/certs/CA.crt ./keystore/CA.crt
    ```

## Step 4: Configure and start the MQTT broker

1. Add the following MQTT server entry to your ```/etc/hosts``` configuration file:

    ```
    127.0.0.1 mqtt-pqc-broker
    ```

2. Make ```start_broker.sh``` executable:

    ```
    chmod +x start_broker.sh
    ```

3. Launch the MQTT broker with TLS 1.3 and ML-DSA credentials:

    ```
    ./start_broker.sh --cert ./keystore/server.crt --key ./keystore/server.key
    ```

4. Confirm broker is listening on port 8883:

    ```
    ss -tlnp | grep 8883
    ```

## Step 5: Run TrustEdge subscriber

1. Make ```consumer.sh``` executable:

    ```
    chmod +x consumer.sh
    ```

2. Subscribe to topic ```pqc/secure/channel```:

    ```
    ./consumer.sh --broker mqtt-pqc-broker --port 8883 --ca-cert ./keystore/CA.crt
    ```

3. You should see a “Connected” message followed by readiness to receive.

## Step 6: Run TrustEdge publisher

1. Make ```publisher.sh``` executable:

    ```
    chmod +x publisher.sh
    ```

2. Publish a test message to ```pqc/secure/channel```:
    
    ```
    ./publisher.sh --broker mqtt-pqc-broker --port 8883 --ca-cert ./keystore/CA.crt
    ```

## Step 7: Capture and decrypt handshake in Wireshark

You can capture MQTT traffic on the loopback interface using Wireshark. Configure Wireshark to use your (pre)-master-secret log, filter for TLS packets, and then inspect both the hybrid key-exchange parameters and the server’s PQC x.509 certificate.

**Capture traffic on the loopback adapter**

1. Open Wireshark.
1. Select the **“lo”** (loopback) interface.
1. Click **Start** to begin capture.
1. Reproduce your MQTT client’s connection.
1. Stop capture once the TLS handshake and MQTT CONNECT are complete.

**Configure TLS decryption**

1. In Wireshark, go to **Edit > Preferences.**
1. Expand **Protocols**, then scroll to **TLS**.
1. In **(Pre)-Master-Secret log filename**, browse and select ```demo-pqc/client_keys.txt```.
1. Click **OK**.

Wireshark will now use those secrets to decrypt TLSv1.3 session data, including PQC certificates.

**Filter for TLS handshake packets**

1. At the top of the main window, set the display filter to:

    ```
    tls
    ```

2. Press **Enter**.

> [!NOTE]
> This hides non-TLS traffic, so you can focus on the handshake.

**Examine the key-exchange in ClientHello**

1. Find the **ClientHello** packet in the packet list.
1. Expand **Transport Layer Security → Extension: supported_groups**.
1. You will see two hybrid groups announced:

| Hex Value | Decimal | Name | Description |
|----------|----------|----------|----------|
| 0x11EC | 4588 | X25519MLKEM768 | Post-quantum hybrid ECDHE-MLKEM Key Agreement for TLS 1.3|
| 0x11EB | 4587 | secp256r1MLKEM768 | Post-quantum hybrid ECDHE-MLKEM Key Agreement for TLS 1.3|

> [!NOTE]
> These tell the broker which PQC-hybrid key-exchange algorithms the client supports. To look up any new TLS parameter values, consult the **TLS Parameters** registry on the IANA website.

**Inspect the server certificate**

1. Locate the **Certificate** message sent by the broker.
1. Expand **Transport Layer Security → Certificate** and click on the server’s X.509 entry.
1. Note the **Algorithm ID** field: ```2.16.840.1.101.3.4.3.17```

> [!NOTE]
> This Algorithm ID is the OID dot notation for ML-DSA-44, the post-quantum signature algorithm. You can see the description and ASN.1 notation at the [OID repository for 2.16.840.1.101.3.4.3.17](https://oid-base.com/get/2.16.840.1.101.3.4.3.17).
