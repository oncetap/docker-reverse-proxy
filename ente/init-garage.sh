#!/bin/sh
set -ea

echo "Initializing Garage object storage..."

# Wait for Garage to be ready
echo "Waiting for Garage to be ready..."
until sudo docker exec ente-garage /garage status 2>/dev/null; do
  sleep 2
done

# Check if layout has already been applied
LAYOUT_CHECK=$(sudo docker exec ente-garage /garage status 2>&1 || true)

if echo "$LAYOUT_CHECK" | grep -q "NO ROLE ASSIGNED"; then
  echo "Configuring cluster layout..."
  NODE_ID=$(echo "$LAYOUT_CHECK" | awk '/^[0-9a-f]{10,}/{print $1; exit}')

  if [ -z "$NODE_ID" ]; then
    echo "ERROR: Could not determine Garage node ID"
    exit 1
  fi

  sudo docker exec ente-garage /garage layout assign -z dc1 -c 1G "$NODE_ID"
  sudo docker exec ente-garage /garage layout apply --version 1
  echo "Layout applied."
else
  echo "Cluster layout already exists, skipping."
fi

# Create buckets (idempotent)
echo "Creating storage buckets..."
for bucket in b2-eu-cen wasabi-eu-central-2-v3 scw-eu-fr-v3; do
  if sudo docker exec ente-garage /garage bucket list 2>/dev/null | grep -q "$bucket"; then
    echo "  Bucket '$bucket' already exists, skipping."
  else
    sudo docker exec ente-garage /garage bucket create "$bucket"
    echo "  Bucket '$bucket' created."
  fi
done

# Load .env
if [ ! -f .env ]; then
  echo "ERROR: .env file not found."
  exit 1
fi

. ./.env

# Create S3 access key if it doesn't exist
echo "Creating S3 access key..."
if sudo docker exec ente-garage /garage key list 2>/dev/null | grep -q "ente-s3"; then
  echo "  Key 'ente-s3' already exists, skipping."
else
  KEY_OUTPUT=$(sudo docker exec ente-garage /garage key create ente-s3 2>&1)
  S3_KEY_ID=$(echo "$KEY_OUTPUT" | grep -oP 'Key ID:\s*\K\S+')
  S3_SECRET=$(echo "$KEY_OUTPUT" | grep -oP 'Secret key:\s*\K\S+')

  if [ -z "$S3_KEY_ID" ] || [ -z "$S3_SECRET" ]; then
    echo "ERROR: Failed to parse key output"
    echo "$KEY_OUTPUT"
    exit 1
  fi

  # Write S3 credentials to .env
  echo "S3_ACCESS_KEY=$S3_KEY_ID" >> .env
  echo "S3_SECRET_KEY=$S3_SECRET" >> .env
  echo "  Key 'ente-s3' created and saved to .env."
  echo "  Key ID: $S3_KEY_ID"
fi

# Re-source .env to pick up S3 keys
. ./.env

# Replace S3 placeholders in museum.yaml (only if they haven't been replaced yet)
if grep -q 'S3_ACCESS_KEY\|S3_SECRET_KEY' museum.yaml 2>/dev/null; then
  sed -i "s/\${S3_ACCESS_KEY}/$S3_ACCESS_KEY/g; s/\${S3_SECRET_KEY}/$S3_SECRET_KEY/g" museum.yaml
  echo "Updated museum.yaml with S3 credentials."
fi

# Grant key permissions on buckets (idempotent)
echo "Granting key permissions..."
for bucket in b2-eu-cen wasabi-eu-central-2-v3 scw-eu-fr-v3; do
  sudo docker exec ente-garage /garage bucket allow --key ente-s3 --read --write --owner "$bucket" 2>/dev/null || true
done

echo "Garage initialization complete!"