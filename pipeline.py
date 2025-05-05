# pipeline.py
import os
import requests
import subprocess
import assemblyai as aai
from yt_dlp import YoutubeDL

aai.settings.api_key = "a67553f9853843d3b418834ceca47587"


def download_youtube_audio(youtube_url):
    output_dir = "uploads"
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    expected_mp3 = os.path.join(output_dir, "audio.mp3")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'ffmpeg_location': '/usr/local/opt/ffmpeg/bin/ffmpeg',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    # Find the resulting mp3 file
    for filename in os.listdir(output_dir):
        if filename.endswith(".mp3"):
            return os.path.join(output_dir, filename)

    raise FileNotFoundError("Audio download failed — no .mp3 file found in uploads directory")


def convert_mp4_to_mp3(input_path):
    output_path = os.path.splitext(input_path)[0] + ".mp3"
    subprocess.run([
        "/usr/local/opt/ffmpeg/bin/ffmpeg",
        "-i", input_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        output_path
    ], check=True)
    return output_path


def upload_to_assemblyai(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": aai.settings.api_key},
            files={"file": f}
        )
    response.raise_for_status()
    return response.json()["upload_url"]


def transcribe_audio(audio_url):
    config = aai.TranscriptionConfig(speaker_labels=True, disfluencies=False)
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_url, config)

    if transcript.utterances:
        return "\n\n".join(f"Speaker {utt.speaker}: {utt.text}" for utt in transcript.utterances)
    elif transcript.text:
        return transcript.text
    else:
        print("❌ No transcript text found — check if the audio is valid.")
        return None


def run_transcription(youtube_url=None, local_file=None, status_callback=print):
    if youtube_url:
        status_callback("🎧 Downloading from YouTube...")
        file_path = download_youtube_audio(youtube_url)
    elif local_file:
        status_callback("📁 Using uploaded file...")
        ext = os.path.splitext(local_file)[1].lower()
        if ext == ".mp4":
            status_callback("🎞 Converting MP4 to MP3...")
            file_path = convert_mp4_to_mp3(local_file)
        else:
            file_path = local_file
    else:
        raise ValueError("No source provided for transcription.")

    status_callback("⬆️ Uploading to AssemblyAI...")
    audio_url = upload_to_assemblyai(file_path)

    status_callback("🧠 Transcribing...")
    text = transcribe_audio(audio_url)

    if not text:
        raise ValueError("Transcription failed or returned empty result.")

    # Construct the review-ready output
    review_prompt = """You are an expert AI assistant helping prepare transcripts for human review before downstream use.

Your task is to return the transcript **exactly as-is**, but with only **transcription-related issues** visibly flagged — such as misspellings, repetitions, grammar errors, or garbled segments caused by speech-to-text systems. Do not correct or flag any factual errors or questionable claims — fact-checking will happen later.

Instructions:
- Do not rewrite, paraphrase, or summarize any part of the transcript.
- Keep all speaker labels, dialogue order, and punctuation untouched.
- Highlight only likely **transcription mistakes**, using:
    - **Bold** → for mis-capitalized words, stutters, or broken grammar
    - 🟡 emoji → placed just after each bolded word/phrase to draw human attention
- Only include very short clarifying comments if the error is especially unclear.
- Do not mark content unless you're reasonably confident it’s a transcription error.

Example:
- “wall street” → **Wall street** 🟡
- “and, and” → **and, and** 🟡
- “Upper west side” → **Upper west side** 🟡

Transcript:
---
"""

    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", "review-ready-transcript.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(review_prompt)
        f.write(text.strip())
        f.write("\n---")

    status_callback("✅ Transcription saved with GPT review prompt.")
    status_callback("\n👉 Open the downloaded `review-ready-transcript.txt`, copy everything inside, and paste it into a **new ChatGPT thread** for the cleanest and most accurate analysis.\n")

    return output_path
