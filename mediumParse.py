#!/usr/bin/env python3
"""
Medium Makale & İçerik İndirici (SEO/GEO Uyumlu & Modüler Yapı)

CLI Kullanımı:
    python mediumParse.py -u "https://medium.com/@welifiliz" -c genel -f md --download-images
    python mediumParse.py --batch sample-urls.txt -c python -f json -t 8

GUI Kullanımı:
    python mediumParse.py
"""

import argparse
import sys
from pathlib import Path

# Local imports
from core.scraper import MediumScraperCore
from core.image_downloader import localize_markdown_images
from core.parser import build_markdown_with_frontmatter
from utils.helpers import (
    ROOT, load_config, generate_unique_filename,
    is_article_url, is_profile_url
)

MAKALELER_DIR = ROOT / "articles"
MAKALELER_DIR.mkdir(parents=True, exist_ok=True)


def run_cli(args):
    """Komut satırı (CLI) üzerinden çalıştırma işlevi."""
    print("=" * 60)
    print("Medium Scraper CLI Motoru Başlatılıyor...")
    print("=" * 60)

    scraper = MediumScraperCore()
    category = args.category or "genel"
    output_format = args.format or "md"
    download_imgs = args.download_images
    max_threads = args.threads or 5
    category_dir = MAKALELER_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)

    urls_to_process = []

    if args.url:
        urls_to_process.append(args.url.strip())

    if args.batch:
        batch_path = Path(args.batch)
        if batch_path.exists():
            with open(batch_path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                urls_to_process.extend(urls)
            print(f"[BİLGİ] {len(urls)} adet URL {batch_path.name} dosyasından okundu.")
        else:
            print(f"[HATA] Toplu dosya bulunamadı: {args.batch}")
            sys.exit(1)

    if not urls_to_process:
        print("[HATA] Lütfen bir URL (-u) veya toplu dosya (--batch) belirtin.")
        sys.exit(1)

    all_articles = []

    for target in urls_to_process:
        if is_profile_url(target):
            print(f"[RSS/Profil] {target} taranıyor...")
            try:
                rss_articles = scraper.fetch_user_rss(target)
                all_articles.extend(rss_articles)
            except Exception as e:
                print(f"[HATA] Profil çekilemedi ({target}): {e}")
        elif is_article_url(target):
            print(f"[Makale] {target} çekiliyor...")
            try:
                article_data = scraper.fetch_single_article(target)
                all_articles.append(article_data)
            except Exception as e:
                print(f"[HATA] Makale çekilemedi ({target}): {e}")

    if not all_articles:
        print("[HATA] İşlenebilecek makale bulunamadı.")
        sys.exit(1)

    print(f"\n[KAYIT] Toplam {len(all_articles)} makale '{category}' klasörüne kaydediliyor...")

    for idx, article in enumerate(all_articles, 1):
        title = article["title"]
        metadata = article["metadata"]
        markdown_content = article["content_markdown"]
        text_content = article["content_text"]
        orig_url = article.get("original_url", "")

        if download_imgs and markdown_content:
            print(f"[{idx}/{len(all_articles)}] Görseller yerel dizine indiriliyor...")
            markdown_content, img_cnt = localize_markdown_images(markdown_content, category_dir)
            if img_cnt > 0:
                print(f"  -> {img_cnt} adet görsel indirildi.")

        filename = generate_unique_filename(title, orig_url, extension=output_format)
        file_path = category_dir / filename

        if output_format == "md":
            content_to_write = build_markdown_with_frontmatter(metadata, markdown_content)
        elif output_format == "txt":
            content_to_write = f"Başlık: {title}\nYazar: {metadata.get('author')}\nTarih: {metadata.get('published_at')}\nURL: {orig_url}\n\n{text_content}"
        elif output_format == "json":
            import json
            content_to_write = json.dumps({
                "metadata": metadata,
                "content_markdown": markdown_content,
                "content_text": text_content
            }, ensure_ascii=False, indent=2)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_to_write)

        print(f"  [+] Kaydedildi: {file_path}")

    print("\n[BAŞARILI] CLI işlemi tamamlandı!")


def main():
    parser = argparse.ArgumentParser(description="Medium Makale & İçerik İndirici (SEO/GEO Ready)")
    parser.add_argument("-u", "--url", type=str, help="Medium Makale veya Profil URL'si (@kullanici)")
    parser.add_argument("-b", "--batch", type=str, help="Toplu URL listesi içeren metin dosyası (.txt)")
    parser.add_argument("-c", "--category", type=str, default="genel", help="Kayıt kategorisi/klasörü")
    parser.add_argument("-f", "--format", type=str, choices=["md", "txt", "json"], default="md", help="Çıktı formatı")
    parser.add_argument("--download-images", action="store_true", help="Görselleri yerel images/ dizinine indir")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Çoklu iş parçacığı sayısı")
    parser.add_argument("--gui", action="store_true", help="Arayüzü (GUI) başlat")

    args = parser.parse_args()

    # Eğer komut satırı argümanı verilmişse CLI modunda çalış
    if args.url or args.batch:
        run_cli(args)
    else:
        # Argüman yoksa GUI başlat
        from gui.modern_app import ModernMediumScraperApp
        app = ModernMediumScraperApp()
        app.mainloop()


if __name__ == "__main__":
    main()