import hashlib
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict:
    """Loads configuration from config.json with fallback defaults."""
    defaults = {
        "default_output_dir": "articles",
        "default_category": "genel",
        "download_images": False,
        "max_concurrent_threads": 5,
        "proxies": ["https://freedium.to/", "https://readmedium.com/"],
        "request_timeout": 20,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "skip_keywords": [
            "OpenAI", "o1 chat", "o1 API", "Terms of Service", "Privacy Policy",
            "Read Medium articles with AI", "read medium", "articles with ai",
            "sign up", "log in", "subscribe", "become a member"
        ]
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
    return defaults


def clean_text(raw_text: str) -> str:
    """Metin içindeki gereksiz boşlukları ve gizli karakterleri temizler."""
    if not raw_text:
        return ""
    text = re.sub(r'[\s\xa0]+', ' ', raw_text)
    return text.strip()


def clean_html_tags(raw_html: str) -> str:
    """Tüm HTML etiketlerini ve HTML varlıklarını temizler."""
    if not raw_html:
        return ""
    cleanr = re.compile(r'<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    entities = {
        '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
        '&quot;': '"', '&#39;': "'", '&rsquo;': "'", '&lsquo;': "'",
        '&rdquo;': '"', '&ldquo;': '"', '&mdash;': '—', '&ndash;': '–'
    }
    for ent, char in entities.items():
        cleantext = cleantext.replace(ent, char)
    return re.sub(r'\n\s*\n', '\n\n', cleantext).strip()


def slugify(text: str) -> str:
    """Türkçe karakterleri dönüştürür ve SEO uyumlu dosya adı üretir."""
    tr_map = {
        'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g',
        'ı': 'i', 'İ': 'i', 'ö': 'o', 'Ö': 'o',
        'ş': 's', 'Ş': 's', 'ü': 'u', 'Ü': 'u',
        'Â': 'a', 'â': 'a', 'Î': 'i', 'î': 'i', 'Û': 'u', 'û': 'u'
    }
    for tr_char, eng_char in tr_map.items():
        text = text.replace(tr_char, eng_char)
    text = text.lower()
    text = re.sub(r'[\s_]+', '_', text)
    text = re.sub(r'[^a-z0-9_]', '', text)
    text = text.strip('_')
    return text or "makale"


def generate_unique_filename(title: str, url: str, extension: str = "md") -> str:
    """Çakışmaları önlemek için başlık slug'ı ve URL hash'inden benzersiz dosya adı oluşturur."""
    safe_slug = slugify(title)[:60]
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:6]
    return f"{safe_slug}_{url_hash}.{extension.lstrip('.')}"


def extract_username(url_or_username: str) -> str:
    """Girdi string'inden Medium kullanıcı adını tam formatta çıkartır (@username)."""
    url_or_username = url_or_username.strip()
    if "medium.com/" in url_or_username:
        match = re.search(r'@([^/?]+)', url_or_username)
        if match:
            return f"@{match.group(1)}"
    return url_or_username if url_or_username.startswith("@") else f"@{url_or_username}"


def is_article_url(url: str) -> bool:
    """Verilen URL'nin tekil makale linki olup olmadığını kontrol eder."""
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if not path:
        return False

    parts = [p for p in path.split("/") if p]

    # Profil şablonları: medium.com/@kullanici (sadece 1 parça ve @ ile başlıyor) veya u/id
    if netloc in ["medium.com", "www.medium.com"] or "medium.com" in netloc:
        if len(parts) == 1 and (parts[0].startswith("@") or parts[0] in ["u", "about", "lists", "foliage", "sitemap", "feed"]):
            return False

    return True


def is_profile_url(url_or_username: str) -> bool:
    """Girdinin profil veya kullanıcı adı olup olmadığını tespit eder."""
    input_str = url_or_username.strip()
    if input_str.startswith("@") and "/" not in input_str:
        return True
    if "medium.com/feed/" in input_str:
        return True

    parsed = urllib.parse.urlparse(input_str)
    path = parsed.path.strip("/")
    parts = [p for p in path.split("/") if p]

    if "medium.com" in parsed.netloc.lower():
        if len(parts) == 1 and parts[0].startswith("@"):
            return True
        if len(parts) == 2 and parts[0] == "u":
            return True

    return False

