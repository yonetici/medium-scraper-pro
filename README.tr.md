# Medium Scraper & Multi-AI Editor Pro (Türkçe)

[🇺🇸 English Documentation](README.md) | [🇹🇷 Türkçe Dokümantasyon](README.tr.md)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![AI: Multi--Provider](https://img.shields.io/badge/AI-OpenAI_|_Gemini_|_DeepSeek_|_OpenRouter_|_Kimi_|_Grok_|_Qwen-deepskyblue.svg)](https://www.openai.com/)

Python ve CustomTkinter ile geliştirilmiş gelişmiş bir **Medium Makale İndirici & Çoklu Yapay Zeka (AI) İçerik Editörü**. Makaleleri/profilleri indirir, görselleri yerel dizine kaydeder ve indirilen yazıları major AI servisleri (**OpenAI**, **Gemini**, **DeepSeek**, **OpenRouter**, **Kimi**, **Grok**, **Qwen** veya **Özel Endpoint'ler**) kullanarak analiz edip, teknik eksiklerini tamamlayarak akıcı native İngilizceye dönüştürür.

---

## ✨ Temel Özellikler

### 🤖 Çoklu AI Servis Desteği (Birebir çeviri değildir!)
Seçilen yapay zeka servisi makaleyi analiz eder, anlatım boşluklarını ve eksik teknik detayları/kod örneklerini tespit eder, güncel en iyi pratiklerle (best practices) zenginleştirerek profesyonel İngilizceye dönüştürür.
- **DeepSeek** (`deepseek-chat`)
- **OpenAI** (`gpt-4o-mini`, `gpt-4o`)
- **Gemini (Google)** (`gemini-2.5-flash`, `gemini-2.5-pro`)
- **OpenRouter** (`google/gemini-2.5-flash`, `anthropic/claude-3.5-sonnet` vb.)
- **Kimi (Moonshot AI)** (`moonshot-v1-8k`)
- **Grok (xAI)** (`grok-2-latest`)
- **Qwen (Alibaba DashScope)** (`qwen-plus`, `qwen-max`)
- **Custom (Özel OpenAI-uyumlu Endpoint'ler)**

*Her servis için girilen API Key ve model tercihleri `config.json` dosyasında ayrı ayrı saklanır.*

---

## 📌 Arayüz Yapısı (Sekmeli Görünüm)

### 🌐 Çift Dilli Arayüz Desteği (TR / EN)
Masaüstü arayüzünün sağ üst köşesinde **TR | EN** dil geçişi mevcuttur. İstediğiniz zaman arayüz dilini Türkçe veya İngilizceye anlık olarak değiştirebilirsiniz.

### 📥 Sekme 1: Makale İndirici
- **Girdi Seçenekleri**: Tekil makale URL'si, Medium kullanıcı adı (`@kullanici`), RSS akışı veya toplu metin dosyası (`.txt`).
- **Proxy Otomatik Geçiş**: Ödeme duvarı ve DNS engellerini aşan proxy zinciri (`Freedium` -> `ReadMedium` -> `Doğrudan`).
- **Çoklu İş Parçacığı (Multi-threading)**: `ThreadPoolExecutor` ile hızlı toplu indirme.
- **Yerel Görsel Arşivleme**: Görseller `articles/<kategori>/images/` dizinine indirilir ve bağlantılar yerel yollarla (`./images/img_...`) değiştirilir.

### 🤖 Sekme 2: Multi-AI Editor & İngilizce Yeniden Yazım
- **İndirilmiş Makale Seçici**: İndirilen makaleleri kategorilerine göre listeleyin ve orijinal metni sol panelde canlı önizleyin.
- **AI Dönüştürücü**: Seçilen makaleyi tercih ettiğiniz AI servisi ile tek tıkla analiz edip İngilizceye genişleterek `_en.md` olarak kaydedin.

---

## 🛠️ Kurulum

1. **Repoyu klonlayın:**
   ```bash
   git clone https://github.com/yonetici/medium-scraper-pro.git
   cd medium-scraper-pro
   ```

2. **Gerekli paketleri yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Kullanım

### 1. Masaüstü Arayüzü (GUI)

Arayüzü başlatmak için:

```bash
python mediumParse.py
```

### 2. Komut Satırı Kullanımı (CLI)

```bash
# OpenAI gpt-4o-mini ile çalıştırma:
python mediumParse.py -u "https://medium.com/@welifiliz/kurumsal-d%C3%BCnyada-react-ekosistemi-233776774cea" -c yazilim --rewrite-en --ai-provider "OpenAI" --ai-model "gpt-4o-mini" --api-key "sk-..."

# Gemini ile çalıştırma:
python mediumParse.py -u "https://medium.com/@welifiliz" -c genel --rewrite-en --ai-provider "Gemini" --api-key "AIzaSy..."
```

---

## 📄 Lisans

MIT Lisansı ile lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakabilirsiniz.
