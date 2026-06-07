#!/bin/sh
set -ea

if [ ! -f .env ]; then
  echo "ERROR: .env file not found."
  exit 1
fi

. ./.env

envsubst '${POSTGRES_PASSWORD} ${ENTE_ENCRYPTION_KEY} ${ENTE_HASH_KEY} ${ENTE_JWT_SECRET}' < museum.yaml.template > museum.yaml
echo "Generated museum.yaml"

envsubst '${GARAGE_RPC_SECRET}' < garage.toml.template > garage.toml
echo "Generated garage.toml"
