# Setup
## Optional Requirement
- Docker Buildx (docker-buildx<sup>AUR</sup>)

## Cloudflare Origin Certificate
Add a proxied A/AAAA record of `domain.tld` on `DNS > Records`.

Create an origin certificate from `Cloudflare Dashboard > domain.tld > SSL/TLS > Origin Server (Create Certificate) > Generate private key and CSR with Cloudflare (Private key type [RSA (2048)])`.

Once created, choose `Key Format (PEM)`.

Copy the contents of `Origin Certificate` and paste it into `traefik/certs/app.domain.tld.pem`. For `Private Key`, paste it into `traefik/certs/app.domain.tld.key`.

### Authenticated Origin Pulls (mTLS)

Download Cloudflare's CA certificate for Authenticated Origin Pulls from [here](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/global/#1-download-the-cloudflare-certificate)
and look for `Download the Cloudflare authenticated origin pull certificate (.PEM)`, click the that link (or use [this direct link](https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem) instead) and move the downloaded file to `traefik/certs/cloudflare_mtls.pem`.

Finally, `chmod` all the certificate files with the `600` permission:
```
sudo chmod 600 traefik/certs/cloudflare_mtls.pem
sudo chmod 600 traefik/certs/app.domain.tld.pem
sudo chmod 600 traefik/certs/app.domain.tld.key
```
