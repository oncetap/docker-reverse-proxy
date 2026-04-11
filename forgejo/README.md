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
