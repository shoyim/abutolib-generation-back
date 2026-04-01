# services.py
import json
import os
import subprocess
import google.generativeai as genai
from processing_app.utils import split_text_into_chunks
from dotenv import load_dotenv

load_dotenv()

proxy_url = "socks5://socks5:9091"
os.environ['http_proxy'] = proxy_url
os.environ['https_proxy'] = proxy_url
os.environ['HTTP_PROXY'] = proxy_url
os.environ['HTTPS_PROXY'] = proxy_url

os.environ['GOOGLE_API_USE_MTLS'] = 'never'
os.environ['GOOGLE_API_USE_CLIENT_CERTIFICATE'] = 'false'

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
                raise Exception("OCR natija fayli (sidecar) yaratilmadi.")
                
            if os.path.exists(output_pdf):
                os.remove(output_pdf)
                
            return text
        except subprocess.CalledProcessError as e:
            raise Exception(f"ocrmypdf xatosi: {e.stderr}")

    @staticmethod
    def call_gemini_llm(chunk_text, config):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY environment variable topilmadi.")
        
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"""
        Siz professional test tuzuvchisiz. 
        QUYIDAGI MATN ASOSIDA {config['questions_count']} TA SAVOL TUZING.
        
        MATN: {chunk_text}
        
        TILI: {config['language']}
        QIYINCHILIK: {config['difficulty']}
        
        QOIDALAR:
        1. Faqat berilgan matn mazmunidan savollar tuzing.
        2. Mavzuni matndan avtomatik aniqlang.
        3. Matematik formulalarni $...$ (KaTeX) formatida yozing.
        4. Javobni faqat ushbu JSON strukturada qaytaring:
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
        """
        
        response = model.generate_content(prompt)
        return json.loads(response.text)

    @classmethod
    def process_full_pipeline(cls, file_path, config):
        raw_text = cls.run_ocr(file_path)
        
        if len(raw_text.strip()) < 20:
            raise Exception("OCR matnni aniqlay olmadi. Iltimos, PDF sifatini tekshiring.")
        
        chunks = split_text_into_chunks(raw_text, size=2500, overlap=300)
        
        all_questions = []
        for chunk in chunks[:2]:
            quiz_data = cls.call_gemini_llm(chunk, config)
            if "questions" in quiz_data:
                all_questions.extend(quiz_data['questions'])
        
        return all_questions