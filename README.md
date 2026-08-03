# Medium Scraper & Multi-AI Editor Pro

[🇺🇸 English Documentation](README.md) | [🇹🇷 Türkçe Dokümantasyon](README.tr.md)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![AI: Multi--Provider](https://img.shields.io/badge/AI-OpenAI_|_Gemini_|_DeepSeek_|_OpenRouter_|_Kimi_|_Grok_|_Qwen-deepskyblue.svg)](https://www.openai.com/)

A high-performance **Medium Article Scraper & Multi-AI Content Editor** built with Python and CustomTkinter. Features a **Tabbed Desktop Interface** with instant **Bilingual UI Toggle (TR / EN)** to scrape Medium articles/profiles, archive images locally, select downloaded articles, analyze gaps, expand technical depth, and rewrite them into native English Markdown via major AI providers (**OpenAI**, **Gemini**, **DeepSeek**, **OpenRouter**, **Kimi**, **Grok**, **Qwen**, or **Custom Endpoints**).

---

## ✨ Major Features

### 🌐 Bilingual Interface (TR / EN)
Includes a real-time **TR | EN** language switch in the header bar. Toggle between Turkish and English instantly without restarting the application!

### 🤖 Multi-Provider AI Engine (Not Direct Translation!)
Supports major AI providers via an interactive dropdown:
- **DeepSeek** (`deepseek-chat`)
- **OpenAI** (`gpt-4o-mini`, `gpt-4o`)
- **Gemini (Google)** (`gemini-2.5-flash`, `gemini-2.5-pro`)
- **OpenRouter** (`google/gemini-2.5-flash`, `anthropic/claude-3.5-sonnet` etc.)
- **Kimi (Moonshot AI)** (`moonshot-v1-8k`)
- **Grok (xAI)** (`grok-2-latest`)
- **Qwen (Alibaba DashScope)** (`qwen-plus`, `qwen-max`)
- **Custom OpenAI-Compatible Endpoints**

*Each provider maintains its own stored API key and model preference in `config.json`.*

---

## 📌 GUI Architecture

### 📥 Tab 1: Makale İndirici / Article Downloader
- **Flexible Inputs**: Scrape single article URLs, Medium user handles (e.g. `@welifiliz`), RSS feeds, or batch URL text files (`.txt`).
- **Proxy Fallback Pipeline**: Bypasses paywalls and DNS blocks (`Freedium` -> `ReadMedium` -> `Direct`).
- **Multi-Threaded Scraping**: Fast concurrent downloads using Python's `ThreadPoolExecutor`.
- **Local Image Archiving**: Downloads images to `articles/<category>/images/` and updates links to relative local paths (`./images/img_...`).

### 🤖 Tab 2: Multi-AI Editor & English Rewriter
- **Local Article Browser & Selector**: Browse downloaded articles across local category subfolders with a live preview.
- **Provider Selector & Masked Key Inputs**: Switch between OpenAI, Gemini, DeepSeek, OpenRouter, Kimi, Grok, Qwen, or Custom endpoints with automatic API key memory.
- **AI Content Rewrite & Expansion**: Analyzes the selected article, identifies missing architectural/technical gaps, expands upon modern best practices, and rewrites it into fluent native English Markdown.

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

### 2. Command Line Interface (CLI)

```bash
# OpenAI with gpt-4o-mini
python mediumParse.py -u "https://medium.com/@welifiliz/kurumsal-d%C3%BCnyada-react-ekosistemi-233776774cea" -c yazilim --rewrite-en --ai-provider "OpenAI" --ai-model "gpt-4o-mini" --api-key "sk-..."

# Gemini with gemini-2.5-flash
python mediumParse.py -u "https://medium.com/@welifiliz" -c genel --rewrite-en --ai-provider "Gemini" --api-key "AIzaSy..."
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
