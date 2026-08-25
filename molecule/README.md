<!--
SPDX-FileCopyrightText: 2018-2025 Slavi Pantaleev
SPDX-FileCopyrightText: 2019-2022 Aaron Raimist
SPDX-FileCopyrightText: 2019-2023 MDAD project contributors
SPDX-FileCopyrightText: 2023 QEDeD
SPDX-FileCopyrightText: 2024 Fabio Bonelli
SPDX-FileCopyrightText: 2024 Nikita Chernyi
SPDX-FileCopyrightText: 2024-2026 Suguru Hirahara
SPDX-FileCopyrightText: 2026 spatterlight

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Molecule Testing

This role supports [Molecule](https://docs.ansible.com/projects/molecule/), an Ansible testing framework designed for developing and testing Ansible collections, playbooks, and roles.

## Prerequisites

To utilize Molecule you need to prepare several requirements:

- **x86** computer running one of these operating systems that make use of [systemd](https://systemd.io/):
  - **Archlinux**
  - **CentOS**, **Rocky Linux**, **AlmaLinux**, or possibly other RHEL alternatives (although your mileage may vary)
  - **Debian** (10/Buster or newer)
  - **Ubuntu** (18.04 or newer, although [20.04 may be problematic](https://github.com/mother-of-all-self-hosting/mash-playbook/blob/main/docs/ansible.md#supported-ansible-versions) if you run the Ansible playbook on it)
- `root` access on the computer which Molecule runs against
- [Ansible](http://ansible.com/) program
- [Python](https://www.python.org/)
  - Most distributions install Python by default, but some don't (e.g. Ubuntu 18.04) and require manual installation (something like `apt-get install python3`)
- [Docker](https://www.docker.com)
  - Access to Docker UNIX socket (`/var/run/docker.sock`) is required by default

## Installation

To set up the environment for using Molecule, run the command below on the terminal:

```bash
python3 -m venv ./molecule/venv
source ./molecule/venv/bin/activate
pip3 install -r ./molecule/requirements.txt
```

## Scenarios

Currently these testing scenarios are available:

### `default`

Tests a standard Docker Registry installation.

Before the role runs, the scenario records that the host has no registry, and starts the stock container image as a negative control, so that what a registry provides on its own is not credited to the role. The control is handed [an explicit minimal configuration file](default/files/control-config.yml) rather than left on the one the container image bundles: the bundled file describes how the image is packaged rather than how the registry behaves, and it is not stable across releases. It says nothing about `storage.delete`, so what the control pins down is the registry's own compiled-in default — measured at `405` on both 2.8.3 and 3.1.1.

The role is then installed **at the last 2.x release first**, and an image is pushed through it, before the role's own version is installed over the same storage path. What 2.8.3 wrote is fetched back out of the upgraded registry and re-hashed on the host, so that "a v3 registry still serves a v2 store" is measured rather than assumed. A fresh install cannot see the only question a major version bump raises for someone who already runs a registry.

It also checks that the systemd service is active, that `/v2/` identifies itself as a registry, and that a container image can be pushed and read back with every digest matching — over the registry HTTP API rather than with `docker push`, so that the result does not depend on the Docker version the test runs against. The pushed blob is then located on the host, under the role's bind-mounted data path.

The role is installed twice more, with `docker_registry_storage_delete_enabled` off and then on, to show that the setting reaches the running process: the same deletion is refused with `405` and then accepted with `202`. Since the v3 container image's own configuration file turns deletion *on*, that `405` is evidence that the role's env file overrides the file inside the image — which the scenario states explicitly, by reading the bundled configuration file out of the running container. That read doubles as the test for `docker_registry_container_config_path`.

What the v3 image's configuration file would otherwise have changed is checked too: the debug/metrics port is refused on the container's own address while the API answers on that same address (which is what keeps the refusal from being a broken probe), and `X-Content-Type-Options: nosniff` is still sent.

Finally the running version is compared against `docker_registry_version`, and the garbage collection script and its timer are checked — including an assertion that the script is *not* valid bash. See [Garbage collection](../README.md#garbage-collection) for why that is deliberate.

### `default-selfbuild`

Tests a standard Docker Registry installation with self-building the container image.

Since the `default` scenario covers the registry's behavior, this one checks what is peculiar to self-building: that the service runs the locally built image, and that this image carries no repository digest — which an image pulled from a registry always does, and one built here never can.

## Running

By default it is configured to run the scenarios on Ubuntu 26.04.

```bash
molecule test --scenario-name default
```

You can utilize other distributions by setting one to the `MOLECULE_DISTRO` environment variable:

```bash
# Ubuntu 24.04
MOLECULE_DISTRO=ubuntu2404 molecule test --scenario-name default

# Debian 13
MOLECULE_DISTRO=debian13 molecule test --scenario-name default

# Debian 12
MOLECULE_DISTRO=debian12 molecule test --scenario-name default
```
