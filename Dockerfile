FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-uzb \
    tesseract-ocr-eng \
    ghostscript \
    ocrmypdf \
    libpng-dev \
    libjpeg-dev \
    poppler-utils \
    poppler-data \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir gunicorn PyMuPDF pdf2image pillow
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media/ocr_tmp
RUN mkdir -p /app/temp_pages

ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]