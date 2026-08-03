import json
import os
import queue
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    HAS_CTK = True
except Exception:
    HAS_CTK = False

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TKINTER = True
except Exception:
    HAS_TKINTER = False

from core.ai_rewriter import DeepSeekRewriter
from core.image_downloader import localize_markdown_images
from core.parser import build_markdown_with_frontmatter
from core.scraper import MediumScraperCore
from utils.helpers import (
    ROOT, CONFIG_PATH, load_config, generate_unique_filename,
    is_article_url, is_profile_url
)

MAKALELER_DIR = ROOT / "articles"
MAKALELER_DIR.mkdir(parents=True, exist_ok=True)


class ThreadSafeQueueLogger:
    def __init__(self, msg_queue: queue.Queue):
        self.msg_queue = msg_queue

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.msg_queue.put(("log", f"[{timestamp}] {message}\n"))

    def progress(self, val: float):
        self.msg_queue.put(("progress", val))

    def done(self, message: str = ""):
        if message:
            self.log(message)
        self.msg_queue.put(("done", None))

    def error(self, err_msg: str):
        self.log(f"[HATA] {err_msg}")
        self.msg_queue.put(("error", err_msg))


BaseAppClass = ctk.CTk if HAS_CTK else (tk.Tk if HAS_TKINTER else object)


