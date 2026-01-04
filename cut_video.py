import json
import sys
import subprocess
from pathlib import Path

"""
Cuts video clips based on timestamped highlights.

Args:
    video_path: original video
    highlights_path: JSON with [{"start","end","text"}]
    output_dir: folder to save clips
    padding_seconds: seconds added before/after each clip
"""

def cut_video(
        video_path: Path,
        highlights_path: Path,
        output_dir: Path,
        padding_seconds: float = 1.0
):
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    if not highlights_path.exists():
        raise FileNotFoundError(f"Highlights not found: {highlights_path}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(highlights_path, "r", encoding="uft-8") as file:
        highlights = json.load(file)

    if not highlights:
        print("No highlights found")

        return

    #Creating a clip for each highligh
    #All clips must be chronologically ordered
    for i, h in enumerate(highlights, start=1):
        start = max(0, h["start"] - padding_seconds)
        end = h["end"] + padding_seconds
        duration = end - start

        output_file = output_dir / f"clip_{i:02d}.mp4"

        ffmpeg_command = [
            "ffmpeg",           # Executable binary
            "-y",               # Overwrite output
            "-ss", str(start),  # Start offset
            "-i", str(video_path), # Input source
            "-t", str(duration),# Duration limit
            "-c", "copy",       # Stream copy
            str(output_file)    # Output destination
        ]

        print(f"Cutting clip {i}: {start:.2f}s → {end:.2f}s")

        try:
            subprocess.run(
                ffmpeg_command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            print(f"Failed to cut the clit {i}")

    print("All clips created.")

def main():
    if len(sys.argv) < 3:
        print("Usage: python cut_video.py <video_path> <highlights.json>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    highlights_path = Path(sys.argv[2])

    output_dir = Path("data/clips")

    cut_video(video_path, highlights_path, output_dir)

if __name__ == "__main__":
    main()