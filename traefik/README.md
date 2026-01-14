# Setup
## Requirements
- Apache Tools (`apache-tools`<sup>AUR</sup>)

## Automatic restart at every start of the month
### For refreshing expired TLS certificates
```
# Open crontab editor
sudo EDITOR=nano crontab -e

# Use arrow keys and put this at the bottom
0 0 1 * * cd /path/to/traefik && docker compose up -d --force-recreate traefik
```

## Modify
### Generate `user:pass` for `traefik.http.middlewares.traefik-auth.basicauth.users=` on `compose.yaml`
```
echo $(htpasswd -nbB -C 13 username 'supastrongpasswordcanbe64ormore') | sed -e s/\\$/\\$\\$/g
```
