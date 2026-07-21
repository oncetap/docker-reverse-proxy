# Setup

## Create a dedicated DNS-only record for REALITY proxy
Create a dummy subdomain that looks harmless, e.g. `stats.domain.tld` (This will be used later for setting up the VLESS host)

## Change default login credentials
After finishing the container setup, start it and login to the domain you set 3xui to with the default credentials:

Default username: `admin`
Default password: `admin`

After logging in, change these on Panel Settings > Authentication.

You can use other tools to generate a random username and password but you can also generate them with this command:
```
# For username:
tr -dc 'a-z0-9' < /dev/urandom | head -c 12 ; echo

# For password:
openssl rand -base64 24
```

## Create Inbound
Goto `Inbounds > "+" icon button`

### Basics
Remark: `VLESS REALITY` (Name for the Inbound, can be anything memorable and distinct)

Protocol: `vless`

Port: `8443`

### Protocol
Set `Generate keys` to `X25519 (native)` and press `Generate`.

### Stream
Set `Transmission` to `RAW`. Make sure everything else is disabled on this tab.

### Security
Set `Security` to `Reality`.

Target: `aws.amazon.com:443`

SNI: `aws.amazon.com`

Scroll down and click `Get New Cert`

Then press `Save`.

## Create Client
Goto `Client > "+" icon button`

### Basics
Email: `VLESS Client 1` (Does not necessarily have to be an email, it's essentially the client's name)

Scroll down and set `Attached inbounds` to the `Inbound` you created earlier (i.e. `VLESS REALITY`).

## Create Hosts
Goto `Hosts > "+" icon button`

### Basic (tab 1)
Remark: `VLESS REALITY` (Can be the same as the Inbound's remark for less confusion)

Inbounds: `Set to the Inbound you created earlier`

Address: `stats.domain.tld` (Same as the DNS-only record you created earlier)

Port: `443`

### Security (tab 2)
Make sure `Security` is set to `same`.

### Clash (Mihomo) [tab 4] **OPTIONAL**
IP version: `ipv4-prefer`

Enable both `Mihomo X25519` and `Shuffle host`

And you're done. Once you finish all these steps, you can go back to the `Clients` tab
and find the client you created earlier. From there, click the `3 vertical dots icon button > QR Code` and open the collapsible that has the tags `Vless` `TCP` `REALITY` then click the `Copy` icon button.

You can import this configuration on an Xray client

<b><u>Recommended clients (Not endorsing them, I just found these clients to be the ones that work best)</u></b>:

**Windows/Linux/MacOS**: [v2rayN](https://github.com/2dust/v2rayn)

**Android**: [v2rayNG](https://github.com/2dust/v2rayng)

**iOS**: [Hiddify](https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532)

Afterwards, you should be able to browse normally like it's a normal VPN if everything is setup correctly.
