# pipeline.py
import os
import requests
import subprocess
import assemblyai as aai
from yt_dlp import YoutubeDL
import shutil

aai.settings.api_key = "a67553f9853843d3b418834ceca47587"

def find_ffmpeg():
    """Find ffmpeg executable in the system PATH"""
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg not found! Please install ffmpeg:\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Ubuntu/Debian: sudo apt-get install ffmpeg\n"
            "  - Windows: Download from https://ffmpeg.org/download.html"
        )
    return ffmpeg_path

def convert_to_mp3(input_path):
    """Convert any audio/video file to MP3 format"""
    output_path = os.path.splitext(input_path)[0] + ".mp3"
    
    # Check if file is already MP3
    if input_path.lower().endswith('.mp3'):
        return input_path
    
    try:
        ffmpeg_path = find_ffmpeg()
        # Convert to MP3 using ffmpeg
        subprocess.run([
            ffmpeg_path,
            "-i", input_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-ab", "192k",  # Bitrate
            "-ar", "44100",  # Sample rate
            output_path
        ], check=True, capture_output=True, text=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error converting file to MP3: {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"Error during conversion: {str(e)}")

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

def run_transcription(local_file=None, status_callback=print):
    if not local_file:
        raise ValueError("No file provided for transcription.")

    try:
        status_callback("📁 Processing file...")
        file_path = convert_to_mp3(local_file)
        
        status_callback("⬆️ Uploading to AssemblyAI...")
        audio_url = upload_to_assemblyai(file_path)

        status_callback("🧠 Transcribing...")
        text = transcribe_audio(audio_url)

        if not text:
            raise ValueError("Transcription failed or returned empty result.")

        # Construct the review-ready output
        review_prompt = """You are an expert AI assistant helping prepare AI-transcribed audio for human review before downstream use.
Your task is to return the transcript exactly as-is, with only clear transcription-related issues visibly flagged — such as misspellings, grammar errors, incorrect speaker labels, or garbled segments caused by speech-to-text errors. Do not flag factual errors or questionable claims — fact-checking will happen later.
✅ You must preserve every single word of the transcript, including filler words, hesitations, or repeated phrases.
 🚫 Never abridge or replace any part of the transcript with ellipses (...) or summaries. The output must reflect the full, verbatim transcript without omission.
What to Flag:
Only flag issues that are clearly transcription errors, such as:
Incorrect words (e.g., homophones, slurred recognitions)


Garbled or broken phrases


Missing or incorrect punctuation that affects clarity


Speaker label errors or changes mid-section


Obvious formatting glitches (e.g., line breaks, word splitting)


⚠️ Do not flag:
Repetitions (e.g., "the the") unless they create confusion


Minor capitalization issues unless they impede comprehension


Natural disfluencies that match normal spoken language


How to Flag:
Use bold → for transcription errors (e.g., mis-capitalized words, grammar issues, broken phrases)


Use 🟡 → immediately after each bolded error or [bracketed note]


Use [BRACKETED NOTES] for short clarifying tags (e.g., [should be "Super Bowl"], [possible speaker change])


Ensure bracketed notes are bolded


✅ Example: **the the** 🟡 **[repetition]**
 ✅ Example: **[POSSIBLE SPEAKER LABEL ERROR]** 🟡

Key:
 bold = transcription error
 🟡 = needs human review
 [note] = clarification

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
        
    except Exception as e:
        status_callback(f"❌ Error: {str(e)}")
        raise
