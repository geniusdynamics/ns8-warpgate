# SPDX-License-Identifier: GPL-3.0-or-later

"""Session recordings storage: local disk (default) or an S3-compatible
bucket.

Warpgate 0.30 keeps the recordings storage in its database
(parameters.recordings_storage, a RecordingsStorageConfig serialized as
JSON), not in warpgate.yaml, and changes it with the admin API
(PUT /@warpgate/admin/api/parameters). The S3 variant has these fields
(warpgate-aws/src/s3.rs, S3StorageConfig): bucket, region, endpoint (None
for AWS), path_style, prefix, credentials and scratch_path. There is no
TLS verification setting.

The module stores the credentials with mode "Auto" (the ambient AWS
credential chain): the access key ID and the secret key reach the
container as AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from the 0600
file state/s3.env. The secret key is therefore neither in warpgate.yaml
nor in the database ("Static" credentials would be stored there in
clear text).

Non-secret settings (module environment):

- WARPGATE_RECORDINGS_STORAGE: "local" (default, also when unset) or "s3"
- WARPGATE_S3_ENDPOINT, WARPGATE_S3_REGION, WARPGATE_S3_BUCKET,
  WARPGATE_S3_PREFIX, WARPGATE_S3_PATH_STYLE ("1" or "0")
- WARPGATE_RECORDINGS_APPLIED: "s3" after the module wrote the S3 storage
  into Warpgate; switching back to local writes the disk storage again
- WARPGATE_RECORDINGS_DISK_PATH: the disk path Warpgate used before
"""

import datetime
import hashlib
import hmac
import http.client
import os
import re
import ssl
import urllib.parse

import warpgate_cluster as wc

S3_ENV = "s3.env"
DEFAULT_DISK_PATH = "/data/recordings"
SCRATCH_PATH = "/data/recordings-scratch"

ENDPOINT_RE = re.compile(r"^https?://(\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?)(:[0-9]{1,5})?/?$")
REGION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
PREFIX_RE = re.compile(r"^[A-Za-z0-9!_.*'()/-]{0,512}$")
ACCESS_KEY_RE = re.compile(r"^[\x21-\x7e]{1,128}$")


def settings():
    """Non-secret recordings settings"""
    env = os.environ
    s3 = wc.read_envfile(wc.state_dir() / S3_ENV)
    return {
        "storage": "s3" if env.get("WARPGATE_RECORDINGS_STORAGE") == "s3" else "local",
        "endpoint": env.get("WARPGATE_S3_ENDPOINT", ""),
        "region": env.get("WARPGATE_S3_REGION", ""),
        "bucket": env.get("WARPGATE_S3_BUCKET", ""),
        "prefix": env.get("WARPGATE_S3_PREFIX", ""),
        "path_style": env.get("WARPGATE_S3_PATH_STYLE", "1") != "0",
        "access_key_id": s3.get("AWS_ACCESS_KEY_ID", ""),
        "secret_access_key_set": bool(s3.get("AWS_SECRET_ACCESS_KEY")),
    }


def secret_key():
    return wc.read_envfile(wc.state_dir() / S3_ENV).get("AWS_SECRET_ACCESS_KEY", "")


def requested(request, cur):
    """Effective recordings settings of a configure-module request: missing
    fields keep the current values, a blank secret keeps the saved one"""
    rec = request.get("recordings")
    if not isinstance(rec, dict):
        return dict(cur, secret_access_key="")
    want = {
        "storage": rec.get("storage") or cur["storage"],
        "endpoint": rec.get("endpoint", cur["endpoint"]) or "",
        "region": rec.get("region", cur["region"]) or "",
        "bucket": rec.get("bucket", cur["bucket"]) or "",
        "prefix": rec.get("prefix", cur["prefix"]) or "",
        "path_style": bool(rec.get("path_style", cur["path_style"])),
        "access_key_id": rec.get("access_key_id", cur["access_key_id"]) or "",
        "secret_access_key": rec.get("secret_access_key") or "",
    }
    want["endpoint"] = want["endpoint"].strip()
    want["region"] = want["region"].strip()
    want["bucket"] = want["bucket"].strip()
    want["prefix"] = want["prefix"].strip().strip("/")
    want["access_key_id"] = want["access_key_id"].strip()
    # A new access key ID needs its own secret key
    keeps_key = want["access_key_id"] == cur["access_key_id"] and cur["secret_access_key_set"]
    want["secret_access_key_set"] = bool(want["secret_access_key"]) or keeps_key
    return want


