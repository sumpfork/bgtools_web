#!/bin/bash

set -ex

if [ -z "$1" ]
  then
    echo "No stage argument supplied"
    exit 1
fi

cp "$1_config.yaml" config.yaml

npx aws-cdk@2.x deploy

