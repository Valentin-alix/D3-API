#!/bin/bash

set -e

poetry run poetry install

docker-compose -f docker-compose.dev.yml up -d