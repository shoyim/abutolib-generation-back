# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import os
import tempfile
import sys
from .services import QuizService

@method_decorator(csrf_exempt, name='dispatch')
class QuizGenerateView(APIView):
    
    def post(self, request):
        pdf_file = request.FILES.get("pdf_file")
        start_page = request.data.get("start_page")
        end_page = request.data.get("end_page")
        language = request.data.get("language", "uz")
        difficulty = request.data.get("difficulty", "o'rta")
        questions_count = request.data.get("questions_count", 15)
        
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
            questions_count = int(questions_count)
        except ValueError:
            return Response(
                {"error": "start_page, end_page va questions_count integer bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if start_page < 1 or end_page < start_page:
            return Response(
                {"error": "start_page 1 dan kichik yoki end_page start_page dan kichik bo'lmasligi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if questions_count < 1 or questions_count > 50:
            return Response(
                {"error": "questions_count 1-50 oralig'ida bo'lishi kerak"},
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
            
            ocr_texts = QuizService.ocr_pdf_pages(tmp_path, start_page, end_page)
            os.unlink(tmp_path)
            
            if not ocr_texts:
                return Response(
                    {"error": "OCR hech qanday matn topmadi"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            all_questions = []
            pages_with_content = len([text for text in ocr_texts.values() if text and len(text.strip()) >= 50])
            
            if pages_with_content == 0:
                return Response(
                    {"error": "Hech bir sahifada yetarlicha matn topilmadi"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            questions_per_page = max(1, questions_count // pages_with_content)
            
            for page_num, page_text in ocr_texts.items():
                if not page_text or len(page_text.strip()) < 50:
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
            
            if len(all_questions) > questions_count:
                all_questions = all_questions[:questions_count]
            
            return Response({
                "status": "success",
                "start_page": start_page,
                "end_page": end_page,
                "total_questions": len(all_questions),
                "data": all_questions
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Xatolik yuz berdi: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )