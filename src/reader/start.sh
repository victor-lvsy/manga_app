#!/bin/bash
if [ -z "$ENVIRONMENT" ]; then
    echo "ENVIRONMENT is not set. Please set it to dev or prod"
    exit 1
fi

if [ "$ENVIRONMENT" = "dev" ]; then
    python -m src.reader.app dev
else
    if [ "$ENVIRONMENT" = "prod" ]; then
        python -m src.reader.app prod
    else
        echo "Invalid ENVIRONMENT"
        exit 1
    fi
fi