from rest_framework import serializers

class OCRRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    start_page = serializers.IntegerField(required=False, min_value=1)
    end_page = serializers.IntegerField(required=False, min_value=1)