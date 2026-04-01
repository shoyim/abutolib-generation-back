from django.db import models
import os


class OCRJob(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_PROCESSING, 'Jarayonda'),
        (STATUS_DONE, 'Tayyor'),
        (STATUS_FAILED, 'Xato'),
    ]

    # Upload
    pdf_file = models.FileField(upload_to='uploads/')
    original_filename = models.CharField(max_length=255)

    # Settings
    languages = models.CharField(
        max_length=100,
        default='uz,ru,en',
        help_text="Vergul bilan ajratilgan til kodlari, masalan: uz,ru,en"
    )

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_pages = models.IntegerField(default=0)
    processed_pages = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    output_directory = models.CharField(max_length=500, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "OCR Ish"
        verbose_name_plural = "OCR Ishlar"

    def __str__(self):
        return f"{self.original_filename} ({self.get_status_display()})"

    @property
    def progress_percent(self):
        if self.total_pages == 0:
            return 0
        return int((self.processed_pages / self.total_pages) * 100)

    @property
    def output_files(self):
        """Output text fayllar ro'yxati"""
        if not self.output_directory or not os.path.exists(self.output_directory):
            return []
        files = []
        for f in sorted(os.listdir(self.output_directory)):
            if f.endswith('.txt'):
                filepath = os.path.join(self.output_directory, f)
                size = os.path.getsize(filepath)
                files.append({
                    'name': f,
                    'path': filepath,
                    'size': size,
                    'size_kb': round(size / 1024, 1),
                })
        return files

    @property
    def language_list(self):
        return [lang.strip() for lang in self.languages.split(',') if lang.strip()]