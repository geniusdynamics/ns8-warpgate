# SPDX-License-Identifier: GPL-3.0-or-later

import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

CALLBACK = "/@warpgate/api/sso/return"
SETTINGS = Path(os.environ.get("AGENT_STATE_DIR", ".")) / "oidc.json"


class RegistrationError(Exception):
    def __init__(self, field, code):
        super().__init__(code)
        self.field = field


@contextmanager
def settings_lock():
    with SETTINGS.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def provider_name(issuer):
    return "ns8-oidc-" + hashlib.sha256(issuer.encode()).hexdigest()[:24]


def read_settings():
    try:
        return json.loads(SETTINGS.read_text())
    except FileNotFoundError:
        return {"mode": "disabled"}


def write_settings(settings):
    with tempfile.NamedTemporaryFile(mode="w", dir=SETTINGS.parent, delete=False) as stream:
        try:
            json.dump(settings, stream)
            stream.flush()
            os.replace(stream.name, SETTINGS)
        finally:
            Path(stream.name).unlink(missing_ok=True)


def https_issuer(value):
    try:
        url = urlsplit(value)
        return (
            url.scheme == "https" and bool(url.hostname) and url.port != 0
            and url.username is None and url.password is None
            and not any(c.isspace() or ord(c) < 32 or c in "?#\\"
                        for c in value)
        )
    except ValueError:
        return False


def discover(rdb):
    import agent
    from agent.ldapproxy import Ldapproxy

    domains = sorted(Ldapproxy().get_domains_list())
    providers = {}
    for record in agent.list_service_providers(rdb, "oidc", "http", sortby="module_seq_asc"):
        module = record.get("module_id", "")
        uuid = record.get("module_uuid")
        prefix = record.get("issuer_url_prefix", "")
        host = record.get("host", "")
        if not uuid or not re.fullmatch(r"(?:idp|keycloak|lemonldapng)\d+", module):
            continue
        if not https_issuer(prefix) or not prefix.startswith(f"https://{host}/") or not prefix.endswith("/"):
            continue
        domain = record.get("domain", "")
        providers[uuid] = {
            "id": uuid, "module": module, "label": record.get("ui_name") or module,
            "prefix": prefix, "domains": [name for name in domains if not domain or name == domain],
        }
    return providers


def invalid(field, code):
    import agent

    agent.set_status("validation-failed")
    json.dump([{"field": field, "parameter": field, "value": "", "error": code}], sys.stdout)
    raise SystemExit(3)


def save_configuration(settings):
    import agent

    current = read_settings()
    old_domain = current.get("domain")
    if current.get("owns_binding") and old_domain != settings.get("domain"):
        bound = agent.get_bound_domain_list(agent.redis_connect())
        if old_domain in bound:
            agent.bind_user_domains([domain for domain in bound if domain != old_domain], check=True)
    write_settings(settings)


def configure(request):

    current = read_settings()
    requested = request.get("oidc")
    mode = requested["mode"] if requested is not None else current["mode"]
    if mode == "disabled":
        return {"mode": mode}

    callback = f"https://{request['host']}{CALLBACK}"
    if mode == "manual":
        if requested is None:
            return current
        issuer, client = requested.get("issuer", ""), requested.get("client_id", "")
        secret = requested.get("secret", "")
        if not https_issuer(issuer):
            invalid("oidc_issuer", "oidc_invalid_issuer")
        if not client.strip():
            invalid("oidc_client_id", "oidc_required")
        if not secret and current["mode"] == mode and (issuer, client) == (current["issuer"], current["client_id"]):
            secret = current["secret"]
        if not secret:
            invalid("oidc_secret", "oidc_required")
        return {"mode": mode, "issuer": issuer, "client_id": client, "secret": secret}

    selection = requested if requested is not None else current
    provider, domain = selection.get("provider", ""), selection.get("domain", "")
    module = os.environ["MODULE_ID"]
    if (
        current["mode"] == mode and current["provider"] == provider
        and current["domain"] == domain and current["callback"] == callback
        and current["client_id"] == module
    ):
        return current

    try:
        return register(current, selection, callback)
    except RegistrationError as error:
        invalid(error.field, str(error))


