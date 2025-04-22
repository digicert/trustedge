Make sure your TrustEdge version is minimum Trustedge v24.7.2 Build 2187 or above per installed.
# wget https://github.com/digicert/trustedge/releases/download/trustedge_24.7.2-2154/trustedge_24.7.2-2154.aarch64.deb
# Follow the instructions at - https://dev.digicert.com/en/trustedge/tutorials.html
# Start broker
./start_broker.sh --cert ./keystore/server.crt --key ./keystore/server.key

# Start consumer
./consumer.sh --broker mosquitto-service-01 --port 8883 --ca-cert ./keystore/CA.crt

# Start publisher
./publisher.sh --broker mosquitto-service-01 --port 8883 --ca-cert ./keystore/CA.crt
