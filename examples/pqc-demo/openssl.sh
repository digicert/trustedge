#!/bin/bash

set -e

# Set script directory
SCRIPT_DIR=$( cd $(dirname $0) ; pwd -P )

if [[ "$(uname -m)" == "x86_64" ]]; then
    PLATFORM_DIR=x86_64
elif [[ "$(uname -m)" == "aarch64" ]]; then
    PLATFORM_DIR=aarch64
else
    echo "ERROR: Unable to detect platform"
    exit -1
fi

export OPENSSL_CONF=$SCRIPT_DIR/mosquitto/openssl.cnf
export OPENSSL_MODULES=$SCRIPT_DIR/mosquitto/$PLATFORM_DIR
export LD_LIBRARY_PATH=$SCRIPT_DIR/mosquitto/$PLATFORM_DIR:$LD_LIBRARY_PATH

./mosquitto/$PLATFORM_DIR/openssl $@