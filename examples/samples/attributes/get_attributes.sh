#!/bin/bash

set -e

LOCATION="$1"
IP_ADDRESS="$2"

echo -n "{\"location\": \"${LOCATION}\", \"ip_address\": \"${IP_ADDRESS}\"}"

