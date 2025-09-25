#!/bin/bash

set -e

ESTC_SERVER_DN=""
ESTC_SERVER_URL=""
ESTC_USER=""
ESTC_PASSWORD=""
ESTC_CRED_ARG=""

function help() {
    echo "Usage: $0 --estc-server-dn <server name> --estc-server-url <url> [--estc-user <username>] [--estc-password <password>]"
    echo ""
    echo "Options:"
    echo "  --estc-server-dn      EST server name (e.g., demo.one.digicert.com)"
    echo "  --estc-server-url     URL of the EST server (e.g., /.well-known/est/devicetrustmanager/IOT_9a3d5e22-17c4-4f56-88a7-7cf8c914fa61)"
    echo "  --estc-user           [Optional] Username for EST authentication"
    echo "  --estc-password       [Optional] Password for EST authentication"
    echo "  --help                Display this help message"
    echo ""
}

# Process command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --estc-server-dn)
            if [ -z "$2" ]; then
                echo "Error: --estc-server-dn requires a value.";
                exit 1;
            fi
            ESTC_SERVER_DN="$2";
            shift
            ;;
        --estc-server-url)
            if [ -z "$2" ]; then
                echo "Error: --estc-server-url requires a value.";
                exit 1;
            fi
            ESTC_SERVER_URL="$2";
            shift
            ;;
        --estc-user)
            if [ -z "$2" ]; then
                echo "Error: --estc-user requires a value.";
                exit 1;
            fi
            ESTC_USER="$2";
            shift
            ;;
        --estc-password)
            if [ -z "$2" ]; then
                echo "Error: --estc-password requires a value.";
                exit 1;
            fi
            ESTC_PASSWORD="$2";
            shift
            ;;
        *)
            help
            echo "Unknown parameter passed: $1";
            exit 1
            ;;
    esac
    shift
done

if [ -z "$ESTC_SERVER_DN" ] || [ -z "$ESTC_SERVER_URL" ]; then
    help
    echo "Error: --estc-server-dn and --estc-server-url are required.";
    exit 1
fi

if [ -n "$ESTC_USER" ]; then
    ESTC_CRED_ARG="--estc-user $ESTC_USER"
fi

if [ -n "$ESTC_PASSWORD" ]; then
    ESTC_CRED_ARG+=" --estc-pass $ESTC_PASSWORD"
fi

# Clean up any existing keys/certs
rm -f /etc/digicert/keystore/keys/mldsa_server_keygen.*
rm -f /etc/digicert/keystore/certs/mldsa_server_keygen.*

wget -P /etc/digicert/keystore/ca http://cacerts.digicert.com/DigiCertGlobalRootG2.crt > /dev/null 2>&1
wget -P /etc/digicert/keystore/ca http://cacerts.digicert.com/DigiCertGlobalRootCA.crt > /dev/null 2>&1

# Get CA certs
trustedge certificate est \
    --estc-server-dn $ESTC_SERVER_DN \
    --estc-server-url $ESTC_SERVER_URL/cacerts

# Issue certificate using server keygen
trustedge certificate est \
    --estc-server-dn $ESTC_SERVER_DN \
    --estc-server-url $ESTC_SERVER_URL/serverkeygen \
    --estc-authentication-mode BASIC \
    --algorithm QS \
    --pq-alg MLDSA_44 \
    --key-alias mldsa_server_keygen \
    --csr-conf server_csr.cnf \
    --log-level INFO \
    $ESTC_CRED_ARG
