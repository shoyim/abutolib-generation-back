import os
import subprocess
import uuid
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import OCRRequestSerializer

tesseract_path = r"D:\abutolib-generation\ocr_bin\tesseract.exe"
gs_path = r"D:\abutolib-generation\ocr_bin\gs\bin\gswin64c.exe"

import os
os.environ['PATH'] += f";{os.path.dirname(tesseract_path)};{os.path.dirname(gs_path)}"

class OCRSimpleView(APIView):
    def post(self, request):
        serializer = OCRRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data['file']
        start_page = serializer.validated_data.get('start_page')
        end_page = serializer.validated_data.get('end_page')

        temp_id = uuid.uuid4().hex
        file_path = default_storage.save(f"ocr_tmp/{temp_id}_{file_obj.name}", file_obj)
        full_input_path = default_storage.path(file_path)
        
        output_pdf = f"{full_input_path}_out.pdf"
        sidecar_txt = f"{full_input_path}.txt"
        
        cmd = ["ocrmypdf", "--language", "uzb+eng", "--force-ocr", "--sidecar", sidecar_txt]
        
        if start_page and end_page:
            cmd += ["--pages", f"{start_page}-{end_page}"]
        
        cmd += [full_input_path, output_pdf]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            pages_dict = {}
            if os.path.exists(sidecar_txt):
                with open(sidecar_txt, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    pages = content.split('\f')
                    current_page = start_page if start_page else 1
                    
                    for page_content in pages:
                        if page_content.strip():
                            pages_dict[f"page_{current_page}"] = page_content.strip()
                            current_page += 1


                for f in [sidecar_txt, output_pdf, full_input_path]:
                    if os.path.exists(f): os.remove(f)
                
                return Response({
                    "status": "success",
                    "data": pages_dict
                }, status=status.HTTP_200_OK)
            
            return Response({"error": "Matn fayli yaratilmadi"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except subprocess.CalledProcessError as e:
            return Response({
                "error": "OCR jarayonida xatolik",
                "details": e.stderr
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)