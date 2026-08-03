import json
import re
from typing import Dict, Any

try:
    from bs4 import BeautifulSoup, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

from utils.helpers import clean_text, clean_html_tags


def extract_metadata(html_text: str, fallback_title: str = "", source_url: str = "") -> Dict[str, Any]:
    """HTML sayfasından OpenGraph ve JSON-LD metadata verilerini çıkarır."""
    metadata = {
        "title": fallback_title,
        "author": "",
        "published_at": "",
        "description": "",
        "image_url": "",
        "tags": [],
        "site_name": "Medium",
        "original_url": source_url
    }

    if HAS_BS4:
        soup = BeautifulSoup(html_text, 'html.parser')

        # 1. JSON-LD Ayrıştırma
        json_scripts = soup.find_all('script', type=re.compile(r'application/ld\+json', re.I))
        for script in json_scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string.strip())
                if isinstance(data, list):
                    data = data[0]
                if isinstance(data, dict):
                    if data.get("@type") in ["NewsArticle", "BlogPosting", "SocialMediaPosting", "Article"]:
                        if data.get("headline"):
                            metadata["title"] = clean_text(data["headline"])
                        if "author" in data:
                            author_data = data["author"]
                            if isinstance(author_data, dict):
                                metadata["author"] = author_data.get("name", "")
                            elif isinstance(author_data, str):
                                metadata["author"] = author_data
                            elif isinstance(author_data, list) and len(author_data) > 0:
                                first_author = author_data[0]
                                metadata["author"] = first_author.get("name", "") if isinstance(first_author, dict) else str(first_author)
                        if "datePublished" in data:
                            metadata["published_at"] = str(data["datePublished"])
                        if "description" in data:
                            metadata["description"] = clean_text(data["description"])
                        if "image" in data:
                            img = data["image"]
                            metadata["image_url"] = img[0] if isinstance(img, list) and img else (img if isinstance(img, str) else "")
                        if "keywords" in data:
                            kw = data["keywords"]
                            metadata["tags"] = kw if isinstance(kw, list) else [k.strip() for k in str(kw).split(",") if k.strip()]
            except Exception:
                pass

        # 2. OpenGraph Meta Etiketleri
        og_mapping = {
            "og:title": ("title", True),
            "og:description": ("description", False),
            "og:image": ("image_url", False),
            "article:author": ("author", False),
            "article:published_time": ("published_at", False),
            "og:site_name": ("site_name", False)
        }
        for prop, (key, force_update) in og_mapping.items():
            if not metadata[key] or force_update:
                meta_tag = soup.find('meta', property=prop) or soup.find('meta', attrs={'name': prop})
                if meta_tag and meta_tag.get('content'):
                    metadata[key] = clean_text(meta_tag['content'])

        # Fallback title
        if not metadata["title"] or metadata["title"].lower() in ["medium", "read medium"]:
            h1 = soup.find('h1')
            if h1:
                metadata["title"] = clean_text(h1.get_text())
            elif soup.title:
                title_val = soup.title.get_text()
                title_val = re.split(r' \| by | - | \| ', title_val)[0].strip()
                if title_val and "read medium" not in title_val.lower():
                    metadata["title"] = clean_text(title_val)

    else:
        # Regex Fallback
        json_ld_matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, re.DOTALL | re.IGNORECASE)
        for json_str in json_ld_matches:
            try:
                data = json.loads(json_str.strip())
                if isinstance(data, list):
                    data = data[0]
                if isinstance(data, dict) and data.get("@type") in ["NewsArticle", "BlogPosting", "SocialMediaPosting", "Article"]:
                    if data.get("headline"):
                        metadata["title"] = clean_text(data["headline"])
                    if "author" in data:
                        metadata["author"] = data["author"].get("name", "") if isinstance(data["author"], dict) else str(data["author"])
                    if "datePublished" in data:
                        metadata["published_at"] = data["datePublished"]
                    if "description" in data:
                        metadata["description"] = clean_text(data["description"])
            except Exception:
                pass

        if not metadata["title"] or metadata["title"].lower() in ["medium", "read medium"]:
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.DOTALL | re.IGNORECASE)
            if h1_match:
                metadata["title"] = clean_html_tags(h1_match.group(1))

    if not metadata["title"]:
        metadata["title"] = fallback_title or "Başlıksız Makale"

    return metadata


def parse_code_blocks_with_bs4(soup: BeautifulSoup) -> None:
    """BS4 kullanarak pre ve code etiketlerindeki programlama dillerini koruyup dönüştürür."""
    for pre in soup.find_all('pre'):
        code_tag = pre.find('code')
        lang = ""
        if code_tag:
            # Language detection via class
            classes = code_tag.get('class', []) + pre.get('class', [])
            for c in classes:
                if c.startswith('language-') or c.startswith('lang-'):
                    lang = c.split('-', 1)[1]
                    break
            if not lang and pre.get('data-language'):
                lang = pre.get('data-language')

            code_text = code_tag.get_text()
        else:
            code_text = pre.get_text()

        # Markdown replacement
        pre.replace_with(f"\n\n```{lang}\n{code_text.strip()}\n```\n\n")


def html_to_markdown(html_content: str) -> str:
    """HTML içeriğini semantik olarak zengin Markdown formatına dönüştürür."""
    if HAS_BS4:
        soup = BeautifulSoup(html_content, 'html.parser')
        parse_code_blocks_with_bs4(soup)
        processed_html = str(soup)
    else:
        processed_html = html_content

    if HAS_HTML2TEXT:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0
        return h.handle(processed_html).strip()

    text = processed_html

    # Headings
    for i in range(6, 0, -1):
        pattern = fr'<h{i}[^>]*>(.*?)</h{i}>'
        replacement = r'\n\n' + ('#' * i) + r' \1\n\n'
        text = re.sub(pattern, replacement, text, flags=re.DOTALL | re.IGNORECASE)

    # Paragraphs & Blockquotes
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'\n\n> \1\n\n', text, flags=re.DOTALL | re.IGNORECASE)

    # Lists
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'</?[ul|ol][^>]*>', r'\n', text, flags=re.IGNORECASE)

    # Inline Code
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)

    # Bold & Italic
    text = re.sub(r'<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(?:em|i)[^>]*>(.*?)</(?:em|i)>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)

    # Images and Links
    text = re.sub(r'<img[^>]*src=["\'](.*?)["\'][^>]*alt=["\'](.*?)["\'][^>]*>', r'![\2](\1)', text, flags=re.IGNORECASE)
    text = re.sub(r'<img[^>]*alt=["\'](.*?)["\'][^>]*src=["\'](.*?)["\'][^>]*>', r'![\1](\2)', text, flags=re.IGNORECASE)
    text = re.sub(r'<img[^>]*src=["\'](.*?)["\'][^>]*>', r'![](\1)', text, flags=re.IGNORECASE)
    text = re.sub(r'<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)

    text = clean_html_tags(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def build_markdown_with_frontmatter(metadata: dict, body_markdown: str) -> str:
    """Markdown dosyası için YAML Frontmatter başlığı oluşturur."""
    tags_yaml = ""
    if metadata.get("tags"):
        tags_yaml = "\ntags:\n" + "\n".join(f"  - {t}" for t in metadata["tags"])

    frontmatter = f"""---
title: "{metadata.get('title', '')}"
author: "{metadata.get('author', '')}"
date: "{metadata.get('published_at', '')}"
original_url: "{metadata.get('original_url', '')}"
site: "{metadata.get('site_name', 'Medium')}"{tags_yaml}
---

# {metadata.get('title', '')}

{body_markdown}
"""
    return frontmatter.strip()
