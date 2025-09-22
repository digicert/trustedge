# TrustEdge Certificate Commands
rm -rf /etc/digicert/keystore/keys/*.*
rm -rf /etc/digicert/keystore/certs/*.*


trustedge certificate -a QS -g MLDSA_44 -o CA.key -x CA.crt -i ca_csr.cnf -da 3651 
trustedge certificate -a QS -g MLDSA_44 -o server.key -x server.crt -i server_csr.cnf -da 3651 -sk CA.key -sc CA.crt

echo "All TrustEdge Key and Certificates Generated Successfully."


trustedge certificate -pc keystore/server.crt

trustedge certificate -pc keystore/CA.crt