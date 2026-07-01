from flask import Flask, request, jsonify
from PIL import Image
from io import BytesIO
import requests

app = Flask(__name__)

MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024   # 15MB cap on the fetch itself
MAX_SOURCE_DIMENSION = 4000              # refuse absurdly large source images

def process_image(url):
    # Stream the download so we can bail early if it's too big
    response = requests.get(url, timeout=10, stream=True)
    if response.status_code != 200:
        return None, "Failed to fetch image"

    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
        return None, "Image too large"

    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            return None, "Image too large"
        chunks.append(chunk)
    raw = b"".join(chunks)

    try:
        img = Image.open(BytesIO(raw))
        img.load()  # will raise if truncated/corrupt
    except Exception:
        return None, "Invalid image"

    # Reject huge source images BEFORE any RGBA conversion/resize
    if img.width > MAX_SOURCE_DIMENSION or img.height > MAX_SOURCE_DIMENSION:
        return None, "Image dimensions too large"

    img = img.convert("RGBA")
    img = img.resize((128, 128), Image.LANCZOS)

    rgb_img = Image.new("RGB", img.size, (255, 255, 255))
    rgb_img.paste(img, mask=img.split()[3])
    quantized = rgb_img.quantize(colors=32)

    palette_raw = quantized.getpalette()
    palette = []
    for i in range(32):
        r = palette_raw[i * 3]
        g = palette_raw[i * 3 + 1]
        b = palette_raw[i * 3 + 2]
        palette.append([r, g, b])

    pixels = list(quantized.getdata())
    alpha_data = list(img.split()[3].getdata())

    return {
        "palette": palette,
        "pixels": pixels,
        "alpha": alpha_data,
        "size": 128
    }, None

@app.route("/process")
def process():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    result, error = process_image(url)
    if result is None:
        return jsonify({"error": error or "Failed to process image"}), 500

    return jsonify(result)

@app.route("/")
def health():
    return "Paint Processor is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
