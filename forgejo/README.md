# Setup

## Internal network for forgejo and its dedicated postgres db
`sudo docker network create --internal forgejo-net`

More configurable keys for `app.ini` at [Forgejo's configuration cheatsheet](https://forgejo.org/docs/latest/admin/config-cheat-sheet)

## Generate password for the database
```
echo "DB_PASS=$(openssl rand -base64 36 | tr -d '\n')" >> .env
```

### Changing the password of the databse
```
sudo docker exec -it forgejo-db-1 psql -U forgejo -d forgejo -c "ALTER USER forgejo WITH PASSWORD 'NEWPASSWORDHERE';"
```

### Upgrade Postgres Database
```
# Dump everything from the database to a backup file
sudo docker compose exec -T db pg_dumpall -U forgejo > pg_backup.sql

# Stop containers
sudo docker compose down

# Remove old database folder
sudo rm -rf ./postgres

# Only start the database container
sudo docker compose up -d db

# Restore database backup from the dump file earlier
sudo docker compose exec -T db psql -U forgejo < pg_backup.sql

# Start the main container
sudo docker compose up -d
```

#### If upgrading to Postgres 18, change the volume mount for `db` in `compose.yml`
```
# From
- ./postgres:/var/lib/postgresql/data

# To
- ./postgres:/var/lib/postgresql
```