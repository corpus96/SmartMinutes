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
    
    # Re-encode during merge to ensure consistent codecs and sync
    ffmpeg_command = [
        "ffmpeg",            # Executable binary
        "-y",                # Overwrite output
        "-f", "concat",      # Format: concat
        "-safe", "0",        # Allow unsafe paths
        "-i", str(concat_file), # Text file list
        "-c:v", "libx264",   # Re-encode video for consistency
        "-c:a", "aac",       # Re-encode audio for consistency
        "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
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

    # Use input seeking (-ss before -i) for speed, but re-encode for sync
    # This ensures audio/video stay in sync
    ffmpeg_command = [
        "ffmpeg",           # Executable binary
        "-y",               # Overwrite output
        "-ss", str(start),  # Start offset (before input for faster seeking)
        "-i", str(video_path), # Input source
        "-t", str(duration),# Duration limit
        "-c:v", "libx264",  # Re-encode video for sync
        "-c:a", "aac",      # Re-encode audio for sync
        "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
        "-strict", "experimental",
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

def _merge_overlapping_highlights(highlights: list, padding_seconds: float) -> list:
    """Merge highlights that would overlap after padding is applied."""
    if not highlights:
        return []
    
    # Sort by start time
    sorted_highlights = sorted(highlights, key=lambda x: x["start"])
    merged = []
    
    for h in sorted_highlights:
        if not merged:
            merged.append(h.copy())
            continue
        
        # Calculate padded boundaries
        current_start = max(0, h["start"] - padding_seconds)
        last_end = merged[-1]["end"] + padding_seconds
        
        # Check if this highlight overlaps or is adjacent to the last one
        if current_start <= last_end:
            # Merge: extend the end time and combine text
            merged[-1]["end"] = max(merged[-1]["end"], h["end"])
            merged[-1]["text"] += " " + h["text"]
        else:
            # No overlap, add as new highlight
            merged.append(h.copy())
    
    return merged

def cut_video(
        video_path: Path,
        highlights_path: Path,
        output_dir: Path,
        padding_seconds: float = 2.0,
        auto_merge: bool = True,
        output_video_name: Path = None
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

    # Merge overlapping/adjacent highlights before cutting
    # This prevents duplicate content and sync issues
    merged_highlights = _merge_overlapping_highlights(highlights, padding_seconds)
    
    if len(merged_highlights) < len(highlights):
        print(f"Merged {len(highlights)} highlights into {len(merged_highlights)} non-overlapping segments")

    # Creating a clip for each merged highlight
    # All clips must be chronologically ordered
    for i, h in enumerate(merged_highlights, start=1):
        _cut_single_clip(video_path, h, i, output_dir, padding_seconds)

    print("All clips created.")
    
    # Automatically merge all clips into a single video if requested
    # If auto merge is off, all clips are stored in the directory.
    if auto_merge:
        # Generate output video name from original video name if not provided
        if output_video_name is None:
            original_name = video_path.stem  # Get filename without extension
            output_video_name = output_dir.parent / f"summarize_{original_name}.mp4"
        else:
            output_video_name = Path(output_video_name)
        
        merge_clips(output_dir, output_video_name)
        _cleanup_clips(output_dir)
    else:
        print("Auto-merge is off, keeping individual clips...")
        _delete_concat_file(output_dir)
        