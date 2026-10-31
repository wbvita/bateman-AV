"""Novinky pro Bateman Antivirus — každé ráno vybere 3 velké události.

Běží v GitHub Actions (repozitář wbvita/bateman-AV, workflow novinky.yml)
a zapíše `news.json` do větve `news`. Bateman si soubor stáhne spolu
s kontrolou aktualizací (sentinel_core::news). Jen standardní knihovna.

Jak se pozná „velká událost" bez člověka a bez AI:
  1. píše o ní víc redakcí (shluk podobných titulků z různých webů),
  2. obsahuje slova velkých témat (útok, únik, krypto, Nvidia, miliardy…),
  3. šum (slevy, recenze, tipy na seriály, rozhovory) se vyřadí.
Do souboru jde jen titulek, krátký perex z RSS (je určený k přebírání),
zdroj a odkaz — nikdy celý článek.

Použití:  python vyber.py --out news.json [--previous news.json] [--rss-dir slozka]
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# Stejné weby jako sentinel_core::news::NEWS_SOURCES — jiné odkazy Bateman zahodí.
FEEDS = [
    ("Lupa.cz", "lupa.cz", "https://www.lupa.cz/rss/clanky/"),
    ("Živě.cz", "zive.cz", "https://www.zive.cz/rss/sc-47/"),
    ("Root.cz", "root.cz", "https://www.root.cz/rss/clanky/"),
    ("CzechCrunch", "cc.cz", "https://cc.cz/feed/"),
    ("iROZHLAS", "irozhlas.cz", "https://www.irozhlas.cz/rss/irozhlas/section/veda-technologie"),
]

USER_AGENT = "Bateman-Novinky/1 (+https://github.com/wbvita/bateman-AV)"
MAX_ITEMS = 3
KEEP_DAYS = 3
WINDOW_HOURS = 30
MAX_TITLE = 160
MAX_SUMMARY = 400

# Slova velkých témat (bez diakritiky, malá písmena, kořeny) → body.
BIG = {
    "utok": 3, "hacker": 3, "hack": 3, "unik dat": 4, "unikl": 3, "ransomware": 4,
    "kradez": 3, "ukradl": 3, "zranitelnost": 3, "zero-day": 4, "kybern": 3, "malware": 3,
    "podvod": 2, "phishing": 3, "spyware": 4, "sledovan": 2, "vypadek": 2, "vypadl": 2,
    "varuje": 2, "penezenk": 2, "trezor": 1, "windows": 2, "aktualizac": 1, "heslo": 2,
    "kryptomen": 3, "bitcoin": 3, "burza": 2, "binance": 3, "miliard": 1,
    "nvidia": 3, "apple": 2, "microsoft": 2, "google": 2, "openai": 3, "anthropic": 3,
    "meta": 1, "amazon": 2, "tesla": 2, "musk": 2, "intel": 2, "amd": 2, "samsung": 2,
    "umela inteligence": 2, " ai ": 1, "cip": 2, "polovodic": 2, "propoust": 3,
    "akvizic": 2, "kupuje": 2, "pokut": 3, "zakon": 2, "regulac": 2, "evropsk": 2,
    "eu ": 1, "soud": 2, "zakaz": 2, "rekord": 1, "prvni na svete": 3, "nasa": 2, "spacex": 2,
}
# Šum — zpráva s tímhle se nevybere vůbec.
NOISE = [
    "sleva", "slevy", "black friday", "akce", "recenze", "test ", "testujeme", "soutez",
    "tipy", "tip na", "netflix", "na vikend", "serial", "film", "rozhovor", "podcast",
    "jak na", "navod", "nejlepsi", "srovnani", "horoskop", "zpravy z technologii",
    "kazdy patek", "prehled", "foto:", "video:", "hra roku", "hry", "recept",
]
CATEGORIES = [
    ("crypto", ["kryptomen", "bitcoin", "ethereum", "binance", "blockchain"]),
    ("security", ["utok", "hacker", "hack", "unik", "ransomware", "zranitelnost", "malware", "varuje",
                  "phishing", "spyware", "kybern", "podvod", "zero-day", "heslo"]),
    ("ai", ["umela inteligence", " ai ", "openai", "anthropic", "chatgpt", "gemini", "claude",
            "llm", "jazykov model"]),
    ("science", ["vedc", "vyzkum", "nasa", "vesmir", "planet", "vakcin", "lekar", "klima",
                 "studie", "spacex", "raket"]),
]
STOPWORDS = set(
    "a i v ve na do z ze s se k ke o u za po pro pri od jak ze uz jen tak by byl byla bylo "
    "jsou je to ten ta tu tom ty co kdo ktery ktera ktere ale nebo jako aby kdyz podle pred "
    "nove novy nova vice mene let rok roku let let prvni dalsi jeho jeji jejich si sve svuj "
    "the of and to in for on with".split()
)


@dataclass
class Story:
    source: str
    domain: str
    title: str
    summary: str
    url: str
    published: dt.datetime
    words: set[str] = field(default_factory=set)
    score: float = 0.0
    coverage: list[str] = field(default_factory=list)


def plain(text: str) -> str:
    """Bez diakritiky, malými písmeny — na porovnávání a klíčová slova."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


