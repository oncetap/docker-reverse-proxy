# Setup
The admin site and wireguard host domains should not be the same.
Ex: Use `wg.domain.tld` for the dashboard/admin of `wg-easy`, and `wg-connect.domain.ltd` as the actual WireGuard's connection host and both should still point at the server's IP.

If you face any connectivity issues with the WireGuard server, use the edge branch branch instead: `image: ghcr.io/wg-easy/wg-easy:edge`