def validate(want):
    """Raise wc.ClusterError for invalid S3 settings (local: nothing to check)"""
    if want["storage"] != "s3":
        return
    endpoint = want["endpoint"]
    if endpoint and not ENDPOINT_RE.fullmatch(endpoint):
        raise wc.ClusterError("recordings_endpoint", "s3_invalid_endpoint", endpoint)
    if endpoint:
        try:
            port = urllib.parse.urlsplit(endpoint).port
        except ValueError:
            port = 0
        if port == 0:
            raise wc.ClusterError("recordings_endpoint", "s3_invalid_endpoint", endpoint)
    if not want["region"]:
        raise wc.ClusterError("recordings_region", "required", "")
    if not REGION_RE.fullmatch(want["region"]):
        raise wc.ClusterError("recordings_region", "s3_invalid_region", want["region"])
    bucket = want["bucket"]
    if not bucket:
        raise wc.ClusterError("recordings_bucket", "required", "")
    if (not BUCKET_RE.fullmatch(bucket) or ".." in bucket or ".-" in bucket or "-." in bucket
            or re.fullmatch(r"[0-9.]+", bucket)):
        raise wc.ClusterError("recordings_bucket", "s3_invalid_bucket", bucket)
    if not want["path_style"] and "." in bucket and (endpoint or "").startswith("https"):
        # A dotted bucket name does not match the endpoint's wildcard certificate
        raise wc.ClusterError("recordings_bucket", "s3_dotted_bucket_needs_path_style", bucket)
    prefix = want["prefix"]
    if not PREFIX_RE.fullmatch(prefix) or any(part in ("", ".", "..") for part in prefix.split("/") if prefix):
        raise wc.ClusterError("recordings_prefix", "s3_invalid_prefix", prefix)
    if not want["access_key_id"]:
        raise wc.ClusterError("recordings_access_key_id", "required", "")
    if not ACCESS_KEY_RE.fullmatch(want["access_key_id"]):
        raise wc.ClusterError("recordings_access_key_id", "s3_invalid_access_key", "")
    secret = want.get("secret_access_key") or ""
    if not secret and not want["secret_access_key_set"]:
        raise wc.ClusterError("recordings_secret_access_key", "required", "")
    if secret and (len(secret) > 256 or any(c.isspace() or ord(c) < 32 for c in secret)):
        raise wc.ClusterError("recordings_secret_access_key", "s3_invalid_secret", "")


def env_values(want):
    """Module environment of the settings (no secret)"""
    if want["storage"] != "s3":
        return {"WARPGATE_RECORDINGS_STORAGE": "local"}
    return {
        "WARPGATE_RECORDINGS_STORAGE": "s3",
        "WARPGATE_S3_ENDPOINT": want["endpoint"],
        "WARPGATE_S3_REGION": want["region"],
        "WARPGATE_S3_BUCKET": want["bucket"],
        "WARPGATE_S3_PREFIX": want["prefix"],
        "WARPGATE_S3_PATH_STYLE": "1" if want["path_style"] else "0",
    }


def save(want):
    """Persist the settings: the module environment and state/s3.env (0600).
    Returns the environment values (also applied to os.environ)."""
    import agent

    values = env_values(want)
    if want["storage"] == "s3":
        secret = want.get("secret_access_key") or secret_key()
        wc.write_envfile(wc.state_dir() / S3_ENV, {"AWS_ACCESS_KEY_ID": want["access_key_id"],
                                                   "AWS_SECRET_ACCESS_KEY": secret})
    else:
        wc.remove(wc.state_dir() / S3_ENV)
    agent.mset_env(values)
    os.environ.update(values)
    return values


