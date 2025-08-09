#!/bin/bash

set -e

poetry run poetry install

git submodule init
git submodule update

docker-compose -f docker-compose.dev.yml up -d