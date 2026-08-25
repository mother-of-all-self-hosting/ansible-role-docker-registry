<!--
SPDX-FileCopyrightText: 2023, 2026 Slavi Pantaleev
SPDX-FileCopyrightText: 2026 Suguru Hirahara

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Docker Registry Ansible role

This is an [Ansible](https://www.ansible.com/) role which installs the [Docker Registry](https://docs.docker.com/registry/) container image distribution registry to run as a [Docker](https://www.docker.com/) container wrapped in a systemd service.

This role *implicitly* depends on:

- [`com.devture.ansible.role.playbook_help`](https://github.com/devture/com.devture.ansible.role.playbook_help)
- [`com.devture.ansible.role.systemd_docker_base`](https://github.com/devture/com.devture.ansible.role.systemd_docker_base)

Check [`defaults/main.yml`](defaults/main.yml) for the full list of supported options.

💡 For an Ansible playbook which integrates this role and makes it easier to use, see the [Mother-of-All-Self-Hosting Ansible playbook](https://github.com/mother-of-all-self-hosting/mash-playbook).

## Upgrading from Docker Registry v2 to v3

This role used to install Docker Registry 2.8.3 and now installs 3.x. **No data migration is involved**, and there is nothing for you to do beyond re-running the playbook.

- **The on-disk layout is unchanged.** v3 reads a store written by 2.8.3 as-is. There is no upstream migration guide because upstream does not consider one necessary ([distribution/distribution#4615](https://github.com/distribution/distribution/discussions/4615)).
- **Rolling back works.** 2.8.3 was verified to serve a store that v3 had written to, including images that had only ever been pushed under v3, with digests intact. If v3 gives you trouble, pinning `docker_registry_version` back to `2.8.3` is a safe retreat. Set `docker_registry_container_config_path` back to `/etc/docker/registry/config.yml` as well, since that file moved inside the container image.
- The Molecule `default` scenario performs the upgrade on every CI run: it installs the role at 2.8.3, pushes an image, installs the current version over the same storage path, and then re-fetches and re-hashes what 2.8.3 wrote.

Things to be aware of:

- **The `oss` and `swift` storage drivers are gone in v3.** Only relevant if you selected one through `docker_registry_environment_variables_additional_variables`; a plain filesystem-backed registry (what this role sets up) is unaffected.
- **Some configuration keys were renamed or removed in v3**, again only relevant if you set them yourself: the `compatibility.*` and `reporting.*` sections are gone, and the whole `redis.*` section was reshaped (`redis.addr` became the list `redis.addrs`, and `redis.pool.*` became `maxidleconns`/`poolsize`/`connmaxidletime`). The `REGISTRY_*` environment variable override mechanism itself is unchanged.
- **Schema 1 manifests are rejected outright by v3**, with an HTTP 500. This can only affect you if `docker_registry_data_path` points at a directory inherited from a registry older than 2.8 — this role has only ever installed 2.8.1 or newer, and 2.8.3 already refuses to accept schema 1 pushes.
- **The container image's bundled configuration file changed** in ways this role now compensates for: it turns image deletion on, opens an unauthenticated debug/metrics listener on `:5001`, logs at `debug` level, and no longer sends `X-Content-Type-Options: nosniff`. The role's defaults keep all four at what 2.8.3 effectively did. See `docker_registry_storage_delete_enabled`, `docker_registry_http_debug_addr`, `docker_registry_log_level` and `docker_registry_http_headers` in [`defaults/main.yml`](defaults/main.yml).

## Garbage collection

**Garbage collection does not work and has never worked.** This role installs `bin/garbage-collect` plus a systemd service and timer for it, and the playbook enables the timer, but under the role's default settings the generated script is not valid bash: `on_exit()` ends up with an empty body, and `bash` exits with a syntax error without running any of it. Before that, the script had a different defect (a blank first line, which the kernel rejects with `ENOEXEC`), so no collection has ever run on any installation.

This is being left as it is on purpose, rather than repaired:

- Nothing is deleted, so no registry can lose data to it.
- Repairing it would mean that the first collection any operator ever gets is a **v3** collection, running over however many years of accumulated data. v3's collector deletes classes of files that 2.8.3's never touched — dangling per-repository `_layers` links ([#4344](https://github.com/distribution/distribution/pull/4344)) and marking that recurses through manifest lists ([#4285](https://github.com/distribution/distribution/pull/4285)).

Two caveats worth knowing:

- The breakage is **specific to the default settings**. Setting either `docker_registry_garbage_collect_stop_service_enabled` or `docker_registry_garbage_collect_command_post` gives `on_exit()` a real body, at which point the script is valid and collection *does* run on schedule. If you have set either of those, you are running garbage collection.
- The timer fires on schedule regardless, and the unit fails each time, so `systemctl --failed` on a host running this role will show `<identifier>-garbage-collect.service`.

If you need to reclaim space, run a collection by hand against the same storage path, having decided for yourself that you want it.

## Development

### pre-commit

You can optionally install a Git pre-commit hook (via [mise](https://mise.jdx.dev/) + [prek](https://prek.j178.dev/)) that runs formatting and linting checks before each commit. See [`.pre-commit-config.yaml`](./.pre-commit-config.yaml) for which hooks are to be executed.

To install the hook, run the [`just`](https://github.com/casey/just) command below:

```sh
just prek-install-git-pre-commit-hook
```

### Molecule

This role supports [Molecule](https://docs.ansible.com/projects/molecule/), an Ansible testing framework designed for developing and testing Ansible collections, playbooks, and roles.

Refer to [this page](./molecule/README.md) for details about how to utilize it.
