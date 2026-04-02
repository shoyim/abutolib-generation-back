from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .quiz_service import QuizService


class QuizGenerateView(APIView):
    def post(self, request):
        pages_data = request.data.get("pages_data")
        config = request.data.get("config")

        if not pages_data or not config:
            return Response(
                {"error": "pages_data va config majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not config.get("questions_count") or not config.get("difficulty"):
            return Response(
                {"error": "config ichida questions_count va difficulty majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if isinstance(pages_data, dict):
            raw_text = "\n\n".join(pages_data.values())
        elif isinstance(pages_data, str):
            raw_text = pages_data
        else:
            return Response(
                {"error": "pages_data noto'g'ri formatda"},
                status=status.HTTP_400_BAD_REQUEST
            )

        questions = QuizService.process_full_pipeline(config=config, raw_text=raw_text)

        return Response({
            "status": "success",
            "total_questions": len(questions),
            "data": questions
        }, status=status.HTTP_200_OK)