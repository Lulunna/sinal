import json
import os
import sys
import threading
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http.server import HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sinal_core import (canonical_url, clean_html, collect, estimate_cost, is_public_url,  # noqa: E402
                        parse_feed, rank)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)

RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Novo modelo de IA reduz custo</title><link>https://a.com/x?utm_source=tw</link>
<pubDate>Sat, 14 Nov 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;Um &lt;b&gt;LLM&lt;/b&gt; mais barato&lt;/p&gt;</description></item>
<item><title>Notícia velha</title><link>https://a.com/velha</link><pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate></item>
<item><title>Receita de bolo</title><link>https://a.com/bolo</link><pubDate>Sat, 14 Nov 2026 09:00:00 GMT</pubDate><description>Farinha e ovos</description></item>
</channel></rss>""".encode("utf-8")

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Novo modelo de IA reduz custo!</title><link rel="alternate" href="https://b.com/mesma-historia"/>
<updated>2026-11-14T11:00:00Z</updated><summary>Resumo</summary></entry>
<entry><title>Guia de n8n para automação</title><link rel="alternate" href="https://b.com/n8n"/>
<updated>2026-11-14T08:00:00Z</updated><content>Passo a passo de workflow e integração</content></entry>
</feed>""".encode("utf-8")

BOMB = """<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]><rss><channel><item><title>&lol;</title><link>https://x.com</link></item></channel></rss>""".encode("utf-8")


def fake_fetch(url):
    return {"https://a.com/feed": RSS, "https://b.com/feed": ATOM, "https://c.com/bomb": BOMB}[url]


class TestParsing(unittest.TestCase):
    def test_rss_and_atom(self):
        self.assertEqual(len(parse_feed(RSS)), 3)
        a = parse_feed(ATOM)
        self.assertEqual(a[1]["url"], "https://b.com/n8n")
        self.assertIn("workflow", a[1]["text"])

    def test_html_is_cleaned(self):
        self.assertEqual(parse_feed(RSS)[0]["text"], "Um LLM mais barato")
        self.assertEqual(clean_html("<script>x()</script><p>oi&amp;tchau</p>"), "oi&tchau")

    def test_entity_bomb_refused(self):
        with self.assertRaises(ValueError):
            parse_feed(BOMB)

    def test_canonical_url(self):
        self.assertEqual(canonical_url("HTTPS://A.com/x/?utm_source=a&id=2#frag"), "https://a.com/x?id=2")


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.srcs = [{"id": 1, "name": "A", "url": "https://a.com/feed", "topic": "ia"},
                     {"id": 2, "name": "B", "url": "https://b.com/feed", "topic": "geral"},
                     {"id": 3, "name": "C", "url": "https://c.com/bomb", "topic": "x"}]

    def run_collect(self, **kw):
        import sinal_core
        orig = sinal_core.is_public_url
        sinal_core.is_public_url = lambda u: True  # sem DNS no teste
        try:
            return collect({"sources": self.srcs, "since_hours": 48, **kw}, fetcher=fake_fetch, now=NOW)
        finally:
            sinal_core.is_public_url = orig

    def test_drops_old_duplicate_and_bad_feeds(self):
        r = self.run_collect()
        urls = [i["url"] for i in r["items"]]
        self.assertEqual(urls, ["https://a.com/x", "https://a.com/bolo", "https://b.com/n8n"])
        s = r["stats"]
        self.assertEqual((s["dropped_old"], s["dropped_duplicate"], s["feeds_ok"]), (1, 1, 2))
        self.assertEqual(len(s["feeds_failed"]), 1)

    def test_known_urls_are_skipped(self):
        r = self.run_collect(known_urls=["https://a.com/x?utm_medium=z"])
        self.assertNotIn("https://a.com/x", [i["url"] for i in r["items"]])
        self.assertEqual(r["stats"]["dropped_known"], 1)


