# pipeline.py
import os
import requests
import subprocess
import assemblyai as aai
from yt_dlp import YoutubeDL

aai.settings.api_key = "a67553f9853843d3b418834ceca47587"

def convert_to_mp3(input_path):
    """Convert any audio/video file to MP3 format"""
    output_path = os.path.splitext(input_path)[0] + ".mp3"
    
    # Check if file is already MP3
    if input_path.lower().endswith('.mp3'):
        return input_path
        
    # Convert to MP3 using ffmpeg
    subprocess.run([
        "/usr/local/opt/ffmpeg/bin/ffmpeg",
        "-i", input_path,
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-ab", "192k",  # Bitrate
        "-ar", "44100",  # Sample rate
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

Your task is to return the transcript **exactly as-is**, but with only **transcription-related issues** visibly flagged — such as misspellings, repetitions, mis-capitalizations, grammar issues, incorrect speaker labels, or garbled segments caused by speech-to-text errors. Do **not** flag any factual errors or questionable claims — fact-checking will happen later.

### Flagging Rules:
- Do **not rewrite, paraphrase, or summarize** any part of the transcript.
- **Preserve all speaker labels, timestamps, and dialogue order exactly as written.**
- Flag **only** issues you're reasonably confident are transcription errors.

### How to Flag:
- Use **bold** → for mis-capitalized words, grammar issues, repetitions, or broken syntax.
- Use 🟡 → placed **immediately after** each bolded word/phrase or bracketed note.
- Use **[BRACKETED NOTES]** for short clarifying tags (e.g., **[repetition]**, **[should be "Super Bowl"]**, **[possible speaker change]**).
- Make sure **bracketed notes are bolded as well**:  
  Example: `**the the** 🟡 **[repetition]**`

### Additional Guidelines:
- If a new speaker seems to be mislabeled under an existing speaker, flag with:  
  `**[POSSIBLE SPEAKER LABEL ERROR]** 🟡`
- Only use clarifying notes if they will **speed up** human review — avoid speculative comments.
- Do not flag content unless it is clearly a transcription mistake or speaker labeling issue.

---

Key: **bold** = transcription error · 🟡 = needs review · **[note]** = clarification

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
