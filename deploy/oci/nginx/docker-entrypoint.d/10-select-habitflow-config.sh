#!/bin/sh
set -eu

domain="${DOMAIN:?DOMAIN must be set}"
case "$domain" in
  *[!A-Za-z0-9.-]* | '' | .* | *..*)
    echo "DOMAIN contains unsupported characters." >&2
    exit 1
    ;;
esac

template_dir=/etc/nginx/habitflow-templates
target=/etc/nginx/templates/habitflow.conf.template

mkdir -p "$(dirname "$target")"

if [ -f "/etc/letsencrypt/live/$domain/fullchain.pem" ] \
  && [ -f "/etc/letsencrypt/live/$domain/privkey.pem" ]; then
  cp "$template_dir/habitflow.conf.template" "$target"
  echo "Using HTTPS Nginx configuration for $domain."
else
  cp "$template_dir/habitflow.http.conf.template" "$target"
  echo "Using HTTP-only Nginx configuration for certificate issuance."
fi
