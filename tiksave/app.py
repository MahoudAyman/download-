from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import yt_dlp, requests, os, re

app = Flask(__name__, static_folder="static")
CORS(app)

def valid_url(url):
    return bool(re.match(r'(https?://)?(www\.|vm\.)?tiktok\.com/.+', url))

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/info")
def get_info():
    url = request.args.get("url", "").strip()
    if not url or not valid_url(url):
        return jsonify({"error": "رابط غير صحيح"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()
        for f in (info.get("formats") or []):
            if f.get("vcodec") != "none" and f.get("acodec") != "none":
                q = str(f.get("format_note") or f.get("height") or "SD")
                if q not in seen:
                    seen.add(q)
                    formats.append({"format_id": f["format_id"], "quality": q, "ext": f.get("ext","mp4"), "type": "video"})

        for f in (info.get("formats") or []):
            if f.get("vcodec") == "none" and f.get("acodec") != "none":
                formats.append({"format_id": f["format_id"], "quality": "صوت فقط", "ext": "mp3", "type": "audio"})
                break

        return jsonify({
            "title": info.get("title", "فيديو تيك توك"),
            "author": info.get("uploader", "unknown"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "like_count": info.get("like_count", 0),
            "formats": formats
        })
    except Exception as e:
        return jsonify({"error": "تعذّر جلب الفيديو"}), 422

@app.route("/api/download")
def download():
    url = request.args.get("url", "").strip()
    format_id = request.args.get("format_id", "best")
    ext = request.args.get("ext", "mp4")

    if not url or not valid_url(url):
        return jsonify({"error": "رابط غير صحيح"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "format": format_id}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get("url") or info["requested_formats"][0]["url"]
            title = re.sub(r'[^\w\s-]', '', info.get("title", "video"))[:50]

        r = requests.get(video_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.tiktok.com/"
        }, stream=True, timeout=30)

        content_type = "audio/mpeg" if ext == "mp3" else "video/mp4"

        return Response(
            r.iter_content(chunk_size=65536),
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{title}.{ext}"',
                "Content-Length": r.headers.get("Content-Length", ""),
            }
        )
    except:
        return jsonify({"error": "فشل التنزيل"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
