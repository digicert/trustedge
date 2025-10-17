# Overview
This tutorial showcases the integration of Post-Quantum Cryptography (PQC) in IoT communications. It demonstrates a quantum-safe session between the open-source [DigiCert TrustEdge MQTT client](https://github.com/digicert/trustedge) and the open-source [Eclipse Mosquitto MQTT broker](https://mosquitto.org/). The MQTT session is secured using ML-DSA certificates to authenticate the MQTT client with the Mosquitto broker and employs hybrid key exchange (X25519 + ML-KEM-768) during the TLS 1.3 session.

> **Note:** PQC is only supported in TLS 1.3 as per IETF. TLS 1.2 is feature-frozen, making it essential for all TLS clients and servers to upgrade to TLS 1.3.

## Before you begin

- You need a [TrustEdge compatible device.](https://dev.digicert.com/en/trustedge/system-requirements.html)
- ```sudo``` (root) privileges on your device is needed.
- You have an understanding of the [TrustEdge keystore directory and permissions.](https://dev.digicert.com/en/trustedge/install-and-configure/manage-the-keystore.html)
- [GitHub CLI](https://docs.github.com/en/github-cli/github-cli/about-github-cli) to clone the TrustEdge repository.
- Install the prerequisites using
  ```
  sudo apt install wget unzip
  ``` 

## Architecture

![Setup Architecture is as follows](https://github.com/digicert/trustedge/blob/demo-pqc-v2/examples/pqc-demo/assets/MQTTS-PQC-1738287869933.jpg)

## Step 1: Install TrustEdge

1. Remove any previous TrustEdge installation:

    ```
    sudo apt remove --purge trustedge
    ```
2. Download the latest [TrustEdge release ```.deb``` package](https://github.com/digicert/trustedge/releases) appropriate for your CPU architecture:

    ```
    # 64-bit Intel/AMD (x86_64)
    wget https://github.com/digicert/trustedge/releases/latest/download/trustedge-x64-deb.zip
    ```
    ```
    # 64-bit ARM (AArch64)
    wget https://github.com/digicert/trustedge/releases/latest/download/trustedge-aarch64-deb.zip
    ```
    ```
    # 32-bit ARM
    wget https://github.com/digicert/trustedge/releases/latest/download/trustedge-arm-deb.zip
    ```

3. Extract the TrustEdge installer
    ```
    unzip trustedge-<cpu_arch>-deb.zip
    ```   

4. Install the new package:

   ```
   sudo dpkg -i trustedge_<version>.<cpu_arch>.deb
   ```

5. Verify version ≥ v24.7.2-2187:

   ```
   trustedge --version
   ```

6. Add your user to the ```trustedge``` user group (logout and login to ensure this takes effect) :

   ```
   sudo adduser "$(whoami)" trustedge
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

### Option 1: TrustEdge self signed certificate generation

1. Copy the PQC demo CSR configuration files to the ```/etc/digicert/keystore/conf``` directory:

    ```
    cp ca_csr.cnf /etc/digicert/keystore/conf
    cp server_csr.cnf /etc/digicert/keystore/conf
    ```
> [!NOTE]
> You can automate the next steps by running the PQC demo script ```certGeneration.sh```. If you decide to automate this process, skip to [Step 4: Configure and start the MQTT broker](#step-4-configure-and-start-the-mqtt-broker).

2. Generate root CA keypair and certificate:

    ```
    trustedge certificate -a QS -g MLDSA_44 -o CA.pem -x CA.pem -i ca_csr.cnf -da 3651
    ```

3. Generate Mosquitto MQTT broker server keypair and certificate, signed by the root CA:

    ```
    trustedge certificate -a QS -g MLDSA_44 -o server.pem -x server.pem -i server_csr.cnf -da 3651 -sk CA.pem -sc CA.pem
    ```

4. Verify the Mosquitto MQTT broker server certificate and the root CA certificate:

    ```
    trustedge certificate -pc /etc/digicert/keystore/certs/server.pem
    trustedge certificate -pc /etc/digicert/keystore/certs/CA.pem
    ```

### Option 2: EST server key generation and certificate issuance

> [!NOTE]
> This requires a network connection to [DigiCert Device Trust Manager's](https://docs.digicert.com/en/device-trust-manager.html) EST endpoint with an ML-DSA PKI heirarchy configured. Any EST client, including ```curl```, can be used to request and receive an ML-DSA certificate over EST. See the [Configure and use EST tutorial](https://docs.digicert.com/en/device-trust-manager/tutorials/configure-and-use-est.html) for more information.

1. Copy the PQC demo CSR configuration files to the ```/etc/digicert/keystore/conf``` directory:

    ```
    cp server_csr.cnf /etc/digicert/keystore/conf
    ```

2. Generate server key and certificate signed by the root CA:

    ```
    ./est_server_keygen_mldsa.sh --estc-server-dn <server-name> --estc-server-url <url> --estc-user <user> --estc-password <password>
    ```

3. Verify server certificate:

    ```
    trustedge certificate -pc /etc/digicert/keystore/certs/server.pem
    trustedge certificate -pc /etc/digicert/keystore/certs/CA.pem
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
   ./start_broker.sh --keystore /etc/digicert/keystore
   ```

    To start the MQTT broker using a locally built Mosquitto (build instructions provided in Appendix), use the following steps:

     ```
     cd mosquitto-2.0.22/build/src
     ```

    Create a `mosq.conf` file with the following contents

    ```
    per_listener_settings true

    listener 1883 0.0.0.0
    allow_anonymous true

    listener 8883 0.0.0.0
    allow_anonymous true
    protocol mqtt
    cafile /etc/digicert/keystore/certs/server.pem
    certfile /etc/digicert/keystore/certs/server.pem
    keyfile /etc/digicert/keystore/keys/server.pem
    ```

    Start the broker
  
    ```
    ./mosquitto -c mosq.conf 
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
    ./consumer.sh --broker mqtt-pqc-broker --port 8883 --keystore /etc/digicert/keystore
    ```

3. You should see a “Connected” message followed by readiness to receive.

## Step 6: Run TrustEdge publisher

1. Make ```publisher.sh``` executable:

    ```
    chmod +x publisher.sh
    ```

2. Publish a test message to ```pqc/secure/channel```:

    ```
    ./publisher.sh --broker mqtt-pqc-broker --port 8883 --keystore /etc/digicert/keystore
    ```

## Step 7: Capture and decrypt handshake in Wireshark

You can capture MQTT traffic on the loopback interface using Wireshark. Configure Wireshark to use your (pre)-master-secret log, filter for TLS packets, and then inspect both the hybrid key-exchange parameters and the server’s PQC x.509 certificate.

**Capture traffic on the loopback adapter**

1. Open Wireshark with sudo or as a root user to capture traffic on the loopback interface.
   ```
   sudo wireshark
   ```
1. Select the **“lo”** (loopback) interface.
1. Click **Start** to begin capture.
1. Reproduce your MQTT client’s connection.
1. Stop capture once the TLS handshake and MQTT CONNECT are complete.

**Configure TLS decryption**

1. In Wireshark, go to **Edit > Preferences.**
1. Expand **Protocols**, then scroll to **TLS**.
1. In **(Pre)-Master-Secret log filename**, browse and select ```pqc-demo/client_keys.txt```.
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
1. Expand **Transport Layer Security → TLSv1.3 Record Layer → Handshake Protocol → Extension: supported_groups → Supported Groups**.
1. You will see two hybrid groups announced:

| Hex Value | Decimal | Name | Description |
|----------|----------|----------|----------|
| 0x11EC | 4588 | X25519MLKEM768 | Post-quantum hybrid X25519 ECDH + ML-KEM-768 Key Agreement for TLS 1.3|
| 0x11EB | 4587 | secp256r1MLKEM768 | Post-quantum hybrid secp256r1 ECDH + ML-KEM-768 Key Agreement for TLS 1.3|

> [!NOTE]
> These tell the broker which PQC-hybrid key-exchange algorithms the client supports. To look up the TLS parameter values, consult the [IANA TLS Parameters registry](https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml#tls-parameters-8).

![Hybrid](https://github.com/digicert/trustedge/blob/master/examples/pqc-demo/assets/ws_hybridkeyexchange.png)

**Inspect the server certificate**

1. Locate the **Certificate** message sent by the broker.
1. Expand **Transport Layer Security → TLSv1.3 Record Layer → Handshake Protocol → Certificates → Certificate** and click on the server’s X.509 entry.
1. Note the **Algorithm ID** field: ```2.16.840.1.101.3.4.3.17```

> [!NOTE]
> This Algorithm ID is the OID dot notation for ML-DSA-44, the post-quantum signature algorithm. You can see the description and ASN.1 notation at the [OID repository for 2.16.840.1.101.3.4.3.17](https://oid-base.com/get/2.16.840.1.101.3.4.3.17).

![Hybrid](https://github.com/digicert/trustedge/blob/master/examples/pqc-demo/assets/ws_mldsa.png)

## Appendix

### Building Mosquitto with OpenSSL 3.5.1

Configuration parameters - export the following environment variables so they can be picked up for subsequent operations

    export OPENSSL_INSTALL_PATH=<path>
    export OPENSSL_LIB_PATH=$( [ "$(uname -m)" = "x86_64" ] && echo lib64 || echo lib )

Download and install OpenSSL 3.5.1


    wget https://github.com/openssl/openssl/releases/download/openssl-3.5.1/openssl-3.5.1.tar.gz
    tar xf openssl-3.5.1.tar.gz
    cd openssl-3.5.1
    rm -rf $OPENSSL_INSTALL_PATH
    mkdir -p $OPENSSL_INSTALL_PATH
    ./config --prefix=$OPENSSL_INSTALL_PATH --openssldir=$OPENSSL_INSTALL_PATH shared
    make clean all
    make install

Download and build Mosquitto

    wget https://mosquitto.org/files/source/mosquitto-2.0.22.tar.gz
    tar xf mosquitto-2.0.22.tar.gz
    cd mosquitto-2.0.22
    mkdir build
    cd build
    cmake .. \
      -DWITH_TLS=ON \
      -DCMAKE_PREFIX_PATH=$OPENSSL_INSTALL_PATH/$OPENSSL_LIB_PATH/cmake/OpenSSL \
      -DCMAKE_FIND_ROOT_PATH=$OPENSSL_INSTALL_PATH \
      -DOPENSSL_INCLUDE_DIR=$OPENSSL_INSTALL_PATH/include \
      -DOPENSSL_LIBRARIES="$OPENSSL_INSTALL_PATH/$OPENSSL_LIB_PATH/libssl.so;$OPENSSL_INSTALL_PATH/$OPENSSL_LIB_PATH/libcrypto.so" \
      -DOPENSSL_SSL_LIBRARY=$OPENSSL_INSTALL_PATH/$OPENSSL_LIB_PATH/libssl.so \
      -DOPENSSL_CRYPTO_LIBRARY=$OPENSSL_INSTALL_PATH/$OPENSSL_LIB_PATH/libcrypto.so \
      -DCMAKE_BUILD_TYPE=Release
    make clean all

## Congratulations

Congratulations on completing this tutorial! For more information on PQC visit [DigiCert Solutions for Post-Quantum](https://www.digicert.com/solutions/security-solutions-for-post-quantum-computing).
