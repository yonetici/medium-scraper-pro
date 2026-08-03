# Medium Scraper & DeepSeek AI Editor Pro

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![AI: DeepSeek](https://img.shields.io/badge/AI-DeepSeek_v3-deepskyblue.svg)](https://www.deepseek.com/)

A powerful, high-performance **Medium Article Scraper & AI Content Editor** built with Python and CustomTkinter. Features a sleek **Tabbed Desktop Interface** to scrape Medium articles/profiles, archive images locally, select downloaded articles, analyze gaps, expand technical depth, and rewrite them into native English Markdown via **DeepSeek API**.

---

## ✨ Features & Interface Architecture

### 📌 Tab 1: 📥 Makale İndirici (Scraper & Downloader)
- **Flexible Inputs**: Scrape single article URLs, Medium user handles (e.g. `@welifiliz`), RSS feeds, or batch URL text files (`.txt`).
- **Proxy Fallback Pipeline**: Automatically bypasses paywalls and DNS blocks (`Freedium` -> `ReadMedium` -> `Direct`).
- **Multi-Threaded Scraping**: Fast concurrent downloads using Python's `ThreadPoolExecutor`.
- **Local Image Archiving**: Automatically downloads images to `articles/<category>/images/` and converts links to relative local paths (`./images/img_...`).
- **Syntax Highlighting & Rich Formatting**: Preserves code block language tags (`python`, `javascript`, `cpp`, etc.) during HTML-to-Markdown conversion.

### 📌 Tab 2: 🤖 AI Editor & İngilizce Yeniden Yazım (DeepSeek Converter)
- **Local Article Browser & Selector**: Browse downloaded articles across local category subfolders with a live preview.
- **DeepSeek AI Content Rewrite & Expansion**: Analyzes the selected article, identifies missing architectural/technical gaps, expands upon modern best practices, and rewrites it into fluent native English Markdown.
- **Masked API Key Management**: Safely stores your DeepSeek API key in `config.json`.
- **Live Side-by-Side Preview**: Displays both the original text and the generated English article inside the GUI.

---

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yonetici/medium-scraper-pro.git
   cd medium-scraper-pro
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

### 1. Graphical User Interface (GUI)

Launch the tabbed desktop app simply by running:

```bash
python mediumParse.py
```

- Use **Sekme 1 (Makale İndirici)** to download Medium articles to `articles/`.
- Switch to **Sekme 2 (AI Editor)** to pick any downloaded article, enter your DeepSeek API Key, and click **"✨ Seçili Makaleyi DeepSeek ile Geliştir & İngilizce Yaz"**.

---

### 2. Command Line Interface (CLI)

#### Single Article Scraping + DeepSeek AI Rewrite
```bash
python mediumParse.py -u "https://medium.com/@welifiliz/kurumsal-d%C3%BCnyada-react-ekosistemi-233776774cea" -c yazilim -f md --rewrite-en --api-key "sk-YOUR_DEEPSEEK_KEY"
```

#### Batch Scraping from URL File
```bash
python mediumParse.py -b urls.txt -c python_articles -f json -t 8 --download-images
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
