"""Sinal: lógica em Python (só biblioteca padrão).

Quatro partes, todas chamadas pelo n8n por HTTP:
  - collect: lê feeds RSS/Atom, limpa, tira repetidas e antigas
  - rank:    dá uma nota de relevância (0 a 100) com base nos seus interesses
  - cost:    estima o custo de uma chamada à IA a partir dos tokens
  - segurança: só aceita endereços públicos (evita SSRF)
"""
import html
import ipaddress
import re
import socket
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

USER_AGENT = "Sinal/1.0 (+leitor pessoal de noticias)"
MAX_FEED_BYTES = 2_000_000
FEED_TIMEOUT = 8
MAX_PER_FEED = 15
MAX_TEXT_CHARS = 1500

# Preços de referência em dólar por 1 milhão de tokens (entrada, saída).
# São estimativas: confira a tabela oficial do Google antes de usar para cobrança.
PRICES = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
}
DEFAULT_PRICE = (0.30, 2.50)


# ----------------------------------------------------------------- segurança
def is_public_url(url):
    """True só para http(s) cujo endereço resolve para IP público."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        for info in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80)):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                    or ip.is_multicast or ip.is_unspecified):
                return False
        return True
    except Exception:
        return False


# --------------------------------------------------------------- texto e URLs
def clean_html(raw, limit=MAX_TEXT_CHARS):
    if not raw:
        return ""
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def canonical_url(url):
    p = urlparse((url or "").strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid", "ref", "source")]
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(q), ""))


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_text(s):
    return strip_accents((s or "").lower())


def title_tokens(title):
    return {w for w in re.findall(r"[a-z0-9]{3,}", norm_text(title))}


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        d = parsedate_to_datetime(value)
    except Exception:
        d = None
    if d is None:
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


# ---------------------------------------------------------------------- feeds
def _local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child_text(el, *names):
    for c in el:
        if _local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def parse_feed(xml_bytes):
    """Lê RSS 2.0 ou Atom. Devolve lista de {title, url, published_at, text}."""
    head = xml_bytes[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in xml_bytes[:20000].lower():
        raise ValueError("feed com DTD/entidades foi recusado")
    root = ET.fromstring(xml_bytes)
    out = []
    for el in root.iter():
        name = _local(el.tag)
        if name not in ("item", "entry"):
            continue
        title = clean_html(_child_text(el, "title"), 300)
        link = ""
        if name == "item":
            link = _child_text(el, "link") or _child_text(el, "guid")
        else:
            for c in el:
                if _local(c.tag) == "link" and c.attrib.get("href") and c.attrib.get("rel", "alternate") == "alternate":
                    link = c.attrib["href"]
                    break
        date = parse_date(_child_text(el, "pubDate", "published", "updated", "date"))
        body = _child_text(el, "encoded", "content", "description", "summary")
        if title and link.startswith("http"):
            out.append({
                "title": title,
                "url": link,
                "published_at": date.isoformat() if date else None,
                "text": clean_html(body),
            })
    return out


def fetch_url(url):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, text/xml, */*"})
    with urlopen(req, timeout=FEED_TIMEOUT) as r:
        return r.read(MAX_FEED_BYTES)


def _load_source(src, fetcher):
    url = src.get("url", "")
    if not is_public_url(url):
        return src, [], "endereço não permitido"
    try:
        items = parse_feed(fetcher(url))
        return src, items[:MAX_PER_FEED], None
    except Exception as e:
        return src, [], f"{type(e).__name__}: {str(e)[:120]}"


def collect(payload, fetcher=fetch_url, now=None):
    """payload: {sources:[{id,name,url,topic}], known_urls:[...], since_hours:48}"""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=float(payload.get("since_hours", 48)))
    known = {canonical_url(u) for u in payload.get("known_urls", [])}
    sources = payload.get("sources", [])[:30]
    stats = {"feeds_ok": 0, "feeds_failed": [], "fetched": 0, "dropped_old": 0, "dropped_known": 0, "dropped_duplicate": 0}

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda s: _load_source(s, fetcher), sources))

    items, seen_urls, seen_titles = [], set(), []
    for src, feed_items, err in results:
        if err:
            stats["feeds_failed"].append({"url": src.get("url"), "error": err})
            continue
        stats["feeds_ok"] += 1
        for it in feed_items:
            stats["fetched"] += 1
            cu = canonical_url(it["url"])
            d = parse_date(it["published_at"]) if it["published_at"] else None
            if d and d < since:
                stats["dropped_old"] += 1
                continue
            if cu in known:
                stats["dropped_known"] += 1
                continue
            toks = title_tokens(it["title"])
            if cu in seen_urls or any(_jaccard(toks, t) >= 0.8 for t in seen_titles):
                stats["dropped_duplicate"] += 1
                continue
            seen_urls.add(cu)
            seen_titles.append(toks)
            items.append({
                "source_id": src.get("id"),
                "source_name": src.get("name"),
                "source_topic": src.get("topic"),
                "title": it["title"],
                "url": cu,
                "published_at": it["published_at"],
                "text": it["text"],
            })
    return {"items": items, "stats": stats}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ------------------------------------------------------------------ relevância
def rank(items, interests, now=None):
    """Nota de 0 a 100 para cada item. É uma regra simples e explicável:
    cada interesse tem peso (1 a 10) e palavras-chave. Palavra no título vale 3,
    no texto vale 1. Tema igual ao da fonte dá um bônus pequeno."""
    now = now or datetime.now(timezone.utc)
    total_weight = sum(max(1, int(i.get("weight", 5))) for i in interests) or 1
    prepared = []
    for i in interests:
        kws = [norm_text(k) for k in i.get("keywords", []) if k and k.strip()]
        pats = [re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])") for k in kws]
        prepared.append((i["topic"], max(1, int(i.get("weight", 5))), pats))

    ranked = []
    for it in items:
        title = norm_text(it.get("title"))
        text = norm_text(it.get("text"))
        acc, best, best_val, matched = 0.0, None, 0.0, []
        for topic, weight, pats in prepared:
            hits_title = sum(1 for p in pats if p.search(title))
            hits_text = sum(1 for p in pats if p.search(text))
            s = min(1.0, (3 * hits_title + hits_text) / 5.0)
            if norm_text(it.get("source_topic")) == norm_text(topic):
                s = min(1.0, s + 0.15)
            if s > 0:
                matched.append({"topic": topic, "strength": round(s, 2)})
            val = weight * s
            acc += val
            if val > best_val:
                best, best_val = topic, val
        # os 3 interesses mais fortes já bastam para chegar a 100
        score = min(100, round(100 * acc / (0.45 * total_weight)))
        d = parse_date(it.get("published_at")) if it.get("published_at") else None
        if d and (now - d) < timedelta(hours=12):
            score = min(100, score + 5)
        out = dict(it)
        out["score"] = int(score)
        out["best_topic"] = best
        out["matched"] = sorted(matched, key=lambda m: -m["strength"])[:3]
        ranked.append(out)
    ranked.sort(key=lambda x: -x["score"])
    return ranked


# ----------------------------------------------------------------------- custo
def estimate_cost(model, input_tokens, output_tokens):
    pin, pout = PRICES.get(model, DEFAULT_PRICE)
    usd = (max(0, int(input_tokens or 0)) * pin + max(0, int(output_tokens or 0)) * pout) / 1_000_000
    return {"model": model, "known_model": model in PRICES, "cost_usd": round(usd, 6),
            "price_per_million": {"input": pin, "output": pout}}
