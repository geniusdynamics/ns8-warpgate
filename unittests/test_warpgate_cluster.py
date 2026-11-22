# SPDX-License-Identifier: GPL-3.0-or-later
# Run: python3 -m unittest discover -s unittests

import base64
import json
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "imageroot" / "pypkg"))
import warpgate_cluster as wc  # noqa: E402

KEY_A = base64.b64encode(b"a" * 32).decode()
KEY_B = base64.b64encode(b"b" * 32).decode()


class FakeRedis:
    def __init__(self, hashes=None, strings=None):
        self.hashes = hashes or {}
        self.strings = strings or {}

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def hmget(self, key, fields):
        return [self.hget(key, f) for f in fields]

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def get(self, key):
        return self.strings.get(key)


def cluster_redis():
    return FakeRedis({
        "cluster/module_uuid": {"warpgate1": "uuid-1", "warpgate2": "uuid-2", "kumomta1": "uuid-k"},
        "cluster/module_node": {"warpgate1": "1", "warpgate2": "2", "kumomta1": "1"},
        "module/warpgate1/environment": {"IMAGE_URL": "ghcr.io/geniusdynamics/warpgate:1.3.0"},
        "module/warpgate2/environment": {"IMAGE_URL": "ghcr.io/geniusdynamics/warpgate:1.3.0"},
        "module/kumomta1/environment": {"IMAGE_URL": "ghcr.io/geniusdynamics/kumomta:1.0.0"},
        "node/1/vpn": {"ip_address": "10.5.4.1"},
    })


