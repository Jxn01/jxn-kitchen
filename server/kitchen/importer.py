"""Import a recipe from a URL (spec §6.3).

`recipe-scrapers` reads the page field by field; any field it fails on (a site changed its markup — Mindmegette's
scraper broke this way) falls back to our own reader of the page's schema.org Recipe JSON-LD, which most recipe
sites carry for search engines. Unknown sites go through the same generic path.

The server fetches pages on someone's say-so, so the URL is checked first (SSRF guard): http(s) only, and every
address the host resolves to — at every redirect hop — must be a public internet address: no LAN (HA at .2!),
loopback, link-local, tailnet (CGNAT) or reserved ranges.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit  # noqa: F401 (urlsplit is used by app.py too)

import httpx

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0 Safari/537.36')
MAX_PAGE = 5 * 1024 * 1024
MAX_IMAGE = 10 * 1024 * 1024
Resolver = Callable[[str], list[str]]
_LOCAL_SUFFIXES = ('.localhost', '.local', '.home', '.lan', '.internal', '.home.arpa')


class ImportRefused(ValueError):
    """The URL is not imported at all (422). `code`: scheme | private | unknown_host."""
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class FetchFailed(RuntimeError):
    """The page could not be fetched; the link is saved as a draft. `code`: http_status | too_large | unreachable |
    redirects. The app shows each code as a plain sentence in EN/HU (i18n `import.reason.<code>`)."""
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


# every reason code a draft can carry (the web app has a sentence for each; a test keeps them in step)
DRAFT_REASONS = ('http_status', 'too_large', 'unreachable', 'redirects', 'private', 'unknown_host', 'no_recipe',
                 'scraper', 'scan')   # 'scan': a draft read by OCR (sub-project 7)


def default_resolver(host: str) -> list[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None)})


def check_url(url: str, resolve: Resolver = default_resolver) -> str:
    return pin_url(url, resolve)[0]


def pin_url(url: str, resolve: Resolver = default_resolver) -> tuple[str, str, str]:
    """Validate a URL and return (url, host, checked_ip). The request must then CONNECT TO checked_ip (not resolve
    the name again): a second lookup could answer differently (DNS rebinding) and reach the LAN."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ImportRefused('only http(s) links to public recipe sites can be imported', 'scheme')
    host = parts.hostname.lower().rstrip('.')
    if host == 'localhost' or host.endswith(_LOCAL_SUFFIXES):     # local-only names, whatever DNS says
        raise ImportRefused('links to the home network or private addresses are not imported', 'private')
    try:
        addrs = [host] if _is_ip(host) else resolve(host)
    except OSError as e:
        raise ImportRefused(f'unknown host: {host}', 'unknown_host') from e
    if not addrs:
        raise ImportRefused(f'unknown host: {host}', 'unknown_host')
    for a in addrs:
        ip = ipaddress.ip_address(a.split('%')[0])
        if not ip.is_global or ip.is_multicast:
            raise ImportRefused('links to the home network or private addresses are not imported', 'private')
    return url.strip(), host, addrs[0].split('%')[0]


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


async def fetch(http: httpx.AsyncClient, url: str, resolve: Resolver, limit: int = MAX_PAGE,
                accept: str = 'text/html,application/xhtml+xml') -> tuple[str, bytes, str]:
    """GET with manual redirects (each hop re-checked), a size cap and a browser UA. -> (final url, body, type)."""
    for _ in range(6):
        url, host, ip = pin_url(url, resolve)
        parts = urlsplit(url)
        netloc = f'[{ip}]' if ':' in ip else ip
        if parts.port:
            netloc += f':{parts.port}'
        pinned = parts._replace(netloc=netloc).geturl()     # connect to the checked address…
        headers = {'User-Agent': UA, 'Accept': accept, 'Accept-Language': 'hu,en;q=0.8',
                   'Host': parts.netloc.rsplit('@', 1)[-1]}  # …while asking for (and TLS-verifying) the real host
        try:
            async with http.stream('GET', pinned, headers=headers, timeout=15, follow_redirects=False,
                                   extensions={'sni_hostname': host}) as r:
                if r.status_code in (301, 302, 303, 307, 308) and 'location' in r.headers:
                    url = urljoin(url, r.headers['location'])
                    continue
                if r.status_code != 200:
                    raise FetchFailed(f'the site answered {r.status_code}', 'http_status')
                body = bytearray()
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > limit:
                        raise FetchFailed('the page is too large', 'too_large')
                return url, bytes(body), r.headers.get('content-type', '')
        except httpx.HTTPError as e:
            raise FetchFailed(f'could not reach the site ({type(e).__name__})', 'unreachable') from e
    raise FetchFailed('too many redirects', 'redirects')


