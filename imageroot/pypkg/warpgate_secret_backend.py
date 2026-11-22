# SPDX-License-Identifier: GPL-3.0-or-later

"""Warpgate's own secret backend: an OpenBao server that "secret://"
references (target credentials, SSH client keys, SSH certificate signing)
resolve against.

Warpgate 0.30 keeps secret backends in its database and manages them with
the admin API (warpgate-admin/src/api/secret_backends.rs): GET/POST
/secret-backends, PUT/DELETE /secret-backends/{id}. A backend has a name,
backend_type ("vault" or "openbao"), address, namespace, auth (Token,
AppRole or Kubernetes), tls_skip_verify and allowed_paths (path prefixes
"mount/path" matched on whole segments; empty allows any). Warpgate renews
a renewable token itself, up to its maximum TTL.

Modes (WARPGATE_SECRET_BACKEND_MODE):

- "off" (default, also when unset): the module does nothing; manage
  secret backends in Warpgate yourself.
- "manual": get-configuration returns the values to enter in Warpgate's
  Config > Secret backends page (no secret).
- "managed": the module registers the backend through the admin API, with
  the token provisioned by ns8-openbao (openbao@any:secretsclient), and
  updates it whenever the module gets a new token (before the 30 days
  maximum TTL). Only members that do not join another instance manage it:
  the backend row lives in the shared database.

Scope (WARPGATE_SECRET_BACKEND_SCOPE): "module" uses the module token,
limited by allowed_paths to <kv mount>/<module prefix>/targets; "group"
uses the token of a shared group approved by the OpenBao administrator
(<kv mount>/groups/<group>). The module token can also read the module's
own OpenBao mirror (database password, encryption keyring...): Warpgate's
allowed_paths keep references out of it, but anybody who obtains the
stored token from Warpgate's database could use it directly. Enable the
database encryption key (the token is then stored encrypted) or prefer a
group.
"""

import os
import re

import warpgate_cluster as wc

DEFAULT_NAME = "ns8-openbao"
NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
GROUP_RE = re.compile(r"^[a-z0-9-]*[a-z]$")
TARGETS = "targets"


def settings():
    env = os.environ
    mode = env.get("WARPGATE_SECRET_BACKEND_MODE") or "off"
    return {
        "mode": mode if mode in ("off", "manual", "managed") else "off",
        "name": env.get("WARPGATE_SECRET_BACKEND_NAME") or DEFAULT_NAME,
        "scope": "group" if env.get("WARPGATE_SECRET_BACKEND_SCOPE") == "group" else "module",
        "group": env.get("WARPGATE_SECRET_BACKEND_GROUP", ""),
    }


def requested(request, cur):
    sb = request.get("secret_backend")
    if not isinstance(sb, dict):
        return dict(cur)
    return {
        "mode": sb.get("mode") or cur["mode"],
        "name": (sb.get("name", cur["name"]) or DEFAULT_NAME).strip(),
        "scope": sb.get("scope") or cur["scope"],
        "group": (sb.get("group", cur["group"]) or "").strip(),
    }


def validate(want, vault, cluster_mode):
    """vault: the effective OpenBao settings (wc.vault_settings() shape)"""
    if want["mode"] == "off":
        return
    if not NAME_RE.fullmatch(want["name"]):
        raise wc.ClusterError("secret_backend_name", "secret_backend_invalid_name", want["name"])
    if want["scope"] == "group" and not GROUP_RE.fullmatch(want["group"]):
        raise wc.ClusterError("secret_backend_group", "secret_backend_invalid_group", want["group"])
    if want["mode"] == "managed":
        if cluster_mode == "join":
            raise wc.ClusterError("secret_backend_mode", "secret_backend_managed_by_creator", "managed")
        if not vault["vault_enabled"] or vault["vault_mode"] != "provisioned":
            raise wc.ClusterError("secret_backend_mode", "secret_backend_requires_provisioning", "managed")


def save(want):
    import agent

    values = {
        "WARPGATE_SECRET_BACKEND_MODE": want["mode"],
        "WARPGATE_SECRET_BACKEND_NAME": want["name"],
        "WARPGATE_SECRET_BACKEND_SCOPE": want["scope"],
        "WARPGATE_SECRET_BACKEND_GROUP": want["group"] if want["scope"] == "group" else "",
    }
    agent.mset_env(values)
    os.environ.update(values)
    return values


