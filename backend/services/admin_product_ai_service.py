import os
import json
import re
from openai import OpenAI


class AdminProductAIService:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai").lower()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        self.client = None
        if self.provider == "openai" and self.api_key:
            self.client = OpenAI(api_key=self.api_key, timeout=20.0, max_retries=1)

    def interpret_product_request(self, admin_message: str, current_draft=None):
        current_draft = current_draft or {}
        normalized_draft = self._normalize_product_draft(current_draft)
        cleaned_message = (admin_message or "").strip()

        if not cleaned_message and not self._has_any_value(normalized_draft):
            return {
                "status": "needs_clarification",
                "follow_up_question": "Please describe the product you want to add.",
                "product": normalized_draft,
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "empty request"
                }
            }

        if self.provider != "openai":
            return {
                "status": "needs_clarification",
                "follow_up_question": "AI provider is not configured correctly.",
                "product": normalized_draft,
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "AI_PROVIDER not openai"
                }
            }

        if not self.api_key or not self.client:
            return {
                "status": "needs_clarification",
                "follow_up_question": "OpenAI API is not configured.",
                "product": normalized_draft,
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "OPENAI_API_KEY missing or client not initialized"
                }
            }

        try:
            system_prompt = """
You are an assistant helping an admin create a product for an e-commerce catalog.

Your job:
- Read the admin's latest message.
- Read the current draft.
- Merge them into one improved product draft.
- Infer obvious fields from context when reasonable.
- Do NOT ask for fields that can already be reasonably inferred from the admin's information.

Required product fields:
- name: string
- description: string
- bullet_points: array of short strings
- category: string
- tags: array of short strings
- price: number
- stock: integer

Important behavior:
- If the admin provides brand, model, product type, quantity, or features, use them.
- If the admin says something like "BMW cars" and later "model name is M4", the name should become "BMW M4".
- If the admin provides clear features, generate description, bullet_points, and tags from them.
- Infer category when obvious. Example: cars -> Vehicles, mouse -> Accessories, monitor -> Monitors.
- Do NOT invent price or stock if not provided.
- If only a small missing piece remains, ask only for that missing piece.
- If enough information exists, return status = "ready".

Rules:
- Return ONLY valid JSON.
- Do NOT return markdown.
- Do NOT return explanations outside JSON.
- bullet_points should be short and useful.
- tags should be short lowercase words or short phrases.
- stock must be an integer.
- price must be numeric.

JSON format:
{
  "status": "needs_clarification" or "ready",
  "follow_up_question": "..." or null,
  "product": {
    "name": "...",
    "description": "...",
    "bullet_points": ["...", "..."],
    "category": "...",
    "tags": ["...", "..."],
    "price": 0,
    "stock": 0
  }
}
"""

            user_prompt = f"""
Current draft:
{json.dumps(normalized_draft, ensure_ascii=False)}

Admin message:
{cleaned_message}
"""

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_completion_tokens=500,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(raw)
            ai_product = self._normalize_product_draft(parsed.get("product", {}))

            merged_product = self._merge_product_drafts(normalized_draft, ai_product)
            merged_product = self._apply_local_inference(merged_product, cleaned_message)

            status = parsed.get("status", "needs_clarification")
            follow_up_question = parsed.get("follow_up_question")

            missing_fields = self._get_missing_required_fields(merged_product)

            if missing_fields:
                status = "needs_clarification"
                if not isinstance(follow_up_question, str) or not follow_up_question.strip():
                    follow_up_question = self._build_follow_up_question(missing_fields)
            else:
                status = "ready"
                follow_up_question = None

            return {
                "status": status,
                "follow_up_question": follow_up_question,
                "product": merged_product,
                "_meta": {
                    "source": "openai",
                    "provider": self.provider,
                    "model": self.model,
                    "error": None
                }
            }

        except Exception as e:
            fallback_product = self._apply_local_inference(normalized_draft, cleaned_message)
            missing_fields = self._get_missing_required_fields(fallback_product)

            return {
                "status": "needs_clarification" if missing_fields else "ready",
                "follow_up_question": self._build_follow_up_question(missing_fields) if missing_fields else None,
                "product": fallback_product,
                "_meta": {
                    "source": "fallback",
                    "provider": self.provider,
                    "model": self.model,
                    "error": "OpenAI request failed"
                }
            }

    def _merge_product_drafts(self, current_draft, new_draft):
        merged = {
            "name": new_draft.get("name") or current_draft.get("name"),
            "description": new_draft.get("description") or current_draft.get("description"),
            "bullet_points": new_draft.get("bullet_points") or current_draft.get("bullet_points") or [],
            "category": new_draft.get("category") or current_draft.get("category"),
            "tags": new_draft.get("tags") or current_draft.get("tags") or [],
            "price": new_draft.get("price") if new_draft.get("price") is not None else current_draft.get("price"),
            "stock": new_draft.get("stock") if new_draft.get("stock") is not None else current_draft.get("stock")
        }

        return self._normalize_product_draft(merged)

    def _apply_local_inference(self, product, latest_message):
        product = self._normalize_product_draft(product)
        message = (latest_message or "").strip()

        combined_text = " ".join([
            product.get("name") or "",
            product.get("description") or "",
            " ".join(product.get("bullet_points", [])),
            product.get("category") or "",
            " ".join(product.get("tags", [])),
            message
        ]).strip()

        lowered = combined_text.lower()

        brand = self._extract_brand(lowered)
        model = self._extract_model_name(message)

        if not product.get("category"):
            inferred_category = self._infer_category(lowered)
            if inferred_category:
                product["category"] = inferred_category

        if not product.get("name"):
            inferred_name = self._infer_name(lowered, brand, model, product.get("category"))
            if inferred_name:
                product["name"] = inferred_name
        else:
            if brand and model and model.lower() not in product["name"].lower():
                if brand.lower() in product["name"].lower():
                    product["name"] = f"{brand} {model}"
                elif product["name"].lower() in ["cars", "bmw cars", "car", "vehicle", "vehicles"]:
                    product["name"] = f"{brand} {model}"

        if not product.get("description"):
            inferred_description = self._infer_description(product, lowered, brand, model)
            if inferred_description:
                product["description"] = inferred_description

        if not product.get("bullet_points"):
            product["bullet_points"] = self._infer_bullet_points(lowered)

        if not product.get("tags"):
            product["tags"] = self._infer_tags(lowered, brand, model, product.get("category"))

        if product.get("stock") is None:
            stock = self._extract_stock(lowered)
            if stock is not None:
                product["stock"] = stock

        if product.get("price") is None:
            price = self._extract_price(lowered)
            if price is not None:
                product["price"] = price

        product = self._normalize_product_draft(product)

        return product

    def _extract_brand(self, lowered_text):
        known_brands = [
            "bmw", "mercedes", "audi", "toyota", "tesla", "ford", "honda",
            "apple", "samsung", "dell", "hp", "lenovo", "logitech"
        ]

        for brand in known_brands:
            if re.search(rf"\b{re.escape(brand)}\b", lowered_text):
                return brand.upper() if brand == "bmw" or brand == "hp" else brand.title()

        return None

    def _extract_model_name(self, text):
        if not text:
            return None

        patterns = [
            r"model name is\s+([A-Za-z0-9\- ]+)",
            r"model is\s+([A-Za-z0-9\- ]+)",
            r"\bmodel:\s*([A-Za-z0-9\- ]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = re.split(r"[.,;\n]", value)[0].strip()
                return value

        return None

    def _extract_stock(self, lowered_text):
        patterns = [
            r"\bi have\s+(\d+)\b",
            r"\bstock\s*(?:is|=)?\s*(\d+)\b",
            r"\bquantity\s*(?:is|=)?\s*(\d+)\b",
            r"\b(\d+)\s+(?:units|items|cars|products)\b"
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered_text)
            if match:
                return int(match.group(1))

        return None

    def _extract_price(self, lowered_text):
        patterns = [
            r"\bprice\s*(?:is|=)?\s*(\d+(?:\.\d+)?)\b",
            r"\bpriced?\s*(?:at)?\s*(\d+(?:\.\d+)?)\b",
            r"\bcosts?\s*(\d+(?:\.\d+)?)\b"
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered_text)
            if match:
                return float(match.group(1))

        return None

    def _infer_category(self, lowered_text):
        if any(word in lowered_text for word in ["car", "cars", "vehicle", "vehicles", "bmw", "mercedes", "audi", "tesla"]):
            return "Vehicles"

        if any(word in lowered_text for word in ["mouse", "keyboard", "headset", "accessory", "accessories"]):
            return "Accessories"

        if any(word in lowered_text for word in ["monitor", "display", "screen"]):
            return "Monitors"

        return None

    def _infer_name(self, lowered_text, brand, model, category):
        if brand and model:
            return f"{brand} {model}"

        if brand and any(word in lowered_text for word in ["car", "cars", "vehicle", "vehicles"]):
            return f"{brand} Cars"

        if model and category == "Vehicles":
            return model

        if "mouse" in lowered_text:
            return "Mouse"

        if "keyboard" in lowered_text:
            return "Keyboard"

        if "monitor" in lowered_text:
            return "Monitor"

        return None

    def _infer_description(self, product, lowered_text, brand, model):
        features = self._infer_bullet_points(lowered_text)
        category = product.get("category")

        if category == "Vehicles":
            if brand and model:
                return f"{brand} {model} vehicle available for purchase with premium features and advanced driving support."
            if brand:
                return f"{brand} vehicle available for purchase with premium features and advanced driving support."
            return "Vehicle available for purchase with premium features and advanced driving support."

        if category == "Accessories":
            return "Accessory product available for purchase with practical features for daily use."

        if category == "Monitors":
            return "Monitor product available for purchase for work and display needs."

        if features:
            return f"Product available for purchase with features such as {', '.join(features[:3])}."

        return None

    def _infer_bullet_points(self, lowered_text):
        feature_map = [
            ("leather seats", "Leather seats"),
            ("gps", "GPS"),
            ("advanced safety", "Advanced safety"),
            ("highway driving support", "Highway driving support"),
            ("wireless", "Wireless connection"),
            ("ergonomic", "Ergonomic design"),
            ("full hd", "Full HD"),
            ("hdmi", "HDMI support"),
            ("mechanical", "Mechanical switches"),
            ("rgb", "RGB lighting")
        ]

        bullet_points = []

        for key, value in feature_map:
            if key in lowered_text and value not in bullet_points:
                bullet_points.append(value)

        return bullet_points

    def _infer_tags(self, lowered_text, brand, model, category):
        tags = []

        if brand:
            tags.append(brand.lower())

        if model:
            tags.append(model.lower())

        if category == "Vehicles":
            for tag in ["car", "vehicle"]:
                if tag not in tags:
                    tags.append(tag)

        keyword_map = [
            "gps",
            "leather seats",
            "advanced safety",
            "highway driving support",
            "wireless",
            "ergonomic",
            "office",
            "gaming",
            "mechanical",
            "monitor",
            "display",
            "mouse",
            "keyboard"
        ]

        for keyword in keyword_map:
            if keyword in lowered_text and keyword not in tags:
                tags.append(keyword)

        return tags

    def _normalize_product_draft(self, product):
        if not isinstance(product, dict):
            product = {}

        return {
            "name": self._clean_string(product.get("name")),
            "description": self._clean_string(product.get("description")),
            "bullet_points": self._clean_list(product.get("bullet_points")),
            "category": self._clean_string(product.get("category")),
            "tags": self._clean_list(product.get("tags")),
            "price": self._clean_price(product.get("price")),
            "stock": self._clean_stock(product.get("stock"))
        }

    def _clean_string(self, value):
        if value is None:
            return None

        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        return cleaned if cleaned else None

    def _clean_list(self, value):
        if value is None:
            return []

        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",")]
            return [item for item in parts if item]

        if not isinstance(value, list):
            return []

        cleaned = []
        for item in value:
            if isinstance(item, str):
                s = item.strip()
                if s and s not in cleaned:
                    cleaned.append(s)

        return cleaned

    def _clean_price(self, value):
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _clean_stock(self, value):
        if value is None or value == "":
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_missing_required_fields(self, product):
        missing = []

        if not product.get("name"):
            missing.append("name")

        if not product.get("description"):
            missing.append("description")

        if not product.get("bullet_points"):
            missing.append("bullet_points")

        if not product.get("category"):
            missing.append("category")

        if not product.get("tags"):
            missing.append("tags")

        if product.get("price") is None:
            missing.append("price")

        if product.get("stock") is None:
            missing.append("stock")

        return missing

    def _build_follow_up_question(self, missing_fields):
        if "price" in missing_fields and "stock" in missing_fields:
            return "What price and stock quantity should I use for this product?"

        if "price" in missing_fields:
            return "What price should I use for this product?"

        if "stock" in missing_fields:
            return "What stock quantity should I use for this product?"

        if "name" in missing_fields:
            return "What product name should I use?"

        if "description" in missing_fields:
            return "Please provide a short product description."

        if "category" in missing_fields:
            return "What category should I use for this product?"

        if "tags" in missing_fields:
            return "What tags should I use for this product?"

        if "bullet_points" in missing_fields:
            return "Please provide the key product features or bullet points."

        return "Please provide the missing information so I can complete the product."

    def _has_any_value(self, product):
        return any([
            product.get("name"),
            product.get("description"),
            product.get("bullet_points"),
            product.get("category"),
            product.get("tags"),
            product.get("price") is not None,
            product.get("stock") is not None
        ])


admin_product_ai_service = AdminProductAIService()
