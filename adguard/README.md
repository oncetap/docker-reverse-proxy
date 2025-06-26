# Setup
## Requirements
- Apache Tools (`apache-tools`<sup>AUR</sup>)

## Setup Login
Generate the hashed password for the `password` field on `conf/AdGuardHome.yaml` with the fommand:
```
echo $(htpasswd -nbB -C 13 username 'supastrongpasswordcanbe64charactersormore') | sed -e s/\\$/\\$\\$/g
```
The generated output of this command is in the format of `username:hashedpassword`. Your chosen username should be the value of `name` and `hashedpassword` should be the value of `password`.

## ClientID Setup

For each ClientID you create, you also need to create a DNS record on Cloudflare for it to have a working subdomain for DNS over TLS.

The DNS record should be a DNS-only A record with the name `<ClientID>.dns.domain.tld` pointing to the server's public IPv4 address.

## Allowed Clients

To use this, you need to add the `proxy` Docker network's subnet CIDR first to prevent *networking problems*.

You can get this CIDR by running `sudo docker network inspect proxy | jq -r '.[].IPAM.Config[].Subnet'`. For example, if the output from this command is `172.18.0.0/16`, you should add that value to the `Allowed Clients` field.

Each whitelist record is separated with newlines:
```
172.18.0.0/16
mysupersecretclientidhere
myipaddress
```
