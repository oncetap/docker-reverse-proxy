# Setup

## Internal network for ntfy and its dedicated postgres db
`sudo docker network create --internal ntfy-net`

## Modify
### Generate `user:pass` for `NTFY_AUTH_USERS` on `compose.yaml`
```
echo $(htpasswd -nbB -C 13 username 'supastrongpasswordcanbe64ormore') | sed -e s/\\$/\\$\\$/g
```
Then replace the value `USERNAMEHERE:PASSWORDHERE` from `NTFY_AUTH_USERS` with the command output. Make sure `:admin` is still intact at the end of the value.

### Generate Keys for `NTFY_WEB_PUSH_*` on `compose.yml`
- Go to [ntfy's official config generator](https://docs.ntfy.sh/config/#config-generator)
- Toggle `Which features do you want to enable? > Web push` and switch to the new `Web Push` tab.
- If the `Private key` & `Public key` fields are empty, press `Regenerate keys`. Then, copy and paste the generated private & public keys from the config generator into the respective `NTFY_WEB_PUSH_*` fields.

### Generate password for the database
```
echo "DB_PASS=$(openssl rand -base64 36 | tr -d '\n')" >> .env
```

### Upgrade Postgres Database
```
# Dump everything from the database to a backup file
sudo docker compose exec -T db pg_dumpall -U ntfy > pg_backup.sql

# Stop containers
sudo docker compose down

# Remove old database folder
sudo rm -rf ./postgres

# Only start the database container
sudo docker compose up -d db

# Restore database backup from the dump file earlier
sudo docker compose exec -T db psql -U ntfy < pg_backup.sql

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