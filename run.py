import sys
from pathlib import Path

from video_utils import extract_audio
from transcribe import transcribe_audio
from summarize import summarize_text

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
    transcribe_path = data_dir / "transcript.txt"
    summary_path = data_dir / "summary.txt"
    

    print("Extracting audio")
    extract_audio(video_path, audio_path)

    print("Transcribing audio")
    transcript = transcribe_audio(audio_path)
    transcribe_path.write_text(transcript, encoding="utf-8")

    print("Creating summary")
    summary = summarize_text(transcript)
    summary_path.write_text(summary, encoding="utf-8")

    print("Done!")
    print(f"Transcript: {transcribe_path}")
    print(f"Summary: {summary_path}")

if __name__ == "__main__":
    main()