# Medium Scraper & Article Downloader Pro

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)

A powerful, high-performance **Medium Article & Profile Scraper** built with Python and CustomTkinter. It features proxy fallback pipelines, BeautifulSoup4 parsing with code syntax highlighting, local image archiving, YAML frontmatter metadata extraction, and multi-threaded batch scraping.

---

## ✨ Features

- 🎨 **Modern Dark Mode GUI**: Built using `CustomTkinter` for a sleek desktop experience.
- ⚡ **Multi-Threaded Batch Scraping**: Concurrently scrape multiple articles using Python's `ThreadPoolExecutor`.
- 🔄 **Proxy Fallback Pipeline**: Seamlessly bypasses paywalls and DNS blocks using a multi-stage proxy strategy (`Freedium` -> `ReadMedium` -> `Direct`).
- 🖼️ **Local Image Archiving**: Automatically downloads images inside articles to a local `images/` directory and converts remote URLs into relative local paths.
- 📝 **Syntax Highlighting & Rich Markdown**: Preserves programming code block languages (`python`, `javascript`, `cpp`, etc.) during HTML-to-Markdown conversion.
- 📊 **Metadata Extraction**: Extracts OpenGraph and JSON-LD schema metadata (`title`, `author`, `date`, `original_url`, `tags`).
- 📁 **Multiple Output Formats**: Export articles as **Markdown (`.md`)** with YAML Frontmatter, **Plain Text (`.txt`)**, or **JSON (`.json`)**.
- 💻 **Dual Mode**: Runs in both interactive Desktop GUI and automated CLI modes.

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

Features inside GUI:
- Enter single article URL or Medium user handle (e.g. `@welifiliz`).
- Select a batch `.txt` file containing multiple URLs.
- Choose destination category folder and export format (`md`, `txt`, `json`).
- Toggle "Download Images to Local Directory".
- Adjust concurrent thread count slider.
- Monitor real-time logs and open output folder with one click.

---

### 2. Command Line Interface (CLI)

Run automated CLI operations with arguments:

#### Single Article / Profile Scraping
```bash
python mediumParse.py -u "https://medium.com/@welifiliz" -c yazilim -f md --download-images
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
| `-t` | `--threads` | Number of concurrent threads | `5` |

---

## 📂 Project Structure

```
medium-scraper-pro/
├── config.json              # Configuration file (proxies, user agents, filters)
├── mediumParse.py           # Main entry point (CLI & GUI launcher)
├── requirements.txt         # Project dependencies
├── README.md                # Project documentation
├── core/
│   ├── parser.py            # BS4 & html2text HTML-to-Markdown parser
│   ├── scraper.py           # Proxy fallback pipeline & ThreadPoolExecutor
│   └── image_downloader.py  # Image localizer & downloader
├── gui/
│   └── modern_app.py        # CustomTkinter Dark Mode desktop application
├── utils/
│   └── helpers.py           # Slugify, filename, and URL helper functions
└── articles/                # Destination directory for saved articles
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
