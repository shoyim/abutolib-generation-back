import os
import subprocess
from celery import shared_task

@shared_task
def process_ocr_task(input_path, start_page=None, end_page=None):
    output_pdf = f"{input_path}_out.pdf"
    sidecar_txt = f"{input_path}.txt"
    
    cmd = ["ocrmypdf", "--language", "uzb+eng", "--force-ocr", "--sidecar", sidecar_txt]
    
    if start_page and end_page:
        cmd += ["--pages", f"{start_page}-{end_page}"]
    
    cmd += [input_path, output_pdf]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        pages_dict = {}
        if os.path.exists(sidecar_txt):
            with open(sidecar_txt, 'r', encoding='utf-8') as f:
                content = f.read()
                pages = content.split('\f')
                for i, page_content in enumerate(pages, start=start_page if start_page else 1):
                    if page_content.strip():
                        pages_dict[f"page_{i}"] = page_content.strip()

            for f in [sidecar_txt, output_pdf, input_path]:
                if os.path.exists(f): os.remove(f)
                
            return {"status": "success", "data": pages_dict}
    except Exception as e:
        return {"status": "error", "message": str(e)}