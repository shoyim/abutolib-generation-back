# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
import tempfile
import time
import sys
from .services import QuizService


class QuizGenerateView(APIView):
    def post(self, request):
        pdf_file = request.FILES.get("pdf_file")
        start_page = request.data.get("start_page")
        end_page = request.data.get("end_page")
        language = request.data.get("language", "uz")
        difficulty = request.data.get("difficulty", "o'rta")
        questions_per_page = request.data.get("questions_per_page", 5)

        if not pdf_file:
            return Response(
                {"error": "pdf_file majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not start_page or not end_page:
            return Response(
                {"error": "start_page va end_page majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_page = int(start_page)
            end_page = int(end_page)
            questions_per_page = int(questions_per_page)
        except ValueError:
            return Response(
                {"error": "start_page, end_page va questions_per_page integer bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_page < 1 or end_page < start_page:
            return Response(
                {"error": "start_page 1 dan kichik yoki end_page start_page dan kichik bo'lmasligi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if questions_per_page < 1 or questions_per_page > 20:
            return Response(
                {"error": "questions_per_page 1-20 oralig'ida bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_languages = ["uz", "en", "ru"]
        if language not in allowed_languages:
            return Response(
                {"error": f"language {allowed_languages} dan biri bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_difficulties = ["oson", "o'rta", "qiyin"]
        if difficulty not in allowed_difficulties:
            return Response(
                {"error": f"difficulty {allowed_difficulties} dan biri bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                for chunk in pdf_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name

            print(f"PDF fayl saqlandi: {tmp_path}", file=sys.stderr)
            print(f"OCR boshlanmoqda: {start_page} - {end_page} sahifalar", file=sys.stderr)

            ocr_texts = QuizService.ocr_pdf_pages(tmp_path, start_page, end_page)

            os.unlink(tmp_path)

            if not ocr_texts:
                return Response(
                    {"error": "OCR hech qanday matn topmadi"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            print(f"OCR natijasi: {len(ocr_texts)} sahifa topildi", file=sys.stderr)

            all_questions = []
            for page_num, page_text in ocr_texts.items():
                print(f"Sahifa {page_num} ishlanmoqda...", file=sys.stderr)
                print(f"Matn uzunligi: {len(page_text)} belgi", file=sys.stderr)
                
                if not page_text or len(page_text.strip()) < 50:
                    print(f"Sahifa {page_num} matni juda qisqa, o'tkazib yuborildi", file=sys.stderr)
                    continue

                config = {
                    "questions_count": questions_per_page,
                    "difficulty": difficulty,
                    "language": language,
                    "page_number": page_num
                }

                questions = QuizService.generate_questions_from_text(page_text, config)

                if questions:
                    all_questions.extend(questions)
                    print(f"Sahifa {page_num}: {len(questions)} ta savol qo'shildi", file=sys.stderr)
                else:
                    print(f"Sahifa {page_num}: hech qanday savol yaratilmadi", file=sys.stderr)

                time.sleep(1)

            print(f"Jami savollar: {len(all_questions)}", file=sys.stderr)

            return Response({
                "status": "success",
                "start_page": start_page,
                "end_page": end_page,
                "total_questions": len(all_questions),
                "data": all_questions
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Umumiy xatolik: {e}", file=sys.stderr)
            return Response(
                {"error": f"Xatolik yuz berdi: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )