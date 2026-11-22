# SPDX-License-Identifier: GPL-3.0-or-later
# Run: python3 -m unittest discover -s unittests

"""Recordings storage (local / S3), admit-peer material, Warpgate admin
API helpers and the Warpgate secret backend."""

import datetime
import http.server
import json
import os
import stat
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "imageroot" / "pypkg"))
import warpgate_api  # noqa: E402
import warpgate_cluster as wc  # noqa: E402
import warpgate_recordings as wr  # noqa: E402
import warpgate_secret_backend as wsb  # noqa: E402

SECRET = "s3cr3t/Key+value"


def fake_agent():
    agent = types.ModuleType("agent")
    agent.saved = {}

    def mset_env(values):
        agent.saved.update(values)

    agent.mset_env = mset_env
    agent.set_env = lambda key, value: agent.saved.__setitem__(key, value)
    return agent


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {
            "AGENT_STATE_DIR": self.tmp.name, "MODULE_ID": "warpgate1", "NODE_ID": "1",
            "TCP_PORT_HTTP": "20001", "TRAEFIK_HOST": "warpgate.example.org"}, clear=False)
        self.env.start()
        for key in list(os.environ):
            if key.startswith(("WARPGATE_RECORDINGS", "WARPGATE_S3_", "WARPGATE_SECRET_BACKEND", "WARPGATE_VAULT",
                               "WARPGATE_CLUSTER")):
                del os.environ[key]
        self.agent = fake_agent()
        self.modules = mock.patch.dict(sys.modules, {"agent": self.agent})
        self.modules.start()

    def tearDown(self):
        self.modules.stop()
        self.env.stop()
        self.tmp.cleanup()

    def path(self, name):
        return Path(self.tmp.name) / name

    def mode(self, name):
        return stat.S_IMODE(os.stat(self.path(name)).st_mode)

    def s3_request(self, **changes):
        rec = {"storage": "s3", "endpoint": "https://s3.example.org:9000", "region": "us-east-1",
               "bucket": "warpgate-recordings", "prefix": "node1/", "path_style": True,
               "access_key_id": "AKIAEXAMPLE", "secret_access_key": SECRET}
        rec.update(changes)
        return {"recordings": rec}


class FakeApi:
    """warpgate_api stand-in: records the calls, serves fixed answers"""

    ApiError = warpgate_api.ApiError

    def __init__(self, parameters=None, backends=None):
        self.parameters = parameters or {"recordings_storage": {"kind": "Disk", "path": "/data/recordings"}}
        self.backends = backends if backends is not None else []
        self.calls = []

    def request(self, path, method="GET", data=None, **_kw):
        self.calls.append((method, path, data))
        if path == "/parameters" and method == "GET":
            return self.parameters
        if path == "/parameters" and method == "PUT":
            self.parameters = dict(self.parameters, **data)
            return None
        if path == "/secret-backends" and method == "GET":
            return self.backends
        if path == "/secret-backends" and method == "POST":
            self.backends.append(dict(data, id="b-1"))
            return self.backends[-1]
        if path.startswith("/secret-backends/") and method == "PUT":
            return data
        raise AssertionError(f"unexpected call {method} {path}")

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