def register(current, selection, callback, rotate=False):
    import agent
    import agent.tasks

    provider, domain = selection.get("provider", ""), selection.get("domain", "")
    module = os.environ["MODULE_ID"]
    rdb = agent.redis_connect()
    endpoint = discover(rdb).get(provider)
    if not endpoint:
        raise RegistrationError("oidc_provider", "oidc_provider_unavailable")
    if domain not in endpoint["domains"]:
        raise RegistrationError("oidc_domain", "oidc_domain_unavailable")
    bound = agent.get_bound_domain_list(rdb)
    added = domain not in bound
    if added and not agent.bind_user_domains([*bound, domain]):
        raise RegistrationError("oidc_domain", "oidc_registration_failed")

    issuer = endpoint["prefix"] + domain
    try:
        result = agent.tasks.run(
            f"module/{endpoint['module']}", "register-client",
            data={
                "domain": domain,
                "redirect_uris": [callback],
                "post_logout_redirect_uris": [callback.removesuffix(CALLBACK) + "/"],
                "rotate_secret": rotate,
            },
            extra={"isNotificationHidden": True},
        )
        response = result.get("output")
        if result.get("exit_code") != 0 or not isinstance(response, dict):
            raise ValueError()
        secret = response.get("client_secret")
        if (
            response.get("issuer") != issuer or response.get("client_id") != module
            or response.get("realm") != domain or not isinstance(secret, str) or not secret
        ):
            raise ValueError()
    except Exception:
        if added:
            agent.bind_user_domains(bound)
        raise RegistrationError("oidc_provider", "oidc_registration_failed") from None

    refreshed = {
        "mode": "ns8", "provider": provider, "domain": domain, "issuer": issuer,
        "client_id": module, "secret": secret, "callback": callback,
        "owns_binding": added or (
            current.get("owns_binding", False) and current.get("domain") == domain
        ),
    }
    # Links are scoped to the selected provider and realm. A hostname change
    # of the same provider must keep the existing Warpgate credential key.
    if current.get("provider") == provider and current.get("domain") == domain:
        name = current.get("name") or provider_name(current["issuer"])
        if name != provider_name(issuer):
            refreshed["name"] = name
    return refreshed


def render(volume, host):
    source = volume / "warpgate.yaml"
    generated = volume / ".ns8-warpgate.yaml"
    settings = read_settings()
    if settings["mode"] == "disabled":
        if not generated.is_symlink() or os.readlink(generated) != source.name:
            generated.unlink(missing_ok=True)
            generated.symlink_to(source.name)
        return

    import yaml

    try:
        config = yaml.safe_load(source.read_text())
        providers = config.get("sso_providers") or []
        name = settings.get("name") or provider_name(settings["issuer"])
        if any(provider["name"] == name for provider in providers):
            raise ValueError("duplicate provider name")
        config["external_host"] = host
        # Warpgate otherwise uses its container listener's port for the callback.
        config.setdefault("http", {})["external_port"] = 443
        config["sso_providers"] = [*providers, {
            "name": name,
            "label": "OpenID Connect",
            "auto_create_users": False,
            "provider": {
                "type": "custom",
                "issuer_url": settings["issuer"],
                "client_id": settings["client_id"],
                "client_secret": settings["secret"],
                "scopes": ["email", "profile"],
                "role_mappings": {},
                "admin_role_mappings": {},
                "trust_unknown_audiences": False,
            },
        }]
        with tempfile.NamedTemporaryFile(mode="w", dir=volume, delete=False) as stream:
            try:
                yaml.safe_dump(config, stream, sort_keys=False)
                stream.flush()
                owner = source.stat()
                os.fchown(stream.fileno(), owner.st_uid, owner.st_gid)
                os.replace(stream.name, generated)
            finally:
                Path(stream.name).unlink(missing_ok=True)
    except (yaml.YAMLError, KeyError, TypeError, AttributeError, ValueError):
        # Do not log parser diagnostics that can include credentials.
        raise SystemExit("Could not render Warpgate OIDC configuration") from None


if __name__ == "__main__":
    render(Path(sys.argv[1]), sys.argv[2])