# ---------------------------------------------------------------------------
# Cluster members: the S3 settings travel with admit-peer
# ---------------------------------------------------------------------------

def peer_material():
    """The recordings settings for a joining member (secret)"""
    cur = settings()
    if cur["storage"] != "s3":
        return {"storage": "local"}
    return {key: cur[key] for key in ("storage", "endpoint", "region", "bucket", "prefix", "path_style",
                                      "access_key_id")} | {"secret_access_key": secret_key()}


def install_from_peer(material):
    """Apply the recordings settings received from the peer (no-op when
    the peer does not send them, e.g. an older module release)"""
    if not isinstance(material, dict) or material.get("storage") not in ("local", "s3"):
        return False
    want = {
        "storage": material["storage"],
        "endpoint": str(material.get("endpoint") or ""),
        "region": str(material.get("region") or ""),
        "bucket": str(material.get("bucket") or ""),
        "prefix": str(material.get("prefix") or ""),
        "path_style": bool(material.get("path_style", True)),
        "access_key_id": str(material.get("access_key_id") or ""),
        "secret_access_key": str(material.get("secret_access_key") or ""),
        "secret_access_key_set": False,
    }
    try:
        validate(want)
    except wc.ClusterError:
        raise wc.ClusterError("cluster_peer", "invalid_peer_recordings") from None
    save(want)
    return True


# ---------------------------------------------------------------------------
# Warpgate parameters (admin API)
# ---------------------------------------------------------------------------

def warpgate_storage(cur=None, disk_path=None):
    """The RecordingsStorageConfig the module wants in Warpgate"""
    cur = cur or settings()
    if cur["storage"] != "s3":
        return {"kind": "Disk", "path": disk_path or os.environ.get("WARPGATE_RECORDINGS_DISK_PATH")
                or DEFAULT_DISK_PATH}
    return {
        "kind": "S3",
        "bucket": cur["bucket"],
        "region": cur["region"],
        "endpoint": cur["endpoint"].rstrip("/") or None,
        "path_style": bool(cur["path_style"]),
        "prefix": cur["prefix"],
        "credentials": {"mode": "Auto"},
        "scratch_path": SCRATCH_PATH,
    }


def manages_parameters(cluster_mode):
    """Members that joined another instance do not write the shared
    database row: its creator does, so an outdated copy never wins"""
    return cluster_mode != "join"


def needs_admin_api(cur=None, cluster_mode="standalone"):
    cur = cur or settings()
    if not manages_parameters(cluster_mode):
        return False
    return cur["storage"] == "s3" or os.environ.get("WARPGATE_RECORDINGS_APPLIED") == "s3"


def apply(api, cluster_mode="standalone"):
    """Write the recordings storage into Warpgate when it differs.
    Returns True when Warpgate was changed."""
    import agent

    if not manages_parameters(cluster_mode):
        return False
    cur = settings()
    applied = os.environ.get("WARPGATE_RECORDINGS_APPLIED", "")
    if cur["storage"] != "s3" and applied != "s3":
        return False  # never touched by the module: leave Warpgate's own setting
    params = api.request("/parameters") or {}
    current = params.get("recordings_storage") or {}
    env = {}
    if cur["storage"] == "s3":
        if current.get("kind") == "Disk" and current.get("path"):
            env["WARPGATE_RECORDINGS_DISK_PATH"] = current["path"]
        desired = warpgate_storage(cur)
        env["WARPGATE_RECORDINGS_APPLIED"] = "s3"
    else:
        desired = warpgate_storage(cur)
        env["WARPGATE_RECORDINGS_APPLIED"] = ""
    changed = comparable(current) != comparable(desired)
    if changed:
        api.request("/parameters", "PUT", {"recordings_storage": desired})
    agent.mset_env(env)
    os.environ.update(env)
    return changed


