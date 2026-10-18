"""Repeatable synthetic vision checks through a local OpenAI-compatible API.

Tests chart reading, shape/color/position recognition, OCR, and two-image input.
These are smoke fixtures, not a representative vision-accuracy benchmark.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, time, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def fixtures(folder):
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 34)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 25)
    rows = []
    image = Image.new('RGB', (720, 420), 'white')
    d = ImageDraw.Draw(image)
    d.rectangle((55, 65, 235, 245), fill='red')
    d.ellipse((440, 65, 620, 245), fill='blue')
    d.text((155, 310), 'ARYA VISION 8462', font=font, fill='black')
    rows.append(('shapes', image, 'Describe the shapes on the left and right, including their colors. Transcribe the text at the bottom.', [['red', 'square'], ['blue', 'circle'], ['8462']]))
    image = Image.new('RGB', (720, 420), 'white')
    d = ImageDraw.Draw(image)
    d.text((30, 20), 'Completed tests by module', font=font, fill='black')
    for x, height, label, color in [(110, 80, 'Parser: 4', 'green'), (310, 160, 'Cache: 8', 'orange'), (510, 240, 'Router: 12', 'purple')]:
        d.rectangle((x, 340 - height, x + 85, 340), fill=color)
        d.text((x - 20, 355), label, font=small, fill='black')
    rows.append(('chart', image, 'Which module has the highest number of completed tests? State its name and exact value.', [['router'], ['12']]))
    image = Image.new('RGB', (720, 420), '#17202a')
    d = ImageDraw.Draw(image)
    for y, text in [(40, 'Build check: FAILED'), (105, 'File: parser.py'), (170, 'Line 27: expected token COLON'), (235, 'Build ID: ARYA-5907')]:
        d.text((35, y), text, font=small, fill='white')
    rows.append(('build-screen', image, 'Read this build screen. Report the file name, line number, expected token and build ID.', [['parser.py'], ['27'], ['colon'], ['arya-5907']]))
    out = []
    for name, image, prompt, checks in rows:
        path = folder / (name + '.png')
        image.save(path)
        out.append((name, [path], prompt, checks))
    out.append(('two-images', [out[0][1][0], out[2][1][0]], 'Read both images. Report the numeric code in the shapes image and the build ID in the build screen.', [['8462'], ['arya-5907']]))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url', default='http://127.0.0.1:8080')
    ap.add_argument('--model', required=True)
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    folder = Path(a.out)
    folder.mkdir(parents=True, exist_ok=True)
    cases = fixtures(folder)
    rows = []
    for run in range(a.runs):
        for name, paths, prompt, checks in cases:
            content = [{'type': 'text', 'text': f'[Vision trial {name}-{run}-{time.time_ns()}] ' + prompt}]
            for path in paths:
                content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()}})
            body = {'model': a.model, 'messages': [{'role': 'user', 'content': content}], 'max_tokens': 256, 'temperature': 0, 'reasoning_effort': 'none', 'chat_template_kwargs': {'enable_thinking': False}}
            row = {'case': name, 'run': run, 'prompt': prompt, 'images': [{'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
            start = time.monotonic()
            try:
                request = urllib.request.Request(a.url.rstrip('/') + '/v1/chat/completions', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
                result = json.load(urllib.request.urlopen(request, timeout=180))
                text = result['choices'][0]['message'].get('content', '')
                lower = text.lower()
                row.update(response=result, seconds=time.monotonic() - start, checks=[all((word in lower for word in group)) for group in checks])
                row['passed'] = all(row['checks'])
            except Exception as exc:
                row.update(passed=False, seconds=time.monotonic() - start, error=str(exc))
            rows.append(row)
            (folder / 'results.json').write_text(json.dumps({'model': a.model, 'scope': 'synthetic OCR, chart, shape and multiple-image smoke checks; first use versus repeated images not separated', 'results': rows}, indent=2), encoding='utf-8')
            print(name, run, 'PASS' if row['passed'] else 'FAIL', round(row['seconds'], 2), flush=True)
    return int(not all((row['passed'] for row in rows)))
if __name__ == '__main__':
    raise SystemExit(main())
