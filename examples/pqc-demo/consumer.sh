#!/bin/bash

set -e

# Set script directory
SCRIPT_DIR=$( cd $(dirname $0) ; pwd -P )

# Show usage
function show_usage
{
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --help                 - Show help options"
    echo "  --broker <hostname>    - Broker to connect to"
    echo "  --port <port>          - Broker port"
    echo "  --ca-cert <path>       - Path to trusted certificate"
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
CA_CERT_FILE=

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
        --ca-cert)
            if [ -z "$2" ]; then
                show_usage "Missing --ca-cert argument"
            fi
            CA_CERT_FILE=$2
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

if [ -z "$CA_CERT_FILE" ]; then
    show_usage "Missing --ca-cert argument"
fi

trustedge mqtt \
    --mqtt_servername $BROKER \
    --mqtt_port $BROKER_PORT \
    --mqtt_client_id trustedge_sub_client \
    --mqtt_sub_topic pqc/secure/channel \
    --ssl_ca_file $CA_CERT_FILE \
    --mqtt_transport SSL