def short(text: str, limit: int) -> str:
    """Celé věty do limitu (nejvýš tři), jinak oříznout na slovo."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for sentence in sentences[:3]:
        candidate = (out + " " + sentence).strip()
        if len(candidate) > limit:
            break
        out = candidate
    if not out:
        out = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return out


def parse_date(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(2_000_000)


def parse_feed(source: str, domain: str, data: bytes) -> list[Story]:
    root = ET.fromstring(data)
    stories = []
    for item in root.iter("item"):
        title = strip_html(item.findtext("title") or "")
        url = (item.findtext("link") or "").strip()
        summary = strip_html(item.findtext("description") or "")
        published = parse_date(item.findtext("pubDate"))
        host = re.sub(r"^https://([^/]+).*$", r"\1", url).lower()
        if not title or not url.startswith("https://") or not published:
            continue
        if not (host == domain or host.endswith("." + domain)):
            continue
        # Patička WordPressu („Článek X pochází z webu…") do shrnutí nepatří.
        summary = re.sub(r"\s*(Článek|The post)\s.*$", "", summary)
        # Perex občas začíná titulkem — ten se neopakuje.
        if summary.lower().startswith(title.lower()):
            summary = summary[len(title):].lstrip(" .:–-")
        stories.append(Story(source, domain, title[:MAX_TITLE], short(summary, MAX_SUMMARY), url, published))
    return stories


def has_word(text: str, word: str) -> bool:
    """Slovo nebo jeho kořen od začátku slova („nasa" není v „nasadil",
    ale „kryptomen" je v „kryptoměny")."""
    return re.search(r"(?<![a-z0-9])" + re.escape(word.strip()), text) is not None


def keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", plain(text))
    # Kořen = prvních 5 znaků (čeština skloňuje: Binance/Binancí, burza/burzy).
    return {w[:5] for w in words if len(w) >= 3 and w not in STOPWORDS}


def is_noise(story: Story) -> bool:
    title = plain(story.title)
    return any(has_word(title, n) for n in NOISE)


def topic_score(story: Story) -> float:
    text = " " + plain(story.title + " " + story.summary) + " "
    title = " " + plain(story.title) + " "
    score = 0.0
    for word, points in BIG.items():
        if has_word(title, word):
            score += points
        elif has_word(text, word):
            score += points / 2
    # Velké peníze (ne „miliardy osobokilometrů").
    if re.search(r"\d+[,.]?\d*\s*(mld\.?|miliard\w*|milion\w*)\s*(dolar|korun|eur|kc|usd|\$)", text):
        score += 3
    return score


def category(story: Story) -> str:
    """Podle titulku (perex zmiňuje kdeco), jinak technologie."""
    title = " " + plain(story.title) + " "
    for name, words in CATEGORIES:
        if any(has_word(title, w) for w in words):
            return name
    return "tech"


def similar(a: Story, b: Story) -> bool:
    if not a.words or not b.words:
        return False
    common = a.words & b.words
    return len(common) >= 2 and len(common) / min(len(a.words), len(b.words)) >= 0.3


def pick(stories: list[Story], now: dt.datetime) -> list[Story]:
    recent = [s for s in stories if now - s.published <= dt.timedelta(hours=WINDOW_HOURS) and not is_noise(s)]
    for s in recent:
        s.words = keywords(s.title)
        s.score = topic_score(s)
    # Shluky: stejná událost z různých redakcí.
    clusters: list[list[Story]] = []
    for s in sorted(recent, key=lambda x: x.published, reverse=True):
        for cluster in clusters:
            if any(similar(s, other) for other in cluster):
                cluster.append(s)
                break
        else:
            clusters.append([s])
    ranked = []
    for cluster in clusters:
        sources = sorted({s.source for s in cluster})
        best = max(cluster, key=lambda s: (s.score, len(s.summary)))
        best.coverage = sources
        # Víc redakcí = hlavní signál, téma = druhý.
        total = 6 * (len(sources) - 1) + best.score
        ranked.append((total, best))
    ranked.sort(key=lambda pair: (pair[0], pair[1].published), reverse=True)
    chosen: list[Story] = []
    used_sources: dict[str, int] = {}
    for total, story in ranked:
        # Jen větší věci: víc redakcí, nebo silné téma u jedné.
        if total < 4:
            continue
        if used_sources.get(story.source, 0) >= 2:
            continue
        chosen.append(story)
        used_sources[story.source] = used_sources.get(story.source, 0) + 1
        if len(chosen) == MAX_ITEMS:
            break
    return chosen


def to_item(story: Story) -> dict:
    return {
        "category": category(story),
        "title": story.title,
        "summary": story.summary,
        "source": story.source,
        "url": story.url,
        "published_at": story.published.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": story.coverage if len(story.coverage) > 1 else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--previous", help="včerejší news.json (zachovají se 2 předchozí dny)")
    parser.add_argument("--rss-dir", help="místo stahování číst <doména>.xml z této složky (test)")
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    stories: list[Story] = []
    for source, domain, url in FEEDS:
        try:
            if args.rss_dir:
                with open(f"{args.rss_dir}/{domain}.xml", "rb") as f:
                    data = f.read()
            else:
                data = fetch(url)
            stories.extend(parse_feed(source, domain, data))
        except Exception as err:  # jeden nedostupný web nesmí zastavit ostatní
            print(f"varování: {source}: {err}", file=sys.stderr)

    chosen = pick(stories, now)
    today = (now + dt.timedelta(hours=1)).date().isoformat()  # Praha je UTC+1/+2
    days = [{"date": today, "items": [to_item(s) for s in chosen]}]
    if args.previous:
        try:
            with open(args.previous, encoding="utf-8") as f:
                previous = json.load(f)
            days += [d for d in previous.get("days", []) if d.get("date") != today]
        except (OSError, ValueError) as err:
            print(f"varování: předchozí soubor: {err}", file=sys.stderr)
    days = sorted(days, key=lambda d: d["date"], reverse=True)[:KEEP_DAYS]

    feed = {"version": 1, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "days": days}
    data = json.dumps(feed, ensure_ascii=False, indent=1).encode("utf-8")
    if len(data) > 60_000:
        print("chyba: soubor je moc velký", file=sys.stderr)
        return 1
    with open(args.out, "wb") as f:
        f.write(data)
    for s in chosen:
        print(f"[{category(s)}] {s.title} — {', '.join(s.coverage)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
