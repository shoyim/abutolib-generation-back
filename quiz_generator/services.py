# services.py
import os
import json
import tempfile
import base64
import requests
import time
import sys
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

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
    def ocr_pdf_pages_fast(cls, pdf_path, start_page, end_page):
        page_texts = {}
        
        try:
            from pdf2image import convert_from_path
            import pytesseract
            from PIL import Image
            import io

            print(f"PDF2Image bilan OCR boshlanmoqda...", file=sys.stderr)
            
            images = convert_from_path(pdf_path, dpi=150, first_page=start_page, last_page=end_page)
            print(f"Jami {len(images)} ta rasmga aylantirildi (sahifalar: {start_page}-{end_page})", file=sys.stderr)
            
            def process_page(idx, image):
                page_num = start_page + idx
                try:
                    tesseract_text = pytesseract.image_to_string(image, lang='uzb+eng', config='--psm 6')
                    return page_num, tesseract_text if tesseract_text else ""
                except Exception as e:
                    print(f"Sahifa {page_num} xatosi: {e}", file=sys.stderr)
                    return page_num, ""
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(process_page, idx, img): idx for idx, img in enumerate(images)}
                
                for future in concurrent.futures.as_completed(futures):
                    page_num, text = future.result()
                    page_texts[page_num] = text
                    if text:
                        print(f"Sahifa {page_num}: {len(text)} belgi", file=sys.stderr)
                    else:
                        print(f"Sahifa {page_num}: matn topilmadi", file=sys.stderr)
            
            return page_texts

        except Exception as e:
            print(f"PDF2Image xatosi: {e}", file=sys.stderr)
            return {}

    @classmethod
    def generate_questions_from_text_fast(cls, page_text, config):
        if not cls.DEEPSEEK_API_KEY:
            print("DeepSeek API kaliti topilmadi", file=sys.stderr)
            return []

        if not page_text or len(page_text.strip()) < 50:
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

        prompt = f"""Create {config['questions_count']} multiple-choice questions from the text.

Rules:
- Each question must have 4 options (a, b, c, d)
- Only one correct answer
- Questions must be based ONLY on the given text
- Return ONLY valid JSON
- It is not necessary to get the question numbers.

Output format:
{{
    "questions": [
        {{
            "question_text": "question text",
            "topic": "Question asked topic"
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
{page_text[:4000]}
"""

        headers = {
            "Authorization": f"Bearer {cls.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 3000,
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

                print(f"{len(questions)} ta savol yaratildi", file=sys.stderr)
                return questions

            else:
                print(f"API xatosi: {response.status_code}", file=sys.stderr)
                return []

        except Exception as e:
            print(f"Test yaratish xatosi: {e}", file=sys.stderr)
            return []