class ModernMediumScraperApp(BaseAppClass):
    def __init__(self):
        if not HAS_TKINTER and not HAS_CTK:
            raise RuntimeError("Tkinter/CustomTkinter kütüphanesi bu Python ortamında yüklü değil.")
        super().__init__()

        self.title("Medium Makale İndirici & DeepSeek AI Editor Pro")
        self.geometry("940x780")
        self.minsize(880, 680)

        self.config_data = load_config()
        self.msg_queue = queue.Queue()
        self.batch_urls = []
        self.articles_cache = {}

        self.setup_ui()
        self.after(100, self.poll_queue)

    def setup_ui(self):
        if HAS_CTK:
            self.tabview = ctk.CTkTabview(self)
            self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

            self.tab_scraper = self.tabview.add("📥 Makale İndirici")
            self.tab_ai = self.tabview.add("🤖 AI Editor & İngilizce Yeniden Yazım")
        else:
            self.notebook = ttk.Notebook(self)
            self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
            self.tab_scraper = ttk.Frame(self.notebook)
            self.tab_ai = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_scraper, text="Makale İndirici")
            self.notebook.add(self.tab_ai, text="AI Editor")

        self.build_scraper_tab()
        self.build_ai_editor_tab()

    # ---------------------------------------------------------------------------
    # SEKME 1: MAKALE İNDİRİCİ
    # ---------------------------------------------------------------------------
    def build_scraper_tab(self):
        tab = self.tab_scraper
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(4, weight=1)

        # Girdi Alanı
        input_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="Girdi")
        input_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        url_label = ctk.CTkLabel(
            input_frame,
            text="Profil URL'si (@kullanici), Makale Linki veya RSS:",
            font=ctk.CTkFont(size=13)
        ) if HAS_CTK else ctk.Label(input_frame, text="Profil/Makale URL:")
        url_label.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

        self.url_var = ctk.StringVar(value="https://medium.com/@welifiliz")
        self.url_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.url_var,
            placeholder_text="https://medium.com/@kullanici veya makale URL"
        ) if HAS_CTK else ctk.Entry(input_frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        batch_btn = ctk.CTkButton(
            input_frame,
            text="Toplu Dosya Seç (.txt)",
            command=self.select_batch_file,
            width=140
        ) if HAS_CTK else ctk.Button(input_frame, text="Toplu Dosya Seç", command=self.select_batch_file)
        batch_btn.grid(row=1, column=1, padx=(0, 15), pady=5)

        self.batch_status_label = ctk.CTkLabel(
            input_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ) if HAS_CTK else ctk.Label(input_frame, text="")
        self.batch_status_label.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")

        # Ayarlar
        settings_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="Ayarlar")
        settings_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        settings_frame.grid_columnconfigure((1, 3), weight=1)

        cat_label = ctk.CTkLabel(settings_frame, text="Kategori Klasörü:") if HAS_CTK else ctk.Label(settings_frame, text="Kategori:")
        cat_label.grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")

        self.category_var = ctk.StringVar(value="genel")
        self.category_combo = ctk.CTkComboBox(
            settings_frame,
            variable=self.category_var,
            values=self.get_local_categories()
        ) if HAS_CTK else ctk.Entry(settings_frame, textvariable=self.category_var)
        self.category_combo.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        fmt_label = ctk.CTkLabel(settings_frame, text="Çıktı Formatı:") if HAS_CTK else ctk.Label(settings_frame, text="Format:")
        fmt_label.grid(row=0, column=2, padx=(15, 5), pady=10, sticky="w")

        self.format_var = ctk.StringVar(value="md")
        self.format_combo = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.format_var,
            values=["md", "txt", "json"]
        ) if HAS_CTK else ctk.Entry(settings_frame, textvariable=self.format_var)
        self.format_combo.grid(row=0, column=3, padx=(5, 15), pady=10, sticky="ew")

        self.download_images_var = ctk.BooleanVar(value=self.config_data.get("download_images", False))
        self.img_switch = ctk.CTkSwitch(
            settings_frame,
            text="Görselleri Yerel Dizine İndir (images/)",
            variable=self.download_images_var
        ) if HAS_CTK else ctk.Checkbutton(settings_frame, text="Görselleri İndir", variable=self.download_images_var)
        self.img_switch.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

        threads_label = ctk.CTkLabel(settings_frame, text="Eşzamanlı İş Parçacığı:") if HAS_CTK else ctk.Label(settings_frame, text="Threads:")
        threads_label.grid(row=1, column=2, padx=(15, 5), pady=(0, 10), sticky="w")

        self.threads_var = ctk.StringVar(value=str(self.config_data.get("max_concurrent_threads", 5)))
        self.threads_combo = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.threads_var,
            values=["1", "2", "3", "5", "8", "10"]
        ) if HAS_CTK else ctk.Entry(settings_frame, textvariable=self.threads_var)
        self.threads_combo.grid(row=1, column=3, padx=(5, 15), pady=(0, 10), sticky="ew")

        # Butonlar
        action_frame = ctk.CTkFrame(tab, fg_color="transparent") if HAS_CTK else ctk.Frame(tab)
        action_frame.grid(row=2, column=0, padx=15, pady=8, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.fetch_btn = ctk.CTkButton(
            action_frame,
            text="Makaleleri Çek ve Kaydet",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#219150",
            height=42,
            command=self.start_fetch
        ) if HAS_CTK else ctk.Button(action_frame, text="Makaleleri Çek ve Kaydet", command=self.start_fetch)
        self.fetch_btn.grid(row=0, column=0, sticky="ew")

        self.open_folder_btn = ctk.CTkButton(
            action_frame,
            text="Makaleler Klasörünü Aç",
            height=42,
            command=self.open_articles_folder
        ) if HAS_CTK else ctk.Button(action_frame, text="Klasörü Aç", command=self.open_articles_folder)
        self.open_folder_btn.grid(row=0, column=1, padx=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(action_frame) if HAS_CTK else None
        if self.progress_bar:
            self.progress_bar.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="ew")
            self.progress_bar.set(0)

        # Log Alanı
        log_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="İndirme Günlüğü")
        log_frame.grid(row=4, column=0, padx=15, pady=(5, 15), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        if HAS_CTK:
            self.log_area = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Courier", size=12))
            self.log_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.log_area = st.ScrolledText(log_frame, wrap="word", height=12)
            self.log_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # ---------------------------------------------------------------------------
    # SEKME 2: AI EDITOR & İNGİLİZCE YENİDEN YAZIM
    # ---------------------------------------------------------------------------
    def build_ai_editor_tab(self):
        tab = self.tab_ai
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Üst Ayarlar: API Key & Kategori Seçici
        top_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="DeepSeek Ayarları")
        top_frame.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)

        key_label = ctk.CTkLabel(top_frame, text="DeepSeek API Key:", font=ctk.CTkFont(weight="bold")) if HAS_CTK else ctk.Label(top_frame, text="API Key:")
        key_label.grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")

        self.ai_api_key_var = ctk.StringVar(value=self.config_data.get("deepseek_api_key", ""))
        self.ai_api_key_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.ai_api_key_var,
            placeholder_text="sk-...",
            show="*"
        ) if HAS_CTK else ctk.Entry(top_frame, textvariable=self.ai_api_key_var, show="*")
        self.ai_api_key_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        save_key_btn = ctk.CTkButton(
            top_frame,
            text="Anahtarı Kaydet",
            width=120,
            command=self.save_ai_key_click
        ) if HAS_CTK else ctk.Button(top_frame, text="Kaydet", command=self.save_ai_key_click)
        save_key_btn.grid(row=0, column=2, padx=(5, 15), pady=10)

        # Sol Panel: İndirilmiş Makale Seçici & Orijinal Metin Önizleme
        left_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="İndirilmiş Makaleler")
        left_frame.grid(row=1, column=0, padx=(15, 5), pady=5, sticky="nsew")
        left_frame.grid_columnconfigure(1, weight=1)
        left_frame.grid_rowconfigure(2, weight=1)

        cat_sel_label = ctk.CTkLabel(left_frame, text="Kategori:") if HAS_CTK else ctk.Label(left_frame, text="Kategori:")
        cat_sel_label.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")

        self.ai_category_var = ctk.StringVar(value="genel")
        self.ai_category_combo = ctk.CTkComboBox(
            left_frame,
            variable=self.ai_category_var,
            values=self.get_local_categories(),
            command=self.on_ai_category_change
        ) if HAS_CTK else ctk.Entry(left_frame, textvariable=self.ai_category_var)
        self.ai_category_combo.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        refresh_files_btn = ctk.CTkButton(
            left_frame,
            text="Yenile",
            width=70,
            command=self.refresh_ai_article_list
        ) if HAS_CTK else ctk.Button(left_frame, text="Yenile", command=self.refresh_ai_article_list)
        refresh_files_btn.grid(row=0, column=2, padx=(5, 10), pady=8)

        art_sel_label = ctk.CTkLabel(left_frame, text="Makale Seç:") if HAS_CTK else ctk.Label(left_frame, text="Makale:")
        art_sel_label.grid(row=1, column=0, padx=(10, 5), pady=(0, 8), sticky="w")

        self.ai_article_var = ctk.StringVar(value="Makale seçin...")
        self.ai_article_combo = ctk.CTkOptionMenu(
            left_frame,
            variable=self.ai_article_var,
            values=["(Makale bulunamadı)"],
            command=self.on_ai_article_selected
        ) if HAS_CTK else ctk.Entry(left_frame, textvariable=self.ai_article_var)
        self.ai_article_combo.grid(row=1, column=1, columnspan=2, padx=(5, 10), pady=(0, 8), sticky="ew")

        if HAS_CTK:
            self.ai_orig_preview = ctk.CTkTextbox(left_frame, font=ctk.CTkFont(size=12))
            self.ai_orig_preview.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.ai_orig_preview = st.ScrolledText(left_frame, wrap="word", height=15)
            self.ai_orig_preview.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")

        # Sağ Panel: AI Çalıştırma & İngilizce Çıktı Önizleme
        right_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="DeepSeek AI Çıktısı")
        right_frame.grid(row=1, column=1, padx=(5, 15), pady=5, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        self.ai_convert_btn = ctk.CTkButton(
            right_frame,
            text="✨ Seçili Makaleyi DeepSeek ile Geliştir & İngilizce Yaz",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#8e44ad",
            hover_color="#732d91",
            height=38,
            command=self.start_ai_rewrite_single
        ) if HAS_CTK else ctk.Button(right_frame, text="DeepSeek ile İngilizce Yaz", command=self.start_ai_rewrite_single)
        self.ai_convert_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        if HAS_CTK:
            self.ai_output_preview = ctk.CTkTextbox(right_frame, font=ctk.CTkFont(size=12))
            self.ai_output_preview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.ai_output_preview = st.ScrolledText(right_frame, wrap="word", height=15)
            self.ai_output_preview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Tab yüklenince makale listesini doldur
        self.refresh_ai_article_list()

    # ---------------------------------------------------------------------------
    # SEKMELER ARASI MANTIKSAL İŞLEVLER
    # ---------------------------------------------------------------------------
    def get_local_categories(self):
        categories = ["genel"]
        if MAKALELER_DIR.exists():
            for p in MAKALELER_DIR.iterdir():
                if p.is_dir() and p.name not in ["images", "rewritten"]:
                    categories.append(p.name)
        return sorted(list(set(categories)))

    def on_ai_category_change(self, choice=None):
        self.refresh_ai_article_list()

    def refresh_ai_article_list(self):
        cat = self.ai_category_var.get().strip() or "genel"
        cat_dir = MAKALELER_DIR / cat
        self.articles_cache = {}

        if cat_dir.exists():
            for p in cat_dir.glob("*.*"):
                if p.is_file() and p.suffix in [".md", ".json", ".txt"] and not p.name.endswith("_en.md"):
                    self.articles_cache[p.name] = p

        files = sorted(list(self.articles_cache.keys()))
        if files:
            if HAS_CTK:
                self.ai_article_combo.configure(values=files)
            self.ai_article_var.set(files[0])
            self.on_ai_article_selected(files[0])
        else:
            if HAS_CTK:
                self.ai_article_combo.configure(values=["(Makale bulunamadı)"])
            self.ai_article_var.set("(Makale bulunamadı)")
            self.ai_orig_preview.delete("1.0", "end")
            self.ai_orig_preview.insert("1.0", "Bu kategoride henüz indirilmiş makale yok.")

    def on_ai_article_selected(self, choice):
        if choice in self.articles_cache:
            file_path = self.articles_cache[choice]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.ai_orig_preview.delete("1.0", "end")
                self.ai_orig_preview.insert("1.0", content[:3000] + ("\n\n... (devamı var)" if len(content) > 3000 else ""))
            except Exception as e:
                self.ai_orig_preview.delete("1.0", "end")
                self.ai_orig_preview.insert("1.0", f"Dosya okunamadı: {e}")

    def save_ai_key_click(self):
        key_val = self.ai_api_key_var.get().strip()
        if not key_val:
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir API Key girin.")
            return
        self.config_data["deepseek_api_key"] = key_val
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Başarılı", "DeepSeek API Key config.json dosyasına kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydedilemedi: {e}")

    def start_ai_rewrite_single(self):
        api_key = self.ai_api_key_var.get().strip()
        selected_filename = self.ai_article_var.get()
        cat = self.ai_category_var.get().strip() or "genel"

        if not api_key:
            messagebox.showwarning("API Key Eksik", "Lütfen DeepSeek API Key girin.")
            return

        if selected_filename not in self.articles_cache:
            messagebox.showwarning("Makale Seçilmedi", "Lütfen dönüştürülecek bir makale seçin.")
            return

        file_path = self.articles_cache[selected_filename]
        self.ai_convert_btn.configure(state="disabled")
        self.ai_output_preview.delete("1.0", "end")
        self.ai_output_preview.insert("1.0", "[DeepSeek AI] Makale analiz ediliyor, eksikler tamamlanıyor ve İngilizceye çevriliyor...\nLütfen bekleyin (10-30 saniye)...")

        def _worker():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                title = file_path.stem
                orig_url = ""

                # Frontmatter veya JSON okuma
                if file_path.suffix == ".json":
                    try:
                        jdata = json.loads(raw_content)
                        title = jdata.get("metadata", {}).get("title", title)
                        orig_url = jdata.get("metadata", {}).get("original_url", "")
                        raw_content = jdata.get("content_markdown", raw_content)
                    except Exception:
                        pass
                else:
                    title_match = re.search(r'title:\s*"(.*?)"', raw_content)
                    if title_match:
                        title = title_match.group(1)
                    url_match = re.search(r'original_url:\s*"(.*?)"', raw_content)
                    if url_match:
                        orig_url = url_match.group(1)

                metadata = {"title": title, "original_url": orig_url, "author": ""}
                rewriter = DeepSeekRewriter(api_key=api_key)
                rewritten_md = rewriter.rewrite_and_expand_article(raw_content, metadata)

                en_filename = f"{file_path.stem}_en.md"
                en_file_path = (MAKALELER_DIR / cat) / en_filename
                with open(en_file_path, "w", encoding="utf-8") as f:
                    f.write(rewritten_md)

                def _update_ui_success():
                    self.ai_output_preview.delete("1.0", "end")
                    self.ai_output_preview.insert("1.0", f"--- KAYDEDİLDİ: {cat}/{en_filename} ---\n\n" + rewritten_md)
                    self.ai_convert_btn.configure(state="normal")
                    messagebox.showinfo("Başarılı", f"İngilizce makale kaydedildi:\n{cat}/{en_filename}")

                self.after(0, _update_ui_success)

            except Exception as err:
                def _update_ui_error():
                    self.ai_output_preview.delete("1.0", "end")
                    self.ai_output_preview.insert("1.0", f"[HATA] DeepSeek AI İşlem Başarısız:\n{err}")
                    self.ai_convert_btn.configure(state="normal")
                    messagebox.showerror("Hata", str(err))

                self.after(0, _update_ui_error)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    # ---------------------------------------------------------------------------
    # ORTAK YARDIMCI İŞLEVLER (SEKME 1)
    # ---------------------------------------------------------------------------
    def select_batch_file(self):
        file_path = filedialog.askopenfilename(
            title="Toplu URL Dosyası Seç",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
                self.batch_urls = lines
                self.batch_status_label.configure(
                    text=f"Seçilen Dosya: {Path(file_path).name} ({len(lines)} bağlantı yüklendi)"
                )
                self.log_direct(f"[BİLGİ] {len(lines)} adet URL {Path(file_path).name} dosyasından yüklendi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Toplu dosya okunamadı: {e}")

    def log_direct(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = f"[{timestamp}] {message}\n"
        self.log_area.insert("end", text)
        self.log_area.see("end")

    def poll_queue(self):
        try:
            while True:
                msg_type, payload = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.log_area.insert("end", payload)
                    self.log_area.see("end")
                elif msg_type == "progress" and self.progress_bar:
                    self.progress_bar.set(payload)
                elif msg_type == "done":
                    self.fetch_btn.configure(state="normal")
                    if self.progress_bar:
                        self.progress_bar.set(1.0)
                    self.refresh_ai_article_list()
                elif msg_type == "error":
                    self.fetch_btn.configure(state="normal")
                    messagebox.showerror("Hata", payload)
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)

    def open_articles_folder(self):
        path = MAKALELER_DIR.resolve()
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])

    def start_fetch(self):
        target_input = self.url_var.get().strip()
        category = self.category_var.get().strip() or "genel"
        output_format = self.format_var.get().strip() or "md"
        download_imgs = self.download_images_var.get()
        max_threads = int(self.threads_var.get() or 5)

        if not target_input and not self.batch_urls:
            messagebox.showwarning("Uyarı", "Lütfen bir URL girin veya toplu dosya seçin.")
            return

        self.fetch_btn.configure(state="disabled")
        if self.progress_bar:
            self.progress_bar.set(0.1)

        logger = ThreadSafeQueueLogger(self.msg_queue)
        
        t = threading.Thread(
            target=self._run_scraping_process,
            args=(target_input, category, output_format, download_imgs, max_threads, logger),
            daemon=True
        )
        t.start()

    def _run_scraping_process(self, target_input, category, output_format, download_imgs, max_threads, logger):
        scraper = MediumScraperCore(logger=logger)
        category_dir = MAKALELER_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        try:
            articles_to_save = []

            if self.batch_urls:
                logger.log(f"{len(self.batch_urls)} adet toplu URL eşzamanlı çekiliyor ({max_threads} iş parçacığı)...")
                
                def on_progress(completed, total, msg):
                    logger.log(msg)
                    logger.progress(completed / max(total, 1))

                articles_to_save = scraper.fetch_batch_articles(
                    self.batch_urls,
                    max_workers=max_threads,
                    progress_callback=on_progress
                )

            elif is_profile_url(target_input):
                logger.log(f"Profil/RSS beslemesi taranıyor: {target_input}")
                articles_to_save = scraper.fetch_user_rss(target_input)

            elif is_article_url(target_input):
                logger.log(f"Tekil makale indiriliyor: {target_input}")
                article_data = scraper.fetch_single_article(target_input)
                articles_to_save = [article_data]

            else:
                raise Exception("Geçersiz girdi. Lütfen geçerli bir Medium makalesi veya profil adresi girin.")

            if not articles_to_save:
                raise Exception("Hiçbir makale çekilemedi.")

            total_saved = 0
            for idx, article in enumerate(articles_to_save, 1):
                title = article["title"]
                metadata = article["metadata"]
                markdown_content = article["content_markdown"]
                text_content = article["content_text"]
                orig_url = article.get("original_url", target_input)

                if download_imgs and markdown_content:
                    logger.log(f"[{idx}/{len(articles_to_save)}] Görseller indiriliyor...")
                    markdown_content, img_cnt = localize_markdown_images(markdown_content, category_dir, logger)
                    if img_cnt > 0:
                        logger.log(f"[Görsel] {img_cnt} adet görsel indirildi ve yerelleştirildi.")

                filename = generate_unique_filename(title, orig_url, extension=output_format)
                file_path = category_dir / filename

                if output_format == "md":
                    content_to_write = build_markdown_with_frontmatter(metadata, markdown_content)
                elif output_format == "txt":
                    content_to_write = f"Başlık: {title}\nYazar: {metadata.get('author')}\nTarih: {metadata.get('published_at')}\nURL: {orig_url}\n\n{text_content}"
                elif output_format == "json":
                    content_to_write = json.dumps({
                        "metadata": metadata,
                        "content_markdown": markdown_content,
                        "content_text": text_content
                    }, ensure_ascii=False, indent=2)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content_to_write)

                total_saved += 1
                logger.log(f"[KAYDEDİLDİ] {category}/{filename}")
                logger.progress(total_saved / len(articles_to_save))

            logger.done(f"İşlem Tamamlandı! Toplam {total_saved} makale '{category}' klasörüne kaydedildi.")

        except Exception as e:
            logger.error(str(e))
