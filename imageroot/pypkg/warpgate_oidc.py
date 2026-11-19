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


def entry_name(entry):
    return entry.get("name") or provider_name(entry["issuer"])


def read_settings():
    try:
        saved = json.loads(SETTINGS.read_text())
    except FileNotFoundError:
        return []
    if "entries" in saved:
        return saved["entries"]
    return [saved] if saved["mode"] != "disabled" else []


def write_settings(settings):
    with tempfile.NamedTemporaryFile(mode="w", dir=SETTINGS.parent, delete=False) as stream:
        try:
            json.dump({"entries": settings}, stream)
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


def owned_domains(entries):
    return {entry["domain"] for entry in entries if entry.get("owns_binding")}


def remove_bindings(domains):
    if not domains:
        return
    import agent

    bound = agent.get_bound_domain_list(agent.redis_connect())
    remaining = [domain for domain in bound if domain not in domains]
    if remaining != bound:
        agent.bind_user_domains(remaining, check=True)


def save_configuration(settings):
    owned = owned_domains(read_settings()) | owned_domains(settings)
    used = {entry["domain"] for entry in settings if entry["mode"] == "ns8"}
    remove_bindings(owned - used)
    for entry in settings:
        if entry["mode"] == "ns8" and entry["domain"] in owned:
            entry["owns_binding"] = True
    write_settings(settings)


def configure(request):
    current = read_settings()
    if "oidc_entries" in request:
        requested = request["oidc_entries"]
    elif "oidc" in request:
        legacy = request["oidc"]
        first = [legacy] if legacy["mode"] != "disabled" else []
        requested = first + current[1:]
    else:
        requested = current

    callback = f"https://{request['host']}{CALLBACK}"
    entries = []
    issuers = set()
    names = set()
    selections = set()
    try:
        for selected in requested:
            if selected["mode"] == "manual":
                entry = manual_entry(selected, current)
            else:
                key = (selected.get("provider"), selected.get("domain"))
                if key in selections:
                    raise RegistrationError("oidc_entries", "oidc_duplicate_provider")
                selections.add(key)
                previous = next((item for item in current if item["mode"] == "ns8"
                                 and (item["provider"], item["domain"]) == key), {})
                if (previous.get("callback") == callback
                        and previous.get("client_id") == os.environ["MODULE_ID"]):
                    entry = dict(previous)
                else:
                    entry = register(previous, selected, callback)
                if selected.get("label"):
                    entry["label"] = selected["label"].strip()
            entries.append(entry)
            name = entry_name(entry)
            if entry["issuer"] in issuers or name in names:
                raise RegistrationError("oidc_entries", "oidc_duplicate_provider")
            issuers.add(entry["issuer"])
            names.add(name)
    except RegistrationError as error:
        remove_bindings(owned_domains(entries) - owned_domains(current))
        field = "oidc_entries" if "oidc_entries" in request else error.field
        invalid(field, str(error))
    return entries


def manual_entry(selected, current):
    issuer, client = selected.get("issuer", ""), selected.get("client_id", "")
    if not https_issuer(issuer):
        raise RegistrationError("oidc_issuer", "oidc_invalid_issuer")
    if not client.strip():
        raise RegistrationError("oidc_client_id", "oidc_required")
    previous = next((item for item in current if item["mode"] == "manual"
                     and (item["issuer"], item["client_id"]) == (issuer, client)), {})
    secret = selected.get("secret") or previous.get("secret")
    if not secret:
        raise RegistrationError("oidc_secret", "oidc_required")
    entry = {"mode": "manual", "issuer": issuer, "client_id": client, "secret": secret}
    if selected.get("label"):
        entry["label"] = selected["label"].strip()
    return entry


def register(current, selection, callback, rotate=False, other_issuers=()):
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
    issuer = endpoint["prefix"] + domain
    if issuer in other_issuers:
        raise RegistrationError("oidc_entries", "oidc_duplicate_provider")
    bound = agent.get_bound_domain_list(rdb)
    added = domain not in bound
    if added and not agent.bind_user_domains([*bound, domain]):
        raise RegistrationError("oidc_domain", "oidc_registration_failed")

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
    if selection.get("label"):
        refreshed["label"] = selection["label"]
    # Links are scoped to the selected provider and realm. A hostname change
    # of the same provider must keep the existing Warpgate credential key.
    if current.get("provider") == provider and current.get("domain") == domain:
        name = current.get("name") or provider_name(current["issuer"])
        if name != provider_name(issuer):
            refreshed["name"] = name
    return refreshed


def default_label(entry):
    host = urlsplit(entry["issuer"]).hostname
    if entry["mode"] == "ns8":
        return f"{host} ({entry['domain']})"
    return host


def render(volume, host):
    source = volume / "warpgate.yaml"
    generated = volume / ".ns8-warpgate.yaml"
    settings = read_settings()
    if not settings:
        if not generated.is_symlink() or os.readlink(generated) != source.name:
            generated.unlink(missing_ok=True)
            generated.symlink_to(source.name)
        return

    import yaml

    try:
        config = yaml.safe_load(source.read_text())
        providers = config.get("sso_providers") or []
        names = {provider["name"] for provider in providers}
        config["external_host"] = host
        # Warpgate otherwise uses its container listener's port for the callback.
        config.setdefault("http", {})["external_port"] = 443
        config["sso_providers"] = providers
        for entry in settings:
            name = entry_name(entry)
            if name in names:
                raise ValueError("duplicate provider name")
            names.add(name)
            config["sso_providers"].append({
                "name": name,
                "label": entry.get("label") or default_label(entry),
                "auto_create_users": False,
                "provider": {
                    "type": "custom",
                    "issuer_url": entry["issuer"],
                    "client_id": entry["client_id"],
                    "client_secret": entry["secret"],
                    "scopes": ["email", "profile"],
                    "role_mappings": {},
                    "admin_role_mappings": {},
                    "trust_unknown_audiences": False,
                },
            })
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