class RecordingsValidationTest(StateTestCase):
    def want(self, **changes):
        return wr.requested(self.s3_request(**changes), wr.settings())

    def code(self, **changes):
        with self.assertRaises(wc.ClusterError) as ctx:
            wr.validate(self.want(**changes))
        return ctx.exception.field, ctx.exception.code

    def test_defaults_are_local(self):
        cur = wr.settings()
        self.assertEqual(cur["storage"], "local")
        self.assertFalse(cur["secret_access_key_set"])
        # A request without "recordings" keeps the current (local) storage
        want = wr.requested({"host": "x"}, cur)
        self.assertEqual(want["storage"], "local")
        wr.validate(want)

    def test_valid_s3(self):
        want = self.want()
        wr.validate(want)
        self.assertEqual(want["prefix"], "node1")
        wr.validate(self.want(endpoint=""))  # AWS
        wr.validate(self.want(endpoint="http://10.5.4.1:9000", path_style=True))
        wr.validate(self.want(endpoint="https://[fd00::1]:9000/"))

    def test_invalid_values(self):
        self.assertEqual(self.code(endpoint="ftp://s3.example.org"), ("recordings_endpoint", "s3_invalid_endpoint"))
        self.assertEqual(self.code(endpoint="https://s3.example.org/bucket"),
                         ("recordings_endpoint", "s3_invalid_endpoint"))
        self.assertEqual(self.code(endpoint="https://s3.example.org:99999"),
                         ("recordings_endpoint", "s3_invalid_endpoint"))
        self.assertEqual(self.code(region=""), ("recordings_region", "required"))
        self.assertEqual(self.code(region="us east"), ("recordings_region", "s3_invalid_region"))
        self.assertEqual(self.code(bucket=""), ("recordings_bucket", "required"))
        for bucket in ("Bad_Bucket", "ab", "a..b", "192.168.1.1", "-bucket", "a" * 64):
            self.assertEqual(self.code(bucket=bucket), ("recordings_bucket", "s3_invalid_bucket"), bucket)
        self.assertEqual(self.code(bucket="my.bucket", path_style=False),
                         ("recordings_bucket", "s3_dotted_bucket_needs_path_style"))
        self.assertEqual(self.code(prefix="a/../b"), ("recordings_prefix", "s3_invalid_prefix"))
        self.assertEqual(self.code(prefix="a b"), ("recordings_prefix", "s3_invalid_prefix"))
        self.assertEqual(self.code(access_key_id=""), ("recordings_access_key_id", "required"))
        self.assertEqual(self.code(access_key_id="AK IA"), ("recordings_access_key_id", "s3_invalid_access_key"))
        self.assertEqual(self.code(secret_access_key=""), ("recordings_secret_access_key", "required"))
        self.assertEqual(self.code(secret_access_key="a\nb"), ("recordings_secret_access_key", "s3_invalid_secret"))

    def test_blank_secret_keeps_saved_one_for_the_same_key(self):
        wr.save(self.want())
        os.environ.update(self.agent.saved)
        wr.validate(self.want(secret_access_key=""))
        # Another access key ID needs its own secret key
        self.assertEqual(self.code(access_key_id="OTHERKEY", secret_access_key=""),
                         ("recordings_secret_access_key", "required"))


class RecordingsSaveTest(StateTestCase):
    def test_secret_only_in_private_file(self):
        values = wr.save(wr.requested(self.s3_request(), wr.settings()))
        self.assertEqual(self.mode(wr.S3_ENV), 0o600)
        self.assertEqual(wc.read_envfile(self.path(wr.S3_ENV)),
                         {"AWS_ACCESS_KEY_ID": "AKIAEXAMPLE", "AWS_SECRET_ACCESS_KEY": SECRET})
        self.assertNotIn(SECRET, json.dumps(values))
        self.assertNotIn(SECRET, json.dumps(self.agent.saved))
        self.assertEqual(values["WARPGATE_S3_PREFIX"], "node1")
        cur = wr.settings()
        self.assertTrue(cur["secret_access_key_set"])
        self.assertNotIn(SECRET, json.dumps(cur))

    def test_blank_secret_is_kept(self):
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        wr.save(wr.requested(self.s3_request(secret_access_key="", bucket="other-bucket"), wr.settings()))
        self.assertEqual(wr.secret_key(), SECRET)
        self.assertEqual(os.environ["WARPGATE_S3_BUCKET"], "other-bucket")

    def test_local_removes_the_secret(self):
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        wr.save(wr.requested({"recordings": {"storage": "local"}}, wr.settings()))
        self.assertFalse(self.path(wr.S3_ENV).exists())
        self.assertEqual(os.environ["WARPGATE_RECORDINGS_STORAGE"], "local")


