# ns8-warpgate

A [NethServer 8](https://github.com/NethServer/ns8-core) module for [Warpgate](https://github.com/warp-tech/warpgate) - a smart SSH, HTTPS and MySQL bastion that requires no client-side software.

## Features

- Smart SSH bastion with web-based terminal access
- HTTPS reverse proxy capabilities
- MySQL database proxy support
- Web admin interface for user management
- No client software installation required
- Automatic SSL certificate management via Let's Encrypt

## Quick Start

## Install

Instantiate the module with:

```bash
add-module ghcr.io/geniusdynamics/warpgate:latest 1
```

The output will return the instance name:

```json
{"module_id": "warpgate1", "image_name": "warpgate", "image_url": "ghcr.io/geniusdynamics/warpgate:latest"}
```

## Configure

Let's assume that the warpgate instance is named `warpgate1`.

Launch `configure-module`, by setting the following parameters:

- `host`: a fully qualified domain name for the application
- `http2https`: enable or disable HTTP to HTTPS redirection (true/false)
- `lets_encrypt`: enable or disable Let's Encrypt certificate (true/false)

Example:

```
api-cli run configure-module --agent module/warpgate1 --data - <<EOF
{
  "host": "warpgate.domain.com",
  "http2https": true,
  "lets_encrypt": false
}
EOF
```

The above command will:

- start and configure the warpgate instance
- configure a virtual host for Traefik to access the instance

## Get the configuration

You can retrieve the configuration with

```
api-cli run get-configuration --agent module/warpgate1
```

## Uninstall

To uninstall the instance:

```bash
remove-module --no-preserve warpgate1
```

## Smarthost setting discovery

Some configuration settings, like the smarthost setup, are not part of the
`configure-module` action input: they are discovered by looking at some
Redis keys. To ensure the module is always up-to-date with the
centralized [smarthost
setup](https://geniusdynamics.github.io/ns8-core/core/smarthost/) every time
warpgate starts, the command `bin/discover-smarthost` runs and refreshes
the `state/smarthost.env` file with fresh values from Redis.

Furthermore if smarthost setup is changed when warpgate is already
running, the event handler `events/smarthost-changed/10reload_services`
restarts the main module service.

See also the `systemd/user/warpgate.service` file.

This setting discovery is just an example to understand how the module is
expected to work: it can be rewritten or discarded completely.

## Debug

### Check Environment Variables

The module runs under an agent that initializes environment variables in `/home/warpgate1/.config/state`. To verify them:

```bash
runagent -m warpgate1 env
```

### Access the Module Environment

Become the runagent for testing scripts with all environment variables loaded:

```bash
runagent -m warpgate1
echo $PATH
```

Expected output:
```
/home/warpgate1/.config/bin:/usr/local/agent/pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/usr/
```

### Container Debugging

First, enter the module environment:
```bash
runagent -m warpgate1
```

List running containers:
```bash
podman ps
```

Example output:
```
CONTAINER ID  IMAGE                                      COMMAND               CREATED        STATUS        PORTS                    NAMES
d292c6ff28e9  localhost/podman-pause:4.6.1-1702418000                          9 minutes ago  Up 9 minutes  127.0.0.1:20015->80/tcp  80b8de25945f-infra
d8df02bf6f4a  docker.io/library/mariadb:10.11.5          --character-set-s...  9 minutes ago  Up 9 minutes  127.0.0.1:20015->80/tcp  mariadb-app
9e58e5bd676f  docker.io/library/nginx:stable-alpine3.17  nginx -g daemon o...  9 minutes ago  Up 9 minutes  127.0.0.1:20015->80/tcp  warpgate-app
```

View environment variables inside a container:
```bash
podman exec warpgate-app env
```

Run a shell inside a container:
```bash
podman exec -ti warpgate-app sh
```

## Testing

Test the module using the `test-module.sh` script:

```bash
./test-module.sh <NODE_ADDR> ghcr.io/geniusdynamics/warpgate:latest
```

The tests are built using [Robot Framework](https://robotframework.org/).

## UI translation

Translated with [Weblate](https://hosted.weblate.org/projects/ns8/).

To setup the translation process:

- add [GitHub Weblate app](https://docs.weblate.org/en/latest/admin/continuous.html#github-setup) to your repository
- add your repository to [hosted.weblate.org]((https://hosted.weblate.org) or ask a geniusdynamics developer to add it to ns8 Weblate project
