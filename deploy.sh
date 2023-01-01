#!/bin/bash

set -ex

if [ -z "$1" ]
  then
    echo "No stage argument supplied"
    exit 1
fi

# assume config is via region/profile set
if [ -z "$AWS_REGION" ] || [ -z "$AWS_PROFILE" ];
  then
    echo "Need both AWS_PROFILE and AWS_REGION set"
    exit 1
fi

cp "$1_config.yaml" config.yaml

npx aws-cdk@2.x deploy
