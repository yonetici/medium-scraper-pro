"""
Localization and internationalization dictionary for Medium Scraper Pro.
Supports Turkish (TR) and English (EN).
"""

TRANSLATIONS = {
    "TR": {
        "title": "Medium Makale İndirici & Multi-AI Editor Pro",
        "tab_scraper": "📥 Makale İndirici",
        "tab_ai": "🤖 Multi-AI Editor & İngilizce Yeniden Yazım",
        "url_label": "Profil URL'si (@kullanici), Makale Linki veya RSS:",
        "url_placeholder": "https://medium.com/@kullanici veya makale URL",
        "batch_btn": "Toplu Dosya Seç (.txt)",
        "category_label": "Kategori Klasörü:",
        "format_label": "Çıktı Formatı:",
        "download_imgs": "Görselleri Yerel Dizine İndir (images/)",
        "threads_label": "Eşzamanlı İş Parçacığı:",
        "fetch_btn": "Makaleleri Çek ve Kaydet",
        "open_folder": "Makaleler Klasörünü Aç",
        "download_log": "İndirme Günlüğü",
        "ai_settings_title": "AI Sağlayıcısı ve Ayarları",
        "ai_service": "AI Servisi:",
        "model_label": "Model İsmi:",
        "api_key": "API Key:",
        "save_settings": "Ayarları Kaydet",
        "downloaded_articles_title": "İndirilmiş Makaleler",
        "category": "Kategori:",
        "article_label": "Makale Seç:",
        "refresh_btn": "Yenile",
        "ai_output_title": "AI Çıktı Paneli",
        "convert_btn": "✨ Seçili Makaleyi Seçilen AI ile Geliştir & İngilizce Yaz",
        "ui_lang": "Arayüz Dili / UI Language:",
        "ready_msg": "Arayüz hazır. Lütfen bir URL girin veya toplu dosya seçin.",
        "no_articles_cat": "Bu kategoride henüz indirilmiş makale yok.",
        "select_file_warn": "Lütfen bir URL girin veya toplu dosya seçin.",
        "key_saved_msg": "{provider} ayarları config.json dosyasına kaydedildi!",
        "key_missing_warn": "Lütfen {provider} için bir API Key girin.",
        "no_art_selected_warn": "Lütfen dönüştürülecek bir makale seçin.",
        "ai_processing_msg": "[{provider} AI - {model}] Makale analiz ediliyor, eksikler tamamlanıyor ve İngilizceye çevriliyor...\nLütfen bekleyin (10-30 saniye)...",
        "ai_saved_msg": "İngilizce makale ({provider}) kaydedildi:\n{filename}"
    },
    "EN": {
        "title": "Medium Scraper & Multi-AI Editor Pro",
        "tab_scraper": "📥 Article Downloader",
        "tab_ai": "🤖 Multi-AI Editor & English Rewriter",
        "url_label": "Profile URL (@username), Article Link, or RSS:",
        "url_placeholder": "https://medium.com/@username or article URL",
        "batch_btn": "Select Batch File (.txt)",
        "category_label": "Category Folder:",
        "format_label": "Output Format:",
        "download_imgs": "Download Images Locally (images/)",
        "threads_label": "Concurrent Threads:",
        "fetch_btn": "Fetch & Save Articles",
        "open_folder": "Open Articles Folder",
        "download_log": "Download Logs",
        "ai_settings_title": "AI Provider & Settings",
        "ai_service": "AI Service:",
        "model_label": "Model Name:",
        "api_key": "API Key:",
        "save_settings": "Save Settings",
        "downloaded_articles_title": "Downloaded Articles",
        "category": "Category:",
        "article_label": "Select Article:",
        "refresh_btn": "Refresh",
        "ai_output_title": "AI Output Panel",
        "convert_btn": "✨ Analyze, Expand & Rewrite Selected Article in English",
        "ui_lang": "UI Language / Arayüz Dili:",
        "ready_msg": "UI Ready. Please enter a URL or select a batch file.",
        "no_articles_cat": "No downloaded articles found in this category.",
        "select_file_warn": "Please enter a URL or select a batch file.",
        "key_saved_msg": "{provider} settings saved to config.json!",
        "key_missing_warn": "Please enter an API Key for {provider}.",
        "no_art_selected_warn": "Please select an article to convert.",
        "ai_processing_msg": "[{provider} AI - {model}] Analyzing article, filling gaps, and rewriting in native English...\nPlease wait (10-30 seconds)...",
        "ai_saved_msg": "English article ({provider}) saved successfully:\n{filename}"
    }
}


def get_text(key: str, lang: str = "TR") -> str:
    """Returns localized string for the specified key and language (TR/EN)."""
    lang_dict = TRANSLATIONS.get(lang.upper(), TRANSLATIONS["TR"])
    return lang_dict.get(key, TRANSLATIONS["TR"].get(key, key))
