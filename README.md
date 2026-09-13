# homeforge

Ansible project to build, track, and rebuild my home server and the services running on it.

A local Docker sandbox (`docker/`) runs disposable Ubuntu 24.04 and Ubuntu 26.04 containers reachable over SSH, so playbooks can be developed and tested without touching the real mini PC. Both the sandbox and the real mini PC belong to the same inventory group (`homeserver`), so every playbook is written once and runs against either — only the inventory file passed on the command line changes.

## Project structure

```
.
├── .ansible-lint                  # ansible-lint rule configuration
├── .yamllint                      # yamllint configuration
├── ansible.cfg                    # points ansible-playbook at the test inventory by default
├── requirements.txt               # pinned ansible-core version (installed into .venv)
├── setup.sh                       # one-time local setup (venv, requirements, SSH keys) — see below
├── docker/                        # local test sandbox — never used against the real mini PC
│   ├── Dockerfile-24.04           # Ubuntu 24.04 + systemd + sshd, built for Ansible testing
│   ├── Dockerfile-26.04           # Ubuntu 26.04 + systemd + sshd, built for Ansible testing
│   ├── docker-compose.yml         # runs the images above, port 2222 -> 22 and 2223 -> 22
│   └── ssh_keys/                  # keypair generated locally, gitignored
├── inventory/
│   ├── dev.yml                    # homeserver group -> the Docker sandbox
│   ├── production.yml             # homeserver group -> the real mini PC
│   ├── group_vars/
│   │   └── homeserver.yml         # vars shared by both environments (e.g. ansible_become)
│   └── host_vars/
│       └── bigboy.yml             # machine-specific overrides (e.g. SSH key path), gitignored
├── playbooks/                     # locations for the different playbooks
└── roles/                         # the actual task implementations, called by playbooks
```

## Prerequisites

- Python 3
- Docker + the Docker Compose plugin
- SSH client (`ssh-keygen`)

## One-time setup

```bash
./setup.sh
```

- creates `.venv` and installs `requirements.txt` into it
- generates the sandbox SSH keypair (`docker/ssh_keys/ansible_test`)
- prompts for the path to your real SSH private key for the mini PC and writes it to `inventory/host_vars/bigboy.yml` (gitignored)

It's safe
to re-run at any time: existing steps are skipped or updated in place rather than
duplicated.

The script only sets up the venv for its own subshell — activate it in your shell
afterward to use it interactively:

```bash
source .venv/bin/activate
```

## Quick start: test against the Docker sandbox

```bash
# build & start the sandbox
docker compose -f docker/docker-compose.yml up -d --build

# run a playbook against it (uses inventory/dev.yml by default, per ansible.cfg)
ansible-playbook playbooks/example.yml
```

Expected output:

```
PLAY [Example playbook] ****************************************************************************************************************************************************************************************

TASK [Gathering Facts] *****************************************************************************************************************************************************************************************
ok: [test-ubuntu-noble]
ok: [test-ubuntu-resolute]

TASK [example : Print welcome message] *************************************************************************************************************************************************************************
ok: [test-ubuntu-noble] => {
    "msg": "Hello from the homeserver Ansible project!"
}
ok: [test-ubuntu-resolute] => {
    "msg": "Hello from the homeserver Ansible project!"
}

PLAY RECAP *****************************************************************************************************************************************************************************************************
test-ubuntu-noble          : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
test-ubuntu-resolute       : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Tear the sandbox down when you're done:

```bash
docker compose -f docker/docker-compose.yml down
```

Rebuilding from scratch is just `down` followed by `up -d --build` again — that's the
point of the sandbox: it should always be safe to throw away and recreate.

## Running against the real mini PC

Run any playbook with the production inventory explicitly:

   ```bash
   ansible-playbook -i inventory/production.yml playbooks/example.yml
   ```

   Production is never used by accident — `ansible.cfg` defaults to the test inventory,
   so you must pass `-i inventory/production.yml` explicitly to target the real box.

## CI / Linting

Three lint jobs run automatically on every merge/pull request:

| Job | Tool | What it checks |
|---|---|---|
| `ansible-lint` | ansible-lint | Ansible best practices and task correctness |
| `yamllint` | yamllint | YAML syntax and formatting |
| `syntax-check` | ansible-playbook --syntax-check | Parses every playbook for structural errors |

GitHub Actions runs these automatically on every pull request (`.github/workflows/lint.yml`).

To run the checks locally (tools are included in `requirements.txt` and installed by `setup.sh`):

```bash
source .venv/bin/activate
ansible-lint
yamllint -c .yamllint.yml .
ansible-playbook --syntax-check playbooks/*.yml -i inventory/dev.yml
```

## Playbooks

- [example.yml](playbooks/example.yml) - Example playbook for testing the Ansible setup
- [setup.yml](playbooks/setup.yml) - Setup all services
