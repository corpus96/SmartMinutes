import subprocess

from pathlib import Path

"""
Extracts audio from a video file using ffmpeg.

Args:
    video_path (Path): Path to input video
    output_audio_path (Path): Path to output .wav file
"""

def extract_audio(video_path: Path, output_audio_path: Path):
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y", #Overwrite output
        "-i", str(video_path), #input video
        "-vn", #strip audio from video
        "-acodec", "pcm_s161e", #wav format
        "-ar", "1", #mono
        str(output_audio_path)
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        raise RuntimeError("ffmpeg failed to extract audio")