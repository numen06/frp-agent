#!/bin/bash
set -e
FRP_DIR="{{install_path}}"
mkdir -p "$FRP_DIR"
echo "Downloading {{filename}} ..."
cd /tmp && curl -fSL -o "{{filename}}" "{{download_url}}" \
  && tar -xzf "{{filename}}" \
  && cp -f frp_*/frpc "$FRP_DIR/" \
  && rm -f "{{filename}}" \
  && rm -rf frp_*
{{config_line}}{{done_echo}}
