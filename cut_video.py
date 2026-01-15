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

def merge_clips(clips_dir: Path, output_video: Path):
    """Merges video clips into a single video chronologically."""
    if not clips_dir.exists():
        raise FileNotFoundError(f"Clips directory not found: {clips_dir}")
    
    clips = sorted(clips_dir.glob("clip_*.mp4"))
    
    if not clips:
        raise RuntimeError("No clips found to merge.")
    
    concat_file = clips_dir / "concat.txt"
    
    with open(concat_file, "w", encoding="utf-8") as file:
        for clip in clips:
            file.write(f"file '{clip.resolve()}'\n")  # Each line needs newline
    
    output_video.parent.mkdir(parents=True, exist_ok=True)
    
    ffmpeg_command = [
        "ffmpeg",            # Executable binary
        "-y",                # Overwrite output
        "-f", "concat",      # Format: concat demuxer
        "-safe", "0",        # Allow unsafe paths
        "-i", str(concat_file), # Text file list
        "-c", "copy",        # Stream copy
        str(output_video)    # Output destination
    ]
    
    print("Merging clips into a single summarized video...")
    
    try:
        subprocess.run(
            ffmpeg_command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"Summarized video created: {output_video}")
    except subprocess.CalledProcessError:
        raise RuntimeError("ffmpeg failed to merge the clips")

def _cut_single_clip(
        video_path: Path,
        highlight: dict,
        clip_number: int,
        output_dir: Path,
        padding_seconds: float
) -> None:
    """Cuts a single clip from the video based on highlight timestamps."""
    start = max(0, highlight["start"] - padding_seconds)
    end = highlight["end"] + padding_seconds
    duration = end - start

    output_file = output_dir / f"clip_{clip_number:02d}.mp4"

    ffmpeg_command = [
        "ffmpeg",           # Executable binary
        "-y",               # Overwrite output
        "-ss", str(start),  # Start offset
        "-i", str(video_path), # Input source
        "-t", str(duration),# Duration limit
        "-c", "copy",       # Stream copy
        str(output_file)    # Output destination
    ]

    print(f"Cutting clip {clip_number}: {start:.2f}s → {end:.2f}s")

    try:
        subprocess.run(
            ffmpeg_command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to cut clip {clip_number}: {e}")

def _delete_concat_file(output_dir: Path) -> None:
    """Deletes the concat.txt file used for merging."""
    concat_file = output_dir / "concat.txt"
    if concat_file.exists():
        try:
            concat_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to delete concat.txt: {e}")

def _cleanup_clips(output_dir: Path) -> None:
    """Deletes individual clips and concat file after merging."""
    print("Auto-merge is on, cleaning up individual clips...")
    clips = sorted(output_dir.glob("clip_*.mp4"))
    for clip in clips:
        try:
            clip.unlink()
        except Exception as e:
            print(f"Warning: Failed to delete {clip.name}: {e}")
    
    _delete_concat_file(output_dir)

def cut_video(
        video_path: Path,
        highlights_path: Path,
        output_dir: Path,
        padding_seconds: float = 2.0,
        auto_merge: bool = True 
):
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    if not highlights_path.exists():
        raise FileNotFoundError(f"Highlights not found: {highlights_path}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(highlights_path, "r", encoding="utf-8") as file:
        highlights = json.load(file)

    if not highlights:
        print("No highlights found")
        return

    # Creating a clip for each highlight
    # All clips must be chronologically ordered
    for i, h in enumerate(highlights, start=1):
        _cut_single_clip(video_path, h, i, output_dir, padding_seconds)

    print("All clips created.")
    
    # Automatically merge all clips into a single video if requested
    # If auto merge is off, all clips are stored in the directory.
    if auto_merge:
        merge_clips(output_dir, output_dir.parent / "summarized_video.mp4")
        _cleanup_clips(output_dir)
    else:
        print("Auto-merge is off, keeping individual clips...")
        _delete_concat_file(output_dir)
        

def main():
    if len(sys.argv) < 3:
        print("Usage: python cut_video.py <video_path> <highlights.json>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    highlights_path = Path(sys.argv[2])

    output_dir = Path("output/clips")

    cut_video(video_path, highlights_path, output_dir)

if __name__ == "__main__":
    main()