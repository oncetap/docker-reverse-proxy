# Setup
## Requirements
- `gettext` (for `envsubst`)

## Internal network for ente and its dedicated postgres db and garage
`sudo docker network create --internal ente-net`

## DNS Records
Create DNS-only A records on server's public IPv4 address:
```
photos.domain.tld
photos-api.domain.tld
```

If you uncomment any optional endpoints in `compose.yml`, add a DNS record for those as well:
```
ente-accounts.domain.tld
photos-albums.domain.tld
ente-cast.domain.tld
ente-share.domain.tld
photos-embed.domain.tld
paste.domain.tld
ente-locker.domain.tld
```

## Generate secrets
All secrets must be generated with `openssl` and stored in a `.env` file before generating the configuration. Run each command below from this directory:
```
echo "POSTGRES_PASSWORD=$(openssl rand -base64 36 | tr -d '\n')" >> .env
echo "GARAGE_RPC_SECRET=$(openssl rand -hex 32)" >> .env
echo "ENTE_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')" >> .env
echo "ENTE_HASH_KEY=$(openssl rand -base64 64 | tr -d '\n')" >> .env
echo "ENTE_JWT_SECRET=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')" >> .env
```

Do not lose the `.env` file. The encryption and hash keys are critical. If lost, encrypted user data is unrecoverable. S3 access keys are generated automatically by init-garage.sh and appended to `.env`.

## Generate configuration files
After creating your `.env` file with the generated secrets, run the configuration generator:
```
chmod +x generate-config.sh
./generate-config.sh
```

This generates `museum.yaml` and `garage.toml` from their respective `.template` files using the values from your `.env` file.

## Initialize Garage
Then, start the containers for the first time and run the Garage initialization script to create the storage layout, buckets, and access keys:
```
chmod +x init-garage.sh
./init-garage.sh
```

This script is idempotent and can be safely run multiple times.

After the initialization completes, restart so museum picks up the S3 credentials:
```
sudo docker compose down && sudo docker compose up -d
```

## First signup
Open `photos.domain.tld` and create your account. Ente requires email verification even without SMTP configured, the verification code is printed to the museum container logs. Retrieve it with:
```
sudo docker compose logs museum | grep "Verification code"
```

If you'd rather use a fixed verification code for convenience (e.g. during initial setup), add this to `museum.yaml` under `internal:`:
```yaml
internal:
  hardcoded-ott:
    emails:
      - "your@email.com,123456"
```

This sets the verification code to `123456` for that specific email. You can also use a suffix-based rule for all emails on a domain:
```yaml
internal:
  hardcoded-ott:
    local-domain-suffix: "@yourdomain.com"
    local-domain-value: "123456"
```
Remove after creating your admin account.

## Make yourself admin
Admin users must be explicitly whitelisted in `museum.yaml`. After signing up, get your user ID from the database (note: emails are encrypted, so use `name` to identify users):
```
sudo docker compose exec postgres psql -U ente -d ente_db -c "SELECT user_id, name FROM users;"
```

Then add it to `museum.yaml` under `internal.admin` (or `internal.admins` for multiple):
```yaml
internal:
  admin: <your_user_id>
```

For multiple admins:
```yaml
internal:
  admins:
    - <user_id_1>
    - <user_id_2>
```

Restart to apply:
```
sudo docker compose down && sudo docker compose up -d
```

## Increase storage and account validity
Self-hosted accounts start with limited storage. Use the Ente CLI to grant unlimited storage and extend account validity. Install it from [GitHub](https://github.com/ente-io/ente/tree/main/cli), then:

**1. Configure the CLI endpoint**, create `~/.ente/config.yaml`:
```yaml
endpoint:
  api: https://photos-api.domain.tld
```

**2. Set up secrets storage**, the CLI needs a file to store its encryption keys:
```
export ENTE_CLI_SECRETS_PATH=~/.ente/secrets.txt
```
Add this to your `~/.bashrc` or `~/.zshrc` to make it persistent. The CLI will create the file and generate a key automatically on first run. Keep this file secure.

**3. Add your admin account:**
```
ente account add
```
It will prompt for your email, password, and an export directory. The export directory is where decrypted files get saved if you use the CLI's export feature, use any directory you want that exists (e.g. `~/ente-export`).

**4. Update subscription** for unlimited storage and 100-year validity:
```
ente admin update-subscription -a <admin-email> -u <user-email> --no-limit
```

With a custom limit:
```
ente admin update-subscription -a <admin-user-mail> -u <user-email-to-update> --no-limit False
```

Run `ente admin update-subscription --help` for all options.

## Disable registration
To prevent new users from signing up, edit `museum.yaml` and uncomment `disable-registration` under `internal:`:

```yaml
  disable-registration: true
```

Restart to apply:
```
sudo docker compose down && sudo docker compose up -d
```

## Optional endpoints
The following endpoints are commented out in `compose.yml` by default. Uncomment them if you need them, and also uncomment the corresponding `apps:` entries in `museum.yaml.template` before running `generate-config.sh`:

| Endpoint | Port | Purpose |
|----------|------|---------|
| `ente-accounts.domain.tld` | 3001 | Passkey-based 2FA |
| `photos-albums.domain.tld` | 3002 | Public album link sharing |
| `ente-cast.domain.tld` | 3004 | Chromecast support |
| `ente-share.domain.tld` | 3005 | Public file link sharing (Locker) |
| `photos-embed.domain.tld` | 3006 | Embedded album sharing |
| `paste.domain.tld` | 3008 | One-time paste sharing |
| `ente-locker.domain.tld` | 3009 | Locker app |

Remember to also create the corresponding DNS records for any endpoints you enable.

### Upgrade Postgres Database
```
# Dump everything from the database to a backup file
sudo docker compose exec -T postgres pg_dumpall -U ente > pg_backup.sql

# Stop containers
sudo docker compose down

# Remove old database folder
sudo rm -rf ./postgres

# Only start the database container
sudo docker compose up -d postgres

# Restore database backup from the dump file earlier
sudo docker compose exec -T postgres psql -U ente < pg_backup.sql

# Start the main container
sudo docker compose up -d
```

#### If upgrading to Postgres 18, change the volume mount for `postgres` in `compose.yml`
```
# From
- ./postgres:/var/lib/postgresql/data

# To
- ./postgres:/var/lib/postgresql
```
