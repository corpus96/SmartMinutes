import subprocess
from pathlib import Path

#Merges the video clips in a single video with ffmpeg help
def merge_clips(clips_dir: Path, output_video: Path):
    if not clips_dir.exists():
        raise FileNotFoundError(f"Clips directory not found: {clips_dir}")
    
    clips = sorted(clips_dir.glob("clip_*.mp4"))

    if not clips:
        raise RuntimeError("No clips found to merge.")
    
    concat_file = clips_dir / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for clip in clips:
            file.write(f"file '{clip.resolve()}'")


    output_video.parent.mkdir(parents=True, exists_ok=True)


    ffmpeg_command = [
        "ffmpeg",            # Executable binary
        "-y",                # Overwrite output
        "-f", "concat",      # Format: concat demuxer
        "-safe", "0",        # Allow unsafe paths
        "-i", str(concat_file), # Text file list
        "-c", "copy",        # Stream copy
        str(output_video)    # Output destination
    ]

    print("Merging clips into a summarized video")

    try:
        subprocess.run(
            ffmpeg_command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        raise RuntimeError("ffmpeg failed to merge the clips")
    

    print(f"Summarized video created: {output_video}")

def main():
    clips_dir = Path("data/clips")
    output_video = Path("data/summarized_video.mp4")

    merge_clips(clips_dir, output_video)


if __name__ == "__main__":
    main()