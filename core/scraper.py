import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional

from core.parser import extract_metadata, html_to_markdown
from utils.helpers import (
    load_config, clean_html_tags, extract_username, is_article_url
)


class MediumScraperCore:
    """Medium makale ve RSS akışlarını indirmek için gelişmiş scraper motoru."""

    def __init__(self, logger=None):
        self.logger = logger
        self.config = load_config()
        self.default_headers = {
            "User-Agent": self.config.get("user_agent"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        self.skip_keywords = self.config.get("skip_keywords", [])

    def _log(self, message: str):
        if self.logger and hasattr(self.logger, "log"):
            self.logger.log(message)
        else:
            print(message)

    def get_ssl_context(self, unverified: bool = False) -> ssl.SSLContext:
        if unverified:
            return ssl._create_unverified_context()
        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()

    def fetch_url_html(self, target_url: str, custom_headers: dict = None) -> str:
        headers = self.default_headers.copy()
        if custom_headers:
            headers.update(custom_headers)

        req = urllib.request.Request(target_url, headers=headers)
        timeout = self.config.get("request_timeout", 20)

        # Doğrulanmış varsayılan SSL bağlamı dene
        try:
            context = self.get_ssl_context(unverified=False)
            with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception:
            # TLS doğrulama hatası alırsak unverified bağlama düş
            context = self.get_ssl_context(unverified=True)
            with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
                return response.read().decode('utf-8', errors='ignore')

    def fetch_single_article(self, article_url: str) -> Dict[str, Any]:
        self._log(f"Makale çekiliyor: {article_url}")
        html_text = None
        last_error = ""

        clean_target = article_url if article_url.startswith("http") else f"https://{article_url}"

        # 1. Freedium Proxy Denemesi
        freedium_url = f"https://freedium.to/{clean_target}"
        self._log(f"Freedium deneniyor: {freedium_url}")
        try:
            html_text = self.fetch_url_html(freedium_url)
            self._log("[Başarılı] Freedium üzerinden içerik çekildi.")
        except Exception as e:
            last_error = f"Freedium Hatası: {e}"
            self._log(f"[Başarısız] {last_error}")

        # 2. ReadMedium Proxy Denemesi
        if not html_text:
            readmedium_url = f"https://readmedium.com/{clean_target}"
            self._log(f"ReadMedium deneniyor: {readmedium_url}")
            try:
                html_text = self.fetch_url_html(readmedium_url)
                self._log("[Başarılı] ReadMedium üzerinden içerik çekildi.")
            except Exception as e:
                last_error = f"ReadMedium Hatası: {e}"
                self._log(f"[Başarısız] {last_error}")

        # 3. Doğrudan Medium URL Denemesi
        if not html_text:
            self._log(f"Doğrudan bağlantı deneniyor: {clean_target}")
            try:
                html_text = self.fetch_url_html(clean_target)
                self._log("[Başarılı] Doğrudan bağlantı ile içerik çekildi.")
            except Exception as e:
                last_error = f"Doğrudan Bağlantı Hatası: {e}"
                self._log(f"[Başarısız] {last_error}")

        if not html_text:
            raise Exception(f"Makale hiçbir kaynaktan indirilemedi. Son hata: {last_error}")

        # Metadata Çıkarma
        metadata = extract_metadata(html_text, source_url=clean_target)

        # Makale HTML Gövdesini Ayrıştırma
        article_html = ""
        for tag in ["article", "main"]:
            match = re.search(f'<{tag}.*?>(.*?)</{tag}>', html_text, re.DOTALL | re.IGNORECASE)
            if match and ("<p" in match.group(1)):
                article_html = match.group(1)
                break

        if not article_html:
            for pattern in [
                r'<div[^>]*class=["\'][^"\']*(?:post|article|content|story)[^"\']*["\'][^>]*>(.*?)</div>',
                r'<div[^>]*id=["\'][^"\']*(?:post|article|content)[^"\']*["\'][^>]*>(.*?)</div>'
            ]:
                matches = re.findall(pattern, html_text, re.DOTALL | re.IGNORECASE)
                for m in matches:
                    if "<p" in m and len(m) > 200:
                        article_html = m
                        break
                if article_html:
                    break

        if not article_html:
            article_html = html_text

        markdown_body = html_to_markdown(article_html)

        # Reklam ve Arayüz Metinlerini Temizleme
        clean_lines = []
        for line in markdown_body.splitlines():
            if not any(k.lower() in line.lower() for k in self.skip_keywords):
                clean_lines.append(line)

        final_markdown = "\n".join(clean_lines).strip()

        return {
            "metadata": metadata,
            "title": metadata["title"],
            "content_markdown": final_markdown,
            "content_text": clean_html_tags(article_html),
            "original_url": clean_target
        }

    def fetch_user_rss(self, target_input: str) -> List[Dict[str, Any]]:
        username = extract_username(target_input)
        rss_url = f"https://medium.com/feed/{username}"
        self._log(f"RSS beslemesi alınıyor: {rss_url}")

        xml_data = self.fetch_url_html(rss_url)
        articles = []

        try:
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item'):
                title_node = item.find('title')
                link_node = item.find('link')
                pub_node = item.find('pubDate')

                title = title_node.text if title_node is not None else "Başlıksız Makale"
                link = link_node.text if link_node is not None else ""
                pub_date = pub_node.text if pub_node is not None else ""

                content = ""
                content_encoded = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                if content_encoded is not None and content_encoded.text:
                    content = content_encoded.text
                else:
                    desc_node = item.find('description')
                    if desc_node is not None and desc_node.text:
                        content = desc_node.text

                markdown_content = html_to_markdown(content) if content else ""
                text_content = clean_html_tags(content) if content else ""

                metadata = {
                    "title": title,
                    "author": username,
                    "published_at": pub_date,
                    "original_url": link,
                    "site_name": "Medium",
                    "tags": []
                }

                articles.append({
                    "metadata": metadata,
                    "title": title,
                    "content_markdown": markdown_content,
                    "content_text": text_content,
                    "original_url": link
                })
        except ET.ParseError as e:
            raise Exception(f"RSS XML verisi ayrıştırılamadı: {e}")

        return articles

    def fetch_batch_articles(
        self,
        urls: List[str],
        max_workers: int = 5,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """Çoklu iş parçacığı (Multi-threading) ile toplu makale indirir."""
        results = []
        total = len(urls)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.fetch_single_article, url): url
                for url in urls if is_article_url(url)
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                completed += 1
                try:
                    data = future.result()
                    results.append(data)
                    if progress_callback:
                        progress_callback(completed, total, f"[BAŞARILI] {data['title']}")
                except Exception as e:
                    self._log(f"[HATA] {url}: {e}")
                    if progress_callback:
                        progress_callback(completed, total, f"[HATA] {url}: {e}")

        return results
