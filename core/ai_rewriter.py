import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from utils.helpers import load_config


PROVIDERS_REGISTRY = {
    "DeepSeek": {
        "url": "https://api.deepseek.com/chat/completions",
        "default_model": "deepseek-chat"
    },
    "OpenAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini"
    },
    "Gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "default_model": "gemini-2.5-flash"
    },
    "OpenRouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "google/gemini-2.5-flash",
        "extra_headers": {
            "HTTP-Referer": "https://github.com/yonetici/medium-scraper-pro",
            "X-Title": "Medium Scraper Pro"
        }
    },
    "Kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "default_model": "moonshot-v1-8k"
    },
    "Grok": {
        "url": "https://api.x.ai/v1/chat/completions",
        "default_model": "grok-2-latest"
    },
    "Qwen": {
        "url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "default_model": "qwen-plus"
    },
    "Custom": {
        "url": "",
        "default_model": "custom-model"
    }
}


class MultiProviderAIRewriter:
    """Çoklu AI Sağlayıcısı (OpenAI, Gemini, OpenRouter, DeepSeek, Kimi, Grok, Qwen) ile makale analiz ve yeniden yazım motoru."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        custom_url: Optional[str] = None,
        logger=None
    ):
        self.config = load_config()
        self.logger = logger

        self.provider = provider or self.config.get("selected_ai_provider", "DeepSeek")
        if self.provider not in PROVIDERS_REGISTRY:
            self.provider = "DeepSeek"

        provider_keys = self.config.get("ai_provider_keys", {})
        provider_models = self.config.get("ai_provider_models", {})

        self.api_key = api_key or provider_keys.get(self.provider, "")
        self.model = model or provider_models.get(self.provider, PROVIDERS_REGISTRY[self.provider]["default_model"])
        self.custom_url = custom_url or self.config.get("custom_base_url", "")
        self.temperature = self.config.get("deepseek_temperature", 0.7)

    def _log(self, message: str):
        if self.logger and hasattr(self.logger, "log"):
            self.logger.log(message)
        else:
            print(message)

    def get_endpoint_url(self) -> str:
        if self.provider == "Custom":
            if not self.custom_url:
                raise ValueError("Custom (Özel) AI Sağlayıcısı için lütfen geçerli bir Base URL girin.")
            return self.custom_url
        return PROVIDERS_REGISTRY[self.provider]["url"]

    def rewrite_and_expand_article(self, original_markdown: str, metadata: Dict[str, Any]) -> str:
        """Makaleyi seçili AI servis ile analiz edip eksiklerini tamamlar ve akıcı İngilizceye dönüştürür."""
        if not self.api_key:
            raise ValueError(f"{self.provider} API Key bulunamadı! Lütfen arayüzdeki API Key alanından giriş yapın.")

        api_url = self.get_endpoint_url()
        self._log(f"[{self.provider} AI - {self.model}] Makale analiz ediliyor ve İngilizceye geliştirilerek yeniden yazılıyor...")

        system_prompt = (
            "You are a world-class technical writer, software architect, and native English content strategist. "
            "Your goal is NOT to perform a literal translation. Instead, perform a deep critical analysis of the provided article, "
            "identify any missing context, code examples, architectural nuances, or analytical depth, expand upon them with modern "
            "industry best practices, and rewrite the entire piece into a high-impact, engaging native English Markdown article.\n\n"
            "Guidelines:\n"
            "1. Deep Analysis: Elevate the tone, fix logic gaps, and structure sections logically with clear H2/H3 headings.\n"
            "2. Content Expansion: Add modern best practices, clear code blocks with language annotations if applicable, and deep insights.\n"
            "3. Formatting: Output clean, professional GitHub Flavored Markdown.\n"
            "4. YAML Frontmatter: Begin your output strictly with valid YAML frontmatter (title, author, date, original_url, site, language: 'en').\n"
            "5. NO Conversational Filler: Output ONLY the Markdown document starting with `---`."
        )

        user_content = f"""Original Article Title: {metadata.get('title', '')}
Author: {metadata.get('author', '')}
Original URL: {metadata.get('original_url', '')}

Original Article Body:
{original_markdown}
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": self.temperature,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}"
        }

        # Extra headers for specific providers like OpenRouter
        extra_headers = PROVIDERS_REGISTRY.get(self.provider, {}).get("extra_headers", {})
        headers.update(extra_headers)

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=json_data, headers=headers, method="POST")

        ctx = ssl._create_unverified_context()

        try:
            timeout = self.config.get("request_timeout", 45)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)

                choices = res_json.get("choices", [])
                if choices and "message" in choices[0]:
                    rewritten_content = choices[0]["message"]["content"].strip()
                    self._log(f"[{self.provider} AI] [Başarılı] Makale başarıyla geliştirildi ve İngilizceye çevrildi!")
                    return rewritten_content
                else:
                    raise Exception(f"{self.provider} API beklenmeyen yanıt döndürdü: {res_body[:200]}")

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            raise Exception(f"{self.provider} API HTTP Hatası ({e.code}): {error_msg}")
        except Exception as e:
            raise Exception(f"{self.provider} API Bağlantı Hatası: {e}")


# Backward compatibility alias
DeepSeekRewriter = MultiProviderAIRewriter
