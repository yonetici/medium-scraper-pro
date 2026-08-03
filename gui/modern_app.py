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

from core.ai_rewriter import MultiProviderAIRewriter, PROVIDERS_REGISTRY, fetch_provider_models
from core.seo_social_generator import SEOSocialGenerator
from core.image_downloader import localize_markdown_images
from core.parser import build_markdown_with_frontmatter
from core.scraper import MediumScraperCore
from utils.helpers import (
    ROOT, CONFIG_PATH, load_config, generate_unique_filename,
    is_article_url, is_profile_url
)
from utils.i18n import get_text

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

        self.config_data = load_config()
        self.current_lang = self.config_data.get("ui_language", "TR")
        self.msg_queue = queue.Queue()
        self.batch_urls = []
        self.articles_cache = {}
        self.seo_articles_cache = {}

        self.tab_key_scraper = "TAB_SCRAPER"
        self.tab_key_ai = "TAB_AI"
        self.tab_key_seo = "TAB_SEO"
        self.show_api_key_state = False

        self.geometry("1020x860")
        self.minsize(940, 740)

        self.setup_ui()
        self.apply_language()
        self.after(100, self.poll_queue)

    def t(self, key: str) -> str:
        """Localization string helper shortcut."""
        return get_text(key, self.current_lang)

    def setup_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent") if HAS_CTK else ctk.Frame(self)
        top_bar.pack(fill="x", padx=15, pady=(10, 0))
        top_bar.grid_columnconfigure(0, weight=1)

        self.app_title_label = ctk.CTkLabel(
            top_bar,
            text="",
            font=ctk.CTkFont(size=20, weight="bold")
        ) if HAS_CTK else ctk.Label(top_bar, text="", font=("Arial", 16, "bold"))
        self.app_title_label.grid(row=0, column=0, sticky="w")

        self.lang_hdr_label = ctk.CTkLabel(top_bar, text="Language / Dil:", font=ctk.CTkFont(size=12)) if HAS_CTK else ctk.Label(top_bar, text="Language / Dil:")
        self.lang_hdr_label.grid(row=0, column=1, padx=(10, 5), sticky="e")

        self.lang_var = ctk.StringVar(value=self.current_lang)
        self.lang_btn = ctk.CTkSegmentedButton(
            top_bar,
            values=["TR", "EN"],
            variable=self.lang_var,
            command=self.on_language_changed
        ) if HAS_CTK else ctk.Entry(top_bar, textvariable=self.lang_var)
        self.lang_btn.grid(row=0, column=2, sticky="e")

        # 3 Tab Setup
        if HAS_CTK:
            self.tabview = ctk.CTkTabview(self)
            self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

            self.tab_scraper = self.tabview.add(self.tab_key_scraper)
            self.tab_ai = self.tabview.add(self.tab_key_ai)
            self.tab_seo = self.tabview.add(self.tab_key_seo)
        else:
            self.notebook = ttk.Notebook(self)
            self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
            self.tab_scraper = ttk.Frame(self.notebook)
            self.tab_ai = ttk.Frame(self.notebook)
            self.tab_seo = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_scraper, text=self.tab_key_scraper)
            self.notebook.add(self.tab_ai, text=self.tab_key_ai)
            self.notebook.add(self.tab_seo, text=self.tab_key_seo)

        self.build_scraper_tab()
        self.build_ai_editor_tab()
        self.build_seo_social_tab()

    # ---------------------------------------------------------------------------
    # SEKME 1: MAKALE İNDİRİCİ
    # ---------------------------------------------------------------------------
    def build_scraper_tab(self):
        tab = self.tab_scraper
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(4, weight=1)

        self.input_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="Input")
        self.input_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.url_label = ctk.CTkLabel(
            self.input_frame,
            text="",
            font=ctk.CTkFont(size=13)
        ) if HAS_CTK else ctk.Label(self.input_frame, text="")
        self.url_label.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

        self.url_var = ctk.StringVar(value="https://medium.com/@welifiliz")
        self.url_entry = ctk.CTkEntry(
            self.input_frame,
            textvariable=self.url_var,
            placeholder_text=""
        ) if HAS_CTK else ctk.Entry(self.input_frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.batch_btn = ctk.CTkButton(
            self.input_frame,
            text="",
            command=self.select_batch_file,
            width=150
        ) if HAS_CTK else ctk.Button(self.input_frame, text="", command=self.select_batch_file)
        self.batch_btn.grid(row=1, column=1, padx=(0, 15), pady=5)

        self.batch_status_label = ctk.CTkLabel(
            self.input_frame,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ) if HAS_CTK else ctk.Label(self.input_frame, text="")
        self.batch_status_label.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")

        self.settings_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="Settings")
        self.settings_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.settings_frame.grid_columnconfigure((1, 3), weight=1)

        self.cat_label = ctk.CTkLabel(self.settings_frame, text="") if HAS_CTK else ctk.Label(self.settings_frame, text="")
        self.cat_label.grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")

        self.category_var = ctk.StringVar(value="genel")
        self.category_combo = ctk.CTkComboBox(
            self.settings_frame,
            variable=self.category_var,
            values=self.get_local_categories()
        ) if HAS_CTK else ctk.Entry(self.settings_frame, textvariable=self.category_var)
        self.category_combo.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.fmt_label = ctk.CTkLabel(self.settings_frame, text="") if HAS_CTK else ctk.Label(self.settings_frame, text="")
        self.fmt_label.grid(row=0, column=2, padx=(15, 5), pady=10, sticky="w")

        self.format_var = ctk.StringVar(value="md")
        self.format_combo = ctk.CTkOptionMenu(
            self.settings_frame,
            variable=self.format_var,
            values=["md", "txt", "json"]
        ) if HAS_CTK else ctk.Entry(self.settings_frame, textvariable=self.format_var)
        self.format_combo.grid(row=0, column=3, padx=(5, 15), pady=10, sticky="ew")

        self.download_images_var = ctk.BooleanVar(value=self.config_data.get("download_images", False))
        self.img_switch = ctk.CTkSwitch(
            self.settings_frame,
            text="",
            variable=self.download_images_var
        ) if HAS_CTK else ctk.Checkbutton(self.settings_frame, text="", variable=self.download_images_var)
        self.img_switch.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

        self.threads_label = ctk.CTkLabel(self.settings_frame, text="") if HAS_CTK else ctk.Label(self.settings_frame, text="")
        self.threads_label.grid(row=1, column=2, padx=(15, 5), pady=(0, 10), sticky="w")

        self.threads_var = ctk.StringVar(value=str(self.config_data.get("max_concurrent_threads", 5)))
        self.threads_combo = ctk.CTkOptionMenu(
            self.settings_frame,
            variable=self.threads_var,
            values=["1", "2", "3", "5", "8", "10"]
        ) if HAS_CTK else ctk.Entry(self.settings_frame, textvariable=self.threads_var)
        self.threads_combo.grid(row=1, column=3, padx=(5, 15), pady=(0, 10), sticky="ew")

        action_frame = ctk.CTkFrame(tab, fg_color="transparent") if HAS_CTK else ctk.Frame(tab)
        action_frame.grid(row=2, column=0, padx=15, pady=8, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.fetch_btn = ctk.CTkButton(
            action_frame,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#27ae60",
            hover_color="#219150",
            height=42,
            command=self.start_fetch
        ) if HAS_CTK else ctk.Button(action_frame, text="", command=self.start_fetch)
        self.fetch_btn.grid(row=0, column=0, sticky="ew")

        self.open_folder_btn = ctk.CTkButton(
            action_frame,
            text="",
            height=42,
            command=self.open_articles_folder
        ) if HAS_CTK else ctk.Button(action_frame, text="", command=self.open_articles_folder)
        self.open_folder_btn.grid(row=0, column=1, padx=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(action_frame) if HAS_CTK else None
        if self.progress_bar:
            self.progress_bar.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="ew")
            self.progress_bar.set(0)

        self.log_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="")
        self.log_frame.grid(row=4, column=0, padx=15, pady=(5, 15), sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        if HAS_CTK:
            self.log_area = ctk.CTkTextbox(self.log_frame, font=ctk.CTkFont(family="Courier", size=12))
            self.log_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.log_area = st.ScrolledText(self.log_frame, wrap="word", height=12)
            self.log_area.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # ---------------------------------------------------------------------------
    # SEKME 2: MULTI-AI EDITOR & İNGİLİZCE YENİDEN YAZIM
    # ---------------------------------------------------------------------------
    def build_ai_editor_tab(self):
        tab = self.tab_ai
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(2, weight=1)

        self.top_ai_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="")
        self.top_ai_frame.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        self.top_ai_frame.grid_columnconfigure((1, 3), weight=1)

        self.ai_service_label = ctk.CTkLabel(self.top_ai_frame, text="", font=ctk.CTkFont(weight="bold")) if HAS_CTK else ctk.Label(self.top_ai_frame, text="")
        self.ai_service_label.grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")

        selected_prov = self.config_data.get("selected_ai_provider", "DeepSeek")
        self.ai_provider_var = ctk.StringVar(value=selected_prov)
        self.ai_provider_combo = ctk.CTkOptionMenu(
            self.top_ai_frame,
            variable=self.ai_provider_var,
            values=["DeepSeek", "OpenAI", "Gemini", "OpenRouter", "Kimi", "Grok", "Qwen", "Custom"],
            command=self.on_ai_provider_changed
        ) if HAS_CTK else ctk.Entry(self.top_ai_frame, textvariable=self.ai_provider_var)
        self.ai_provider_combo.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.model_label = ctk.CTkLabel(self.top_ai_frame, text="") if HAS_CTK else ctk.Label(self.top_ai_frame, text="")
        self.model_label.grid(row=0, column=2, padx=(15, 5), pady=10, sticky="w")

        init_model = self.config_data.get("ai_provider_models", {}).get(selected_prov, "deepseek-chat")
        self.ai_model_var = ctk.StringVar(value=init_model)
        self.ai_model_combo = ctk.CTkComboBox(
            self.top_ai_frame,
            variable=self.ai_model_var,
            values=PROVIDERS_REGISTRY.get(selected_prov, {}).get("fallback_models", [init_model])
        ) if HAS_CTK else ctk.Entry(self.top_ai_frame, textvariable=self.ai_model_var)
        self.ai_model_combo.grid(row=0, column=3, padx=(5, 15), pady=10, sticky="ew")

        self.api_key_label = ctk.CTkLabel(self.top_ai_frame, text="") if HAS_CTK else ctk.Label(self.top_ai_frame, text="")
        self.api_key_label.grid(row=1, column=0, padx=(15, 5), pady=(0, 10), sticky="w")

        key_container = ctk.CTkFrame(self.top_ai_frame, fg_color="transparent") if HAS_CTK else ctk.Frame(self.top_ai_frame)
        key_container.grid(row=1, column=1, padx=5, pady=(0, 10), sticky="ew")
        key_container.grid_columnconfigure(0, weight=1)

        init_key = self.config_data.get("ai_provider_keys", {}).get(selected_prov, "")
        self.ai_api_key_var = ctk.StringVar(value=init_key)
        self.ai_api_key_entry = ctk.CTkEntry(
            key_container,
            textvariable=self.ai_api_key_var,
            placeholder_text="sk-...",
            show="*"
        ) if HAS_CTK else ctk.Entry(key_container, textvariable=self.ai_api_key_var, show="*")
        self.ai_api_key_entry.grid(row=0, column=0, sticky="ew")

        self.toggle_eye_btn = ctk.CTkButton(
            key_container,
            text="👁️",
            width=35,
            fg_color="gray30",
            hover_color="gray40",
            command=self.toggle_show_api_key
        ) if HAS_CTK else ctk.Button(key_container, text="👁️", command=self.toggle_show_api_key)
        self.toggle_eye_btn.grid(row=0, column=1, padx=(5, 0))

        # Fetch Models Button
        self.fetch_models_btn = ctk.CTkButton(
            self.top_ai_frame,
            text="",
            width=120,
            command=self.fetch_and_update_models_async
        ) if HAS_CTK else ctk.Button(self.top_ai_frame, text="", command=self.fetch_and_update_models_async)
        self.fetch_models_btn.grid(row=1, column=2, padx=5, pady=(0, 10))

        self.save_key_btn = ctk.CTkButton(
            self.top_ai_frame,
            text="",
            width=120,
            command=self.save_ai_key_click
        ) if HAS_CTK else ctk.Button(self.top_ai_frame, text="", command=self.save_ai_key_click)
        self.save_key_btn.grid(row=1, column=3, padx=(5, 15), pady=(0, 10), sticky="ew")

        # Left Panel (Articles)
        self.left_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="")
        self.left_frame.grid(row=1, column=0, padx=(15, 5), pady=5, sticky="nsew")
        self.left_frame.grid_columnconfigure(1, weight=1)
        self.left_frame.grid_rowconfigure(2, weight=1)

        self.ai_cat_sel_label = ctk.CTkLabel(self.left_frame, text="") if HAS_CTK else ctk.Label(self.left_frame, text="")
        self.ai_cat_sel_label.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")

        self.ai_category_var = ctk.StringVar(value="genel")
        self.ai_category_combo = ctk.CTkComboBox(
            self.left_frame,
            variable=self.ai_category_var,
            values=self.get_local_categories(),
            command=self.on_ai_category_change
        ) if HAS_CTK else ctk.Entry(self.left_frame, textvariable=self.ai_category_var)
        self.ai_category_combo.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        self.refresh_files_btn = ctk.CTkButton(
            self.left_frame,
            text="",
            width=70,
            command=self.refresh_ai_article_list
        ) if HAS_CTK else ctk.Button(self.left_frame, text="", command=self.refresh_ai_article_list)
        self.refresh_files_btn.grid(row=0, column=2, padx=(5, 10), pady=8)

        self.ai_art_sel_label = ctk.CTkLabel(self.left_frame, text="") if HAS_CTK else ctk.Label(self.left_frame, text="")
        self.ai_art_sel_label.grid(row=1, column=0, padx=(10, 5), pady=(0, 8), sticky="w")

        self.ai_article_var = ctk.StringVar(value="")
        self.ai_article_combo = ctk.CTkOptionMenu(
            self.left_frame,
            variable=self.ai_article_var,
            values=["..."],
            command=self.on_ai_article_selected
        ) if HAS_CTK else ctk.Entry(self.left_frame, textvariable=self.ai_article_var)
        self.ai_article_combo.grid(row=1, column=1, columnspan=2, padx=(5, 10), pady=(0, 8), sticky="ew")

        if HAS_CTK:
            self.ai_orig_preview = ctk.CTkTextbox(self.left_frame, font=ctk.CTkFont(size=12))
            self.ai_orig_preview.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.ai_orig_preview = st.ScrolledText(self.left_frame, wrap="word", height=15)
            self.ai_orig_preview.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")

        # Right Panel (AI Rewrite Output)
        self.right_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="")
        self.right_frame.grid(row=1, column=1, padx=(5, 15), pady=5, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)

        self.ai_convert_btn = ctk.CTkButton(
            self.right_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#8e44ad",
            hover_color="#732d91",
            height=38,
            command=self.start_ai_rewrite_single
        ) if HAS_CTK else ctk.Button(self.right_frame, text="", command=self.start_ai_rewrite_single)
        self.ai_convert_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        if HAS_CTK:
            self.ai_output_preview = ctk.CTkTextbox(self.right_frame, font=ctk.CTkFont(size=12))
            self.ai_output_preview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.ai_output_preview = st.ScrolledText(self.right_frame, wrap="word", height=15)
            self.ai_output_preview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self.refresh_ai_article_list()

    # ---------------------------------------------------------------------------
    # SEKME 3: SEO & SOSYAL MEDYA STUDIO
    # ---------------------------------------------------------------------------
    def build_seo_social_tab(self):
        tab = self.tab_seo
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Left Panel (SEO Article Selector)
        self.seo_left_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="")
        self.seo_left_frame.grid(row=0, column=0, rowspan=2, padx=(15, 5), pady=10, sticky="nsew")
        self.seo_left_frame.grid_columnconfigure(1, weight=1)
        self.seo_left_frame.grid_rowconfigure(2, weight=1)

        self.seo_cat_sel_label = ctk.CTkLabel(self.seo_left_frame, text="") if HAS_CTK else ctk.Label(self.seo_left_frame, text="")
        self.seo_cat_sel_label.grid(row=0, column=0, padx=(10, 5), pady=8, sticky="w")

        self.seo_category_var = ctk.StringVar(value="genel")
        self.seo_category_combo = ctk.CTkComboBox(
            self.seo_left_frame,
            variable=self.seo_category_var,
            values=self.get_local_categories(),
            command=self.on_seo_category_change
        ) if HAS_CTK else ctk.Entry(self.seo_left_frame, textvariable=self.seo_category_var)
        self.seo_category_combo.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        self.seo_refresh_btn = ctk.CTkButton(
            self.seo_left_frame,
            text="",
            width=70,
            command=self.refresh_seo_article_list
        ) if HAS_CTK else ctk.Button(self.seo_left_frame, text="", command=self.refresh_seo_article_list)
        self.seo_refresh_btn.grid(row=0, column=2, padx=(5, 10), pady=8)

        self.seo_art_label = ctk.CTkLabel(self.seo_left_frame, text="") if HAS_CTK else ctk.Label(self.seo_left_frame, text="")
        self.seo_art_label.grid(row=1, column=0, padx=(10, 5), pady=(0, 8), sticky="w")

        self.seo_article_var = ctk.StringVar(value="")
        self.seo_article_combo = ctk.CTkOptionMenu(
            self.seo_left_frame,
            variable=self.seo_article_var,
            values=["..."],
            command=self.on_seo_article_selected
        ) if HAS_CTK else ctk.Entry(self.seo_left_frame, textvariable=self.seo_article_var)
        self.seo_article_combo.grid(row=1, column=1, columnspan=2, padx=(5, 10), pady=(0, 8), sticky="ew")

        if HAS_CTK:
            self.seo_orig_preview = ctk.CTkTextbox(self.seo_left_frame, font=ctk.CTkFont(size=12))
            self.seo_orig_preview.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.seo_orig_preview = st.ScrolledText(self.seo_left_frame, wrap="word", height=15)
            self.seo_orig_preview.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="nsew")

        # Right Panel (SEO & Social Generation)
        self.seo_right_frame = ctk.CTkFrame(tab) if HAS_CTK else ctk.LabelFrame(tab, text="")
        self.seo_right_frame.grid(row=0, column=1, rowspan=2, padx=(5, 15), pady=10, sticky="nsew")
        self.seo_right_frame.grid_columnconfigure(0, weight=1)
        self.seo_right_frame.grid_rowconfigure(2, weight=1)

        self.seo_generate_btn = ctk.CTkButton(
            self.seo_right_frame,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#e67e22",
            hover_color="#d35400",
            height=40,
            command=self.start_seo_social_generation
        ) if HAS_CTK else ctk.Button(self.seo_right_frame, text="", command=self.start_seo_social_generation)
        self.seo_generate_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Quick Copy Bar
        copy_bar = ctk.CTkFrame(self.seo_right_frame, fg_color="transparent") if HAS_CTK else ctk.Frame(self.seo_right_frame)
        copy_bar.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="ew")
        copy_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.copy_all_btn = ctk.CTkButton(
            copy_bar, text="📋 Copy All", height=28, fg_color="gray30", hover_color="gray40",
            command=lambda: self.copy_to_clipboard(self.seo_output_preview.get("1.0", "end"))
        ) if HAS_CTK else ctk.Button(copy_bar, text="📋 Copy All", command=lambda: self.copy_to_clipboard(self.seo_output_preview.get("1.0", "end")))
        self.copy_all_btn.grid(row=0, column=0, padx=2, sticky="ew")

        self.copy_twitter_btn = ctk.CTkButton(
            copy_bar, text="🐦 Twitter Thread", height=28, fg_color="#1da1f2", hover_color="#0c85d0",
            command=lambda: self.copy_section_to_clipboard("## 🐦 Twitter / X Thread")
        ) if HAS_CTK else ctk.Button(copy_bar, text="🐦 Twitter Thread", command=lambda: self.copy_section_to_clipboard("## 🐦 Twitter / X Thread"))
        self.copy_twitter_btn.grid(row=0, column=1, padx=2, sticky="ew")

        self.copy_linkedin_btn = ctk.CTkButton(
            copy_bar, text="💼 LinkedIn Post", height=28, fg_color="#0077b5", hover_color="#005885",
            command=lambda: self.copy_section_to_clipboard("## 💼 LinkedIn Article Post")
        ) if HAS_CTK else ctk.Button(copy_bar, text="💼 LinkedIn Post", command=lambda: self.copy_section_to_clipboard("## 💼 LinkedIn Article Post"))
        self.copy_linkedin_btn.grid(row=0, column=2, padx=2, sticky="ew")

        self.copy_seo_btn = ctk.CTkButton(
            copy_bar, text="🎯 SEO Package", height=28, fg_color="#27ae60", hover_color="#219150",
            command=lambda: self.copy_section_to_clipboard("## 🎯 SEO & Metadata Package")
        ) if HAS_CTK else ctk.Button(copy_bar, text="🎯 SEO Package", command=lambda: self.copy_section_to_clipboard("## 🎯 SEO & Metadata Package"))
        self.copy_seo_btn.grid(row=0, column=3, padx=2, sticky="ew")

        if HAS_CTK:
            self.seo_output_preview = ctk.CTkTextbox(self.seo_right_frame, font=ctk.CTkFont(size=12))
            self.seo_output_preview.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        else:
            import tkinter.scrolledtext as st
            self.seo_output_preview = st.ScrolledText(self.seo_right_frame, wrap="word", height=15)
            self.seo_output_preview.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self.refresh_seo_article_list()

    def toggle_show_api_key(self):
        self.show_api_key_state = not self.show_api_key_state
        show_char = "" if self.show_api_key_state else "*"
        if HAS_CTK:
            self.ai_api_key_entry.configure(show=show_char)
        else:
            self.ai_api_key_entry.configure(show=show_char)

    # ---------------------------------------------------------------------------
    # UYGULAMA DİL GÜNCELLEMESİ (i18n)
    # ---------------------------------------------------------------------------
    def on_language_changed(self, choice: str):
        self.current_lang = choice
        self.config_data["ui_language"] = choice
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self.apply_language()

    def apply_language(self):
        self.title(self.t("title"))

        if HAS_CTK:
            self.app_title_label.configure(text=self.t("title"))
            try:
                self.tabview._segmented_button._buttons_dict[self.tab_key_scraper].configure(text=self.t("tab_scraper"))
                self.tabview._segmented_button._buttons_dict[self.tab_key_ai].configure(text=self.t("tab_ai"))
                self.tabview._segmented_button._buttons_dict[self.tab_key_seo].configure(text=self.t("tab_seo"))
            except Exception:
                pass
        else:
            try:
                self.notebook.tab(0, text=self.t("tab_scraper"))
                self.notebook.tab(1, text=self.t("tab_ai"))
                self.notebook.tab(2, text=self.t("tab_seo"))
            except Exception:
                pass

        self.url_label.configure(text=self.t("url_label"))
        self.url_entry.configure(placeholder_text=self.t("url_placeholder"))
        self.batch_btn.configure(text=self.t("batch_btn"))
        self.cat_label.configure(text=self.t("category_label"))
        self.fmt_label.configure(text=self.t("format_label"))
        self.img_switch.configure(text=self.t("download_imgs"))
        self.threads_label.configure(text=self.t("threads_label"))
        self.fetch_btn.configure(text=self.t("fetch_btn"))
        self.open_folder_btn.configure(text=self.t("open_folder"))

        if not HAS_CTK:
            self.input_frame.configure(text=self.t("url_label"))
            self.settings_frame.configure(text=self.t("category_label"))
            self.log_frame.configure(text=self.t("download_log"))
            self.top_ai_frame.configure(text=self.t("ai_settings_title"))
            self.left_frame.configure(text=self.t("downloaded_articles_title"))
            self.right_frame.configure(text=self.t("ai_output_title"))
            self.seo_left_frame.configure(text=self.t("downloaded_articles_title"))
            self.seo_right_frame.configure(text=self.t("tab_seo"))

        # AI Tab Labels
        self.ai_service_label.configure(text=self.t("ai_service"))
        self.model_label.configure(text=self.t("model_label"))
        self.api_key_label.configure(text=self.t("api_key"))
        self.fetch_models_btn.configure(text=self.t("fetch_models"))
        self.save_key_btn.configure(text=self.t("save_settings"))
        self.ai_cat_sel_label.configure(text=self.t("category"))
        self.refresh_files_btn.configure(text=self.t("refresh_btn"))
        self.ai_art_sel_label.configure(text=self.t("article_label"))
        self.ai_convert_btn.configure(text=self.t("convert_btn"))

        # SEO Tab Labels
        self.seo_cat_sel_label.configure(text=self.t("category"))
        self.seo_refresh_btn.configure(text=self.t("refresh_btn"))
        self.seo_art_label.configure(text=self.t("article_label"))
        self.seo_generate_btn.configure(text=self.t("seo_btn"))
        self.copy_all_btn.configure(text=self.t("copy_all"))
        self.copy_twitter_btn.configure(text=self.t("copy_twitter"))
        self.copy_linkedin_btn.configure(text=self.t("copy_linkedin"))
        self.copy_seo_btn.configure(text=self.t("copy_seo"))

        self.refresh_ai_article_list()
        self.refresh_seo_article_list()

    # ---------------------------------------------------------------------------
    # MANTIKSAL İŞLEVLER (SEKME 2 & 3)
    # ---------------------------------------------------------------------------
    def get_local_categories(self):
        categories = ["genel"]
        if MAKALELER_DIR.exists():
            for p in MAKALELER_DIR.iterdir():
                if p.is_dir() and p.name not in ["images", "rewritten"]:
                    categories.append(p.name)
        return sorted(list(set(categories)))

    def persist_ai_provider_config(self, provider: str, key_val: str, model_val: str):
        """API Key ve model tercihlerini kalıcı olarak config.json dosyasına yazar."""
        self.config_data["selected_ai_provider"] = provider
        if "ai_provider_keys" not in self.config_data:
            self.config_data["ai_provider_keys"] = {}
        if "ai_provider_models" not in self.config_data:
            self.config_data["ai_provider_models"] = {}

        if key_val:
            self.config_data["ai_provider_keys"][provider] = key_val
        if model_val:
            self.config_data["ai_provider_models"][provider] = model_val

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_ai_provider_changed(self, choice):
        provider = choice
        provider_keys = self.config_data.get("ai_provider_keys", {})
        provider_models = self.config_data.get("ai_provider_models", {})

        key_val = provider_keys.get(provider, "")
        default_model = PROVIDERS_REGISTRY.get(provider, {}).get("default_model", "")
        model_val = provider_models.get(provider, default_model)

        self.ai_api_key_var.set(key_val)
        self.ai_model_var.set(model_val)
        self.config_data["selected_ai_provider"] = provider

        fallbacks = PROVIDERS_REGISTRY.get(provider, {}).get("fallback_models", [default_model])
        if HAS_CTK:
            self.ai_model_combo.configure(values=fallbacks)

        if key_val:
            self.fetch_and_update_models_async()

    def fetch_and_update_models_async(self):
        provider = self.ai_provider_var.get().strip()
        api_key = self.ai_api_key_var.get().strip()
        model_val = self.ai_model_var.get().strip()

        if not api_key:
            messagebox.showwarning("API Key Eksik", self.t("key_missing_warn").format(provider=provider))
            return

        self.persist_ai_provider_config(provider, api_key, model_val)
        self.fetch_models_btn.configure(state="disabled")

        def _fetch_worker():
            try:
                models = fetch_provider_models(provider, api_key)
                def _update_ui():
                    if HAS_CTK and models:
                        self.ai_model_combo.configure(values=models)
                        self.ai_model_var.set(models[0])
                        self.persist_ai_provider_config(provider, api_key, models[0])
                    self.fetch_models_btn.configure(state="normal")
                    messagebox.showinfo("Başarılı / Success", self.t("models_loaded").format(count=len(models), provider=provider))

                self.after(0, _update_ui)
            except Exception as e:
                err_msg = str(e)
                def _err_ui(msg=err_msg):
                    self.fetch_models_btn.configure(state="normal")
                    messagebox.showerror("Hata / Error", self.t("models_fetch_err").format(err=msg))
                self.after(0, _err_ui)

        threading.Thread(target=_fetch_worker, daemon=True).start()

    # SEKME 2 LOGIC
    def on_ai_category_change(self, choice=None):
        self.refresh_ai_article_list()

    def refresh_ai_article_list(self):
        cat = self.ai_category_var.get().strip() or "genel"
        cat_dir = MAKALELER_DIR / cat
        self.articles_cache = {}

        if cat_dir.exists():
            for p in cat_dir.glob("*.*"):
                if p.is_file() and p.suffix in [".md", ".json", ".txt"] and not p.name.endswith("_en.md") and not p.name.endswith("_social.md"):
                    self.articles_cache[p.name] = p

        files = sorted(list(self.articles_cache.keys()))
        if files:
            if HAS_CTK:
                self.ai_article_combo.configure(values=files)
            self.ai_article_var.set(files[0])
            self.on_ai_article_selected(files[0])
        else:
            if HAS_CTK:
                self.ai_article_combo.configure(values=[self.t("no_articles_cat")])
            self.ai_article_var.set(self.t("no_articles_cat"))
            self.ai_orig_preview.delete("1.0", "end")
            self.ai_orig_preview.insert("1.0", self.t("no_articles_cat"))

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
        provider = self.ai_provider_var.get().strip()
        key_val = self.ai_api_key_var.get().strip()
        model_val = self.ai_model_var.get().strip()

        if not key_val:
            messagebox.showwarning("Uyarı / Warning", self.t("key_missing_warn").format(provider=provider))
            return

        self.persist_ai_provider_config(provider, key_val, model_val)
        messagebox.showinfo("Başarılı / Success", self.t("key_saved_msg").format(provider=provider))
        self.fetch_and_update_models_async()

    def start_ai_rewrite_single(self):
        provider = self.ai_provider_var.get().strip()
        api_key = self.ai_api_key_var.get().strip()
        model_name = self.ai_model_var.get().strip()
        selected_filename = self.ai_article_var.get()
        cat = self.ai_category_var.get().strip() or "genel"

        if not api_key:
            messagebox.showwarning("API Key Eksik", self.t("key_missing_warn").format(provider=provider))
            return

        if selected_filename not in self.articles_cache:
            messagebox.showwarning("Makale Seçilmedi", self.t("no_art_selected_warn"))
            return

        self.persist_ai_provider_config(provider, api_key, model_name)
        file_path = self.articles_cache[selected_filename]
        self.ai_convert_btn.configure(state="disabled")
        self.ai_output_preview.delete("1.0", "end")
        self.ai_output_preview.insert("1.0", self.t("ai_processing_msg").format(provider=provider, model=model_name))

        def _worker():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                title = file_path.stem
                orig_url = ""

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
                rewriter = MultiProviderAIRewriter(provider=provider, api_key=api_key, model=model_name)
                rewritten_md = rewriter.rewrite_and_expand_article(raw_content, metadata)

                en_filename = f"{file_path.stem}_en.md"
                en_file_path = (MAKALELER_DIR / cat) / en_filename
                with open(en_file_path, "w", encoding="utf-8") as f:
                    f.write(rewritten_md)

                def _update_ui_success():
                    self.ai_output_preview.delete("1.0", "end")
                    self.ai_output_preview.insert("1.0", f"--- SAVED ({provider}): {cat}/{en_filename} ---\n\n" + rewritten_md)
                    self.ai_convert_btn.configure(state="normal")
                    self.refresh_seo_article_list()
                    messagebox.showinfo("Başarılı / Success", self.t("ai_saved_msg").format(provider=provider, filename=f"{cat}/{en_filename}"))

                self.after(0, _update_ui_success)

            except Exception as err:
                err_msg = str(err)
                def _update_ui_error(msg=err_msg):
                    self.ai_output_preview.delete("1.0", "end")
                    self.ai_output_preview.insert("1.0", f"[HATA] {provider} AI İşlem Başarısız / Failed:\n{msg}")
                    self.ai_convert_btn.configure(state="normal")
                    messagebox.showerror("Hata / Error", msg)

                self.after(0, _update_ui_error)

        t = threading.Thread(target=_worker, daemon=True).start()

    # SEKME 3 LOGIC
    def on_seo_category_change(self, choice=None):
        self.refresh_seo_article_list()

    def refresh_seo_article_list(self):
        cat = self.seo_category_var.get().strip() or "genel"
        cat_dir = MAKALELER_DIR / cat
        self.seo_articles_cache = {}

        if cat_dir.exists():
            for p in cat_dir.glob("*.*"):
                if p.is_file() and p.suffix in [".md", ".json", ".txt"] and not p.name.endswith("_social.md"):
                    self.seo_articles_cache[p.name] = p

        files = sorted(list(self.seo_articles_cache.keys()))
        if files:
            if HAS_CTK:
                self.seo_article_combo.configure(values=files)
            self.seo_article_var.set(files[0])
            self.on_seo_article_selected(files[0])
        else:
            if HAS_CTK:
                self.seo_article_combo.configure(values=[self.t("no_articles_cat")])
            self.seo_article_var.set(self.t("no_articles_cat"))
            self.seo_orig_preview.delete("1.0", "end")
            self.seo_orig_preview.insert("1.0", self.t("no_articles_cat"))

    def on_seo_article_selected(self, choice):
        if choice in self.seo_articles_cache:
            file_path = self.seo_articles_cache[choice]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.seo_orig_preview.delete("1.0", "end")
                self.seo_orig_preview.insert("1.0", content[:3000] + ("\n\n... (devamı var)" if len(content) > 3000 else ""))
            except Exception as e:
                self.seo_orig_preview.delete("1.0", "end")
                self.seo_orig_preview.insert("1.0", f"Dosya okunamadı: {e}")

    def copy_to_clipboard(self, text: str):
        if not text.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(text.strip())
        messagebox.showinfo("Kopyalandı / Copied", self.t("copied_msg"))

    def copy_section_to_clipboard(self, section_header: str):
        full_text = self.seo_output_preview.get("1.0", "end")
        if section_header in full_text:
            parts = full_text.split(section_header)
            if len(parts) > 1:
                section_body = parts[1].split("\n## ")[0].strip()
                self.copy_to_clipboard(f"{section_header}\n\n{section_body}")
                return
        self.copy_to_clipboard(full_text)

    def start_seo_social_generation(self):
        provider = self.ai_provider_var.get().strip()
        api_key = self.ai_api_key_var.get().strip()
        model_name = self.ai_model_var.get().strip()
        selected_filename = self.seo_article_var.get()
        cat = self.seo_category_var.get().strip() or "genel"

        if not api_key:
            messagebox.showwarning("API Key Eksik", self.t("key_missing_warn").format(provider=provider))
            return

        if selected_filename not in self.seo_articles_cache:
            messagebox.showwarning("Makale Seçilmedi", self.t("no_art_selected_warn"))
            return

        self.persist_ai_provider_config(provider, api_key, model_name)
        file_path = self.seo_articles_cache[selected_filename]

        self.seo_generate_btn.configure(state="disabled")
        self.seo_output_preview.delete("1.0", "end")
        self.seo_output_preview.insert("1.0", self.t("seo_processing_msg").format(provider=provider, model=model_name))

        def _worker():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                title = file_path.stem
                orig_url = ""

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
                generator = SEOSocialGenerator(provider=provider, api_key=api_key, model=model_name)
                social_package_md = generator.generate_seo_and_social_package(raw_content, metadata)

                social_filename = f"{file_path.stem}_social.md"
                social_file_path = (MAKALELER_DIR / cat) / social_filename
                with open(social_file_path, "w", encoding="utf-8") as f:
                    f.write(social_package_md)

                def _update_ui_success():
                    self.seo_output_preview.delete("1.0", "end")
                    self.seo_output_preview.insert("1.0", f"--- SAVED ({provider}): {cat}/{social_filename} ---\n\n" + social_package_md)
                    self.seo_generate_btn.configure(state="normal")
                    messagebox.showinfo("Başarılı / Success", self.t("seo_saved_msg").format(provider=provider, filename=f"{cat}/{social_filename}"))

                self.after(0, _update_ui_success)

            except Exception as err:
                err_msg = str(err)
                def _update_ui_error(msg=err_msg):
                    self.seo_output_preview.delete("1.0", "end")
                    self.seo_output_preview.insert("1.0", f"[HATA] {provider} SEO & Sosyal Üretim Başarısız / Failed:\n{msg}")
                    self.seo_generate_btn.configure(state="normal")
                    messagebox.showerror("Hata / Error", msg)

                self.after(0, _update_ui_error)

        t = threading.Thread(target=_worker, daemon=True).start()

    # ---------------------------------------------------------------------------
    # ORTAK YARDIMCI İŞLEVLER (SEKME 1)
    # ---------------------------------------------------------------------------
    def select_batch_file(self):
        file_path = filedialog.askopenfilename(
            title="Toplu URL Dosyası Seç / Select Batch File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
                self.batch_urls = lines
                self.batch_status_label.configure(
                    text=f"Seçilen Dosya / File: {Path(file_path).name} ({len(lines)} URLs)"
                )
                self.log_direct(f"[BİLGİ] {len(lines)} URLs loaded from {Path(file_path).name}.")
            except Exception as e:
                messagebox.showerror("Hata / Error", f"Dosya okunamadı: {e}")

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
                    self.refresh_seo_article_list()
                elif msg_type == "error":
                    self.fetch_btn.configure(state="normal")
                    messagebox.showerror("Hata / Error", payload)
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
            messagebox.showwarning("Uyarı / Warning", self.t("select_file_warn"))
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
