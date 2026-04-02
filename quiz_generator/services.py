import json
import os
import subprocess
import time
from google import genai
from google.genai import types
from processing_app.utils import split_text_into_chunks
from dotenv import load_dotenv

load_dotenv()


class QuizService:
    @staticmethod
    def run_ocr(file_path):
        output_base = file_path.rsplit('.', 1)[0]
        sidecar_file = output_base + ".txt"
        output_pdf = output_base + "_ocr.pdf"

        try:
            subprocess.run([
                "ocrmypdf", "--force-ocr", "--language", "uzb+eng",
                "--sidecar", sidecar_file, file_path, output_pdf
            ], check=True, capture_output=True, text=True)

            text = ""
            if os.path.exists(sidecar_file):
                with open(sidecar_file, "r", encoding="utf-8") as f:
                    text = f.read()
                os.remove(sidecar_file)

            if os.path.exists(output_pdf):
                os.remove(output_pdf)

            return text
        except Exception:
            return ""

    @staticmethod
    def call_gemini_llm(chunk_text, config):
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        prompt = f"""
Siz professional test tuzuvchisiz. {config['questions_count']} ta savol tuzing.
Faqat O'zbek tilida. Matematik formulalarni $...$ formatida yozing.
Javobni FAQAT JSON formatida qaytaring:
{{
    "detected_main_topic": "...",
    "questions": [
        {{
            "topic": "...",
            "difficulty": "{config['difficulty']}",
            "question_text": "...",
            "options": {{"a": "...", "b": "...", "c": "...", "d": "..."}},
            "correct_answer": "a"
        }}
    ]
}}
MATN:
{chunk_text}
"""
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                return json.loads(response.text)
            return None
        except Exception:
            return None

    @classmethod
    def process_full_pipeline(cls, config, file_path=None, raw_text=None):
        if not raw_text:
            if not file_path:
                return []
            raw_text = cls.run_ocr(file_path)

        if not raw_text.strip():
            return []

        chunks = split_text_into_chunks(raw_text, size=8000, overlap=800)
        all_questions = []

        for chunk in chunks:
            try:
                quiz_data = cls.call_gemini_llm(chunk, config)
                if quiz_data and "questions" in quiz_data:
                    all_questions.extend(quiz_data["questions"])
            except Exception:
                if all_questions:
                    return all_questions
                continue

            time.sleep(4)

        return all_questions