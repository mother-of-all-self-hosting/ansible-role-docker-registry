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

### Upgrading from Docker Registry v2 to Distribution Registry v3

This role used to install Docker Registry 2.8.3 and now installs Distribution Registry v3.

>[!NOTE]
> The original Docker Registry project has been deprecated, and donated to Cloud Native Computing Foundation (CNCF) in 2019. See [this announcement](https://docs.docker.com/retired/#registry-now-cncf-distribution) for details.

**No data migration is involved.** The on-disk layout is unchanged, and there is no upstream migration guide because upstream does not consider one necessary (see: [distribution/distribution#4615](https://github.com/distribution/distribution/discussions/4615)). There is nothing for you to do beyond re-running the playbook.

Things to be aware of:

- **The `oss` and `swift` storage drivers are gone in v3.** Only relevant if you selected one through `docker_registry_environment_variables_additional_variables`; a plain filesystem-backed registry (what this role sets up) is unaffected.
- **Some configuration keys were renamed or removed in v3.** Again only relevant if you set them yourself: the `compatibility.*` and `reporting.*` sections are gone, and the whole `redis.*` section was reshaped (`redis.addr` became the list `redis.addrs`, and `redis.pool.*` became `maxidleconns`/`poolsize`/`connmaxidletime`). The `REGISTRY_*` environment variable override mechanism itself is unchanged.
- **Schema 1 manifests are rejected outright by v3**, with an HTTP 500. This can only affect you if `docker_registry_data_path` points at a directory inherited from a registry older than 2.8 — this role has only ever installed 2.8.1 or newer, and 2.8.3 already refuses to accept schema 1 pushes.
- **The container image's bundled configuration file changed** in ways this role now compensates for: it turns image deletion on, opens an unauthenticated debug/metrics listener on `:5001`, logs at `debug` level, and no longer sends `X-Content-Type-Options: nosniff`. The role's defaults keep all four at what 2.8.3 effectively did. See `docker_registry_storage_delete_enabled`, `docker_registry_http_debug_addr`, `docker_registry_log_level` and `docker_registry_http_headers` in [`defaults/main.yml`](defaults/main.yml).

### Garbage collection

**Garbage collection does not work and has never worked.** This role installs `bin/garbage-collect` plus a systemd service and timer for it, and the playbook enables the timer, but under the role's default settings the generated script is not valid bash: `on_exit()` ends up with an empty body, and `bash` exits with a syntax error without running any of it. Before that, the script had a different defect (a blank first line, which the kernel rejects with `ENOEXEC`), so no collection has ever run on any installation.

This is being left as it is on purpose, rather than repaired:

- Nothing is deleted, so no registry can lose data to it.
- Repairing it would mean that the first collection any operator ever gets is a **v3** collection, running over however many years of accumulated data. v3's collector deletes classes of files that 2.8.3's never touched — dangling per-repository `_layers` links ([#4344](https://github.com/distribution/distribution/pull/4344)) and marking that recurses through manifest lists ([#4285](https://github.com/distribution/distribution/pull/4285)).

Two caveats worth knowing:

- The breakage is **specific to the default settings**. Setting either `docker_registry_garbage_collect_stop_service_enabled` or `docker_registry_garbage_collect_command_post` gives `on_exit()` a real body, at which point the script is valid and collection *does* run on schedule. If you have set either of those, you are running garbage collection.
- The timer fires on schedule regardless, and the unit fails each time, so `systemctl --failed` on a host running this role will show `<identifier>-garbage-collect.service`.

If you need to reclaim space, run a collection by hand against the same storage path, having decided for yourself that you want it.

## Troubleshooting

### Check the service's logs

You can find the logs in [systemd-journald](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) by logging in to the server with SSH and running `journalctl -fu docker-registry` (or how you/your playbook named the service, e.g. `mash-docker-registry`).
