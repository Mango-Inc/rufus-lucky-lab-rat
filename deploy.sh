#!/usr/bin/env bash

set -e

gcloud functions deploy on_slack_mention \
  --runtime python39 \
  --memory 512mb \
  --trigger-http --allow-unauthenticated

gcloud functions deploy daily_lunch_bell \
  --runtime python39 \
  --memory 1GB \
  --timeout 540s \
  --trigger-http \
  --allow-unauthenticated
