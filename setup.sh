#!/usr/bin/env bash
#
# One-time local setup: virtualenv, requirements, collections, sandbox SSH keypair, and
# wiring your real private key into inventory/host_vars/bigboy.yml.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# Python versions the pinned ansible-core (requirements.txt) supports as a controller.
# Newer Pythons break it (e.g. 3.15: "module 'dataclasses' has no attribute '_is_type'").
supported_pythons=(3.14 3.13 3.12)

is_supported() {
  local version
  version=$("$1" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null) || return 1
  [[ " ${supported_pythons[*]} " == *" ${version} "* ]]
}

echo "==> Setting up virtual environment (.venv)"
if [ -d .venv ] && ! is_supported .venv/bin/python; then
  echo "    .venv uses an unsupported Python ($(.venv/bin/python --version 2>&1)), recreating it"
  rm -rf .venv
fi

if [ -d .venv ]; then
  echo "    .venv already exists, skipping creation"
else
  # $PYTHON overrides the choice; otherwise use the newest supported python3.X on the PATH
  python="${PYTHON:-}"
  if [ -z "$python" ]; then
    for version in "${supported_pythons[@]}" ""; do
      if command -v "python${version:-3}" >/dev/null && is_supported "python${version:-3}"; then
        python="python${version:-3}"
        break
      fi
    done
  fi
  if [ -z "$python" ] || ! is_supported "$python"; then
    echo "No supported Python found: ansible-core needs Python ${supported_pythons[*]}." >&2
    echo "Install one (e.g. 'brew install python@3.13') or point PYTHON at it: PYTHON=/path/to/python3.13 ./setup.sh" >&2
    exit 1
  fi
  echo "    using $("$python" --version) ($(command -v "$python"))"
  "$python" -m venv .venv
fi
source .venv/bin/activate

echo "==> Installing requirements"
pip install -r requirements.txt

echo "==> Installing Ansible collections (requirements.yml)"
ansible-galaxy collection install -r requirements.yml

echo "==> Generating sandbox SSH keypair (docker/ssh_keys/ansible_test)"
mkdir -p docker/ssh_keys
if [ -f docker/ssh_keys/ansible_test ]; then
  echo "    docker/ssh_keys/ansible_test already exists, skipping"
else
  ssh-keygen -t ed25519 -f docker/ssh_keys/ansible_test -N ""
fi
chmod 400 docker/ssh_keys/ansible_test

echo "==> Configuring ansible_ssh_private_key_file for bigboy"
host_vars_file="inventory/host_vars/bigboy.yml"
mkdir -p "$(dirname "$host_vars_file")"

current_key_path=""
if [ -f "$host_vars_file" ]; then
  current_key_path=$(sed -n 's/^ansible_ssh_private_key_file: *//p' "$host_vars_file")
fi

if [ -n "$current_key_path" ]; then
  read -rp "Path to your private key for the real mini PC [${current_key_path}]: " key_path
  key_path="${key_path:-$current_key_path}"
else
  read -rp "Path to your private key for the real mini PC (e.g. ~/.ssh/id_rsa): " key_path
fi

if [ -z "$key_path" ]; then
  echo "No path entered, skipping bigboy.yml update."
  exit 0
fi

if [ -f "$host_vars_file" ] && grep -q '^ansible_ssh_private_key_file:' "$host_vars_file"; then
  sed -i.bak "s|^ansible_ssh_private_key_file:.*|ansible_ssh_private_key_file: ${key_path}|" "$host_vars_file"
  rm -f "${host_vars_file}.bak"
else
  # Ensure file starts with YAML document start
  if [ ! -f "$host_vars_file" ]; then
    echo "---" > "$host_vars_file"
  elif ! head -1 "$host_vars_file" | grep -q '^---'; then
    # Prepend --- if not already there
    (echo "---"; cat "$host_vars_file") > "${host_vars_file}.tmp" && mv "${host_vars_file}.tmp" "$host_vars_file"
  fi
  echo "ansible_ssh_private_key_file: ${key_path}" >> "$host_vars_file"
fi

echo "==> Done. ${host_vars_file} now points to ${key_path}"
