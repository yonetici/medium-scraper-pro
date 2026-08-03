import json
import os
import queue
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
    from tkinter import filedialog, messagebox
    HAS_TKINTER = True
except Exception:
    HAS_TKINTER = False


from core.image_downloader import localize_markdown_images
from core.parser import build_markdown_with_frontmatter
from core.scraper import MediumScraperCore
from utils.helpers import (
    ROOT, load_config, generate_unique_filename,
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
            raise RuntimeError("Tkinter/CustomTkinter kütüphanesi bu Python ortamında yüklü değil. Lütfen CLI modunu kullanın (ör: python mediumParse.py -u <URL>).")
        super().__init__()


        self.title("Medium Makale & İçerik İndirici (SEO/GEO Ready)")
        self.geometry("780x720")
        self.minsize(720, 640)

        self.config_data = load_config()
        self.msg_queue = queue.Queue()
        self.batch_urls = []

        self.setup_ui()
        self.after(100, self.poll_queue)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Başlık & Banner
        title_label = ctk.CTkLabel(
            self,
            text="Medium Makale & Profil İndirici",
            font=ctk.CTkFont(size=22, weight="bold")
        ) if HAS_CTK else ctk.Label(self, text="Medium Makale & Profil İndirici", font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # 2. Girdi Alanı (URL veya Toplu Dosya)
        input_frame = ctk.CTkFrame(self) if HAS_CTK else ctk.LabelFrame(self, text="Girdi")
        input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
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
        self.batch_status_label.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

        # 3. Ayarlar (Format, Kategori, Görsel İndirme, Threads)
        settings_frame = ctk.CTkFrame(self) if HAS_CTK else ctk.LabelFrame(self, text="Ayarlar")
        settings_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        settings_frame.grid_columnconfigure((1, 3), weight=1)

        # Kategori
        cat_label = ctk.CTkLabel(settings_frame, text="Kategori Klasörü:") if HAS_CTK else ctk.Label(settings_frame, text="Kategori:")
        cat_label.grid(row=0, column=0, padx=(15, 5), pady=12, sticky="w")

        self.category_var = ctk.StringVar(value="genel")
        self.category_combo = ctk.CTkComboBox(
            settings_frame,
            variable=self.category_var,
            values=self.get_local_categories()
        ) if HAS_CTK else ctk.Entry(settings_frame, textvariable=self.category_var)
        self.category_combo.grid(row=0, column=1, padx=5, pady=12, sticky="ew")

        # Format
        fmt_label = ctk.CTkLabel(settings_frame, text="Çıktı Formatı:") if HAS_CTK else ctk.Label(settings_frame, text="Format:")
        fmt_label.grid(row=0, column=2, padx=(15, 5), pady=12, sticky="w")

        self.format_var = ctk.StringVar(value="md")
        self.format_combo = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.format_var,
            values=["md", "txt", "json"]
        ) if HAS_CTK else ctk.Entry(settings_frame, textvariable=self.format_var)
        self.format_combo.grid(row=0, column=3, padx=(5, 15), pady=12, sticky="ew")

        # Görselleri Yerel İndir
        self.download_images_var = ctk.BooleanVar(value=self.config_data.get("download_images", False))
        self.img_switch = ctk.CTkSwitch(
            settings_frame,
            text="Görselleri Yerel Dizine İndir (images/)",
            variable=self.download_images_var
        ) if HAS_CTK else ctk.Checkbutton(settings_frame, text="Görselleri İndir", variable=self.download_images_var)
        self.img_switch.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="w")

        # Eşzamanlı İş Parçacığı (Threads)
        threads_label = ctk.CTkLabel(settings_frame, text="Eşzamanlı İş Parçacığı:") if HAS_CTK else ctk.Label(settings_frame, text="Threads:")
        threads_label.grid(row=1, column=2, padx=(15, 5), pady=(0, 12), sticky="w")

        self.threads_var = ctk.StringVar(value=str(self.config_data.get("max_concurrent_threads", 5)))
        self.threads_combo = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.threads_var,
            values=["1", "2", "3", "5", "8", "10"]
        ) if HAS_CTK else ctk.Entry(settings_frame, textvariable=self.threads_var)
        self.threads_combo.grid(row=1, column=3, padx=(5, 15), pady=(0, 12), sticky="ew")

        # 4. Çalıştırma & İlerleme Alanı
        action_frame = ctk.CTkFrame(self, fg_color="transparent") if HAS_CTK else ctk.Frame(self)
        action_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
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

        # 5. İşlem Günlüğü (Log)
        log_frame = ctk.CTkFrame(self) if HAS_CTK else ctk.LabelFrame(self, text="Log")
        log_frame.grid(row=4, column=0, padx=20, pady=(5, 15), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        if HAS_CTK:
            self.log_area = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Courier", size=12))
            self.log_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.log_area = st.ScrolledText(log_frame, wrap="word", height=12)
            self.log_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.log_direct("Arayüz hazır. Lütfen bir URL girin veya toplu dosya seçin.")

    def get_local_categories(self):
        categories = ["genel"]
        if MAKALELER_DIR.exists():
            for p in MAKALELER_DIR.iterdir():
                if p.is_dir() and p.name != "images":
                    categories.append(p.name)
        return sorted(list(set(categories)))

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
        if HAS_CTK:
            self.log_area.insert("end", text)
            self.log_area.see("end")
        else:
            self.log_area.insert("end", text)
            self.log_area.see("end")

    def poll_queue(self):
        try:
            while True:
                msg_type, payload = self.msg_queue.get_nowait()
                if msg_type == "log":
                    if HAS_CTK:
                        self.log_area.insert("end", payload)
                        self.log_area.see("end")
                    else:
                        self.log_area.insert("end", payload)
                        self.log_area.see("end")
                elif msg_type == "progress" and self.progress_bar:
                    self.progress_bar.set(payload)
                elif msg_type == "done":
                    self.fetch_btn.configure(state="normal")
                    if self.progress_bar:
                        self.progress_bar.set(1.0)
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
        
        # Thread ile çalıştır
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

            # 1. Toplu Dosyadan URL'ler Yüklendiyse
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

            # 2. Tekil Profil veya RSS ise
            elif is_profile_url(target_input):
                logger.log(f"Profil/RSS beslemesi taranıyor: {target_input}")
                articles_to_save = scraper.fetch_user_rss(target_input)

            # 3. Tekil Makale URL'si ise
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

                # Görselleri Yerel Dizine İndir
                if download_imgs and markdown_content:
                    logger.log(f"[{idx}/{len(articles_to_save)}] Görseller indiriliyor...")
                    markdown_content, img_cnt = localize_markdown_images(markdown_content, category_dir, logger)
                    if img_cnt > 0:
                        logger.log(f"[Görsel] {img_cnt} adet görsel indirildi ve yerelleştirildi.")

                # Dosyaya Kaydet
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
