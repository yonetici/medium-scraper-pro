import json
import socket
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from utils.helpers import load_config

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

PROVIDERS_REGISTRY = {
    "DeepSeek": {
        "url": "https://api.deepseek.com/chat/completions",
        "models_url": "https://api.deepseek.com/models",
        "default_model": "deepseek-chat",
        "fallback_models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
    },
    "OpenAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "models_url": "https://api.openai.com/v1/models",
        "default_model": "gpt-4o-mini",
        "fallback_models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini", "o3-mini"]
    },
    "Gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "models_url": "https://generativelanguage.googleapis.com/v1beta/openai/models",
        "default_model": "gemini-2.5-flash",
        "fallback_models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
    },
    "OpenRouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "models_url": "https://openrouter.ai/api/v1/models",
        "default_model": "google/gemini-2.5-flash",
        "fallback_models": [
            "google/gemini-2.5-flash", "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o-mini", "deepseek/deepseek-r1", "meta-llama/llama-3.3-70b-instruct"
        ],
        "extra_headers": {
            "HTTP-Referer": "https://github.com/yonetici/medium-scraper-pro",
            "X-Title": "Medium Scraper Pro"
        }
    },
    "Kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "models_url": "https://api.moonshot.cn/v1/models",
        "default_model": "moonshot-v1-8k",
        "fallback_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
    },
    "Grok": {
        "url": "https://api.x.ai/v1/chat/completions",
        "models_url": "https://api.x.ai/v1/models",
        "default_model": "grok-2-latest",
        "fallback_models": ["grok-2-latest", "grok-beta", "grok-vision-beta"]
    },
    "Qwen": {
        "url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "models_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models",
        "default_model": "qwen-plus",
        "fallback_models": ["qwen-plus", "qwen-max", "qwen-turbo", "qwen-coder-plus"]
    },
    "Custom": {
        "url": "",
        "models_url": "",
        "default_model": "custom-model",
        "fallback_models": ["custom-model"]
    }
}


def parse_api_error_message(error_body: str, http_code: int) -> str:
    """API hata yanıtını ayrıştırır ve Türkçe anlaşılır açıklama üretir."""
    try:
        data = json.loads(error_body)
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            code = err.get("code", "") if isinstance(err, dict) else ""

            if "insufficient_balance" in str(code).lower() or "insufficient balance" in str(msg).lower():
                return "Bakiye Yetersiz (Insufficient Balance): DeepSeek/AI hesabınızda bakiye bulunmuyor. Lütfen sağlayıcı paneline girip bakiye yükleyin."
            if "invalid_api_key" in str(code).lower() or "authentication fails" in str(msg).lower() or http_code == 401:
                return "Geçersiz API Key (401 Auth Error): Girdiğiniz API Key doğrulamadan geçemedi. Lütfen API Anahtarınızı kontrol edin."
            if "model_not_found" in str(code).lower() or "does not exist" in str(msg).lower() or "not found" in str(msg).lower():
                return f"Model Bulunamadı: Sunucuda bu isimde bir model mevcut değil. Lütfen 'Modelleri Yükle' butonuna basarak geçerli modellerden birini seçin. Detay: {msg}"
            
            return f"API Hatası ({http_code}): {msg}"
    except Exception:
        pass

    if http_code == 401:
        return "Geçersiz API Key (401 Auth Error). Lütfen API Key'inizi kontrol edin."
    if http_code == 402:
        return "Bakiye Yetersiz (402 Payment Required). Lütfen hesabınıza bakiye yükleyin."
    if http_code == 400:
        return f"Geçersiz İstek (400 Bad Request): Lütfen model ismini ve girdi parametrelerini kontrol edin. ({error_body[:150]})"

    return f"HTTP Hatası ({http_code}): {error_body[:200]}"


def fetch_provider_models(provider: str, api_key: str, custom_url: Optional[str] = None) -> List[str]:
    """Seçili AI sağlayıcısının sunucusuna bağlanarak aktif model listesini canlı çeker."""
    if provider not in PROVIDERS_REGISTRY:
        provider = "DeepSeek"

    info = PROVIDERS_REGISTRY[provider]
    models_url = info["models_url"]

    if provider == "Custom":
        if custom_url:
            models_url = custom_url.replace("/chat/completions", "/models")
        else:
            return info["fallback_models"]

    if not api_key:
        return info["fallback_models"]

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json"
    }
    if "extra_headers" in info:
        headers.update(info["extra_headers"])

    req = urllib.request.Request(models_url, headers=headers, method="GET")
    ctx = ssl._create_unverified_context()

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            res_json = json.loads(data)

            model_ids = []
            if "data" in res_json and isinstance(res_json["data"], list):
                for item in res_json["data"]:
                    if isinstance(item, dict) and "id" in item:
                        m_id = item["id"]
                        if not any(sub in m_id.lower() for sub in ["embed", "whisper", "tts", "dall-e", "moderation", "bge", "rerank"]):
                            model_ids.append(m_id)
            elif "models" in res_json and isinstance(res_json["models"], list):
                for item in res_json["models"]:
                    if isinstance(item, dict) and "name" in item:
                        model_ids.append(item["name"].replace("models/", ""))

            if model_ids:
                return sorted(list(set(model_ids)))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        parsed_msg = parse_api_error_message(err_body, e.code)
        raise Exception(parsed_msg)
    except Exception as e:
        raise Exception(f"Model listesi çekilemedi: {e}")

    return info["fallback_models"]


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
            "Authorization": f"Bearer {self.api_key.strip()}",
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json"
        }

        extra_headers = PROVIDERS_REGISTRY.get(self.provider, {}).get("extra_headers", {})
        headers.update(extra_headers)

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=json_data, headers=headers, method="POST")

        ctx = ssl._create_unverified_context()

        # Generous timeout for long technical articles (150s = 2.5 minutes)
        ai_timeout = self.config.get("ai_request_timeout", 150)

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=ai_timeout) as response:
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
            error_body = e.read().decode("utf-8", errors="ignore")
            parsed_msg = parse_api_error_message(error_body, e.code)
            raise Exception(f"[{self.provider} AI] {parsed_msg}")
        except (socket.timeout, TimeoutError) as e:
            raise Exception(f"[{self.provider} AI] Zaman Aşımı (Timeout - {ai_timeout}s): AI sunucusunun yanıt üretmesi çok uzun sürdü ({e}). Lütfen tekrar deneyin veya daha kısa bir makale seçin.")
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower():
                raise Exception(f"[{self.provider} AI] Zaman Aşımı (Timeout - {ai_timeout}s): Sunucu yanıt vermedi. Lütfen internet bağlantınızı kontrol edip tekrar deneyin.")
            raise Exception(f"[{self.provider} AI] Bağlantı Hatası: {e}")
        except Exception as e:
            raise Exception(f"[{self.provider} AI] İşlem Hatası: {e}")


DeepSeekRewriter = MultiProviderAIRewriter
