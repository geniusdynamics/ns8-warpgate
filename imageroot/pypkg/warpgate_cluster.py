# SPDX-License-Identifier: GPL-3.0-or-later

"""Database modes, Warpgate cluster membership and OpenBao secrets.

Database modes (WARPGATE_DB_MODE):

- "embedded": Warpgate's own SQLite database in the data volume (default).
- "postgresql19c": a database of a geniusdynamics/ns8-postgresql19c
  instance, obtained with its grant-database action (role pgclient). The
  password is kept in the 0600 file state/database.env as PGPASSWORD:
  Warpgate's driver (sqlx) reads it from the environment, so the database
  URL rendered into the Warpgate configuration and every command line
  carry no secret.

Cluster modes (WARPGATE_CLUSTER_MODE): "standalone", "create" and "join".
Every member uses the same PostgreSQL database, each with its own login
role (grant-database lets instances of the same application share a
database). A joining member gets the shared key material (Warpgate's
credential encryption keyring and the TLS certificate of the protocol
listeners) from an approved peer with the admit-peer action (role wgpeer),
approved on the peer with set-peer-access and bound to the joiner's module
UUID. The SSH host keys and the cluster CA live in the database itself.

OpenBao (WARPGATE_VAULT_ENABLED): a copy of the secrets in a KV version 2
store, with a token pasted by the administrator or provisioned by
geniusdynamics/ns8-openbao (role secretsclient). The local 0600 files stay
the operational copy: starting Warpgate never waits for OpenBao.
"""

import base64
import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PG_SERVICE = "postgresql19c"
DATABASE_ENV = "database.env"
ENCRYPTION_ENV = "encryption.env"
OPENBAO_ENV = "openbao.env"
SHARED_TLS = "cluster-tls.json"
PEER_GRANTS = "peer-access.json"
MODULE_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*[0-9]+$")
DB_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,56}$")
IMAGE_NAME = "warpgate"


class ClusterError(Exception):
    """A validation error: field and error code"""

    def __init__(self, field, code, value=""):
        super().__init__(code)
        self.field = field
        self.code = code
        self.value = value


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def state_dir():
    return Path(os.environ.get("AGENT_STATE_DIR", "."))


def write_private(path, content):
    """Atomic write of a 0600 file"""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def read_envfile(path):
    values = {}
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                line = line.rstrip("\n")
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
    except FileNotFoundError:
        pass
    return values


def write_envfile(path, values):
    for key, value in values.items():
        if "\n" in str(value) or "\n" in key:
            raise ValueError("invalid environment value")
    write_private(path, "".join(f"{k}={v}\n" for k, v in values.items()))


def remove(path):
    Path(path).unlink(missing_ok=True)


def image_name_of(image_url):
    return (image_url or "").rsplit("/", 1)[-1].split(":", 1)[0].split("@", 1)[0]


def database_name_for(client_id):
    """ns8-postgresql19c's default database and login role name"""
    name = re.sub(r"[^a-z0-9_]", "_", client_id.lower())
    if not name or not name[0].isalpha():
        name = "db_" + name
    return name[:63]


def settings():
    """Non-secret settings, from the module environment"""
    env = os.environ
    return {
        "db_mode": env.get("WARPGATE_DB_MODE") or "embedded",
        "db_instance": env.get("WARPGATE_DB_INSTANCE", ""),
        "db_provider": env.get("WARPGATE_DB_PROVIDER", ""),
        "db_cluster_id": env.get("WARPGATE_DB_CLUSTER_ID", ""),
        "db_name": env.get("WARPGATE_DB_NAME", ""),
        "db_user": env.get("WARPGATE_DB_USER", ""),
        "db_host": env.get("WARPGATE_DB_HOST", ""),
        "db_port": env.get("WARPGATE_DB_PORT", ""),
        "cluster_mode": env.get("WARPGATE_CLUSTER_MODE") or "standalone",
        "cluster_peer": env.get("WARPGATE_CLUSTER_PEER", ""),
    }


# ---------------------------------------------------------------------------
# PostgreSQL (ns8-postgresql19c consumer)
# ---------------------------------------------------------------------------

