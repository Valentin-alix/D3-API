#!/bin/bash

parent_path=$( cd "$(dirname $(dirname "${BASH_SOURCE[0]}"))" ; pwd -P )
cd "$parent_path"

set -o allexport
source .env
set +o allexport

cat scripts/init.sql | docker exec -i ezred2db psql -U $DB_USERNAME -d $DB_NAME -v ON_ERROR_STOP=1