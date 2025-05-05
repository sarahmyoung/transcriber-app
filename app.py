# app.py
from flask import Flask, render_template, request, redirect, send_file, jsonify
import os
from pipeline import run_transcription

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

status_message = "Idle"

@app.route('/', methods=['GET', 'POST'])
def index():
    print("Serving index.html")
    return render_template('index.html')


@app.route('/transcribe', methods=['POST'])
def transcribe():
    global status_message
    transcript_path = None
    try:
        youtube_url = request.form.get('youtube_url')
        file = request.files.get('file')

        if youtube_url:
            status_message = "🎧 Downloading from YouTube..."
            transcript_path = run_transcription(youtube_url=youtube_url, status_callback=update_status)
        elif file:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            status_message = "📁 File uploaded. Starting transcription..."
            transcript_path = run_transcription(local_file=file_path, status_callback=update_status)

        if transcript_path:
            status_message = "✅ Transcription complete."
            return send_file(transcript_path, as_attachment=True)

        status_message = "❌ No valid input provided."
        return "No valid input", 400
    except Exception as e:
        status_message = f"❌ Error: {str(e)}"
        return str(e), 500

@app.route('/status')
def status():
    return jsonify({"status": status_message})

def update_status(msg):
    global status_message
    status_message = msg

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)


