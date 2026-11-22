# SPDX-License-Identifier: GPL-3.0-or-later

"""Warpgate admin API, for the settings that Warpgate 0.30 keeps in its
database instead of warpgate.yaml (recordings storage, secret backends).

The module talks to the API with Warpgate's own admin token: "warpgate run
--enable-admin-token" accepts the X-Warpgate-Token header when it equals
the WARPGATE_ADMIN_TOKEN environment variable (warpgate/src/main.rs,
warpgate-protocol-http/src/common.rs in Warpgate 0.30.4). The flag is
passed only while a feature needs it (WARPGATE_RUN_ARGS): an instance that
uses none of them runs exactly as before. The token lives in the 0600 file
state/admin-token.env, never in the module environment, argv or logs.
"""

import json
import os
import secrets
import ssl
import time
import urllib.error
import urllib.request

import warpgate_cluster as wc

ADMIN_TOKEN_ENV = "admin-token.env"
RUN_ARGS = "--enable-admin-token"
API_PREFIX = "/@warpgate/admin/api"


class ApiError(Exception):
    def __init__(self, status=0, message=""):
        super().__init__(f"Warpgate admin API request failed ({status or 'unreachable'})")
        self.status = status
        self.message = message


def admin_token(create=False):
    """The admin token (secret). With create, generate it if missing."""
    path = wc.state_dir() / ADMIN_TOKEN_ENV
    token = wc.read_envfile(path).get("WARPGATE_ADMIN_TOKEN", "")
    if not token and create:
        token = secrets.token_urlsafe(32)
        wc.write_envfile(path, {"WARPGATE_ADMIN_TOKEN": token})
    return token


def run_args(enabled):
    """WARPGATE_RUN_ARGS value: extra arguments of "warpgate run" """
    if enabled:
        admin_token(create=True)
        return RUN_ARGS
    return ""


def request(path, method="GET", data=None, timeout=15, token=None):
    """Call the admin API of the local Warpgate (published on 127.0.0.1,
    self-signed certificate). Returns the decoded JSON body or None."""
    token = token if token is not None else admin_token()
    if not token:
        raise ApiError(0, "no admin token")
    port = int(os.environ["TCP_PORT_HTTP"])
    headers = {"X-Warpgate-Token": token, "Accept": "application/json"}
    host = os.environ.get("TRAEFIK_HOST")
    if host:
        # The Host header Traefik sends: Warpgate builds URLs from it
        headers["Host"] = host
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://127.0.0.1:{port}{API_PREFIX}{path}", data=body,
                                 method=method, headers=headers)
    context = ssl.create_default_context()
    # Warpgate's own self-signed certificate on the loopback listener (the
    # same backend Traefik reaches with skip_cert_verify)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as ex:
        try:
            message = ex.read(512).decode("utf-8", "replace")
        except OSError:
            message = ""
        raise ApiError(ex.code, message) from None
    except (urllib.error.URLError, OSError, ValueError):
        raise ApiError(0) from None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def wait_ready(timeout=180, interval=3):
    """Wait until the admin API answers with the admin token"""
    deadline = time.monotonic() + timeout
    last = None
    while True:
        try:
            request("/parameters", timeout=10)
            return
        except ApiError as ex:
            last = ex
            # 401 can mean that Warpgate is still starting with the old flags
        if time.monotonic() >= deadline:
            raise last
        time.sleep(interval)
