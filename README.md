### Generate init sql & populate

```
bash scripts/dump.sh

scp init.sql ubuntu@145.239.198.180:/home/EzreD2API/scripts/init.sql

bash scripts/populate.sh
```

### Generate dump sql for specific table & populate

Example for collectable_map_info & collectable

```
source .env
docker exec -i ezred2db pg_dump -U $DB_USERNAME --data-only --column-inserts --table=collectable $DB_NAME > coll.sql
docker exec -i ezred2db pg_dump -U $DB_USERNAME --data-only  --column-inserts --table=collectable_map_info $DB_NAME > coll_map_info.sql

cat coll.sql | docker exec -i ezred2db psql -U $DB_USERNAME -d $DB_NAME
cat coll_map_info.sql | docker exec -i ezred2db psql -U $DB_USERNAME -d $DB_NAME
```
