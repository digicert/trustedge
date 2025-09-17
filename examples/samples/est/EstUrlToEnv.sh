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

