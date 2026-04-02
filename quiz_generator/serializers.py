# api/serializers.py
from rest_framework import serializers


class QuizConfigSerializer(serializers.Serializer):
    questions_count = serializers.IntegerField(min_value=1, max_value=100)
    difficulty = serializers.ChoiceField(choices=['oson', 'o\'rta', 'qiyin'])
    model = serializers.ChoiceField(
        choices=['deepseek-chat', 'deepseek-reasoner', 'deepseek-v4'],
        default='deepseek-chat'
    )
    language = serializers.ChoiceField(choices=['uz', 'en', 'ru'], default='uz')
    include_explanations = serializers.BooleanField(default=False)
    use_cache = serializers.BooleanField(default=True)
    use_off_peak = serializers.BooleanField(default=True)
    chunk_size = serializers.IntegerField(min_value=1000, max_value=16000, default=8000)
    delay_between_requests = serializers.FloatField(min_value=0.5, max_value=10, default=2)


class QuizGenerateSerializer(serializers.Serializer):
    pages_data = serializers.JSONField()
    config = QuizConfigSerializer()