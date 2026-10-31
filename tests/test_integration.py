"""End-to-end tests: real HTTP mock trackers + fake Telegram Bot API server.

Exercises the full cycle fetch -> check -> state -> Telegram alert/recovery
with real aiogram calls hitting a local fake Telegram server.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from domain_checker.config import Config
from domain_checker.scheduler import DomainCheckScheduler

KEY = "secret-key"
SENT = []  # messages received by fake Telegram
SEEN = []  # tracker requests (path, headers)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj, ctype="application/json"):
        body = json.dumps(obj).encode() if not isinstance(obj, bytes) else obj
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        SEEN.append((u.path, dict(self.headers), parse_qs(u.query)))
        if u.path == "/admin_api/v1/domains":
            if self.headers.get("Api-Key") != KEY:
                return self._json(401, {"error": "unauthorized"})
            return self._json(
                200,
                [
                    {"id": 1, "name": "alive.test", "state": "active"},
                    {"id": 2, "name": "https://dead.test/", "state": "active"},
                ],
            )
        if u.path == "/public/api/v1/domain/list/all":
            if self.headers.get("api-key") != KEY:
                return self._json(403, {"error": "forbidden"})
            return self._json(
                200,
                [{"id": 7, "name": "binom-a.test"}, {"id": 8, "name": "binom-b.test"}],
            )
        if u.path == "/legacy/api.php":
            if parse_qs(u.query).get("api_key") != [KEY]:
                return self._json(403, {})
            return self._json(200, {"domains": [{"domain": "legacy.test"}]})
        if u.path == "/custom/json":
            if self.headers.get("Authorization") != f"Bearer {KEY}":
                return self._json(401, {})
            return self._json(
                200, {"data": {"domains": ["c1.test", {"url": "http://c2.test/x"}]}}
            )
        if u.path == "/custom/text":
            if self.headers.get("X-Token") != KEY:
                return self._json(401, {})
            return self._json(200, b"t1.test\nt2.test\n\n# comment\n", "text/plain")
        if u.path == "/broken":
            return self._json(500, {"error": "boom"})
        self._json(404, {})

    def do_POST(self):
        # fake Telegram Bot API: /bot<token>/sendMessage
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode(errors="replace")
        if self.path.endswith("/sendMessage"):
            SENT.append(raw)
            return self._json(
                200,
                {
                    "ok": True,
                    "result": {
                        "message_id": len(SENT),
                        "date": 0,
                        "chat": {"id": 42, "type": "private"},
                        "text": "x",
                    },
                },
            )
        self._json(404, {"ok": False, "description": "not found"})


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def make_config(tmp_path, tracker, url, **extra):
    cfg = Config(tmp_path / "none.yaml")
    d = {
        "tracker": {
            "type": tracker,
            "url": url,
            "api_key": KEY,
            **extra.pop("tracker_extra", {}),
        },
        "telegram": {"bot_token": "123:ABC", "chat_id": 42},
        "checker": {
            "interval_minutes": extra.pop("interval", 30),
            "consecutive_failures_threshold": 2,
            "ssl_warning_days": 7,
            "max_concurrent_checks": 5,
            "request_timeout_seconds": 3,
        },
        "database": {"path": str(tmp_path / "db.sqlite")},
    }
    cfg.update(d)
    return cfg


def fake_tg(sched, base):
    session = AiohttpSession(api=TelegramAPIServer.from_base(base))
    sched.notifier.bot = Bot(token="123:ABC", session=session)


@pytest.mark.asyncio
async def test_sources_against_mock_servers(server, tmp_path):
    from domain_checker.sources import BinomSource, CustomSource, KeitaroSource

    assert await KeitaroSource(server, KEY).fetch_domains() == [
        "alive.test",
        "dead.test",
    ]
    assert await BinomSource(server, KEY).fetch_domains() == [
        "binom-a.test",
        "binom-b.test",
    ]
    # legacy Binom v1 fallback (v2 paths 404 under /legacy)
    assert await BinomSource(server + "/legacy", KEY).fetch_domains() == ["legacy.test"]
    assert await CustomSource(
        server + "/custom/json", KEY, domains_path="data.domains"
    ).fetch_domains() == ["c1.test", "c2.test"]
    assert await CustomSource(
        server + "/custom/text", KEY, header_name="X-Token"
    ).fetch_domains() == ["t1.test", "t2.test"]
    with pytest.raises((httpx.HTTPStatusError, httpx.HTTPError)):
        await KeitaroSource(server, "wrong").fetch_domains()


@pytest.mark.asyncio
async def test_full_cycle_alert_and_recovery(server, tmp_path, monkeypatch):
    SENT.clear()
    sched = DomainCheckScheduler(make_config(tmp_path, "keitaro", server))
    await sched.initialize()
    fake_tg(sched, server)

    health = {"alive.test": "up", "dead.test": "down"}

    async def fake_check(domain):
        return {
            "domain": domain,
            "status": health[domain],
            "dns_resolved": True,
            "http_code": 200 if health[domain] == "up" else 502,
            "response_time_ms": 10,
            "ssl_valid": True,
            "ssl_days_remaining": 90,
            "error_message": None if health[domain] == "up" else "HTTP 502",
        }

    monkeypatch.setattr(sched.checker, "check_domain", fake_check)

    await sched.check_all_domains()  # failure 1 -> no alert yet
    assert SENT == []
    await sched.check_all_domains()  # failure 2 -> alert
    assert len(SENT) == 1 and "dead.test" in SENT[0]
    await sched.check_all_domains()  # failure 3 -> no repeat spam
    assert len(SENT) == 1
    health["dead.test"] = "up"
    await sched.check_all_domains()  # recovery message
    assert len(SENT) == 2 and "dead.test" in SENT[1]

    # single blip after recovery must NOT produce an alert or a recovery message
    health["dead.test"] = "down"
    await sched.check_all_domains()
    health["dead.test"] = "up"
    await sched.check_all_domains()
    assert len(SENT) == 2

    state = await sched.storage.get_domain_state("dead.test")
    assert state["consecutive_failures"] == 0
    await sched.notifier.close()


@pytest.mark.asyncio
async def test_tracker_outage_notifies_once(server, tmp_path):
    SENT.clear()
    sched = DomainCheckScheduler(make_config(tmp_path, "custom", server + "/broken"))
    await sched.initialize()
    fake_tg(sched, server)
    await sched.check_all_domains()
    await sched.check_all_domains()
    assert len(SENT) == 1
    await sched.notifier.close()


@pytest.mark.asyncio
async def test_ssl_warning_once_per_day(server, tmp_path, monkeypatch):
    SENT.clear()
    sched = DomainCheckScheduler(make_config(tmp_path, "keitaro", server))
    await sched.initialize()
    fake_tg(sched, server)

    async def fake_check(domain):
        return {
            "domain": domain,
            "status": "up",
            "dns_resolved": True,
            "http_code": 200,
            "ssl_valid": True,
            "ssl_days_remaining": 3,
            "error_message": None,
        }

    monkeypatch.setattr(sched.checker, "check_domain", fake_check)
    await sched.check_all_domains()
    await sched.check_all_domains()
    assert len(SENT) == 2  # one per domain, not per cycle
    await sched.notifier.close()


@pytest.mark.parametrize("minutes", [5, 30, 60, 180])
def test_interval_is_honored(tmp_path, minutes):
    import asyncio

    async def run():
        sched = DomainCheckScheduler(
            make_config(tmp_path, "keitaro", "http://x", interval=minutes)
        )
        sched.start()
        job = sched.scheduler.get_job("domain_check")
        assert job.trigger.interval.total_seconds() == minutes * 60
        assert job.max_instances == 1
        sched.stop()
        await sched.notifier.close()

    asyncio.run(run())


@pytest.mark.asyncio
async def test_migrates_v1_0_database(tmp_path):
    """A DB created by v1.0.x (no is_active/last_seen) must keep working."""
    import sqlite3

    from domain_checker.storage import Storage

    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE domain_state (domain TEXT PRIMARY KEY, last_status TEXT NOT NULL,"
        " consecutive_failures INTEGER DEFAULT 0, last_alert_sent TEXT,"
        " last_recovery_sent TEXT, updated_at TEXT NOT NULL)"
    )
    con.execute(
        "INSERT INTO domain_state VALUES ('a.test','down',3,NULL,NULL,'2026-01-01')"
    )
    con.commit()
    con.close()

    storage = Storage(str(db))
    await storage.initialize()
    await storage.initialize()  # idempotent
    await storage.mark_domains_active(["a.test"])
    await storage.mark_domains_inactive(["a.test"])
    state = await storage.get_domain_state("a.test")
    assert state["consecutive_failures"] == 3
    assert state["is_active"] == 1
