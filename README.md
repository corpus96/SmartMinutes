# SmartMinutes

SmartMinutes is a command-line tool that automatically turns a long video into a short, highlight-only summary video. It extracts the audio, transcribes it with speech-to-text, scores the transcript to find the most important moments (plus a meaningful opening), and stitches those moments back together into a single condensed `.mp4`.

## How It Works

The pipeline (`run.py`) runs the following stages in order:

1. **Audio extraction** (`video_utils.py`) — uses `ffmpeg` to pull a 16 kHz mono WAV out of the source video.
2. **Transcription** (`transcribe.py`) — uses [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (model `small`, CPU, `int8`) to produce timestamped transcript segments.
3. **Highlight selection** (`summarize.py`) — scores segments by word frequency, expands the top segments with surrounding context, merges overlaps, and ensures a substantive opening segment is included (skipping greetings).
4. **Clip cutting & merge** (`cut_video.py`) — cuts a clip for each highlight with `ffmpeg`, merges them chronologically into one video, and cleans up the intermediate clips.

## Outputs

All artifacts are written to an `output/` directory (created automatically, and git-ignored):

| File | Description |
|------|-------------|
| `output/audio/audio.wav` | Extracted audio |
| `output/transcripts/transcript.txt` | Full plain-text transcript |
| `output/highlights/highlights.json` | Selected highlight segments with timestamps |
| `output/summarize_<video_name>.mp4` | Final summarized video |

## Prerequisites

- **Python 3.8+**
- **ffmpeg** must be installed and available on your `PATH`. Verify with:

```bash
ffmpeg -version
```

If it is not installed:

- **Windows:** `winget install Gyan.FFmpeg` (or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to `PATH`)
- **macOS:** `brew install ffmpeg`
- **Linux (Debian/Ubuntu):** `sudo apt install ffmpeg`

## Setup

From the project root (`SmartMinutes/`):

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt
```

> The first run downloads the `faster-whisper` `small` model (a few hundred MB), so the initial transcription will take longer than subsequent runs.

## Usage

Run the pipeline by passing the path to your input video:

```bash
python run.py <path-to-video>
```

Example:

```bash
python run.py data/input/this_is_not_a_video.mp4
```

When it finishes, you'll find the summarized video at `output/summarize_<video_name>.mp4`.

## Configuration

Highlight selection can be tuned through two JSON config files in `config/`:

- **`config/greeting_patterns.json`** — regular expressions used to detect and skip greetings/small talk when choosing the opening segment.
- **`config/problem_keywords.json`** — keywords (e.g. `problem`, `risk`, `blocker`) used as a fallback to find a meaningful opening segment.

You can also adjust summarization behavior programmatically via the parameters of `summarize_segments()` in `summarize.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_highlights` | `5` | Number of top-scoring segments to keep |
| `context_segments` | `1` | Segments of context added before/after each highlight |
| `include_opening` | `True` | Whether to always include a meaningful opening segment |
| `opening_seconds` | `15.0` | Time window (seconds) to search for the opening |

Clip-cutting behavior can be tuned via `cut_video()` in `cut_video.py` (e.g. `padding_seconds`, `auto_merge`).

## Project Structure

```
SmartMinutes/
├── run.py                 # Entry point / pipeline orchestrator
├── video_utils.py         # Audio extraction (ffmpeg)
├── transcribe.py          # Speech-to-text (faster-whisper)
├── summarize.py           # Highlight scoring & selection
├── cut_video.py           # Clip cutting + merging (ffmpeg)
├── merge_clips.py         # Standalone clip-merge helper
├── requirements.txt       # Python dependencies
├── config/
│   ├── greeting_patterns.json
│   └── problem_keywords.json
└── data/
    └── input/             # Place your source videos here
```

## Troubleshooting

- **`ffmpeg failed to extract audio` / `ffmpeg failed to merge the clips`** — Ensure `ffmpeg` is installed and on your `PATH`.
- **`ERROR: INPUT FILE NOT FOUND`** — Double-check the video path you passed to `run.py`.
- **Slow first run** — The Whisper model is downloaded on first use; later runs reuse the cached model.
- **Out of memory / too slow** — The model runs on CPU with `int8` quantization by default. For different performance/accuracy trade-offs, change the model size or device in `transcribe.py`.
