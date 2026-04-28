#!/usr/bin/env python3
import os
import json
import base64
import requests
import argparse
from io import BytesIO
from PIL import Image

def get_api_key():
    # Try environment variable first
    if "GEMINI_API_KEY" in os.environ:
        return os.environ["GEMINI_API_KEY"]
        
    # Try to read from BenchVision local.properties
    props_path = os.path.join(os.path.dirname(__file__), '..', 'BenchVision', 'local.properties')
    if os.path.exists(props_path):
        with open(props_path, 'r') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY'):
                    return line.split('=', 1)[1].strip()
                    
    return None

def main():
    parser = argparse.ArgumentParser(description="Generate CytoAtlas annotations using Gemini 3.1 Pro.")
    parser.add_argument("case_id", help="The ID of the case in cases.json to process (e.g. Case_20260428_085918)")
    args = parser.parse_args()
    
    api_key = get_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment or BenchVision/local.properties")
        return

    cases_json_path = os.path.join(os.path.dirname(__file__), 'cases.json')
    if not os.path.exists(cases_json_path):
        print(f"Error: Could not find {cases_json_path}")
        return

    with open(cases_json_path, 'r') as f:
        cases_data = json.load(f)

    target_case = next((c for c in cases_data.get('cases', []) if c['id'] == args.case_id), None)
    if not target_case:
        print(f"Error: Case '{args.case_id}' not found in cases.json")
        return
        
    image_path = os.path.join(os.path.dirname(__file__), target_case['image'])
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    print(f"Processing case: {args.case_id}")
    print(f"Loading image: {image_path}")
    
    img = Image.open(image_path)
    if img.width > 2000:
        scale = 2000 / img.width
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    buf = BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=85)
    base64_img = base64.b64encode(buf.getvalue()).decode('utf-8')

    specimen_type = target_case.get('specimen_type', 'Unknown fluid')
    magnification = target_case.get('magnification', 'Unknown')
    grid = target_case.get('grid', 'Unknown')
    
    # Calculate total tiles from grid string (e.g. "5x5" or "5×5")
    try:
        parts = grid.replace('×', 'x').split('x')
        num_tiles = int(parts[0]) * int(parts[1])
    except:
        num_tiles = "unknown number of"

    prompt = f"""You are a board-certified hematopathologist reviewing a body fluid cytospin preparation.

Specimen type: {specimen_type}
Magnification: {magnification}
Grid: {grid} (stitched composite of {num_tiles} tiles)

This image is a registered, stitched composite of multiple microscope fields from a Wright-Giemsa stained cytospin.

TASK 0 — Generate a short descriptive case title (4–6 words). This will appear in the case
browser sidebar so it must be specific enough to distinguish this case from others of the same
specimen type. Do NOT begin with the specimen type (e.g. do not start with "BAL" or "Pleural").
Focus on the dominant finding: cell type, pathology, or key morphologic feature.
Examples: "Macrophage-dominant with foamy vacuolation", "Dense neutrophilia, degenerative changes",
"Reactive mesothelial cells, lymphocyte-rich background".

TASK 1 — Identify the 3 most diagnostically interesting or teaching-worthy regions in the image.
For each region draw a TIGHT bounding box that closely fits the feature. Do NOT box the entire
image quadrant — the box should bound the specific cell, cluster, or structure of interest.
Box sizes will naturally vary: a single cell might occupy 2–5% of image width; a large cluster
10–20%; an extended mucus strand 5–30%. Use your judgement to fit the feature.

For each annotation provide:
  x1, y1  — top-left corner of the box (0.0 = left/top edge, 1.0 = right/bottom edge)
  x2, y2  — bottom-right corner of the box (x2 > x1, y2 > y1, always)
  label   — concise feature name (e.g. "Reactive mesothelial cell", "Neutrophil cluster")
  description — 2–3 sentences of teaching commentary for medical students. Describe the
                diagnostic significance and the specific morphologic features to look for.

TASK 2 — Write a 3–5 sentence overall case interpretation paragraph suitable for a teaching
atlas. Summarise cellularity, dominant cell types, background, and any notable or atypical findings.

CRITICAL: Respond ONLY with valid JSON. No markdown fences, no preamble, no explanation.
Exact schema:
{{
  "title": "Short descriptive title here",
  "annotations": [
    {{ "x1": 0.12, "y1": 0.30, "x2": 0.28, "y2": 0.52, "label": "...", "description": "..." }},
    {{ "x1": 0.55, "y1": 0.10, "x2": 0.78, "y2": 0.38, "label": "...", "description": "..." }},
    {{ "x1": 0.40, "y1": 0.65, "x2": 0.62, "y2": 0.88, "label": "...", "description": "..." }}
  ],
  "interpretation": "Overall paragraph here."
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"inlineData": {"mimeType": "image/jpeg", "data": base64_img}},
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }

    print("Calling Gemini API...")
    r = requests.post(url, json=payload)
    if not r.ok:
        print("API Error:", r.status_code, r.text)
        return
        
    resp_data = r.json()
    text = ""
    for candidate in resp_data.get('candidates', []):
        for part in candidate.get('content', {}).get('parts', []):
            text += part.get('text', '')
            
    text = text.replace('```json', '').replace('```', '').strip()
    try:
        parsed = json.loads(text)
    except Exception as e:
        print("JSON parse error:", e)
        print("Raw text output from Gemini:")
        print(text)
        return
        
    target_case['title'] = parsed.get('title', target_case.get('title', ''))
    target_case['annotations'] = parsed.get('annotations', [])
    target_case['interpretation'] = parsed.get('interpretation', '')
    target_case['ai_generated'] = True
    
    with open(cases_json_path, 'w') as f:
        json.dump(cases_data, f, indent=2)
        
    print(f"Successfully generated annotations and updated cases.json for {args.case_id}!")

if __name__ == '__main__':
    main()