class RecordingsWarpgateTest(StateTestCase):
    def test_storage_payload_has_no_secret(self):
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        storage = wr.warpgate_storage()
        self.assertEqual(storage, {
            "kind": "S3", "bucket": "warpgate-recordings", "region": "us-east-1",
            "endpoint": "https://s3.example.org:9000", "path_style": True, "prefix": "node1",
            "credentials": {"mode": "Auto"}, "scratch_path": "/data/recordings-scratch"})
        self.assertNotIn(SECRET, json.dumps(storage))
        wr.save(wr.requested(self.s3_request(endpoint=""), wr.settings()))
        self.assertIsNone(wr.warpgate_storage()["endpoint"])

    def test_untouched_instance_is_left_alone(self):
        api = FakeApi()
        self.assertFalse(wr.needs_admin_api())
        self.assertFalse(wr.apply(api))
        self.assertEqual(api.calls, [])

    def test_switch_to_s3_and_back(self):
        api = FakeApi({"recordings_storage": {"kind": "Disk", "path": "/srv/old-recordings"}})
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        self.assertTrue(wr.needs_admin_api())
        self.assertTrue(wr.apply(api))
        self.assertEqual(api.writes(), [("PUT", "/parameters", {"recordings_storage": wr.warpgate_storage()})])
        self.assertEqual(os.environ["WARPGATE_RECORDINGS_APPLIED"], "s3")
        self.assertEqual(os.environ["WARPGATE_RECORDINGS_DISK_PATH"], "/srv/old-recordings")
        # Warpgate answers with the redacted (Auto: nothing to redact) config
        api.calls.clear()
        self.assertFalse(wr.apply(api))
        self.assertEqual(api.writes(), [])
        # Back to local: the disk path Warpgate had before
        wr.save(wr.requested({"recordings": {"storage": "local"}}, wr.settings()))
        self.assertTrue(wr.needs_admin_api())
        self.assertTrue(wr.apply(api))
        self.assertEqual(api.writes()[-1],
                         ("PUT", "/parameters", {"recordings_storage": {"kind": "Disk", "path": "/srv/old-recordings"}}))
        self.assertEqual(os.environ["WARPGATE_RECORDINGS_APPLIED"], "")
        self.assertFalse(wr.needs_admin_api())

    def test_joined_member_never_writes(self):
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        api = FakeApi()
        self.assertFalse(wr.needs_admin_api(cluster_mode="join"))
        self.assertFalse(wr.apply(api, "join"))
        self.assertEqual(api.calls, [])

    def test_warnings(self):
        self.assertEqual(wr.warnings(wr.settings(), "standalone"), [])
        self.assertEqual(wr.warnings(wr.settings(), "create"), ["cluster_local_recordings"])
        self.assertEqual(wr.warnings(wr.settings(), "join"), ["cluster_local_recordings"])
        wr.save(wr.requested(self.s3_request(endpoint="http://10.5.4.1:9000"), wr.settings()))
        self.assertEqual(wr.warnings(wr.settings(), "create"), ["s3_http_endpoint"])


