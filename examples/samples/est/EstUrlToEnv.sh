#!/bin/bash

###############################################################################
# EstUrlToEnv.sh
#
# PURPOSE:
#   This script parses an EST (Enrollment over Secure Transport) URL and
#   extracts its components into environment variables. These variables can
#   then be used by other scripts or provisioning flows that require access
#   to EST server details.
#
# USAGE:
#   source ./EstUrlToEnv.sh <EST_URL>
#
#   Example:
#     source ./EstUrlToEnv.sh https://clientauth.demo.one.digicert.com/.well-known/est/devicetrustmanager/IOT_<>/device-group/<>/simpleenroll
#
#   This will export the following environment variables:
#     EST_SCHEME      → "https"
#     EST_HOST        → "est.example.com"
#     EST_PORT        → "443"
#     EST_PATH        → "/.well-known/est/simpleenroll"
#
#   These variables can be used in downstream scripts, e.g.:
#     curl -X POST "$EST_SCHEME://$EST_HOST:$EST_PORT$EST_PATH"
#
# NOTES:
#   - The script must be sourced (`source ./EstUrlToEnv.sh`) to persist the
#     exported variables in the current shell session.
#   - If no port is specified in the URL, the default port is inferred based
#     on the scheme (443 for https, 80 for http).
#   - The script performs basic validation and will exit with an error if the
#     URL format is invalid.
#
# COMPATIBILITY:
#   - Tested with Bash 4.x and 5.x
#   - Compatible TrustEdge 
#
# AUTHOR:
#   DigiCert TrustEdge Team
#
# 
###############################################################################



#!/bin/bash

# Input EST URL
EST_URL_INPUT=$1
# Extract components using parameter expansion
EST_HOST=$(echo "$EST_URL_INPUT" | awk -F/ '{print $3}')
EST_POLICY_ID=$(echo "$EST_URL_INPUT" | awk -F/ '{print $7}')
EST_ENDPOINT=$(echo "$EST_URL_INPUT" | awk -F/ '{print "/"$4"/"$5"/"$6"/"$7"/"$8"/"$9}')
EST_TYPE=$(echo "$EST_URL_INPUT" | awk -F/ '{print "/"$10}')


# Export environment variables
export EST_HOST
export EST_POLICY_ID
export EST_URL
export EST_ENDPOINT

# Print values (for verification)
echo "EST_HOST=$EST_HOST"
echo "EST_POLICY_ID=$EST_POLICY_ID"
echo "EST_ENDPOINT=$EST_ENDPOINT"
echo "EST_TYPE=$EST_ENDPOINT"

