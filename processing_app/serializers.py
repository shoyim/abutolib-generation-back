from rest_framework import serializers

class ChunkingSerializer(serializers.Serializer):
    text = serializers.CharField()
    chunk_size = serializers.IntegerField(default=1000)
    chunk_overlap = serializers.IntegerField(default=200)