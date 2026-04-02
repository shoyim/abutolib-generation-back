# services.py - proxy bilan ishlash uchun yangilangan versiya
import os
import json
import tempfile
import base64
import requests
import time
import subprocess


class QuizService:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    @classmethod
    def _get_proxy_config(cls):
        http_proxy = os.getenv("HTTP_PROXY")
        https_proxy = os.getenv("HTTPS_PROXY")
        
        if http_proxy and https_proxy:
            return {
                "http": http_proxy,
                "https": https_proxy
            }
        return None

    @classmethod
    def ocr_pdf_pages(cls, pdf_path, start_page, end_page):
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if end_page > total_pages:
                end_page = total_pages

            page_texts = {}

            for page_num in range(start_page - 1, end_page):
                page = doc[page_num]
                text = page.get_text()

                if not text or len(text.strip()) < 50:
                    images = page.get_images(full=True)
                    if images:
                        for img in images:
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            if pix.n - pix.alpha < 4:
                                img_data = pix.tobytes("png")
                                img_base64 = base64.b64encode(img_data).decode('utf-8')
                                ocr_text = cls.call_deepseek_ocr(img_base64)
                                if ocr_text:
                                    text += "\n" + ocr_text
                            pix = None

                page_texts[page_num + 1] = text

            doc.close()
            return page_texts

        except ImportError:
            return cls.ocr_with_ocrmypdf(pdf_path, start_page, end_page)
        except Exception:
            return cls.ocr_with_ocrmypdf(pdf_path, start_page, end_page)

    @classmethod
    def ocr_with_ocrmypdf(cls, pdf_path, start_page, end_page):
        try:
            import fitz

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_output:
                output_path = tmp_output.name

            subprocess.run([
                "ocrmypdf",
                "--force-ocr",
                "--language", "uzb+eng",
                "--pages", f"{start_page}-{end_page}",
                pdf_path,
                output_path
            ], capture_output=True, check=True)

            doc = fitz.open(output_path)
            page_texts = {}

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                page_texts[start_page + page_num] = text

            doc.close()
            os.unlink(output_path)

            return page_texts

        except Exception:
            return cls.ocr_with_pdf2image(pdf_path, start_page, end_page)

    @classmethod
    def ocr_with_pdf2image(cls, pdf_path, start_page, end_page):
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(pdf_path, first_page=start_page, last_page=end_page, dpi=300)

            page_texts = {}
            for idx, image in enumerate(images):
                page_num = start_page + idx
                text = pytesseract.image_to_string(image, lang='uzb+eng')
                page_texts[page_num] = text

            return page_texts

        except Exception:
            return {}

    @classmethod
    def call_deepseek_ocr(cls, image_base64):
        if not cls.DEEPSEEK_API_KEY:
            return ""

        headers = {
            "Authorization": f"Bearer {cls.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all text from this image. Return only the text, no explanations."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1
        }

        try:
            proxies = cls._get_proxy_config()
            response = requests.post(
                cls.DEEPSEEK_API_URL, 
                headers=headers, 
                json=payload, 
                timeout=30,
                proxies=proxies
            )
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            return ""
        except Exception:
            return ""

    @classmethod
    def generate_questions_from_text(cls, page_text, config):
        if not cls.DEEPSEEK_API_KEY:
            return []

        language_map = {
            "uz": "Uzbek",
            "en": "English",
            "ru": "Russian"
        }
        language_name = language_map.get(config.get("language", "uz"), "Uzbek")

        difficulty_map = {
            "oson": "easy",
            "o'rta": "medium",
            "qiyin": "hard"
        }
        difficulty_en = difficulty_map.get(config.get("difficulty", "o'rta"), "medium")

        prompt = f"""Create {config['questions_count']} multiple-choice questions from the text below.

Language: {language_name}
Difficulty: {difficulty_en}

Rules:
- Each question must have 4 options (a, b, c, d)
- Only one correct answer
- Questions must be based ONLY on the given text
- Return ONLY valid JSON

Output format:
{{
    "questions": [
        {{
            "question_text": "question text",
            "options": {{
                "a": "option a",
                "b": "option b",
                "c": "option c",
                "d": "option d"
            }},
            "correct_answer": "a"
        }}
    ]
}}

Text:
{page_text[:6000]}
"""

        headers = {
            "Authorization": f"Bearer {cls.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a quiz creator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"}
        }

        try:
            proxies = cls._get_proxy_config()
            response = requests.post(
                cls.DEEPSEEK_API_URL, 
                headers=headers, 
                json=payload, 
                timeout=45,
                proxies=proxies
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]

                data = json.loads(content)
                questions = data.get("questions", [])

                for q in questions:
                    q["page"] = config.get("page_number")
                    q["difficulty"] = config.get("difficulty")

                return questions

            return []

        except Exception:
            return []