# Medium Scraper & Multi-AI Publisher Pro (Türkçe)

[🇺🇸 English Documentation](README.md) | [🇹🇷 Türkçe Dokümantasyon](README.tr.md)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GUI: CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![AI: Multi--Provider](https://img.shields.io/badge/AI-OpenAI_|_Gemini_|_DeepSeek_|_OpenRouter_|_Kimi_|_Grok_|_Qwen-deepskyblue.svg)](https://www.openai.com/)

Python ve CustomTkinter ile geliştirilmiş gelişmiş bir **Medium Makale İndirici, Çoklu AI Editör & SEO/Sosyal Medya Yayınlama Studio**. **3 Sekmeli Masaüstü Arayüzü** ve **TR/EN Çift Dil Geçişi** ile makaleleri indirir, görselleri yerel dizine kaydeder, indirilen yazıları major AI servisleri (**OpenAI**, **Gemini**, **DeepSeek**, **OpenRouter**, **Kimi**, **Grok**, **Qwen**) kullanarak analiz edip akıcı native İngilizceye dönüştürür ve tek tıkla **SEO & Sosyal Medya Paketleri** (Twitter Thread, LinkedIn, Instagram, Bülten) üretir.

---

## ✨ Temel Özellikler

### 🌐 Çift Dilli Arayüz Desteği (TR / EN)
Masaüstü arayüzünün sağ üst köşesinde **TR | EN** dil geçişi mevcuttur. İstediğiniz zaman arayüz dilini Türkçe veya İngilizceye anlık olarak değiştirebilirsiniz.

### 🤖 Çoklu AI Servis Desteği ve Canlı Model Çekme
Seçilen yapay zeka servisi makaleyi analiz eder, anlatım boşluklarını ve eksik teknik detayları/kod örneklerini tespit eder, güncel en iyi pratiklerle (best practices) zenginleştirerek profesyonel İngilizceye dönüştürür.
- **DeepSeek** (`deepseek-chat`)
- **OpenAI** (`gpt-4o-mini`, `gpt-4o`)
- **Gemini (Google)** (`gemini-2.5-flash`, `gemini-2.5-pro`)
- **OpenRouter** (`google/gemini-2.5-flash`, `anthropic/claude-3.5-sonnet` vb.)
- **Kimi (Moonshot AI)** (`moonshot-v1-8k`)
- **Grok (xAI)** (`grok-2-latest`)
- **Qwen (Alibaba DashScope)** (`qwen-plus`, `qwen-max`)
- **Custom (Özel OpenAI-uyumlu Endpoint'ler)**

---

## 📌 3 Sekmeli Arayüz Yapısı

### 📥 Sekme 1: Makale İndirici
- **Girdi Seçenekleri**: Tekil makale URL'si, Medium kullanıcı adı (`@kullanici`), RSS akışı veya toplu metin dosyası (`.txt`).
- **Proxy Otomatik Geçiş**: Ödeme duvarı ve DNS engellerini aşan proxy zinciri (`Freedium` -> `ReadMedium` -> `Doğrudan`).
- **Çoklu İş Parçacığı (Multi-threading)**: `ThreadPoolExecutor` ile hızlı toplu indirme.
- **Yerel Görsel Arşivleme**: Görseller `articles/<kategori>/images/` dizinine indirilir ve bağlantılar yerel yollarla (`./images/img_...`) değiştirilir.

### 🤖 Sekme 2: Multi-AI Editor & İngilizce Yeniden Yazım
- **İndirilmiş Makale Seçici**: İndirilen makaleleri kategorilerine göre listeleyin ve orijinal metni sol panelde canlı önizleyin.
- **AI Dönüştürücü**: Seçilen makaleyi tercih ettiğiniz AI servisi ile tek tıkla analiz edip İngilizceye genişleterek `_en.md` olarak kaydedin.
- **Otomatik Kayıt & Parola Göster/Gizle**: API Key'ler kalıcı hafızada tutulur ve göz ikonu (`👁️`) ile kontrol edilebilir.

### 📊 Sekme 3: SEO & Sosyal Medya Studio (YENİ!)
- **SEO & Metadata Paketi**: 5 CTR odaklı H1 başlık alternatifi, Meta Description (açıklama), odak anahtar kelimeler, okuma süresi ve Schema.org JSON-LD verisi.
- **Twitter/X Thread**: 5-7 tweetlik numaralı, emojili ve etiketli paylaşım zinciri.
- **LinkedIn Gönderisi**: Profesyonel hikaye anlatımı dilinde gönderi taslağı.
- **Instagram & Threads Açıklaması**: Görsel altı ilgi çekici özet metin.
- **E-Posta Bülteni (Newsletter)**: Substack / Mailchimp için konu başlığı ve giriş metni.
- **Hızlı Pano Kopyalama**: Tek tıkla Twitter, LinkedIn veya SEO paketini panoya kopyalama ve `_social.md` olarak kaydetme.

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

---

## 📄 Lisans

MIT Lisansı ile lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakabilirsiniz.
