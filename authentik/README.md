# Setup

## Internal network for authentik and its dedicated postgres db
`sudo docker network create --internal authentik-net`

## Setting up environment variables
Move `example.env` to `.env` and configure the file as needed.

## Generate secrets
All secrets must be generated and stored in a `.env` file before starting the containers. Run these commands from the authentik directory:
```
echo "PG_PASS=$(openssl rand -base64 36 | tr -d '\n')" >> .env
echo "AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')" >> .env
```

Note: PostgreSQL passwords longer than 99 characters are not supported. The `openssl` command above generates a 36-character base64 password which is well within the limit.

Do not lose the `.env` file. The secret key is critical, if lost, encrypted data is unrecoverable.

Alternatively, you can manually edit the `.env` file and replace the placeholder values.

## Start the containers
```
sudo docker compose up -d
```

## First login
Open `auth.domain.tld` and you will be prompted to set a password for the `akadmin` user (the default administrator account).

## Email configuration (optional)
Authentik can send emails for password resets, verification, and admin alerts. To configure email, add the following to your `.env` file:

```
AUTHENTIK_EMAIL__HOST=smtp.example.com
AUTHENTIK_EMAIL__PORT=587
AUTHENTIK_EMAIL__USERNAME=your-email@example.com
AUTHENTIK_EMAIL__PASSWORD=your-email-password
AUTHENTIK_EMAIL__USE_TLS=true
AUTHENTIK_EMAIL__FROM=authentik@example.com
```

## Important notes
- Do **not** mount `/etc/timezone` or `/etc/localtime` in the Authentik containers. Authentik uses UTC internally and mounting timezone files will cause problems with OAuth and SAML authentication.
- The first user to log in after setup becomes the `akadmin` administrator.

## Update
When updating Authentik, update the `AUTHENTIK_TAG` in `.env`, then:
```
sudo docker compose pull
sudo docker compose up -d
```

Check the [release notes](https://docs.goauthentik.io/docs/releases/) before upgrading, as some versions require manual migration steps.

## Upgrade Postgres Database
```
# Dump everything from the database to a backup file
sudo docker compose exec -T postgresql pg_dumpall -U authentik > pg_backup.sql

# Stop containers
sudo docker compose down

# Remove old database folder
sudo rm -rf ./postgres

# Only start the database container
sudo docker compose up -d postgresql

# Restore database backup from the dump file earlier
sudo docker compose exec -T postgresql psql -U authentik < pg_backup.sql

# Start the main container
sudo docker compose up -d
```

## Integrating with Immich (OAuth)

### Create an application and provider in Authentik
1. Log in to the Authentik admin interface at `auth.domain.tld`.
2. Navigate to **Applications > Applications** and click **New Application**.
3. Fill in a descriptive name (e.g. "Immich") and optional group.
4. Choose **OAuth2/OpenID Connect** as the provider type.
5. Configure the provider:
   - Note the **Client ID** and **Client Secret**, you will need these in Immich.
   - **Authorization flow**: use the default `default-provider-authorization-implicit-consent`. This skips the consent screen since you are authenticating to your own app. Use `default-provider-authorization-explicit-consent` instead if you want users to manually approve access each time.
   - Add the following **Strict** redirect URIs:
     - `app.immich:///oauth-callback`, for the mobile app
     - `https://immich.domain.tld/auth/login`, for the web client
     - `https://immich.domain.tld/user-settings`, for linking OAuth in user settings
   - Select any available signing key.
6. (Optional) Configure the **Launch URL** to `https://immich.domain.tld/auth/login?autoLaunch=1` so that clicking the application in Authentik will auto-login to Immich.
7. Click **Submit** to save.

### Configure OAuth in Immich
1. In Immich, go to **Administration > Authentication Settings > OAuth**.
2. Set the following:
   - **Enabled**: `true`
   - **Issuer URL**: `https://auth.domain.tld/application/o/<application_slug>/` (replace `<application_slug>` with the slug from the Authentik provider, typically the lowercase name you gave it, e.g. `immich`)
   - **Client ID**: the Client ID from Authentik
   - **Client Secret**: the Client Secret from Authentik
   - **Scope**: `openid email profile`
   - **Button Text**: customize (e.g. "Login with Authentik")
   - **Auto Register**: `true` (recommended, automatically creates an Immich account on first OAuth login)
   - **Auto Launch**: `true` (optional, skips the login page and redirects directly to Authentik)
3. Save the settings.

The Issuer URL should look like `https://auth.domain.tld/application/o/immich/`. The `.well-known/openid-configuration` part is optional and will be automatically appended during discovery.

### Mobile Redirect URI
If your Authentik instance does not accept the custom scheme `app.immich:///oauth-callback` as a redirect URI, you can use Immich's built-in mobile redirect route as a workaround:
1. Add `https://immich.domain.tld/api/oauth/mobile-redirect` as a redirect URI in the Authentik provider.
2. In Immich's OAuth settings, set **Mobile Redirect URI Override** to `https://immich.domain.tld/api/oauth/mobile-redirect`.
