import hashlib
import re
import ssl
import urllib.request
from pathlib import Path
from typing import Tuple


def download_image(url: str, output_dir: Path, timeout: int = 15) -> str:
    """Tekil görseli indirir ve yerel dosya adını döndürür."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Hash unique filename
    url_clean = url.split("?")[0]
    ext = url_clean.split(".")[-1].lower() if "." in url_clean and len(url_clean.split(".")[-1]) <= 4 else "jpg"
    filename = f"img_{hashlib.md5(url.encode('utf-8')).hexdigest()[:10]}.{ext}"
    target_path = output_dir / filename

    if target_path.exists() and target_path.stat().st_size > 0:
        return filename

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)

    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            data = resp.read()
            with open(target_path, "wb") as f:
                f.write(data)
        return filename
    except Exception:
        return ""


def localize_markdown_images(markdown_content: str, category_dir: Path, logger=None) -> Tuple[str, int]:
    """Markdown içerisindeki görselleri indirip yerel görece yollarla günceller."""
    images_dir = category_dir / "images"
    image_pattern = re.compile(r'!\[(.*?)\]\((https?://[^\s\)]+)\)')

    matches = image_pattern.findall(markdown_content)
    if not matches:
        return markdown_content, 0

    download_count = 0
    updated_markdown = markdown_content

    for alt_text, url in matches:
        if logger:
            logger.log(f"Görsel indiriliyor: {url[:50]}...")
        
        local_filename = download_image(url, images_dir)
        if local_filename:
            rel_path = f"./images/{local_filename}"
            old_tag = f"![{alt_text}]({url})"
            new_tag = f"![{alt_text}]({rel_path})"
            updated_markdown = updated_markdown.replace(old_tag, new_tag)
            download_count += 1

    return updated_markdown, download_count
