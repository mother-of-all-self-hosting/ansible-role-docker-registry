<!--
SPDX-FileCopyrightText: 2020 Aaron Raimist
SPDX-FileCopyrightText: 2020 Chris van Dijk
SPDX-FileCopyrightText: 2020 Dominik Zajac
SPDX-FileCopyrightText: 2020 Mickaël Cornière
SPDX-FileCopyrightText: 2020-2024 MDAD project contributors
SPDX-FileCopyrightText: 2020-2024 Slavi Pantaleev
SPDX-FileCopyrightText: 2022 François Darveau
SPDX-FileCopyrightText: 2022 Julian Foad
SPDX-FileCopyrightText: 2022 Warren Bailey
SPDX-FileCopyrightText: 2023 Antonis Christofides
SPDX-FileCopyrightText: 2023 Felix Stupp
SPDX-FileCopyrightText: 2023 Pierre 'McFly' Marty
SPDX-FileCopyrightText: 2024-2026 Suguru Hirahara

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Setting up Distribution Registry

This is an [Ansible](https://www.ansible.com/) role which installs [Distribution Registry](https://github.com/distribution/distribution/) to run as a [Docker](https://www.docker.com/) container wrapped in a systemd service.

Distribution Registry is a stateless, scalable server side application that stores and lets you distribute container images and other content.

See the project's [documentation](https://distribution.github.io/distribution/) to learn what Distribution Registry does and why it might be useful to you.

## Adjusting the playbook configuration

To enable Distribution Registry with this role, add the following configuration to your `vars.yml` file.

**Note**: the path should be something like `inventory/host_vars/mash.example.com/vars.yml` if you use the [MASH Ansible playbook](https://github.com/mother-of-all-self-hosting/mash-playbook).

```yaml
########################################################################
#                                                                      #
# docker_registry                                                      #
#                                                                      #
########################################################################

docker_registry_enabled: true

########################################################################
#                                                                      #
# /docker_registry                                                     #
#                                                                      #
########################################################################
```

### Set the hostname

To enable Distribution Registry you need to set the hostname as well. To do so, add the following configuration to your `vars.yml` file. Make sure to replace `example.com` with your own value.

```yaml
docker_registry_hostname: "example.com"
```

After adjusting the hostname, make sure to adjust your DNS records to point the domain to your server.


### Whitelisting IPs

Only whitelisted IPs will be able to perform DELETE, PATCH, POST, PUT requests against the registry. All other IP addresses get read-only (GET, HEAD) access.

To specify whitelisted IPs, add the following configuration to your `vars.yml` file:

```yaml
docker_registry_private_services_whitelisted_ip_ranges:
  - 1.2.3.4/32
  - 4.3.2.1/32
```

### Enabling image deletion (optional)

To allow for image deletion, add the following configuration to your `vars.yml` file:

```yaml
docker_registry_storage_delete_enabled: true
```

### Extending the configuration

There are some additional things you may wish to configure about the service.

Take a look at:

- [`defaults/main.yml`](../defaults/main.yml) for some variables that you can customize via your `vars.yml` file. You can override settings (even those that don't have dedicated playbook variables) using the `docker_registry_environment_variables_additional_variables` variable

## Installing

After configuring the playbook, run the installation command of your playbook as below:

```sh
ansible-playbook -i inventory/hosts setup.yml --tags=setup-all,start
```

If you use the MASH playbook, the shortcut commands with the [`just` program](https://github.com/mother-of-all-self-hosting/mash-playbook/blob/main/docs/just.md) are also available: `just install-all` or `just setup-all`

## Usage

After running the command for installation, Distribution Registry becomes available at the specified hostname like `https://example.com`.

>[!NOTE]
> The base URL erves an empty (blank) page. To browse your registry's images via a web interface, you may need another piece of software, such as [Docker Registry Browser](https://github.com/klausmeyer/docker-registry-browser).

You should be able to:

- pull images from your registry from any IP address
- push images to your registry from the whitelisted IP addresses (`docker_registry_private_services_whitelisted_ip_ranges`)

With custom Traefik configuration (hint: see [`docker_registry_container_labels_traefik_rule_*` variables](../defaults/main.yml), you may be able to add additional restrictions.

To **test pushing** images, try the following:

```sh
docker pull docker.io/alpine:3.17.2
docker tag docker.io/alpine:3.17.2 registry.example.com/alpine:3.17.2
docker push registry.example.com/alpine:3.17.2
```

To **test pulling** images, try the following:

```sh
# Clean up from before
docker rmi registry.example.com/alpine:3.17.2

docker pull registry.example.com/alpine:3.17.2
```

## Troubleshooting

### Check the service's logs

You can find the logs in [systemd-journald](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) by logging in to the server with SSH and running `journalctl -fu docker-registry` (or how you/your playbook named the service, e.g. `mash-docker-registry`).
