import json
import ssl
import urllib.request
from typing import Dict, Any, Optional

from utils.helpers import load_config


class DeepSeekRewriter:
    """DeepSeek API kullanarak makaleleri analiz eden, genişleten ve İngilizceye dönüştüren modül."""

    def __init__(self, api_key: Optional[str] = None, logger=None):
        self.config = load_config()
        self.api_key = api_key or self.config.get("deepseek_api_key", "")
        self.model = self.config.get("deepseek_model", "deepseek-chat")
        self.temperature = self.config.get("deepseek_temperature", 0.7)
        self.logger = logger
        self.api_url = "https://api.deepseek.com/chat/completions"

    def _log(self, message: str):
        if self.logger and hasattr(self.logger, "log"):
            self.logger.log(message)
        else:
            print(message)

    def rewrite_and_expand_article(self, original_markdown: str, metadata: Dict[str, Any]) -> str:
        """Makaleyi analiz edip eksiklerini tamamlar ve akıcı İngilizce Markdown olarak yeniden üretir."""
        if not self.api_key:
            raise ValueError("DeepSeek API Key bulunamadı! Lütfen ayarlar alanından veya CLI parametresinden API Key girin.")

        self._log("[DeepSeek AI] Makale analiz ediliyor ve İngilizceye geliştirilerek yeniden yazılıyor...")

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

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=json_data, headers=headers, method="POST")

        ctx = ssl._create_unverified_context()

        try:
            timeout = self.config.get("request_timeout", 60)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)

                choices = res_json.get("choices", [])
                if choices and "message" in choices[0]:
                    rewritten_content = choices[0]["message"]["content"].strip()
                    self._log("[DeepSeek AI] [Başarılı] Makale başarıyla geliştirildi ve İngilizceye çevrildi!")
                    return rewritten_content
                else:
                    raise Exception(f"DeepSeek API beklenmeyen yanıt döndürdü: {res_body[:200]}")

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            raise Exception(f"DeepSeek API HTTP Hatası ({e.code}): {error_msg}")
        except Exception as e:
            raise Exception(f"DeepSeek API Bağlantı Hatası: {e}")
