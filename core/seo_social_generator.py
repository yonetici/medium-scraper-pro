import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from core.ai_rewriter import MultiProviderAIRewriter, PROVIDERS_REGISTRY, DEFAULT_USER_AGENT, parse_api_error_message
from utils.helpers import load_config


class SEOSocialGenerator:
    """İndirilen veya İngilizceye çevrilen makaleler için SEO ve Sosyal Medya İçerik Fabrikası motoru."""

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

    def _log(self, message: str):
        if self.logger and hasattr(self.logger, "log"):
            self.logger.log(message)
        else:
            print(message)

    def generate_seo_and_social_package(self, article_content: str, metadata: Dict[str, Any]) -> str:
        """Makale içeriğini analiz ederek SEO meta paketini, Twitter Thread, LinkedIn, Instagram ve Bülten içeriğini tek çıktıda üretir."""
        if not self.api_key:
            raise ValueError(f"{self.provider} API Key bulunamadı! Lütfen arayüzden API Anahtarı girin.")

        rewriter = MultiProviderAIRewriter(
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
            custom_url=self.custom_url,
            logger=self.logger
        )

        api_url = rewriter.get_endpoint_url()
        self._log(f"[{self.provider} AI - {self.model}] SEO & Sosyal Medya içeriği üretiliyor...")

        system_prompt = (
            "You are an expert Content Growth Strategist, SEO Specialist, and Social Media Manager. "
            "Your task is to analyze the provided article and generate a complete, high-converting SEO & Social Media Package.\n\n"
            "Produce clean Markdown output containing EXACTLY the following 5 structured sections with clear H2 headings:\n\n"
            "## 🎯 SEO & Metadata Package\n"
            "- 5 High-CTR Title Headlines\n"
            "- Meta Description (150-160 characters)\n"
            "- Primary & Secondary Focus Keywords\n"
            "- Target Audience & Key Takeaways\n"
            "- Reading Time & Word Count\n"
            "- Schema.org Article JSON-LD snippet in a ```json codeblock\n\n"
            "## 🐦 Twitter / X Thread\n"
            "Provide a 5 to 7 tweet numbered chain with an engaging hook, main takeaways, emojis, and hashtags.\n\n"
            "## 💼 LinkedIn Article Post\n"
            "Provide a professional storytelling LinkedIn post with strong call-to-action and relevant hashtags.\n\n"
            "## 📸 Instagram & Threads Caption\n"
            "Provide a concise visual post caption with emojis and hashtags.\n\n"
            "## 📧 Newsletter Draft\n"
            "Provide a catchy email newsletter subject line and introductory body snippet for Substack / Mailchimp.\n\n"
            "Guidelines: Output ONLY the requested Markdown sections. Do NOT include intro or outro conversational filler."
        )

        user_content = f"""Article Title: {metadata.get('title', 'Article')}
Author: {metadata.get('author', 'Unknown')}
Original URL: {metadata.get('original_url', '')}

Article Content:
{article_content[:6000]}
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.7,
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
        ai_timeout = self.config.get("ai_request_timeout", 150)

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=ai_timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)

                choices = res_json.get("choices", [])
                if choices and "message" in choices[0]:
                    generated_package = choices[0]["message"]["content"].strip()
                    self._log(f"[{self.provider} AI] [Başarılı] SEO & Sosyal Medya paketi üretildi!")
                    return generated_package
                else:
                    raise Exception(f"{self.provider} API beklenmeyen yanıt döndürdü: {res_body[:200]}")

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            parsed_msg = parse_api_error_message(error_body, e.code)
            raise Exception(f"[{self.provider} AI] {parsed_msg}")
        except Exception as e:
            raise Exception(f"[{self.provider} AI] SEO & Sosyal Medya Üretim Hatası: {e}")
