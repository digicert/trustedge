# TrustEdge Certificate Commands
rm -rf /etc/digicert/keystore/keys/*.*
rm -rf /etc/digicert/keystore/certs/*.*


trustedge certificate -a QS -g MLDSA_44 -o CA.pem -x CA.pem -i ca_csr.cnf -da 3651 
trustedge certificate -a QS -g MLDSA_44 -o server.pem -x server.pem -i server_csr.cnf -da 3651 -sk CA.pem -sc CA.pem

echo "All TrustEdge Key and Certificates Generated Successfully."


trustedge certificate -pc /etc/digicert/keystore/certs/server.pem

trustedge certificate -pc /etc/digicert/keystore/certs/CA.pem
