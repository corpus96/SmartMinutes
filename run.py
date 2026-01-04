import sys
import json
from pathlib import Path

from video_utils import extract_audio
from transcribe import transcribe_audio
from summarize import summarize_segments

def main():
    if(len(sys.argv) < 2):
        print("Use run.py <path of the video>")

        sys.exit(1)

    video_path = Path(sys.argv[1])

    print(f"Video path is {video_path}")

    if not video_path.exists():
        print("ERROR: INPUT FILE NOT FOUND")
        sys.exit(1)

    data_dir = Path("data")
    audio_dir = data_dir / "audio"
    data_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)

    audio_path = audio_dir / "audio.wav"
    transcript_txt_path = data_dir / "transcript.txt"
    highlights_json_path = data_dir / "highlights.json"
    summary_txt_path = data_dir / "summary.txt"
    

    print("Extracting audio")
    extract_audio(video_path, audio_path)

    print("Transcribing audio")
    segments = transcribe_audio(audio_path)
    # Expected format:
    # [
    #   {"start": float, "end": float, "text": str},
    #   ...
    # ]

    # Save full transcript (TXT)
    full_text = " ".join(s["text"] for s in segments)
    transcript_txt_path.write_text(full_text, encoding="utf-8")

    highlights = summarize_segments(segments)

    with open(highlights_json_path, "w", encoding="utf-8") as f:
        json.dump(highlights, f, ensure_ascii=False, indent=2)

    print("Done!")
    print(f"Transcript: {transcript_txt_path}")
    print(f"Highlights (timestamps): {highlights_json_path}")
    print(f"Summary: {summary_txt_path}")

if __name__ == "__main__":
    main()