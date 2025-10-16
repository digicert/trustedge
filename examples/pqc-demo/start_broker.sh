#!/bin/bash

set -e

# Set script directory
SCRIPT_DIR=$( cd $(dirname $0) ; pwd -P )

DEFAULT_KEY_FILE="keys/server.pem"
DEFAULT_CERT_FILE="certs/server.pem"

# Show usage
function show_usage
{
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --help                 - Show help options"
    echo "  --keystore <path>      - Path to keystore (picks up $DEFAULT_CERT_FILE and $DEFAULT_KEY_FILE by default)"
    echo ""
    if [ -n "$1" ]; then
        echo "$1"
        echo ""
        exit 1
    else
        exit 0
    fi
}

KEYSTORE_PATH=

# Parse command line arguments
while test $# -gt 0
do
    case "$1" in
        --help)
            show_usage
            ;;
        --keystore)
            if [ -z "$2" ]; then
                show_usage "Missing --keystore argument"
            fi
            KEYSTORE_PATH=$2
            shift
            ;;
        *)
            show_usage "Invalid option: $1"
            ;;
    esac
    shift
done

if [ -z "$KEYSTORE_PATH" ]; then
    show_usage "Missing --keystore argument"
fi

if [[ "$(uname -m)" == "x86_64" ]]; then
    PLATFORM_DIR=x86_64
elif [[ "$(uname -m)" == "aarch64" ]]; then
    PLATFORM_DIR=aarch64
else
    echo "ERROR: Unable to detect platform"
    exit -1
fi

CERT_PATH=$KEYSTORE_PATH/$DEFAULT_CERT_FILE
KEY_PATH=$KEYSTORE_PATH/$DEFAULT_KEY_FILE

export OPENSSL_CONF=$SCRIPT_DIR/mosquitto/openssl.cnf
export OPENSSL_MODULES=$SCRIPT_DIR/mosquitto/$PLATFORM_DIR
export LD_LIBRARY_PATH=$SCRIPT_DIR/mosquitto/$PLATFORM_DIR:$LD_LIBRARY_PATH

sed -i "s:cafile .*:cafile $CERT_PATH:g" $SCRIPT_DIR/mosquitto/mosq.conf
sed -i "s:certfile .*:certfile $CERT_PATH:g" $SCRIPT_DIR/mosquitto/mosq.conf
sed -i "s:keyfile .*:keyfile $KEY_PATH:g" $SCRIPT_DIR/mosquitto/mosq.conf

./mosquitto/$PLATFORM_DIR/mosquitto -c $SCRIPT_DIR/mosquitto/mosq.conf