RECORDS = [
    {"module_id": "postgresql19c1", "node": "1", "host": "10.5.4.1", "port": 20005, "cluster_id": "postgresql19c1"},
    {"module_id": "postgresql19c2", "node": "2", "host": "10.5.4.2", "port": 20005, "cluster_id": "postgresql19c1"},
    {"module_id": "postgresql19c3", "node": "2", "host": "10.5.4.2", "port": 20009, "cluster_id": "postgresql19c3"},
]


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {
            "AGENT_STATE_DIR": self.tmp.name, "MODULE_ID": "warpgate1", "NODE_ID": "1",
            "IMAGE_URL": "ghcr.io/geniusdynamics/warpgate:1.3.0"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def mode(self, name):
        return stat.S_IMODE(os.stat(Path(self.tmp.name) / name).st_mode)


class PickRecordTest(unittest.TestCase):
    def test_prefers_same_node(self):
        self.assertEqual(wc.pick_record(RECORDS, "2")["module_id"], "postgresql19c2")

    def test_falls_back_to_first(self):
        self.assertEqual(wc.pick_record(RECORDS, "9")["module_id"], "postgresql19c1")

    def test_cluster_filter(self):
        self.assertEqual(wc.pick_record(RECORDS, "2", "postgresql19c3")["module_id"], "postgresql19c3")
        self.assertEqual(wc.pick_record(RECORDS, "1", "postgresql19c1")["module_id"], "postgresql19c1")

    def test_preferred(self):
        self.assertEqual(wc.pick_record(RECORDS, "1", preferred="postgresql19c3")["module_id"], "postgresql19c3")
        self.assertIsNone(wc.pick_record(RECORDS, "1", preferred="postgresql19c7"))

    def test_preferred_outside_cluster_falls_back(self):
        self.assertEqual(wc.pick_record(RECORDS, "2", "postgresql19c1", "postgresql19c3")["module_id"],
                         "postgresql19c2")


class DatabaseUrlTest(unittest.TestCase):
    def test_no_password(self):
        url = wc.database_url({"WARPGATE_DB_USER": "warpgate1", "WARPGATE_DB_NAME": "warpgate1",
                               "WARPGATE_DB_HOST": "10.5.4.1", "WARPGATE_DB_PORT": "20005"})
        self.assertEqual(url, "postgres://warpgate1@10.5.4.1:20005/warpgate1?sslmode=disable&connect_timeout=5")

    def test_ipv6(self):
        url = wc.database_url({"WARPGATE_DB_USER": "u", "WARPGATE_DB_NAME": "d",
                               "WARPGATE_DB_HOST": "fd00::1", "WARPGATE_DB_PORT": "5432"})
        self.assertIn("@[fd00::1]:5432/", url)

    def test_database_name(self):
        self.assertEqual(wc.database_name_for("warpgate12"), "warpgate12")
        self.assertEqual(wc.database_name_for("my-app2"), "my_app2")


class ClusterArgsTest(unittest.TestCase):
    def test_standalone(self):
        self.assertEqual(wc.cluster_args("standalone", "10.5.4.1", "20001"), "")

    def test_member(self):
        self.assertEqual(wc.cluster_args("join", "10.5.4.1", "20001"),
                         "--publish=10.5.4.1:20001:8888 --env=WARPGATE_PEER_ADDRESS=10.5.4.1:20001")

    def test_vpn_ip(self):
        self.assertEqual(wc.vpn_ip(cluster_redis(), "1"), "10.5.4.1")
        self.assertEqual(wc.vpn_ip(cluster_redis(), "2"), "")


class ValidateTest(StateTestCase):
    def cur(self, **kw):
        base = {"db_mode": "embedded", "db_instance": "", "cluster_mode": "standalone", "cluster_peer": ""}
        base.update(kw)
        return base

    def check(self, request, cur, records=RECORDS):
        want = wc.requested(request, dict(self.cur(), **cur))
        wc.validate(want, dict(self.cur(), **cur), records, request)

    def assertCode(self, code, request, cur=None, records=RECORDS):
        with self.assertRaises(wc.ClusterError) as ctx:
            self.check(request, cur or {}, records)
        self.assertEqual(ctx.exception.code, code)

    def test_unchanged_request(self):
        self.check({"host": "a.example.org"}, {})

    def test_no_downgrade(self):
        self.assertCode("cannot_switch_to_embedded", {"database": {"mode": "embedded"}}, {"db_mode": "postgresql19c"})

    def test_cluster_needs_postgresql(self):
        self.assertCode("cluster_requires_postgresql", {"cluster": {"mode": "create"}})

    def test_join_needs_peer(self):
        self.assertCode("invalid_peer", {"database": {"mode": "postgresql19c"}, "cluster": {"mode": "join"}})
        self.assertCode("invalid_peer", {"database": {"mode": "postgresql19c"},
                                         "cluster": {"mode": "join", "peer": "warpgate1"}})

    def test_creator_cannot_join(self):
        self.assertCode("cannot_join_from_create",
                        {"cluster": {"mode": "join", "peer": "warpgate2"}},
                        {"db_mode": "postgresql19c", "cluster_mode": "create"})

    def test_instances(self):
        self.assertCode("no_postgresql19c_instance", {"database": {"mode": "postgresql19c"}}, records=[])
        self.assertCode("postgresql19c_instance_not_found",
                        {"database": {"mode": "postgresql19c", "instance": "postgresql19c9"}})
        self.check({"database": {"mode": "postgresql19c", "instance": "postgresql19c2"},
                    "cluster": {"mode": "join", "peer": "warpgate2"}}, {})

    def test_vault(self):
        self.assertCode("required", {"vault_enabled": True, "vault_mode": "provisioned"})
        self.assertCode("invalid_url", {"vault_enabled": True, "vault_address": "ftp://x", "vault_token": "t"})
        self.assertCode("required", {"vault_enabled": True, "vault_address": "https://bao.example.org"})
        self.check({"vault_enabled": True, "vault_address": "https://bao.example.org", "vault_token": "t"}, {})
        self.check({"vault_enabled": True, "vault_mode": "provisioned", "vault_openbao": "openbao1"}, {})


class CredentialsTest(StateTestCase):
    def test_store_credentials_private(self):
        out = {"password": "f" * 64, "host": "10.5.4.2", "port": 20005, "database": "warpgate1",
               "username": "warpgate1", "cluster_id": "postgresql19c1"}
        values = wc.store_credentials(out, RECORDS, "1")
        self.assertEqual(self.mode("database.env"), 0o600)
        self.assertEqual(wc.database_password(), "f" * 64)
        # The endpoint of the same cluster on this node wins
        self.assertEqual(values["WARPGATE_DB_HOST"], "10.5.4.1")
        self.assertNotIn("f" * 64, json.dumps(values))

    def test_envfile_rejects_newlines(self):
        with self.assertRaises(ValueError):
            wc.write_envfile(Path(self.tmp.name) / "x.env", {"A": "1\nB=2"})


class PeerAccessTest(StateTestCase):
    def test_approval_bound_to_uuid(self):
        rdb = cluster_redis()
        wc.set_peer_access(rdb, "warpgate2", True)
        self.assertEqual(self.mode("peer-access.json"), 0o600)
        self.assertEqual(wc.authorize_peer(rdb, "warpgate2", "module/warpgate2"), "warpgate2")
        # Reinstalled with the same ID: new UUID, approval no longer valid
        rdb.hashes["cluster/module_uuid"]["warpgate2"] = "uuid-new"
        with self.assertRaises(wc.ClusterError) as ctx:
            wc.authorize_peer(rdb, "warpgate2", "module/warpgate2")
        self.assertEqual(ctx.exception.code, "peer_not_approved")

    def test_caller_identity(self):
        rdb = cluster_redis()
        wc.set_peer_access(rdb, "warpgate2", True)
        for user in ("module/warpgate3", "admin", ""):
            with self.assertRaises(wc.ClusterError) as ctx:
                wc.authorize_peer(rdb, "warpgate2", user)
            self.assertEqual(ctx.exception.code, "peer_not_authorized")

    def test_only_warpgate_instances(self):
        rdb = cluster_redis()
        for peer in ("kumomta1", "warpgate1", "warpgate9"):
            with self.assertRaises(wc.ClusterError):
                wc.set_peer_access(rdb, peer, True)

    def test_revoke_and_candidates(self):
        rdb = cluster_redis()
        wc.set_peer_access(rdb, "warpgate2", True)
        self.assertEqual(wc.peer_candidates(rdb),
                         [{"module_id": "warpgate2", "node": "2", "allowed": True, "ui_name": ""}])
        wc.set_peer_access(rdb, "warpgate2", False)
        self.assertEqual(wc.approved_peers(rdb), set())


class MaterialTest(StateTestCase):
    def test_roundtrip(self):
        wc.write_envfile(Path(self.tmp.name) / "encryption.env",
                         {"WARPGATE_ENCRYPTION_KEY": KEY_A, "WARPGATE_ENCRYPTION_KEY_OLD": KEY_B})
        pem = {"tls.certificate.pem": "-----BEGIN CERTIFICATE-----\nX\n", "tls.key.pem": "-----BEGIN KEY-----\nY\n"}
        with mock.patch.object(wc, "read_volume_file", side_effect=pem.get):
            material = wc.shared_material()
        self.assertEqual(material["encryption_key"], KEY_A)
        self.assertEqual(material["encryption_key_old"], KEY_B)
        other = tempfile.TemporaryDirectory()
        with mock.patch.dict(os.environ, {"AGENT_STATE_DIR": other.name}):
            wc.install_material(material)
            self.assertEqual(wc.read_keyring_values(),
                             {"WARPGATE_ENCRYPTION_KEY": KEY_A, "WARPGATE_ENCRYPTION_KEY_OLD": KEY_B})
            self.assertEqual(wc.read_shared_tls()["key"], "-----BEGIN KEY-----\nY\n")
            for name in ("encryption.env", "cluster-tls.json"):
                self.assertEqual(stat.S_IMODE(os.stat(Path(other.name) / name).st_mode), 0o600)
            volume = tempfile.TemporaryDirectory()
            (Path(volume.name) / "warpgate.yaml").write_text("x: 1\n")
            self.assertTrue(wc.install_tls_into_volume(volume.name))
            self.assertFalse(wc.install_tls_into_volume(volume.name))
            volume.cleanup()
        other.cleanup()

    def test_rejects_bad_keys(self):
        with self.assertRaises(wc.ClusterError):
            wc.install_material({"encryption_key": "not-a-key"})
        with self.assertRaises(wc.ClusterError):
            wc.install_material({"tls_certificate": "x", "tls_key": "y"})


class VaultTest(StateTestCase):
    def test_secret_items_and_push(self):
        wc.write_envfile(Path(self.tmp.name) / "database.env", {"PGPASSWORD": "p" * 64})
        (Path(self.tmp.name) / "oidc.json").write_text(json.dumps({"entries": [
            {"mode": "manual", "issuer": "https://i", "client_id": "c", "secret": "s"}]}))
        items = wc.secret_items()
        self.assertEqual(set(items), {"database", "oidc"})
        self.assertEqual(json.loads(items["database"])["password"], "p" * 64)
        store = {}

        class FakeVault:
            def get(self, name):
                return store.get(name)

            def set(self, name, value):
                store[name] = value

        with mock.patch.dict(os.environ, {"WARPGATE_VAULT_ENABLED": "1"}), \
                mock.patch.object(wc, "make_vault", return_value=FakeVault()):
            self.assertEqual(wc.push_secrets(), [])
        self.assertEqual(set(store), {"database", "oidc"})

    def test_push_disabled_or_unavailable(self):
        self.assertEqual(wc.push_secrets(), [])
        wc.write_envfile(Path(self.tmp.name) / "database.env", {"PGPASSWORD": "p"})

        class Down:
            def get(self, name):
                raise wc.OpenBaoError(503)

        with mock.patch.dict(os.environ, {"WARPGATE_VAULT_ENABLED": "1"}), \
                mock.patch.object(wc, "make_vault", return_value=Down()):
            self.assertEqual(wc.push_secrets(), ["database"])

    def test_provision_checks_wrapping(self):
        output = {"address": "http://10.5.4.1:20003", "wrapped_token": "w", "wrap_creation_path":
                  "auth/token/create/ns8-client", "kv_mount": "ns8-kv", "kv_prefix": "modules/warpgate1"}
        tasks = types.SimpleNamespace(run=lambda **kw: {"exit_code": 0, "output": output})
        calls = []

        def bao(address, path, method="GET", token="", data=None, timeout=8):
            calls.append(path)
            if path == "sys/wrapping/lookup":
                return {"data": {"creation_path": lookup_path}}
            return {"auth": {"client_token": "tok"}}

        agent_mod = types.ModuleType("agent")
        agent_mod.tasks = tasks
        with mock.patch.dict(sys.modules, {"agent": agent_mod, "agent.tasks": tasks}), \
                mock.patch.object(wc, "bao_request", side_effect=bao):
            lookup_path = "auth/token/create/ns8-client"
            self.assertEqual(wc.provision("openbao1"), ("http://10.5.4.1:20003", "tok", "ns8-kv", "modules/warpgate1"))
            lookup_path = "sys/other"
            calls.clear()
            with self.assertRaises(wc.ClusterError) as ctx:
                wc.provision("openbao1")
            self.assertEqual(ctx.exception.code, "openbao_wrapping_mismatch")
            self.assertNotIn("sys/wrapping/unwrap", calls)


if __name__ == "__main__":
    unittest.main()
