#!/bin/bash
if [ -z "$ENVIRONMENT" ]; then
    echo "ENVIRONMENT is not set. Please set it to dev or prod"
    exit 1
fi

if [ "$ENVIRONMENT" = "dev" ]; then
    python -m src.scraper.api dev
else
    if [ "$ENVIRONMENT" = "prod" ]; then
        python -m src.scraper.api prod
    else
        echo "Invalid ENVIRONMENT"
        exit 1
    fi
fi