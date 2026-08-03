# Medium Scraper & DeepSeek AI Editor Pro

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![AI: DeepSeek](https://img.shields.io/badge/AI-DeepSeek_v3-deepskyblue.svg)](https://www.deepseek.com/)

A powerful, high-performance **Medium Article Scraper & AI Content Editor** built with Python and CustomTkinter. It scrapes Medium articles/profiles, archives images locally, and integrates with **DeepSeek API** to perform deep content analysis, identify missing architectural/technical gaps, expand upon best practices, and rewrite articles into high-quality native English Markdown.

---

## ✨ Key Features

- 🧠 **DeepSeek AI Content Rewrite & Expansion**: Not just translation! Analyzes articles for weaknesses/gaps, expands them with technical depth and best practices, and rewrites them into fluent native English Markdown.
- 🎨 **Modern Dark Mode GUI**: Built using `CustomTkinter` for a sleek desktop experience with masked API key inputs.
- ⚡ **Multi-Threaded Batch Scraping**: Concurrently scrape multiple articles using Python's `ThreadPoolExecutor`.
- 🔄 **Proxy Fallback Pipeline**: Bypasses paywalls and DNS blocks using a multi-stage proxy strategy (`Freedium` -> `ReadMedium` -> `Direct`).
- 🖼️ **Local Image Archiving**: Automatically downloads images inside articles to a local `images/` directory and converts remote URLs into relative local paths.
- 📝 **Syntax Highlighting & Rich Markdown**: Preserves programming code block languages (`python`, `javascript`, `cpp`, etc.) during HTML-to-Markdown conversion.
- 📊 **Metadata Extraction**: Extracts OpenGraph and JSON-LD schema metadata (`title`, `author`, `date`, `original_url`, `tags`).
- 📁 **Multiple Output Formats**: Export articles as **Markdown (`.md`)** with YAML Frontmatter, **Plain Text (`.txt`)**, or **JSON (`.json`)**.

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

Launch the desktop interface simply by running:

```bash
python mediumParse.py
```

GUI Highlights:
- Enter single article URL or Medium user handle (e.g. `@welifiliz`).
- Select a batch `.txt` file containing multiple URLs.
- Toggle **"DeepSeek AI ile İçeriği Analiz Et, Eksikleri Tamamla ve İngilizce Yaz"**.
- Enter & save your DeepSeek API Key.
- Monitor real-time logs and open output folder with one click.

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

#### CLI Parameters
| Flag | Long Flag | Description | Default |
|---|---|---|---|
| `-u` | `--url` | Target Medium article or profile URL | `None` |
| `-b` | `--batch` | Text file containing list of URLs | `None` |
| `-c` | `--category` | Category subfolder inside `articles/` | `genel` |
| `-f` | `--format` | Output format (`md`, `txt`, `json`) | `md` |
| `--download-images` | | Download remote images locally | `False` |
| `--rewrite-en` | | Analyze, expand, and rewrite in English using DeepSeek AI | `False` |
| `--api-key` | | DeepSeek API Key (`sk-...`) | `None` |
| `-t` | `--threads` | Number of concurrent threads | `5` |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