class TestSecurity(unittest.TestCase):
    def test_private_addresses_blocked(self):
        for u in ["http://127.0.0.1/feed", "http://localhost/x", "http://169.254.169.254/latest", "http://10.0.0.5/a",
                  "file:///etc/passwd", "ftp://x.com/a", "not a url"]:
            self.assertFalse(is_public_url(u), u)


class TestRank(unittest.TestCase):
    INTERESTS = [{"topic": "ia", "weight": 10, "keywords": ["ia", "llm", "inteligência artificial"]},
                 {"topic": "automação", "weight": 8, "keywords": ["n8n", "automação", "workflow"]},
                 {"topic": "brasil", "weight": 5, "keywords": ["pix"]}]

    def test_relevant_beats_irrelevant_and_explains(self):
        items = [{"title": "Receita de bolo", "text": "farinha"},
                 {"title": "Guia de n8n para automação com IA", "text": "workflow com LLM", "source_topic": "ia"}]
        r = rank(items, self.INTERESTS, now=NOW)
        self.assertEqual(r[0]["title"], "Guia de n8n para automação com IA")
        self.assertGreaterEqual(r[0]["score"], 70)
        self.assertEqual(r[1]["score"], 0)
        self.assertEqual(r[0]["best_topic"], "ia")

    def test_word_boundaries_and_accents(self):
        r = rank([{"title": "Diaria da Maria", "text": "politica"}, {"title": "Inteligencia artificial em alta", "text": ""}],
                 self.INTERESTS, now=NOW)
        by = {x["title"]: x["score"] for x in r}
        self.assertEqual(by["Diaria da Maria"], 0)  # 'ia' dentro de palavra não conta
        self.assertGreater(by["Inteligencia artificial em alta"], 0)  # sem acento também acha

    def test_score_is_capped_and_empty_interests_safe(self):
        r = rank([{"title": "ia llm n8n workflow pix automação", "text": "ia llm"}], self.INTERESTS, now=NOW)
        self.assertLessEqual(r[0]["score"], 100)
        self.assertEqual(rank([{"title": "x", "text": "y"}], [], now=NOW)[0]["score"], 0)


class TestCost(unittest.TestCase):
    def test_known_and_unknown_model(self):
        self.assertAlmostEqual(estimate_cost("gemini-2.5-flash", 1_000_000, 1_000_000)["cost_usd"], 2.80)
        r = estimate_cost("modelo-novo", 1000, 500)
        self.assertFalse(r["known_model"])
        self.assertEqual(estimate_cost("gemini-2.5-flash", None, None)["cost_usd"], 0)


class TestHandlers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SINAL_API_KEY"] = "segredo"
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "api"))
        import importlib
        cls.cost = importlib.import_module("cost")
        cls.srv = HTTPServer(("127.0.0.1", 0), cls.cost.handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}/"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def post(self, body, key="segredo", raw=None):
        req = urllib.request.Request(self.url, data=raw if raw is not None else json.dumps(body).encode(),
                                     headers={"x-sinal-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_ok(self):
        st, body = self.post({"model": "gemini-2.5-flash", "input_tokens": 2000, "output_tokens": 300})
        self.assertEqual(st, 200)
        self.assertAlmostEqual(body["cost_usd"], 0.00135)

    def test_batch_cost(self):
        st, body = self.post({"calls": [{"model": "gemini-2.5-flash", "input_tokens": 1000, "output_tokens": 100},
                                         {"model": "gemini-2.5-flash", "input_tokens": 0, "output_tokens": 0}, "lixo"]})
        self.assertEqual(st, 200)
        self.assertEqual(len(body["costs"]), 2)
        self.assertAlmostEqual(body["total"], 0.00055)

    def test_wrong_key_and_bad_json(self):
        self.assertEqual(self.post({}, key="errada")[0], 401)
        self.assertEqual(self.post(None, raw=b"{nao-json")[0], 400)
        self.assertEqual(self.post(None, raw=b"[1,2]")[0], 400)


if __name__ == "__main__":
    unittest.main()
