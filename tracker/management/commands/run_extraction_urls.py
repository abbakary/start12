from django.core.management.base import BaseCommand
import tempfile
import os
import requests
import json
from urllib.parse import urlparse

from tracker.utils.document_extraction import extract_document


class Command(BaseCommand):
    help = 'Download given file URLs and run document extraction, printing JSON results.'

    def add_arguments(self, parser):
        parser.add_argument('--urls', nargs='+', help='One or more file URLs to download and extract', required=False)
        parser.add_argument('--output', help='Output JSON file to write results to (optional)')

    def handle(self, *args, **options):
        urls = options.get('urls') or []
        if not urls:
            self.stdout.write(self.style.ERROR('No URLs provided. Use --urls <url1> <url2> ...'))
            return

        results = []
        for url in urls:
            try:
                self.stdout.write(f'Downloading: {url}')
                resp = requests.get(url, stream=True, timeout=30)
                resp.raise_for_status()

                # Determine extension from URL path
                path = urlparse(url).path
                _, ext = os.path.splitext(path)
                if not ext:
                    # Try to infer from content-type
                    ct = resp.headers.get('Content-Type','')
                    if 'pdf' in ct:
                        ext = '.pdf'
                    elif 'jpeg' in ct or 'jpg' in ct:
                        ext = '.jpg'
                    elif 'png' in ct:
                        ext = '.png'
                    else:
                        ext = '.bin'

                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            tf.write(chunk)
                    tmp_path = tf.name

                self.stdout.write(f'Extracting: {tmp_path}')
                extraction = extract_document(tmp_path)
                extraction_output = {
                    'url': url,
                    'file': os.path.basename(tmp_path),
                    'result': extraction
                }
                results.append(extraction_output)

            except Exception as e:
                results.append({'url': url, 'error': str(e)})
            finally:
                try:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

        out_json = json.dumps(results, indent=2, ensure_ascii=False)
        output_file = options.get('output')
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(out_json)
            self.stdout.write(self.style.SUCCESS(f'Wrote results to {output_file}'))
        else:
            self.stdout.write(out_json)
