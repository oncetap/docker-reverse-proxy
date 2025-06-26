# Setup
## Requirements
- Apache Tools (`apache-tools`<sup>AUR</sup>)

## Modify
### Generate `user:pass` for `traefik.http.middlewares.traefik-auth.basicauth.users=` on `compose.yaml`
```
echo $(htpasswd -nbB -C 13 username 'supastrongpasswordcanbe64ormore') | sed -e s/\\$/\\$\\$/g
```
