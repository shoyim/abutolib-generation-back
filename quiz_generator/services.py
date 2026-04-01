import json
import google.generativeai as genai
import subprocess
import os
from processing_app.utils import split_text_into_chunks

class QuizService:
    @staticmethod
    def run_ocr(file_path):
        output_base = file_path.rsplit('.', 1)[0]
        sidecar_file = output_base + ".txt"
        output_pdf = output_base + "_ocr.pdf"
        
        try:
            subprocess.run([
                "ocrmypdf", 
                "--skip-text",
                "--language", "uzb+eng", 
                "--sidecar", sidecar_file, 
                file_path, 
                output_pdf
            ], check=True, capture_output=True)
            
            if os.path.exists(sidecar_file):
                with open(sidecar_file, "r", encoding="utf-8") as f:
                    text = f.read()
                os.remove(sidecar_file)
            else:
                raise Exception("Sidecar file not generated")
                
            if os.path.exists(output_pdf):
                os.remove(output_pdf)
                
            return text
        except subprocess.CalledProcessError as e:
            raise Exception(f"OCR Error: {e.stderr.decode() if e.stderr else str(e)}")

    @staticmethod
    def call_gemini_llm(chunk_text, config):
        api_key = "AIzaSyBdqQmkxDCn25qb9uD2Y9gOoD2xzGapRZg"
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"""
        Siz professional test tuzuvchi ekspertsiz.
        Vazifa: Matn asosida {config['questions_count']} ta test savoli tuzing.
        Tili: {config['language']}
        Qiyinchilik: {config['difficulty']}

        QOIDALAR:
        1. Mavzuni matndan avtomatik aniqlang.
        2. Formulalar uchun KaTeX ($...$) ishlating.
        3. FAQAT JSON qaytaring:
        {{
            "detected_main_topic": "...",
            "questions": [
                {{
                    "topic": "...",
                    "difficulty": "...",
                    "question_text": "...",
                    "options": {{"a": "..", "b": "..", "c": "..", "d": ".."}},
                    "correct_answer": "a"
                }}
            ]
        }}
        Matn: {chunk_text}
        """
        response = model.generate_content(prompt)
        return json.loads(response.text)

    @classmethod
    def process_full_pipeline(cls, file_path, config):
        raw_text = cls.run_ocr(file_path)

        print(raw_text)
        
        if not raw_text.strip():
            raise Exception("OCR natijasida matn topilmadi")

        chunks = split_text_into_chunks(raw_text, size=2000, overlap=300)
        
        all_questions = []
        for chunk in chunks[:2]:
            quiz_data = cls.call_gemini_llm(chunk, config)
            if "questions" in quiz_data:
                all_questions.extend(quiz_data['questions'])
        
        return all_questions