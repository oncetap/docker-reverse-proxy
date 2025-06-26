# Setup
## Optional Requirement
- Docker Buildx (docker-buildx<sup>AUR</sup>)

## Cloudflare Origin Certificate
Add a proxied A/AAAA record of `domain.tld` on `DNS > Records`.

Create an origin certificate from `Cloudflare Dashboard > domain.tld > SSL/TLS > Origin Server (Create Certificate) > Generate private key and CSR with Cloudflare (Private key type [RSA (2048)])`.

Once created, choose `Key Format (PEM)`.

Copy the contents of `Origin Certificate` and paste it into `traefik/certs/app.domain.tld.pem`. For `Private Key`, paste it into `traefik/certs/app.domain.tld.key`.

### Authenticated Origin Pulls (mTLS)

Download Cloudflare's CA certificate for Authenticated Origin Pulls from [here](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/zone-level/#1-upload-certificate-to-origin)
and look for `To use a Cloudflare certificate (which uses a specific CA), download the .PEM file and upload it to your origin.`, click the `download the .PEM file` and move the downloaded file to `traefik/certs/cloudflare_mtls.pem`.

Finally, `chmod` all the certificate files with the `600` permission:
```
sudo chmod 600 traefik/certs/cloudflare_mtls.pem
sudo chmod 600 traefik/certs/app.domain.tld.pem
sudo chmod 600 traefik/certs/app.domain.tld.key
```
