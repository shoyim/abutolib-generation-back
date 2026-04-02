# services.py - to'liq qayta ishlangan versiya
import os
import json
import tempfile
import base64
import requests
import time
import subprocess
import sys


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
        page_texts = {}
        
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if end_page > total_pages:
                end_page = total_pages

            for page_num in range(start_page - 1, end_page):
                page = doc[page_num]
                
                matn = page.get_text()
                
                if not matn or len(matn.strip()) < 100:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    deepseek_text = cls.call_deepseek_ocr(img_base64)
                    if deepseek_text:
                        matn = deepseek_text
                    else:
                        matn = ""
                
                page_texts[page_num + 1] = matn
                print(f"Sahifa {page_num + 1}: {len(matn)} belgi topildi", file=sys.stderr)

            doc.close()
            return page_texts

        except Exception as e:
            print(f"PyMuPDF xatosi: {e}", file=sys.stderr)
            return cls.ocr_with_pdf2image(pdf_path, start_page, end_page)

    @classmethod
    def ocr_with_pdf2image(cls, pdf_path, start_page, end_page):
        page_texts = {}
        
        try:
            from pdf2image import convert_from_path
            import pytesseract
            from PIL import Image
            import io

            images = convert_from_path(pdf_path, first_page=start_page, last_page=end_page, dpi=300)

            for idx, image in enumerate(images):
                page_num = start_page + idx
                
                text = pytesseract.image_to_string(image, lang='uzb+eng')
                
                if not text or len(text.strip()) < 100:
                    buffered = io.BytesIO()
                    image.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    deepseek_text = cls.call_deepseek_ocr(img_base64)
                    if deepseek_text:
                        text = deepseek_text
                    else:
                        text = ""
                
                page_texts[page_num] = text
                print(f"Sahifa {page_num}: {len(text)} belgi topildi", file=sys.stderr)

            return page_texts

        except Exception as e:
            print(f"PDF2Image xatosi: {e}", file=sys.stderr)
            return {}

    @classmethod
    def call_deepseek_ocr(cls, image_base64):
        if not cls.DEEPSEEK_API_KEY:
            print("DeepSeek API kaliti topilmadi", file=sys.stderr)
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
                            "text": "Extract all text from this image. Return only the extracted text. No explanations. Keep the original language."
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
                timeout=60,
                proxies=proxies
            )
            
            print(f"DeepSeek API javobi: {response.status_code}", file=sys.stderr)
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                print(f"OCR natijasi: {len(text)} belgi", file=sys.stderr)
                return text
            else:
                print(f"API xatosi: {response.text}", file=sys.stderr)
                return ""
                
        except Exception as e:
            print(f"DeepSeek OCR xatosi: {e}", file=sys.stderr)
            return ""

    @classmethod
    def generate_questions_from_text(cls, page_text, config):
        if not cls.DEEPSEEK_API_KEY:
            print("DeepSeek API kaliti topilmadi", file=sys.stderr)
            return []

        if not page_text or len(page_text.strip()) < 100:
            print(f"Matn juda qisqa: {len(page_text)} belgi", file=sys.stderr)
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

Important rules:
- Each question must have 4 options (a, b, c, d)
- Only one correct answer
- Questions must be based ONLY on the given text
- Do not add any explanations
- Return ONLY valid JSON, no other text

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
                timeout=60,
                proxies=proxies
            )

            print(f"Test yaratish API javobi: {response.status_code}", file=sys.stderr)

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                print(f"Raw response: {content[:200]}", file=sys.stderr)

                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]

                data = json.loads(content)
                questions = data.get("questions", [])
                
                print(f"{len(questions)} ta savol yaratildi", file=sys.stderr)

                for q in questions:
                    q["page"] = config.get("page_number")
                    q["difficulty"] = config.get("difficulty")

                return questions

            return []

        except json.JSONDecodeError as e:
            print(f"JSON decode xatosi: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Test yaratish xatosi: {e}", file=sys.stderr)
            return []