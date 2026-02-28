#!/bin/bash
NAMESPACE="${1:-codebase_b2320_app}"
docker build -t "$NAMESPACE" .