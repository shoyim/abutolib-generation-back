# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.files.storage import default_storage
import os
from .services import QuizService

class FullQuizGenerateView(APIView):
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Fayl yuklanmadi"}, status=400)
        
        file_path = default_storage.save(f"tmp/{file_obj.name}", file_obj)
        full_path = default_storage.path(file_path)
        
        config = {
            "language": request.data.get('language', "O'zbekcha"),
            "difficulty": request.data.get('difficulty', 'Medium'),
            "questions_count": int(request.data.get('questions_count', 5)),
        }
        
        try:
            questions = QuizService.process_full_pipeline(full_path, config)
            return Response({
                "status": "success",
                "total_questions": len(questions),
                "data": questions
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        finally:
            if os.path.exists(full_path):
                os.remove(full_path)
            output_pdf = full_path.rsplit('.', 1)[0] + "_ocr.pdf"
            if os.path.exists(output_pdf):
                os.remove(output_pdf)