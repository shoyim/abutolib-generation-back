import json
import os
import subprocess
import requests
from processing_app.utils import split_text_into_chunks
from dotenv import load_dotenv

load_dotenv()

proxy_url = "socks5://socks5:9091"
os.environ['http_proxy'] = proxy_url
os.environ['https_proxy'] = proxy_url
os.environ['HTTP_PROXY'] = proxy_url
os.environ['HTTPS_PROXY'] = proxy_url

OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

class QuizService:
    @staticmethod
    def run_ocr(file_path):
        output_base = file_path.rsplit('.', 1)[0]
        sidecar_file = output_base + ".txt"
        output_pdf = output_base + "_ocr.pdf"
        try:
            subprocess.run([
                "ocrmypdf",
                "--force-ocr",
                "--language", "uzb+eng",
                "--sidecar", sidecar_file,
                file_path,
                output_pdf
            ], check=True, capture_output=True, text=True)
            
            if os.path.exists(sidecar_file):
                with open(sidecar_file, "r", encoding="utf-8") as f:
                    text = f.read()
                os.remove(sidecar_file)
            else:
                raise Exception("OCR natija fayli yaratilmadi.")
                
            if os.path.exists(output_pdf):
                os.remove(output_pdf)
                
            return text
        except subprocess.CalledProcessError as e:
            raise Exception(f"OCR xatosi: {e.stderr}")

    @staticmethod
    def call_ollama_llm(chunk_text, config):
        prompt = f"""
Siz professional test tuzuvchisiz.
{config['questions_count']} ta savol tuzing faqat o'zbek tilida.

MATN:
{chunk_text}

QOIDALAR:
1. Faqat berilgan matn mazmunidan savollar tuzing.
2. Mavzuni matndan aniqlang.
3. Matematik formulalarni $...$ formatida yozing.
4. Javobni faqat JSON formatda qaytaring:
{{
    "detected_main_topic": "...",
    "questions": [
        {{
            "topic": "...",
            "difficulty": "{config['difficulty']}",
            "question_text": "...",
            "options": {{"a": "..", "b": "..", "c": "..", "d": ".."}},
            "correct_answer": "a"
        }}
    ]
}}
"""
        data = {
            "model": "phi",
            "prompt": prompt,
            "stream": False
        }
        res = requests.post(OLLAMA_API_URL, json=data, timeout=120)
        res_json = res.json()
        content = res_json.get("response", "").strip()
        if not content:
            raise Exception(f"Ollama bo‘sh javob berdi:\n{res_json}")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise Exception(f"JSON parsing xatosi:\n{content}")

    @classmethod
    def process_full_pipeline(cls, file_path, config):
        raw_text = cls.run_ocr(file_path)
        if len(raw_text.strip()) < 20:
            raise Exception("OCR matn aniqlanmadi.")
        
        chunks = split_text_into_chunks(raw_text, size=1500, overlap=300)
        all_questions = []
        for chunk in chunks:
            quiz_data = cls.call_ollama_llm(chunk, config)
            if "questions" in quiz_data:
                all_questions.extend(quiz_data["questions"])
        return all_questions