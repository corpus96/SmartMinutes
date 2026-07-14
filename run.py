import sys
import json
from pathlib import Path

from Step_1_Transcribe_Video.extract_audio import extract_audio
from Step_1_Transcribe_Video.transcribe import transcribe_audio
from summarize import summarize_segments
from cut_video import cut_video

def main():
    if(len(sys.argv) < 2):
        print("Use run.py <path of the video>")

        sys.exit(1)

    video_path = Path(sys.argv[1])

    print(f"Video path is {video_path}")

    if not video_path.exists():
        print("ERROR: INPUT FILE NOT FOUND")
        sys.exit(1)

    output_dir = Path("output")
    audio_dir = output_dir / "audio"
    transcript_dir = output_dir / "transcripts"
    highlights_dir = output_dir / "highlights"
    summary_dir = output_dir / "summaries"
    clips_dir = output_dir / "clips"

    #Creating above directories if they don't exist
    output_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)
    transcript_dir.mkdir(exist_ok=True)
    highlights_dir.mkdir(exist_ok=True)
    summary_dir.mkdir(exist_ok=True)
    clips_dir.mkdir(exist_ok=True)

    audio_path = audio_dir / "audio.wav"
    transcript_txt_path = transcript_dir / "transcript.txt"
    highlights_json_path = highlights_dir / "highlights.json"
    summary_txt_path = summary_dir / "summary.txt"
    
    #Step 1 - Extract Audio
 
    print("Extracting audio")
    extract_audio(video_path, audio_path)

    print("Transcribing audio")
    segments = transcribe_audio(audio_path)

    # Save full transcript (TXT)
    full_text = " ".join(s["text"] for s in segments)
    transcript_txt_path.write_text(full_text, encoding="utf-8")

    print("Creating higlights")
    highlights = summarize_segments(segments)

    with open(highlights_json_path, "w", encoding="utf-8") as f:
        json.dump(highlights, f, ensure_ascii=False, indent=2)

    print("Cutting video based on highlights...")
    cut_video(video_path, highlights_json_path, clips_dir)
    
    # Generate the expected output video path
    original_name = video_path.stem
    output_video_path = output_dir / f"summarize_{original_name}.mp4"

    print("Done!")
    print(f"Transcript: {transcript_txt_path}")
    print(f"Highlights (timestamps): {highlights_json_path}")
    print(f"Summary: {summary_txt_path}")
    print(f"Summarized video: {output_video_path}")

if __name__ == "__main__":
    main()