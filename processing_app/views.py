from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ChunkingSerializer
from .utils import split_text_into_chunks

class TextChunkingView(APIView):
    def post(self, request):
        serializer = ChunkingSerializer(data=request.data)
        if serializer.is_valid():
            raw_text = serializer.validated_data['text']
            size = serializer.validated_data['chunk_size']
            overlap = serializer.validated_data['chunk_overlap']
            
            try:
                chunks = split_text_into_chunks(raw_text, size, overlap)
                
                result = [
                    {
                        "chunk_id": i + 1,
                        "content": chunk,
                        "length": len(chunk)
                    } for i, chunk in enumerate(chunks)
                ]
                
                return Response({
                    "total_chunks": len(result),
                    "chunks": result
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)