# --- schema.org JSON-LD ---------------------------------------------------------------------------------------

def _recipes_in(node: Any):
    if isinstance(node, list):
        for x in node:
            yield from _recipes_in(x)
    elif isinstance(node, dict):
        t = node.get('@type')
        if t == 'Recipe' or (isinstance(t, list) and 'Recipe' in t):
            yield node
        for k in ('@graph', 'mainEntity', 'itemListElement'):
            if k in node:
                yield from _recipes_in(node[k])


def _minutes(iso: Any) -> int | None:
    if not isinstance(iso, str):
        return None
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso.strip())
    if not m or not any(m.groups()):
        return None
    d, h, mi, _ = (int(x or 0) for x in m.groups())
    return d * 1440 + h * 60 + mi or None


def _int(v: Any) -> int | None:
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, (int, float)):
        return int(v) or None
    m = re.search(r'\d+', str(v or ''))
    return int(m.group()) if m else None


def _steps(v: Any) -> list[str]:
    out: list[str] = []
    if isinstance(v, str):
        out += [s.strip() for s in re.split(r'\n+', v) if s.strip()]
    elif isinstance(v, list):
        for x in v:
            out += _steps(x)
    elif isinstance(v, dict):
        if 'itemListElement' in v:
            out += _steps(v['itemListElement'])
        elif v.get('text'):
            out.append(str(v['text']).strip())
    return out


def _image(v: Any) -> str | None:
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict):
        v = v.get('url')
    return v if isinstance(v, str) and v.startswith('http') else None


def jsonld(html: str) -> dict[str, Any]:
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(m.group(1), strict=False)
        except ValueError:
            continue
        for r in _recipes_in(data):
            return {
                'title': (r.get('name') or '').strip(), 'ingredients': [str(x).strip() for x in r.get('recipeIngredient') or []],
                'steps': _steps(r.get('recipeInstructions')), 'servings': _int(r.get('recipeYield')),
                'total_min': _minutes(r.get('totalTime')), 'prep_min': _minutes(r.get('prepTime')),
                'cook_min': _minutes(r.get('cookTime')), 'image_url': _image(r.get('image')),
            }
    return {}


# --- extraction -----------------------------------------------------------------------------------------------

def clean_title(t: str) -> str:
    t = re.split(r'\s+[|–]\s+', t.strip())[0]
    t = re.sub(r'\s+(recept(\s+képpel)?|recipe)$', '', t, flags=re.I)
    return t.strip()


def page_title(html: str) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    return clean_title(re.sub(r'\s+', ' ', m.group(1))) if m else ''


def extract(html: str, url: str) -> dict[str, Any]:
    from recipe_scrapers import scrape_html
    try:
        s = scrape_html(html, org_url=url, supported_only=False)
    except Exception:
        s = None
    ld = jsonld(html)

    def field(method: str, key: str, conv: Callable[[Any], Any] = lambda v: v) -> Any:
        if s is not None:
            try:
                v = conv(getattr(s, method)())
                if v:
                    return v
            except Exception:
                pass
        return ld.get(key)

    title = field('title', 'title', clean_title) or page_title(html)
    host = (urlsplit(url).hostname or '').removeprefix('www.')
    return {
        'title': clean_title(title) if title else host,
        'ingredients': field('ingredients', 'ingredients', lambda v: [x.strip() for x in v if x and x.strip()]) or [],
        'steps': field('instructions_list', 'steps', lambda v: [x.strip() for x in v if x and x.strip()]) or [],
        'servings': field('yields', 'servings', _int),
        'total_min': field('total_time', 'total_min', _int),
        'prep_min': field('prep_time', 'prep_min', _int),
        'cook_min': field('cook_time', 'cook_min', _int),
        'image_url': field('image', 'image_url', _image),
        'site': host,
    }
