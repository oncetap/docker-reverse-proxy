# Setup

## Requirements
- A system with at least 6GB of RAM and 2 CPU cores

## Internal network for immich and its dedicated redis and postgres db
`sudo docker network create --internal immich-net`

## Setup environment variables
Move `example.env` to `.env`.

## DNS Records
Create DNS-only A records on Cloudflare pointing to the server's public IPv4 address:
```
immich.domain.tld
```

## Generate password for the database
All secrets must be generated and stored in a `.env` file before starting the containers. Run this command from the immich directory:
```
echo "DB_PASSWORD=$(openssl rand -base64 36 | tr -d '\n')" >> .env
```

## Configure the .env file
Edit `.env` and set the following values:
- `UPLOAD_LOCATION`, the path on the host where uploaded photos and videos will be stored.
- `DB_DATA_LOCATION`, the path on the host for the PostgreSQL data. Default is `./pgdata`.
- `TZ`, uncomment and set your timezone (e.g. `America/New_York`).
- `IMMICH_VERSION`, pin to a specific version (e.g. `v1.141.0`) or leave as `release` for the latest.

## Start the containers
```
sudo docker compose up -d
```

## First signup
Open `immich.domain.tld` and create your account. The first user to register will be the admin user. The admin user will be able to add other users to the application.

## Hardware Acceleration (Optional)

### Machine Learning
By default, machine learning runs on CPU. To enable GPU acceleration, modify the `immich-machine-learning` service in `compose.yml` based on your GPU:

#### NVIDIA
Change the image tag and add GPU device reservation:
```yaml
    image: ghcr.io/immich-app/immich-machine-learning:${IMMICH_VERSION:-release}-cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```
You need the NVIDIA Container Toolkit installed on the host. See the [install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) for supported distros, or the [AUR package](https://archlinux.org/packages/extra/x86_64/nvidia-container-toolkit/) for Arch.

#### AMD
Change the image tag and pass the GPU devices:
```yaml
    image: ghcr.io/immich-app/immich-machine-learning:${IMMICH_VERSION:-release}-rocm
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
```

#### Intel (OpenVINO)
Change the image tag and pass the GPU device:
```yaml
    image: ghcr.io/immich-app/immich-machine-learning:${IMMICH_VERSION:-release}-openvino
    devices:
      - /dev/dri:/dev/dri
```
You need `intel-compute-runtime` installed on the host:
```
sudo pacman -S intel-compute-runtime
```

Verify GPU passthrough is working (applies to all):
```
sudo docker compose exec immich-machine-learning ls /dev/dri
```

To go back to CPU, remove the image suffix and the `devices`/`deploy` section.

### Transcoding
To enable hardware-accelerated transcoding, download the matching `hwaccel.transcoding.yml` from the [Immich GitHub releases](https://github.com/immich-app/immich/releases) and place it in the immich directory. Then uncomment the `extends` section in `compose.yml` and set the service to your GPU type (`cpu`, `nvenc`, `quicksync`, `rkmpp`, `vaapi`, or `vaapi-wsl`).

### Machine Learning
For ML hardware acceleration (CUDA, ROCm, OpenVINO, etc.), add the appropriate suffix to the `immich-machine-learning` image tag (e.g. `${IMMICH_VERSION:-release}-cuda`). Uncomment and configure the `extends` section for ML as well. Download the `hwaccel.ml.yml` file from the same releases page.

## Update
```
sudo docker compose pull
sudo docker compose up -d
```

## Database Backup
Immich has built-in database backups. You can configure the backup schedule and location under **Administration > Settings > Backup**.

To manually back up the database:
```
sudo docker compose exec -T database pg_dumpall -U postgres > pg_backup.sql
```

To restore from a backup:
```
sudo docker compose down
sudo rm -rf ./pgdata
sudo docker compose up -d database
sudo docker compose exec -T database psql -U postgres < pg_backup.sql
sudo docker compose up -d
```

### Upgrade Postgres Database
When upgrading the Immich PostgreSQL image to a new major version:
```
# Dump everything from the database to a backup file
sudo docker compose exec -T database pg_dumpall -U postgres > pg_backup.sql

# Stop containers
sudo docker compose down

# Remove old database folder
sudo rm -rf ./pgdata

# Only start the database container
sudo docker compose up -d database

# Restore database backup from the dump file earlier
sudo docker compose exec -T database psql -U postgres < pg_backup.sql

# Start the main container
sudo docker compose up -d
```
