# TrustEdge Certificate Commands
sudo rm -rf /etc/digicert/keystore/keys/*.*
sudo rm -rf /etc/digicert/keystore/certs/*.*
rm -rf ./keystore/*.*


sudo trustedge certificate -a QS -g MLDSA_44 -o CA.key -x CA.crt -i ca_csr.cnf -da 3651 
sudo trustedge certificate -a QS -g MLDSA_44 -o server.key -x server.crt -i server_csr.cnf -da 3651 -sk CA.key -sc CA.crt



# Calculate original MD5 checksums
md5_server_key=$(sudo md5sum /etc/digicert/keystore/keys/server.key | awk '{print $1}')
md5_ca_key=$(sudo md5sum /etc/digicert/keystore/keys/CA.key | awk '{print $1}')
md5_server_crt=$(sudo md5sum /etc/digicert/keystore/certs/server.crt | awk '{print $1}')
md5_ca_crt=$(sudo md5sum /etc/digicert/keystore/certs/CA.crt | awk '{print $1}')

# Copy files to ./keystore
sudo cp /etc/digicert/keystore/keys/server.key ./keystore/server.key
sudo cp /etc/digicert/keystore/certs/server.crt ./keystore/server.crt
sudo cp /etc/digicert/keystore/keys/CA.key ./keystore/CA.key
sudo cp /etc/digicert/keystore/certs/CA.crt ./keystore/CA.crt

# Verify MD5 checksums
md5_copied_server_key=$(md5sum ./keystore/server.key | awk '{print $1}')
md5_copied_ca_key=$(md5sum ./keystore/CA.key | awk '{print $1}')
md5_copied_server_crt=$(md5sum ./keystore/server.crt | awk '{print $1}')
md5_copied_ca_crt=$(md5sum ./keystore/CA.crt | awk '{print $1}')

# Check if the checksums match
if [ "$md5_server_key" != "$md5_copied_server_key" ]; then
  echo "Error: MD5 checksum mismatch for server.key"
  exit 1
fi

if [ "$md5_ca_key" != "$md5_copied_ca_key" ]; then
  echo "Error: MD5 checksum mismatch for CA.key"
  exit 1
fi

if [ "$md5_server_crt" != "$md5_copied_server_crt" ]; then
  echo "Error: MD5 checksum mismatch for server.crt"
  exit 1
fi

if [ "$md5_ca_crt" != "$md5_copied_ca_crt" ]; then
  echo "Error: MD5 checksum mismatch for CA.crt"
  exit 1
fi

echo "All TrustEdge Genarated Certificate Files copied successfully to MQTT Broker Keystore after MD5 checksums match."


trustedge certificate -pc keystore/server.crt

trustedge certificate -pc keystore/CA.crt