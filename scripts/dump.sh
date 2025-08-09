#!/bin/bash

parent_path=$( cd "$(dirname $(dirname "${BASH_SOURCE[0]}"))" ; pwd -P )
cd "$parent_path"

set -o allexport
source .env
set +o allexport

docker exec -i ezred2db pg_dump -U $DB_USERNAME --exclude-table alembic_version --data-only -d $DB_NAME > init.sql