def comparable(storage):
    """A storage config without the redacted secret, for comparisons"""
    storage = dict(storage or {})
    credentials = dict(storage.get("credentials") or {})
    credentials.pop("secret_access_key", None)
    if credentials:
        storage["credentials"] = credentials
    if storage.get("kind") == "S3":
        storage.setdefault("scratch_path", None)
        storage["endpoint"] = storage.get("endpoint") or None
    return storage


def warnings(cur, cluster_mode):
    """Non-blocking hints for the Settings page"""
    result = []
    if cur["storage"] == "local" and cluster_mode != "standalone":
        result.append("cluster_local_recordings")
    if cur["storage"] == "s3" and cur["endpoint"].startswith("http://"):
        result.append("s3_http_endpoint")
    return result


# ---------------------------------------------------------------------------
# Connection test: a signed HEAD bucket request (AWS Signature Version 4)
# ---------------------------------------------------------------------------

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _hmac(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def signing_key(secret, date, region, service):
    k = _hmac(("AWS4" + secret).encode(), date)
    k = _hmac(k, region)
    k = _hmac(k, service)
    return _hmac(k, "aws4_request")


def sign_v4(method, host, path, query, headers, payload_hash, access_key, secret, region, service, amz_date):
    """Return the Authorization header value. headers: lower-case names,
    "host" and "x-amz-date" included."""
    date = amz_date[:8]
    names = sorted(headers)
    canonical_headers = "".join(f"{n}:{' '.join(str(headers[n]).split())}\n" for n in names)
    signed_headers = ";".join(names)
    canonical_query = "&".join(
        f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}"
        for k, v in sorted(query))
    canonical = "\n".join([method, path, canonical_query, canonical_headers, signed_headers, payload_hash])
    scope = f"{date}/{region}/{service}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    signature = hmac.new(signing_key(secret, date, region, service), to_sign.encode(),
                         hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed_headers}, Signature={signature}"


def bucket_url(want):
    """(scheme, host[:port], path) of the bucket, as Warpgate's SDK builds it"""
    endpoint = want["endpoint"].rstrip("/") or f"https://s3.{want['region']}.amazonaws.com"
    url = urllib.parse.urlsplit(endpoint)
    bucket = urllib.parse.quote(want["bucket"], safe="")
    if want["path_style"]:
        return url.scheme, url.netloc, f"/{bucket}"
    return url.scheme, f"{want['bucket']}.{url.netloc}", "/"


def test_bucket(want, secret, timeout=10, now=None):
    """HEAD the bucket with the given credentials. Returns
    {"ok": bool, "error": code, "status": int} and never the secret."""
    scheme, netloc, path = bucket_url(want)
    amz_date = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    headers = {"host": netloc, "x-amz-date": amz_date, "x-amz-content-sha256": EMPTY_SHA256}
    headers["authorization"] = sign_v4("HEAD", netloc, path, [], headers, EMPTY_SHA256, want["access_key_id"],
                                       secret, want["region"], "s3", amz_date)
    url = urllib.parse.urlsplit(f"{scheme}://{netloc}")
    try:
        if scheme == "https":
            conn = http.client.HTTPSConnection(url.hostname, url.port, timeout=timeout,
                                               context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)
        # The Host header must be the signed one, byte for byte
        conn.putrequest("HEAD", path, skip_host=True, skip_accept_encoding=True)
        for name, value in headers.items():
            conn.putheader(name, value)
        conn.endheaders()
        resp = conn.getresponse()
        status = resp.status
        region = resp.getheader("x-amz-bucket-region") or ""
        conn.close()
    except ssl.SSLError:
        return {"ok": False, "error": "s3_tls_error", "status": 0}
    except (OSError, http.client.HTTPException, ValueError):
        return {"ok": False, "error": "s3_unreachable", "status": 0}
    if 200 <= status < 300:
        return {"ok": True, "error": "", "status": status}
    if region and region != want["region"]:
        return {"ok": False, "error": "s3_wrong_region", "status": status}
    code = {301: "s3_wrong_region", 400: "s3_bad_request", 401: "s3_access_denied", 403: "s3_access_denied",
            404: "s3_bucket_not_found"}.get(status, "s3_error")
    return {"ok": False, "error": code, "status": status}
