#!/bin/bash

set -e

# Set script directory
SCRIPT_DIR=$( cd $(dirname $0) ; pwd -P )

DEFAULT_CA_FILE="certs/CA.pem"

# Show usage
function show_usage
{
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --help                 - Show help options"
    echo "  --broker <hostname>    - Broker to connect to"
    echo "  --port <port>          - Broker port"
    echo "  --keystore <path>      - Path to keystore (picks up $DEFAULT_CA_FILE by default)"
    echo ""
    if [ -n "$1" ]; then
        echo "$1"
        echo ""
        exit 1
    else
        exit 0
    fi
}

BROKER=
BROKER_PORT=
KEYSTORE_PATH=

# Parse command line arguments
while test $# -gt 0
do
    case "$1" in
        --help)
            show_usage
            ;;
        --broker)
            if [ -z "$2" ]; then
                show_usage "Missing --broker argument"
            fi
            BROKER=$2
            shift
            ;;
        --port)
            if [ -z "$2" ]; then
                show_usage "Missing --port argument"
            fi
            BROKER_PORT=$2
            shift
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

if [ -z "$BROKER" ]; then
    show_usage "Missing --broker argument"
fi

if [ -z "$BROKER_PORT" ]; then
    show_usage "Missing --port argument"
fi

if [ -z "$KEYSTORE_PATH" ]; then
    show_usage "Missing --keystore argument"
fi

# Enable SSL key logging for debugging purposes.
# WARNING: This should only be used in development environments, as it writes sensitive key material to disk.
export ENABLE_SSL_KEYLOG=1

trustedge mqtt \
    --mqtt_servername $BROKER \
    --mqtt_port $BROKER_PORT \
    --mqtt_client_id trustedge_sub_client \
    --mqtt_sub_topic pqc/secure/channel \
    --ssl_ca_file $KEYSTORE_PATH/$DEFAULT_CA_FILE \
    --mqtt_transport SSL