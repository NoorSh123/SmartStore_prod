import json
import os

from openai import OpenAI


class AISearchService:

    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai").lower()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        self.client = None

        if self.provider == "openai" and self.api_key:
            self.client = OpenAI(api_key=self.api_key, timeout=20.0, max_retries=1)

    def interpret_search_query(self, user_query: str):
        cleaned_query = (user_query or "").strip()

        if not cleaned_query:
            return {
                "keywords": [],
                "category": None,
                "tags": [],
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "empty query"
                }
            }

        if self.provider != "openai":
            fallback = self._fallback_interpretation(cleaned_query)
            fallback["_meta"] = {
                "source": "fallback",
                "provider": self.provider,
                "model": self.model,
                "error": "AI_PROVIDER not openai"
            }
            return fallback

        if not self.api_key or not self.client:
            fallback = self._fallback_interpretation(cleaned_query)
            fallback["_meta"] = {
                "source": "fallback",
                "provider": self.provider,
                "model": self.model,
                "error": "OPENAI_API_KEY missing"
            }
            return fallback

        try:
            system_prompt = """
You are an assistant that converts product search queries into JSON.

Rules:
- Return ONLY valid JSON.
- Do NOT add explanations.
- Remove filler words like: for, with, long, daily, use, the, a, an.
- Extract useful search keywords only.

Return format:

{
 "keywords": ["..."],
 "category": "..." ,
 "tags": ["...", "..."]
}

If category is unknown use null.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_completion_tokens=150,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)

            return {
                "keywords": self._clean_list(parsed.get("keywords", [])),
                "category": self._clean_string(parsed.get("category")),
                "tags": self._clean_list(parsed.get("tags", [])),
                "_meta": {
                    "source": "openai",
                    "provider": self.provider,
                    "model": self.model,
                    "error": None
                }
            }

        except Exception as e:
            fallback = self._fallback_interpretation(cleaned_query)
            fallback["_meta"] = {
                "source": "fallback",
                "provider": self.provider,
                "model": self.model,
                "error": "OpenAI request failed"
            }
            return fallback

    def chat_about_products(self, messages, products):
        cleaned_messages = self._clean_messages(messages)
        latest_message = cleaned_messages[-1]["content"] if cleaned_messages else ""

        if not latest_message:
            return {
                "reply": "Tell me what you are looking for, and I will search the store catalog.",
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "empty message"
                }
            }

        catalog = self._format_catalog(products)

        if not catalog:
            return {
                "reply": "I could not find any matching products in the store catalog. Try asking for a different type of product.",
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "empty catalog"
                }
            }

        if self.provider != "openai" or not self.api_key or not self.client:
            return {
                "reply": self._fallback_chat_reply(products),
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "OpenAI unavailable"
                }
            }

        try:
            system_prompt = """
You are SmartStore's product assistant.

Rules:
- You may ONLY use the catalog products provided in this request.
- Do not mention products, prices, stock, specs, brands, or facts that are not in the provided catalog.
- Do not browse the web, imply web access, or suggest checking external websites.
- If the user asks for something outside the catalog, say that you can only help with products currently in SmartStore.
- If no listed product fits, say so clearly and suggest what is closest from the provided catalog.
- Keep replies concise and useful for shopping.
- When recommending products, refer to product names exactly as they appear in the catalog.
"""

            chat_messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "system",
                    "content": f"""
Catalog products available for this answer:
{json.dumps(catalog, ensure_ascii=False)}
"""
                }
            ]

            for item in cleaned_messages[-8:]:
                chat_messages.append({
                    "role": item["role"],
                    "content": item["content"]
                })

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_completion_tokens=350,
                messages=chat_messages
            )

            return {
                "reply": response.choices[0].message.content.strip(),
                "_meta": {
                    "source": "openai",
                    "provider": self.provider,
                    "model": self.model,
                    "error": None
                }
            }

        except Exception as e:
            return {
                "reply": self._fallback_chat_reply(products),
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "OpenAI request failed"
                }
            }

    def _fallback_interpretation(self, query):
        stop_words = {
            "for", "with", "the", "a", "an",
            "and", "or", "long", "daily", "use"
        }

        words = []

        for w in query.split():
            w = w.lower().strip()
            if w and w not in stop_words:
                words.append(w)

        unique = []

        for w in words:
            if w not in unique:
                unique.append(w)

        return {
            "keywords": unique[:5],
            "category": None,
            "tags": unique[:5]
        }

    def _clean_list(self, value):
        if not isinstance(value, list):
            return []

        result = []

        for item in value:
            if isinstance(item, str):
                s = item.strip().lower()
                if s and s not in result:
                    result.append(s)

        return result

    def _clean_string(self, value):
        if not isinstance(value, str):
            return None

        s = value.strip().lower()

        if not s:
            return None

        return s

    def _clean_messages(self, messages):
        if not isinstance(messages, list):
            return []

        result = []

        for message in messages:
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")

            if role not in {"user", "assistant"}:
                continue

            if not isinstance(content, str):
                continue

            cleaned_content = content.strip()

            if cleaned_content:
                result.append({
                    "role": role,
                    "content": cleaned_content[:1000]
                })

        return result[-10:]

    def _format_catalog(self, products):
        catalog = []

        for product in products[:12]:
            catalog.append({
                "id": product.get("id"),
                "name": product.get("name"),
                "description": product.get("description"),
                "bullet_points": product.get("bullet_points"),
                "category": product.get("category"),
                "tags": product.get("tags"),
                "price": product.get("price"),
                "stock": product.get("stock")
            })

        return catalog

    def _fallback_chat_reply(self, products):
        if not products:
            return "I could not find a matching product in the SmartStore catalog. Try describing the product type or feature you need."

        names = [product.get("name") for product in products[:3] if product.get("name")]

        if not names:
            return "I found a few catalog matches, but they do not have enough details for a confident recommendation."

        if len(names) == 1:
            return f"The closest product I found in SmartStore is {names[0]}."

        return f"The closest products I found in SmartStore are {', '.join(names)}."


ai_search_service = AISearchService()