def pg_records(rdb):
    """Discovery records of the ns8-postgresql19c instances (no secrets)"""
    import agent

    result = []
    for rec in agent.list_service_providers(rdb, PG_SERVICE, "tcp"):
        try:
            result.append({
                "module_id": rec["module_id"],
                "node": str(rec.get("node", "")),
                "host": rec["host"],
                "port": int(rec["port"]),
                "cluster_id": rec.get("cluster_id") or rec["module_id"],
                "ha_mode": rec.get("ha_mode", "standalone"),
                "role": rec.get("role", ""),
                "ui_name": rec.get("ui_name", ""),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(result, key=lambda r: (r["cluster_id"], r["module_id"]))


def pick_record(records, node_id, cluster_id="", preferred=""):
    """The instance to talk to: the preferred one if it exists (and is in
    cluster_id when given), otherwise one of cluster_id (any cluster when
    empty) on this node, otherwise the first one of it."""
    candidates = [r for r in records if not cluster_id or r["cluster_id"] == cluster_id]
    for rec in candidates:
        if preferred and rec["module_id"] == preferred:
            return rec
    if preferred and not cluster_id:
        return None
    for rec in candidates:
        if rec["node"] == str(node_id):
            return rec
    return candidates[0] if candidates else None


def local_endpoint(records, node_id, cluster_id):
    """The read-write endpoint of cluster_id on this node, else any of it"""
    return pick_record(records, node_id, cluster_id)


def grant_database(provider, database):
    """Run grant-database on provider; returns its output (secret)"""
    import agent.tasks

    data = {"database": database} if database else {}
    ret = agent.tasks.run(agent_id=f"module/{provider}", action="grant-database", data=data,
                          extra={"isNotificationHidden": True})
    if ret.get("exit_code") != 0 or not isinstance(ret.get("output"), dict):
        code = "database_grant_failed"
        output = ret.get("output")
        if isinstance(output, list) and output and isinstance(output[0], dict):
            code = output[0].get("error") or code
        raise ClusterError("database", code, provider)
    return ret["output"]


def store_credentials(out, node_records, node_id):
    """Save a grant-database output: the password in database.env (0600),
    the rest in the module environment. Returns the environment values."""
    write_envfile(state_dir() / DATABASE_ENV, {"PGPASSWORD": out["password"]})
    host, port = out["host"], out["port"]
    # Prefer the read-write endpoint of the same cluster on this node
    endpoint = local_endpoint(node_records, node_id, out["cluster_id"]) if node_records else None
    if endpoint and endpoint["node"] == str(node_id):
        host, port = endpoint["host"], endpoint["port"]
    return {
        "WARPGATE_DB_NAME": out["database"],
        "WARPGATE_DB_USER": out["username"],
        "WARPGATE_DB_HOST": host,
        "WARPGATE_DB_PORT": str(port),
        "WARPGATE_DB_CLUSTER_ID": out["cluster_id"],
    }


def database_password():
    return read_envfile(state_dir() / DATABASE_ENV).get("PGPASSWORD", "")


def database_url(env=None):
    """PostgreSQL URL for Warpgate, without the password (PGPASSWORD)"""
    env = env if env is not None else os.environ
    user = urllib.parse.quote(env["WARPGATE_DB_USER"], safe="")
    name = urllib.parse.quote(env["WARPGATE_DB_NAME"], safe="")
    host = env["WARPGATE_DB_HOST"]
    if ":" in host:
        host = f"[{host}]"
    return f"postgres://{user}@{host}:{int(env['WARPGATE_DB_PORT'])}/{name}?sslmode=disable&connect_timeout=5"


def run_warpgate(args, env_names=(), volume="data", check=True):
    """Run a one-shot Warpgate container on the data volume. Secrets reach
    it as environment variables named in env_names, never in argv."""
    cmd = ["podman", "run", "--rm", f"--volume={volume}:/data:Z"]
    for name in env_names:
        cmd.append(f"--env={name}")
    cmd += [os.environ["WARPGATE_IMAGE"], *args]
    return subprocess.run(cmd, stdout=sys.stderr, stderr=sys.stderr, check=check)


def copy_sqlite_to_postgresql(env):
    """Copy the SQLite data into the empty PostgreSQL database"""
    child = dict(os.environ, PGPASSWORD=database_password())
    cmd = ["podman", "run", "--rm", "--volume=data:/data:Z", "--env=PGPASSWORD",
           os.environ["WARPGATE_IMAGE"], "--config", "/data/warpgate.yaml",
           "copy-database", database_url(env)]
    return subprocess.run(cmd, env=child, stdout=sys.stderr, stderr=sys.stderr).returncode == 0


# ---------------------------------------------------------------------------
# Peer approvals (ns8-kumomta set-peer-access / ns8-postgresql19c admit-member)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def access_lock(mode):
    fd = os.open(state_dir() / "peer-access.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+") as lock:
        fcntl.flock(lock, mode)
        yield


def read_grants():
    try:
        return json.loads((state_dir() / PEER_GRANTS).read_text())
    except FileNotFoundError:
        return {}


def registered_uuid(rdb, peer):
    """Module UUID of another installed Warpgate instance, else None"""
    if peer == os.environ.get("MODULE_ID") or not MODULE_ID_RE.fullmatch(peer or ""):
        return None
    image = rdb.hget(f"module/{peer}/environment", "IMAGE_URL")
    if image_name_of(image) != (image_name_of(os.environ.get("IMAGE_URL")) or IMAGE_NAME):
        return None
    return rdb.hget("cluster/module_uuid", peer)


def set_peer_access(rdb, peer, allowed):
    with access_lock(fcntl.LOCK_EX):
        grants = read_grants()
        if allowed:
            module_uuid = registered_uuid(rdb, peer)
            if not module_uuid:
                raise ClusterError("peer", "not_a_warpgate_instance", peer)
            grants[peer] = module_uuid
        else:
            grants.pop(peer, None)
        write_private(state_dir() / PEER_GRANTS, json.dumps(grants, sort_keys=True) + "\n")


def approved_peers(rdb):
    grants = read_grants()
    if not grants:
        return set()
    uuids = rdb.hmget("cluster/module_uuid", list(grants))
    return {peer for peer, uid in zip(grants, uuids) if uid and uid == grants[peer]}


def peer_candidates(rdb):
    """Other Warpgate instances, with their approval state (no secrets)"""
    approved = approved_peers(rdb)
    own = image_name_of(os.environ.get("IMAGE_URL")) or IMAGE_NAME
    result = []
    for module_id, node_id in (rdb.hgetall("cluster/module_node") or {}).items():
        if module_id == os.environ.get("MODULE_ID"):
            continue
        if image_name_of(rdb.hget(f"module/{module_id}/environment", "IMAGE_URL")) != own:
            continue
        result.append({"module_id": module_id, "node": str(node_id), "allowed": module_id in approved,
                       "ui_name": rdb.get(f"module/{module_id}/ui_name") or ""})
    return sorted(result, key=lambda c: c["module_id"])


def authorize_peer(rdb, module_id, task_user):
    """The caller must be the module it claims to be, approved here with
    its current module UUID"""
    prefix, _, peer = (task_user or "").partition("/")
    if prefix != "module" or peer != module_id or not MODULE_ID_RE.fullmatch(peer):
        raise ClusterError("module_id", "peer_not_authorized", module_id)
    with access_lock(fcntl.LOCK_SH):
        expected = read_grants().get(peer)
    if not expected or expected != registered_uuid(rdb, peer):
        raise ClusterError("module_id", "peer_not_approved", module_id)
    return peer


# ---------------------------------------------------------------------------
# Shared key material
# ---------------------------------------------------------------------------

def volume_path(volume="data"):
    out = subprocess.run(["podman", "volume", "inspect", "--format", "{{.Mountpoint}}", volume],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def read_volume_file(name):
    """A file of the data volume (owned by a subordinate UID)"""
    path = os.path.join(volume_path(), name)
    out = subprocess.run(["podman", "unshare", "cat", path], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def read_keyring_values():
    return read_envfile(state_dir() / ENCRYPTION_ENV)


def shared_material():
    """Key material every member needs (secret)"""
    material = {}
    keyring = read_keyring_values()
    if keyring.get("WARPGATE_ENCRYPTION_KEY"):
        material["encryption_key"] = keyring["WARPGATE_ENCRYPTION_KEY"]
        material["encryption_key_old"] = keyring.get("WARPGATE_ENCRYPTION_KEY_OLD", "")
    tls = read_shared_tls()
    certificate = tls.get("certificate") or read_volume_file("tls.certificate.pem")
    key = tls.get("key") or read_volume_file("tls.key.pem")
    if certificate.startswith("-----BEGIN") and key.startswith("-----BEGIN"):
        material["tls_certificate"] = certificate
        material["tls_key"] = key
    return material


def valid_key(value):
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError:
        return False
    return len(raw) == 32 and base64.b64encode(raw).decode() == value


def install_material(material):
    """Store shared key material received from a peer (or OpenBao)"""
    if material.get("encryption_key"):
        keys = [material["encryption_key"], *[k for k in material.get("encryption_key_old", "").split(",") if k]]
        if not all(valid_key(k) for k in keys):
            raise ClusterError("cluster", "invalid_key_material")
        values = {"WARPGATE_ENCRYPTION_KEY": keys[0]}
        if len(keys) > 1:
            values["WARPGATE_ENCRYPTION_KEY_OLD"] = ",".join(keys[1:])
        write_envfile(state_dir() / ENCRYPTION_ENV, values)
    if material.get("tls_certificate") and material.get("tls_key"):
        if not (material["tls_certificate"].startswith("-----BEGIN")
                and material["tls_key"].startswith("-----BEGIN")):
            raise ClusterError("cluster", "invalid_key_material")
        write_private(state_dir() / SHARED_TLS, json.dumps(
            {"certificate": material["tls_certificate"], "key": material["tls_key"]}))


def read_shared_tls():
    try:
        return json.loads((state_dir() / SHARED_TLS).read_text())
    except (FileNotFoundError, ValueError):
        return {}


def install_tls_into_volume(volume):
    """Called by render-warpgate-config, inside podman unshare"""
    tls = read_shared_tls()
    if not tls.get("certificate") or not tls.get("key"):
        return False
    changed = False
    for name, content in (("tls.certificate.pem", tls["certificate"]), ("tls.key.pem", tls["key"])):
        target = Path(volume) / name
        try:
            if target.read_text() == content:
                continue
        except FileNotFoundError:
            pass
        write_private(target, content)
        owner = (Path(volume) / "warpgate.yaml").stat()
        os.chown(target, owner.st_uid, owner.st_gid)
        changed = True
    return changed


# ---------------------------------------------------------------------------
# OpenBao
# ---------------------------------------------------------------------------

class OpenBaoError(Exception):
    def __init__(self, status=0):
        super().__init__(f"OpenBao request failed ({status or 'unreachable'})")
        self.status = status


def vault_settings():
    env = read_envfile(state_dir() / OPENBAO_ENV)
    return {
        "vault_enabled": os.environ.get("WARPGATE_VAULT_ENABLED") == "1",
        "vault_mode": os.environ.get("WARPGATE_VAULT_MODE") or "manual",
        "vault_openbao": os.environ.get("WARPGATE_VAULT_OPENBAO", ""),
        "vault_address": env.get("VAULT_ADDR", ""),
        "vault_token_set": bool(env.get("VAULT_TOKEN")),
        "vault_mount": os.environ.get("WARPGATE_VAULT_MOUNT") or "secret",
        "vault_path": os.environ.get("WARPGATE_VAULT_PATH") or "warpgate",
    }


def bao_request(address, path, method="GET", token="", data=None, timeout=8):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(f"{address.rstrip('/')}/v1/{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as ex:
        raise OpenBaoError(ex.code) from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OpenBaoError(0) from None
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


class Vault:
    """KV version 2 under <mount>/data/<path>/<name>, field "value" """

    def __init__(self, address, token, mount, path):
        self.address = address.rstrip("/")
        self.token = token
        self.mount = mount.strip("/")
        self.path = path.strip("/")

    def secret_path(self, name):
        return f"{self.path}/{name}" if self.path else name

    def get(self, name):
        try:
            out = bao_request(self.address, f"{self.mount}/data/{self.secret_path(name)}", token=self.token)
        except OpenBaoError as ex:
            if ex.status == 404:
                return None
            raise
        value = ((out.get("data") or {}).get("data") or {}).get("value")
        return value if isinstance(value, str) else None

    def set(self, name, value):
        bao_request(self.address, f"{self.mount}/data/{self.secret_path(name)}", "POST",
                    token=self.token, data={"data": {"value": value}})


def make_vault(vs=None):
    vs = vs or vault_settings()
    env = read_envfile(state_dir() / OPENBAO_ENV)
    return Vault(env.get("VAULT_ADDR", ""), env.get("VAULT_TOKEN", ""), vs["vault_mount"], vs["vault_path"])


def provision(openbao_id):
    """ns8-openbao client provisioning: returns (address, token, mount,
    path). The wrapped token is checked, unwrapped and never logged."""
    import agent.tasks

    ret = agent.tasks.run(agent_id=f"module/{openbao_id}", action="provision-client", data={},
                          extra={"isNotificationHidden": True})
    out = ret.get("output")
    if ret.get("exit_code") != 0 or not isinstance(out, dict):
        code = "openbao_provisioning_failed"
        if isinstance(out, list) and out and isinstance(out[0], dict):
            code = out[0].get("error") or code
        raise ClusterError("vault_openbao", code, openbao_id)
    address = out["address"]
    try:
        info = bao_request(address, "sys/wrapping/lookup", "POST", data={"token": out["wrapped_token"]})
        if (info.get("data") or {}).get("creation_path") != out["wrap_creation_path"]:
            raise ClusterError("vault_openbao", "openbao_wrapping_mismatch", openbao_id)
        unwrapped = bao_request(address, "sys/wrapping/unwrap", "POST", token=out["wrapped_token"])
    except OpenBaoError:
        raise ClusterError("vault_openbao", "openbao_unwrap_failed", openbao_id) from None
    token = (unwrapped.get("auth") or {}).get("client_token")
    if not token:
        raise ClusterError("vault_openbao", "openbao_unwrap_failed", openbao_id)
    return address, token, out["kv_mount"], out["kv_prefix"]


def save_vault_env(address, token):
    write_envfile(state_dir() / OPENBAO_ENV, {"VAULT_ADDR": address, "VAULT_TOKEN": token,
                                              "VAULT_TOKEN_ISSUED": str(int(time.time()))})


def secret_items():
    """The secrets mirrored to OpenBao: name -> value (local copies)"""
    items = {}
    password = database_password()
    if password:
        items["database"] = json.dumps({
            "username": os.environ.get("WARPGATE_DB_USER", ""), "password": password,
            "database": os.environ.get("WARPGATE_DB_NAME", ""),
            "host": os.environ.get("WARPGATE_DB_HOST", ""), "port": os.environ.get("WARPGATE_DB_PORT", "")})
    keyring = read_keyring_values()
    if keyring:
        items["encryption"] = json.dumps(keyring, sort_keys=True)
    tls = read_shared_tls()
    if tls:
        items["tls"] = json.dumps(tls, sort_keys=True)
    try:
        oidc = json.loads((state_dir() / "oidc.json").read_text()).get("entries", [])
    except (FileNotFoundError, ValueError, AttributeError):
        oidc = []
    secrets = {f"{e.get('mode')}:{e.get('issuer')}:{e.get('client_id')}": e["secret"]
               for e in oidc if isinstance(e, dict) and e.get("secret")}
    if secrets:
        items["oidc"] = json.dumps(secrets, sort_keys=True)
    return items


def push_secrets(names=None):
    """Mirror the local secrets to OpenBao. Never raises: returns the names
    that could not be written (OpenBao sealed, unreachable or refusing)."""
    vs = vault_settings()
    if not vs["vault_enabled"]:
        return []
    vault = make_vault(vs)
    failed = []
    for name, value in secret_items().items():
        if names and name not in names:
            continue
        try:
            if vault.get(name) != value:
                vault.set(name, value)
        except OpenBaoError:
            failed.append(name)
    return failed


def renew_token():
    """Renew the OpenBao token; returns its remaining lease in seconds"""
    env = read_envfile(state_dir() / OPENBAO_ENV)
    out = bao_request(env["VAULT_ADDR"], "auth/token/renew-self", "POST", token=env["VAULT_TOKEN"], data={})
    return int((out.get("auth") or {}).get("lease_duration") or 0)


def fail(error):
    """Report a ClusterError as a task validation failure and exit"""
    import agent

    agent.set_status("validation-failed")
    json.dump([{"field": error.field, "parameter": error.field, "value": error.value, "error": error.code}],
              sys.stdout)
    raise SystemExit(3)


def vpn_ip(rdb, node_id=None):
    import ipaddress

    value = rdb.hget(f"node/{node_id or os.environ.get('NODE_ID')}/vpn", "ip_address") or ""
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return ""
    return value


def cluster_args(mode, peer_ip, http_port):
    """Extra podman arguments of a cluster member: Warpgate peers reach each
    other's HTTP listener (cluster TLS, CA in the database) on the VPN"""
    if mode == "standalone" or not peer_ip:
        return ""
    return f"--publish={peer_ip}:{http_port}:8888 --env=WARPGATE_PEER_ADDRESS={peer_ip}:{http_port}"


def requested(request, cur):
    """Effective database and cluster settings of a configure-module request"""
    db = request.get("database") or {}
    cl = request.get("cluster") or {}
    return {
        "db_mode": db.get("mode") or cur["db_mode"],
        "db_instance": db.get("instance", cur["db_instance"]) or "",
        "cluster_mode": cl.get("mode") or cur["cluster_mode"],
        "cluster_peer": cl.get("peer", cur["cluster_peer"]) or "",
    }


def validate(want, cur, records, vault_request):
    """Check a configure-module request; raises ClusterError"""
    if want["db_mode"] == "embedded" and cur["db_mode"] == "postgresql19c":
        raise ClusterError("database_mode", "cannot_switch_to_embedded", "embedded")
    if want["cluster_mode"] != "standalone" and want["db_mode"] != "postgresql19c":
        raise ClusterError("cluster_mode", "cluster_requires_postgresql", want["cluster_mode"])
    if want["cluster_mode"] == "join":
        if not MODULE_ID_RE.fullmatch(want["cluster_peer"]) or want["cluster_peer"] == os.environ.get("MODULE_ID"):
            raise ClusterError("cluster_peer", "invalid_peer", want["cluster_peer"])
        if cur["cluster_mode"] == "create":
            raise ClusterError("cluster_mode", "cannot_join_from_create", "join")
    if want["db_mode"] == "postgresql19c":
        if not records:
            raise ClusterError("database_instance", "no_postgresql19c_instance", "")
        if want["db_instance"] and not any(r["module_id"] == want["db_instance"] for r in records):
            raise ClusterError("database_instance", "postgresql19c_instance_not_found", want["db_instance"])
    if vault_request.get("vault_enabled"):
        mode = vault_request.get("vault_mode") or "manual"
        if mode == "provisioned" and not MODULE_ID_RE.fullmatch(vault_request.get("vault_openbao") or ""):
            raise ClusterError("vault_openbao", "required", "")
        if mode == "manual":
            vs = vault_settings()
            address = vault_request.get("vault_address") or vs["vault_address"]
            if not re.fullmatch(r"https?://[^\s/?#]+(/[^\s?#]*)?", address or ""):
                raise ClusterError("vault_address", "invalid_url", address or "")
            if not (vault_request.get("vault_token") or vs["vault_token_set"]):
                raise ClusterError("vault_token", "required", "")


def follow_database_endpoint(removed=""):
    """Event handler: point Warpgate at the read-write endpoint of its
    PostgreSQL cluster on this node (or any other of the same cluster).
    The credentials are valid on every endpoint of the cluster. When the
    instance in use moved to another PostgreSQL cluster, get a login role
    there (grant-database). Returns an exit code."""
    import agent

    cur = settings()
    if cur["db_mode"] != "postgresql19c":
        return 0
    rdb = agent.redis_connect(use_replica=True)
    records = [r for r in pg_records(rdb) if r["module_id"] != removed]
    node_id = os.environ["NODE_ID"]
    values = {}
    provider = next((r for r in records if r["module_id"] == cur["db_provider"]), None)
    if provider and provider["cluster_id"] != cur["db_cluster_id"]:
        print(agent.SD_WARNING + f"{provider['module_id']} is now in PostgreSQL cluster {provider['cluster_id']}:"
              " asking it for a login role on the Warpgate database", file=sys.stderr)
        try:
            out = grant_database(provider["module_id"], cur["db_name"])
        except ClusterError as error:
            print(agent.SD_ERR + f"grant-database failed: {error.code}", file=sys.stderr)
            return 1
        values.update(store_credentials(out, records, node_id))
    else:
        endpoint = local_endpoint(records, node_id, cur["db_cluster_id"])
        if not endpoint:
            print(agent.SD_ERR + f"No endpoint of PostgreSQL cluster {cur['db_cluster_id']} is left", file=sys.stderr)
            return 1
        values = {"WARPGATE_DB_HOST": endpoint["host"], "WARPGATE_DB_PORT": str(endpoint["port"])}
        if not provider:
            values["WARPGATE_DB_PROVIDER"] = endpoint["module_id"]
    changed = {k: v for k, v in values.items() if os.environ.get(k) != v}
    if not changed and "WARPGATE_DB_USER" not in values:
        return 0
    agent.mset_env(values)
    os.environ.update(values)
    print(f"Warpgate database endpoint: {values.get('WARPGATE_DB_HOST')}:{values.get('WARPGATE_DB_PORT')}",
          file=sys.stderr)
    agent.run_helper("systemctl", "--user", "try-restart", "warpgate.service")
    push_secrets(["database"])
    return 0
