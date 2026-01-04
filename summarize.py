import re
from collections import Counter
from typing import List, Dict

def summarize_segments(
        segments: List[Dict],
        max_highlights: int=5

) -> List[Dict]:
    """
    Selects the most important transcript segments and keeps timestamps.

    Input:
        [
          {"start": float, "end": float, "text": str},
          ...
        ]

    Output:
        Same structure, reduced to the most important segments
    """

    if not segments:
        return []
    
    full_text = " ".join["text"]

    words = re.findall(r"\w+", full_text.lower())
    freq = Counter(words)

    scored_segments = []

    for segment in segments:
        segment_words = re.findall(r"\w+", segment["text"].lower())

        if not segment_words:
            continue

        score = sum(freq[w] for w in segment_words) / len(segment_words)

        scored_segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "score": score
        })

    # Pick top segments
    highlights = sorted(
        scored_segments,
        key=lambda x: x["score"],
        reverse=True
    )[:max_highlights]

    #Sort by time (easier for ffmpeg)
    highlights.sort(key=lambda x: x["start"])

    for h in highlights:
        h.pop("score", None)

    return highlights