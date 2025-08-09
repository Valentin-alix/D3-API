#!/bin/bash

parent_path=$( cd "$(dirname $(dirname $(dirname "${BASH_SOURCE[0]}")))" ; pwd -P )
cd "$parent_path"

bash scripts/prod/stop.server.sh

docker compose -f docker-compose.prod.yml build --no-cache --force-rm

docker compose -f docker-compose.prod.yml up -d --force-recreate