from flask import Flask, request, jsonify
from PIL import Image
from io import BytesIO
import requests

app = Flask(__name__)

def process_image(url):
    # Fetch the image
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None
    
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = img.resize((64, 64), Image.LANCZOS)
    
    # Quantize
    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
    rgb_img.paste(img, mask=img.split()[3])
    quantized = rgb_img.quantize(colors=32)
    quantized_rgb = quantized.convert("RGB")
    
    # Build palette
    palette_raw = quantized.getpalette()
    palette = []
    for i in range(32):
        r = palette_raw[i * 3]
        g = palette_raw[i * 3 + 1]
        b = palette_raw[i * 3 + 2]
        palette.append([r, g, b])
    
    # Build pixel map
    pixels = list(quantized.getdata())
    alpha_data = list(img.split()[3].getdata())
    
    return {
        "palette": palette,
        "pixels": pixels,
        "alpha": alpha_data,
        "size": 64
    }

@app.route("/process")
def process():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    result = process_image(url)
    if not result:
        return jsonify({"error": "Failed to process image"}), 500
    
    return jsonify(result)

@app.route("/")
def health():
    return "Paint Processor is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)