class RenderTest(StateTestCase):
    """The S3 secret never reaches the Warpgate configuration file"""

    def test_rendered_config_has_no_secret(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML is not installed")
        import warpgate_oidc

        volume = Path(self.tmp.name) / "volume"
        volume.mkdir()
        (volume / "warpgate.yaml").write_text("external_host: old\nhttp:\n  listen: 0.0.0.0:8888\n")
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        settings = Path(self.tmp.name) / "oidc.json"
        settings.write_text(json.dumps({"entries": [{"mode": "manual", "issuer": "https://id.example.org/r",
                                                     "client_id": "c", "secret": "oidc-secret"}]}))
        with mock.patch.object(warpgate_oidc, "SETTINGS", settings):
            warpgate_oidc.render(volume, "warpgate.example.org")
        rendered = (volume / ".ns8-warpgate.yaml").read_text()
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn("AKIAEXAMPLE", rendered)
        self.assertNotIn("recordings", rendered)
        # Local storage without OIDC: the source file itself is used
        settings.write_text(json.dumps({"entries": []}))
        with mock.patch.object(warpgate_oidc, "SETTINGS", settings):
            warpgate_oidc.render(volume, "warpgate.example.org")
        self.assertTrue((volume / ".ns8-warpgate.yaml").is_symlink())


class PeerMaterialTest(StateTestCase):
    def test_local_peer(self):
        self.assertEqual(wr.peer_material(), {"storage": "local"})

    def test_s3_travels_with_admit_peer(self):
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        material = wr.peer_material()
        self.assertEqual(material["secret_access_key"], SECRET)
        self.assertEqual(material["bucket"], "warpgate-recordings")
        # The joining member, in another state directory
        joiner = tempfile.TemporaryDirectory()
        self.addCleanup(joiner.cleanup)
        for key in list(os.environ):
            if key.startswith(("WARPGATE_S3_", "WARPGATE_RECORDINGS")):
                del os.environ[key]
        with mock.patch.dict(os.environ, {"AGENT_STATE_DIR": joiner.name}):
            self.assertTrue(wr.install_from_peer(json.loads(json.dumps(material))))
            cur = wr.settings()
            self.assertEqual(cur["storage"], "s3")
            self.assertEqual(cur["endpoint"], "https://s3.example.org:9000")
            self.assertTrue(cur["secret_access_key_set"])
            self.assertEqual(wr.secret_key(), SECRET)
            self.assertEqual(stat.S_IMODE(os.stat(Path(joiner.name) / wr.S3_ENV).st_mode), 0o600)
            # A joined member does not write the shared parameters row
            self.assertFalse(wr.needs_admin_api(cluster_mode="join"))

    def test_older_peer_or_bad_material(self):
        self.assertFalse(wr.install_from_peer(None))
        self.assertFalse(wr.install_from_peer({}))
        with self.assertRaises(wc.ClusterError) as ctx:
            wr.install_from_peer({"storage": "s3", "bucket": "Bad_Bucket", "region": "x", "access_key_id": "a",
                                  "secret_access_key": "b"})
        self.assertEqual(ctx.exception.code, "invalid_peer_recordings")
        self.assertTrue(wr.install_from_peer({"storage": "local"}))
        self.assertEqual(os.environ["WARPGATE_RECORDINGS_STORAGE"], "local")

    def test_admit_peer_output(self):
        """Run the admit-peer action step with a fake agent and Redis"""
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        os.environ.update({"WARPGATE_DB_MODE": "postgresql19c", "WARPGATE_CLUSTER_MODE": "create",
                           "WARPGATE_DB_NAME": "warpgate1", "WARPGATE_DB_CLUSTER_ID": "postgresql19c1",
                           "AGENT_TASK_USER": "module/warpgate2"})
        self.agent.redis_connect = lambda **kw: object()
        self.agent.SD_ERR = ""
        script = Path(__file__).resolve().parents[1] / "imageroot/actions/admit-peer/20admit"
        out = mock.MagicMock()
        stdin = types.SimpleNamespace(read=lambda: json.dumps({"module_id": "warpgate2"}))
        with mock.patch.object(wc, "authorize_peer", return_value="warpgate2"), \
                mock.patch.object(wc, "shared_material", return_value={"encryption_key": "k"}), \
                mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", out):
            code = compile(script.read_text(), str(script), "exec")
            exec(code, {"__name__": "__main__"})  # noqa: S102 - the action step under test
        written = "".join(call.args[0] for call in out.write.call_args_list)
        output = json.loads(written)
        self.assertEqual(output["database"], "warpgate1")
        self.assertEqual(output["recordings"]["storage"], "s3")
        self.assertEqual(output["recordings"]["secret_access_key"], SECRET)
        schema = json.loads((script.parent / "validate-output.json").read_text())
        self.assertIn("recordings", schema["properties"])


class SigV4Test(unittest.TestCase):
    def test_aws_get_vanilla_vector(self):
        # aws-sig-v4-test-suite, get-vanilla
        headers = {"host": "example.amazonaws.com", "x-amz-date": "20150830T123600Z"}
        auth = wr.sign_v4("GET", "example.amazonaws.com", "/", [], headers, wr.EMPTY_SHA256, "AKIDEXAMPLE",
                          "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY", "us-east-1", "service", "20150830T123600Z")
        self.assertEqual(auth, "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, "
                               "SignedHeaders=host;x-amz-date, "
                               "Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31")

    def test_bucket_url(self):
        want = {"endpoint": "https://s3.example.org:9000/", "region": "eu-west-1", "bucket": "rec",
                "path_style": True}
        self.assertEqual(wr.bucket_url(want), ("https", "s3.example.org:9000", "/rec"))
        self.assertEqual(wr.bucket_url(dict(want, path_style=False)), ("https", "rec.s3.example.org:9000", "/"))
        self.assertEqual(wr.bucket_url(dict(want, endpoint="")), ("https", "s3.eu-west-1.amazonaws.com", "/rec"))


class FakeS3Handler(http.server.BaseHTTPRequestHandler):
    secret = SECRET
    seen = []

    def do_HEAD(self):  # noqa: N802
        headers = {k.lower(): v for k, v in self.headers.items()}
        type(self).seen.append((self.path, headers.get("host")))
        signed = {k: headers[k] for k in ("host", "x-amz-date", "x-amz-content-sha256")}
        expected = wr.sign_v4("HEAD", headers["host"], self.path, [], signed, headers["x-amz-content-sha256"],
                              "AKIAEXAMPLE", type(self).secret, "us-east-1", "s3", headers["x-amz-date"])
        if self.path != "/warpgate-recordings":
            self.send_response(404)
        elif headers.get("authorization") != expected:
            self.send_response(403)
        else:
            self.send_response(200)
        self.end_headers()

    def log_message(self, *_args):
        pass


class BucketTestTest(unittest.TestCase):
    def setUp(self):
        self.server = http.server.HTTPServer(("127.0.0.1", 0), FakeS3Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        FakeS3Handler.seen = []
        port = self.server.server_address[1]
        self.want = {"endpoint": f"http://127.0.0.1:{port}", "region": "us-east-1", "bucket": "warpgate-recordings",
                     "path_style": True, "access_key_id": "AKIAEXAMPLE"}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_signed_head_bucket(self):
        result = wr.test_bucket(self.want, SECRET)
        self.assertEqual(result, {"ok": True, "error": "", "status": 200})
        self.assertEqual(FakeS3Handler.seen[0][1], self.want["endpoint"].split("//")[1])
        self.assertEqual(wr.test_bucket(self.want, "wrong")["error"], "s3_access_denied")
        self.assertEqual(wr.test_bucket(dict(self.want, bucket="other-bucket"), SECRET)["error"],
                         "s3_bucket_not_found")
        self.assertNotIn(SECRET, json.dumps(result))

    def test_unreachable(self):
        result = wr.test_bucket(dict(self.want, endpoint="http://127.0.0.1:9"), SECRET, timeout=2)
        self.assertEqual(result["error"], "s3_unreachable")

    def test_fixed_clock(self):
        now = datetime.datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        self.assertTrue(wr.test_bucket(self.want, SECRET, now=now)["ok"])


class AdminApiTest(StateTestCase):
    def test_run_args(self):
        self.assertEqual(warpgate_api.run_args(False), "")
        self.assertFalse(self.path(warpgate_api.ADMIN_TOKEN_ENV).exists())
        self.assertEqual(warpgate_api.run_args(True), "--enable-admin-token")
        self.assertEqual(self.mode(warpgate_api.ADMIN_TOKEN_ENV), 0o600)
        token = warpgate_api.admin_token()
        self.assertGreaterEqual(len(token), 40)
        self.assertEqual(warpgate_api.run_args(True), "--enable-admin-token")
        self.assertEqual(warpgate_api.admin_token(), token)  # stable across restarts

    def test_request_needs_token(self):
        with self.assertRaises(warpgate_api.ApiError):
            warpgate_api.request("/parameters")


class SecretBackendTest(StateTestCase):
    VAULT = {"vault_enabled": True, "vault_mode": "provisioned", "vault_openbao": "openbao1",
             "vault_address": "http://10.5.4.1:20003", "vault_token_set": True, "vault_mount": "ns8-kv",
             "vault_path": "modules/warpgate1"}

    def provisioned(self):
        os.environ.update({"WARPGATE_VAULT_ENABLED": "1", "WARPGATE_VAULT_MODE": "provisioned",
                           "WARPGATE_VAULT_OPENBAO": "openbao1", "WARPGATE_VAULT_MOUNT": "ns8-kv",
                           "WARPGATE_VAULT_PATH": "modules/warpgate1"})
        wc.write_envfile(self.path(wc.OPENBAO_ENV), {"VAULT_ADDR": "http://10.5.4.1:20003",
                                                     "VAULT_TOKEN": "module-token", "VAULT_TOKEN_ISSUED": "100"})

    def code(self, request, vault=None, cluster_mode="standalone"):
        want = wsb.requested({"secret_backend": request}, wsb.settings())
        with self.assertRaises(wc.ClusterError) as ctx:
            wsb.validate(want, vault or self.VAULT, cluster_mode)
        return ctx.exception.code

    def test_default_off(self):
        cur = wsb.settings()
        self.assertEqual(cur["mode"], "off")
        self.assertFalse(wsb.needs_admin_api(cur))
        wsb.validate(wsb.requested({}, cur), {"vault_enabled": False, "vault_mode": "manual"}, "standalone")

    def test_validation(self):
        no_vault = dict(self.VAULT, vault_enabled=False)
        self.assertEqual(self.code({"mode": "managed"}, no_vault), "secret_backend_requires_provisioning")
        self.assertEqual(self.code({"mode": "managed"}, dict(self.VAULT, vault_mode="manual")),
                         "secret_backend_requires_provisioning")
        self.assertEqual(self.code({"mode": "managed"}, cluster_mode="join"), "secret_backend_managed_by_creator")
        self.assertEqual(self.code({"mode": "manual", "name": "bad name"}), "secret_backend_invalid_name")
        self.assertEqual(self.code({"mode": "managed", "scope": "group", "group": "warpgate1"}),
                         "secret_backend_invalid_group")
        wsb.validate(wsb.requested({"secret_backend": {"mode": "manual"}}, wsb.settings()),
                     dict(self.VAULT, vault_enabled=False), "join")

    def test_manual_info_has_no_secret(self):
        self.provisioned()
        wsb.save(wsb.requested({"secret_backend": {"mode": "manual"}}, wsb.settings()))
        info = wsb.info()
        self.assertEqual(info["address"], "http://10.5.4.1:20003")
        self.assertEqual(info["allowed_path"], "ns8-kv/modules/warpgate1/targets")
        self.assertEqual(info["reference_example"],
                         "secret://ns8-openbao/ns8-kv/modules/warpgate1/targets/<target>#password")
        self.assertIn('path "ns8-kv/data/modules/warpgate1/targets/*"', info["policy"])
        self.assertNotIn("module-token", json.dumps(info))
        # Without OpenBao settings: the ns8-openbao layout as a template
        for key in list(os.environ):
            if key.startswith("WARPGATE_VAULT"):
                del os.environ[key]
        self.assertEqual(wsb.info()["allowed_path"], "ns8-kv/modules/warpgate1/targets")
        self.assertEqual(wsb.info()["address"], "")

    def test_group_scope(self):
        self.provisioned()
        wsb.save({"mode": "managed", "name": "bao", "scope": "group", "group": "warpgate-cluster"})
        self.assertEqual(wsb.allowed_path(), "ns8-kv/groups/warpgate-cluster")
        self.assertEqual(wsb.token_for(wsb.settings()), "")
        with self.assertRaises(wc.ClusterError) as ctx:
            wsb.apply(FakeApi())
        self.assertEqual(ctx.exception.code, "secret_backend_group_not_approved")

    def test_managed_register_update_refresh(self):
        self.provisioned()
        wsb.save(wsb.requested({"secret_backend": {"mode": "managed"}}, wsb.settings()))
        self.assertTrue(wsb.needs_admin_api())
        self.assertFalse(wsb.needs_admin_api(cluster_mode="join"))
        self.assertEqual(wsb.warnings(wsb.settings()),
                         ["secret_backend_module_scope", "secret_backend_without_encryption_key"])
        api = FakeApi()
        self.assertTrue(wsb.apply(api))
        method, path, body = api.writes()[0]
        self.assertEqual((method, path), ("POST", "/secret-backends"))
        self.assertEqual(body, {"name": "ns8-openbao", "backend_type": "openbao", "address": "http://10.5.4.1:20003",
                                "namespace": None, "auth": {"method": "Token", "token": "module-token"},
                                "tls_skip_verify": False, "allowed_paths": ["ns8-kv/modules/warpgate1/targets"]})
        # Warpgate lists it with the token redacted: nothing to do
        api.backends = [dict(body, id="b-1", auth={"method": "Token", "token": ""})]
        api.calls.clear()
        self.assertFalse(wsb.apply(api))
        self.assertEqual(api.writes(), [])
        # A new token (provisioned again by the timer) is pushed
        wc.write_envfile(self.path(wc.OPENBAO_ENV), {"VAULT_ADDR": "http://10.5.4.1:20003",
                                                     "VAULT_TOKEN": "new-token", "VAULT_TOKEN_ISSUED": "200"})
        self.assertTrue(wsb.apply(api))
        method, path, body = api.writes()[-1]
        self.assertEqual((method, path), ("PUT", "/secret-backends/b-1"))
        self.assertEqual(body["auth"]["token"], "new-token")
        # A joined member never touches the shared row
        api.calls.clear()
        self.assertFalse(wsb.apply(api, "join"))
        self.assertEqual(api.calls, [])


class GroupTokensTest(StateTestCase):
    def test_provision_saves_group_tokens(self):
        output = {"address": "http://10.5.4.1:20003", "wrapped_token": "w", "wrap_creation_path":
                  "auth/token/create/ns8-client", "kv_mount": "ns8-kv", "kv_prefix": "modules/warpgate1",
                  "groups": [{"group_id": "warpgate-cluster", "kv_prefix": "groups/warpgate-cluster",
                              "wrapped_token": "wg"},
                             {"group_id": "bad-wrap", "kv_prefix": "groups/bad-wrap", "wrapped_token": "wb"}]}
        tasks = types.SimpleNamespace(run=lambda **kw: {"exit_code": 0, "output": output})
        self.agent.tasks = tasks

        def bao(address, path, method="GET", token="", data=None, timeout=8):
            if path == "sys/wrapping/lookup":
                ok = data["token"] != "wb"
                return {"data": {"creation_path": "auth/token/create/ns8-client" if ok else "other"}}
            return {"auth": {"client_token": {"w": "tok", "wg": "group-tok"}[token]}}

        with mock.patch.dict(sys.modules, {"agent.tasks": tasks}), \
                mock.patch.object(wc, "bao_request", side_effect=bao):
            self.assertEqual(wc.provision("openbao1")[1], "tok")
        self.assertEqual(wc.read_group_tokens(), {"warpgate-cluster": {"token": "group-tok",
                                                                       "kv_prefix": "groups/warpgate-cluster"}})
        self.assertEqual(self.mode(wc.OPENBAO_GROUPS), 0o600)

    def test_s3_secret_is_mirrored(self):
        wr.save(wr.requested(self.s3_request(), wr.settings()))
        items = wc.secret_items()
        self.assertEqual(json.loads(items["s3"]), {"access_key_id": "AKIAEXAMPLE", "secret_access_key": SECRET})


if __name__ == "__main__":
    unittest.main()