def kv_location(vault=None):
    """(address, kv mount, module prefix) of the OpenBao in use, no secret"""
    vault = vault or wc.vault_settings()
    if vault["vault_enabled"]:
        return vault["vault_address"], vault["vault_mount"], vault["vault_path"]
    return "", "ns8-kv", f"modules/{os.environ.get('MODULE_ID', '')}"


def allowed_path(cur=None, vault=None):
    cur = cur or settings()
    _, mount, prefix = kv_location(vault)
    if cur["scope"] == "group":
        return f"{mount}/groups/{cur['group']}"
    return f"{mount}/{prefix}/{TARGETS}" if prefix else f"{mount}/{TARGETS}"


def info(cur=None, vault=None):
    """What to enter in Warpgate's Config > Secret backends (no secret)"""
    cur = cur or settings()
    address, mount, _ = kv_location(vault)
    path = allowed_path(cur, vault)
    kv_path = path.split("/", 1)[1] if "/" in path else ""
    return {
        "name": cur["name"],
        "backend_type": "openbao",
        "address": address,
        "kv_mount": mount,
        "allowed_path": path,
        "reference_example": f"secret://{cur['name']}/{mount}/{kv_path}/<target>#password",
        "policy": f'path "{mount}/data/{kv_path}/*" {{\n  capabilities = ["read"]\n}}\n',
    }


def warnings(cur):
    result = []
    if cur["mode"] == "managed" and cur["scope"] == "module":
        result.append("secret_backend_module_scope")
        keyring = wc.read_keyring_values()
        if not keyring.get("WARPGATE_ENCRYPTION_KEY"):
            result.append("secret_backend_without_encryption_key")
    return result


def token_for(cur):
    """The token Warpgate gets (secret): the module token, or the group one"""
    if cur["scope"] == "group":
        return wc.read_group_tokens().get(cur["group"], {}).get("token", "")
    return wc.read_envfile(wc.state_dir() / wc.OPENBAO_ENV).get("VAULT_TOKEN", "")


def backend_body(cur, address, token):
    return {
        "name": cur["name"],
        "backend_type": "openbao",
        "address": address,
        "namespace": None,
        "auth": {"method": "Token", "token": token},
        "tls_skip_verify": False,
        "allowed_paths": [allowed_path(cur)],
    }


def needs_admin_api(cur=None, cluster_mode="standalone"):
    cur = cur or settings()
    return cur["mode"] == "managed" and cluster_mode != "join"


def apply(api, cluster_mode="standalone", force=False):
    """Register or update the managed backend. Pushes the token when it is
    newer than the one Warpgate has, or with force. Returns True when
    Warpgate was changed. Raises wc.ClusterError when no token is
    available, warpgate_api.ApiError on API failures."""
    import agent

    cur = settings()
    if not needs_admin_api(cur, cluster_mode):
        return False
    vault = wc.vault_settings()
    token = token_for(cur)
    if not token:
        code = "secret_backend_group_not_approved" if cur["scope"] == "group" else "secret_backend_no_token"
        raise wc.ClusterError("secret_backend_mode", code, cur["group"])
    issued = wc.read_envfile(wc.state_dir() / wc.OPENBAO_ENV).get("VAULT_TOKEN_ISSUED", "")
    pushed = os.environ.get("WARPGATE_SECRET_BACKEND_PUSHED", "")
    signature = f"{cur['name']}|{cur['scope']}|{cur['group']}|{vault['vault_address']}|{allowed_path(cur)}"
    backends = api.request("/secret-backends") or []
    existing = next((b for b in backends if isinstance(b, dict) and b.get("name") == cur["name"]), None)
    current = existing and existing.get("address") == vault["vault_address"] and \
        existing.get("allowed_paths") == [allowed_path(cur)] and \
        (existing.get("auth") or {}).get("method") == "Token"
    if current and not force and pushed == f"{issued}|{signature}":
        return False
    body = backend_body(cur, vault["vault_address"], token)
    if existing:
        api.request(f"/secret-backends/{existing['id']}", "PUT", body)
    else:
        api.request("/secret-backends", "POST", body)
    values = {"WARPGATE_SECRET_BACKEND_PUSHED": f"{issued}|{signature}"}
    agent.mset_env(values)
    os.environ.update(values)
    return True
