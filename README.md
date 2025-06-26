# Setup

## Notice
All configuration files are already pre-configured, edits are the only thing that's left to get their containers up and running.

These containers are also expected to be run with `sudo` if you're not root, and outside of the home directory.

## Requirements
- Certbot with Cloudflare DNS Plugin (`certbot-dns-cloudflare`<sup>AUR</sup>)
- Docker
- Docker Compose
- `sudo docker network create proxy`
- ufw
- `sudo ufw allow 80/tcp; sudo ufw allow 443; sudo ufw allow 853/tcp`

## Increase Buffer Sizes for UDP connections (mainly for HTTP3/QUIC)

`sudo nano /etc/sysctl.d/99-buffer-size.conf` with the contents:
```
net.core.rmem_max=7500000
net.core.wmem_max=7500000
```
Afterwards, run `sudo sysctl -p /etc/sysctl.d/99-buffer-size.conf`. This config persists across reboots if the Linux distro uses systemd.

## Docker Compose
- **Build/Start**:
  - `sudo docker compose up -d`
  - `sudo docker compose up -d --force-recreate`
- **Stop**: `sudo docker compose down`
- **View Logs**:
  - `sudo docker logs containername --details -f`
  - `sudo docker composers logs -f`
- **Inspect**: `sudo docker inspect containername`
- **Build/Rebuild Dockerfile**: `sudo docker compose build`
- **Update**:
  - `docker pull image:tag`
  - `docker compose pull`

## Cloudflare
DNS changes might take a few minutes to propagate, especially if TLS certificates are involved with a reverse proxy.

All DNS records for sites must also be created as DNS-only records on Cloudflare pointing to the server's public address, unless the container and domain are configured like `apptest` to support Cloudflare proxied sites.

The `domain.tld` zone must also be set to `Encryption mode: Full`. This can be changed in `SSL/TLS > Overview > SSL/TLS encryption (Configure) > Custom SSL/TLS (Select) [Full]`.

## Let's Encrypt

From `Cloudflare Dashboard > Profile > API Tokens > Edit zone DNS (Use template) > Include Specific Zone > Copy the generated token`

`sudo nano /etc/letsencrypt/cloudflare/cloudflare.ini` with the contents:
```
dns_cloudflare_api_token = YOUR_COPIED_API_TOKEN
```

### Create certificates

#### Test the creation
```
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare/cloudflare.ini \
  -d domain.tld \
  -d "*.domain.tld" \
  -d "*.dns.domain.tld" \
  --email email@domain.tld \
  --agree-tos \
  --no-eff-email \
  --dry-run \
  --dns-cloudflare-propagation-seconds 60
```

#### If successful, create it
```
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare/cloudflare.ini \
  -d domain.tld \
  -d "*.domain.tld" \
  -d "*.dns.domain.tld" \
  --email email@domain.tld \
  --agree-tos \
  --no-eff-email \
  --dns-cloudflare-propagation-seconds 60
```

#### Enable automatic renewal
```
sudo systemctl enable --now certbot-renew.timer
```

## Regarding the TLS Setup Complexity 
For some reason, Traefik keeps using unsecure, self-signed certificates instead of the working, Let's Encrypt-generated certificates.
Because of this, the TLS certificate setup has to be done this way.
