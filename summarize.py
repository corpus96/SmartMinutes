import re
import json
from collections import Counter
from pathlib import Path
from typing import List, Dict, Optional, Set

def _load_greeting_patterns(config_dir: Path) -> List[str]:
    """Load greeting patterns from config file or return defaults."""
    greeting_patterns_file = config_dir / "greeting_patterns.json"
    try:
        with open(greeting_patterns_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [
            r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b',
            r'\b(thank you|thanks|thank)\b.*\b(coming|for coming)\b',
            r'\b(let\'?s|let us)\s+(get started|begin|start)\b',
            r'\b(welcome|welcomed)\b',
            r'^(hello|hi|hey|thanks|thank you)',
        ]

def _load_problem_keywords(config_dir: Path) -> List[str]:
    """Load problem keywords from config file."""
    problem_keywords_file = config_dir / "problem_keywords.json"
    with open(problem_keywords_file, "r", encoding="utf-8") as f:
        return json.load(f)

def _is_greeting(text: str, greeting_patterns: List[str]) -> bool:
    """Check if text matches any greeting pattern."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in greeting_patterns)

def _score_segments(segments: List[Dict]) -> List[Dict]:
    """Score segments based on word frequency."""
    full_text = " ".join(s["text"] for s in segments)
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
    
    return scored_segments

def _find_segment_index(segments: List[Dict], target_seg: Dict) -> Optional[int]:
    """Find the index of a segment in the original list."""
    for i, seg in enumerate(segments):
        if (abs(seg["start"] - target_seg["start"]) < 0.1 and 
            abs(seg["end"] - target_seg["end"]) < 0.1 and
            seg["text"] == target_seg["text"]):
            return i
    return None

def _expand_with_context(
    segments: List[Dict],
    top_segments: List[Dict],
    context_segments: int,
    used_indices: Set[int]
) -> List[Dict]:
    """Expand selected segments with surrounding context."""
    expanded_highlights = []
    
    for top_seg in top_segments:
        seg_index = _find_segment_index(segments, top_seg)
        if seg_index is None:
            continue
        
        start_idx = max(0, seg_index - context_segments)
        end_idx = min(len(segments) - 1, seg_index + context_segments)
        
        context_segs = []
        for idx in range(start_idx, end_idx + 1):
            if idx not in used_indices:
                context_segs.append(segments[idx])
                used_indices.add(idx)
        
        if context_segs:
            merged_start = min(s["start"] for s in context_segs)
            merged_end = max(s["end"] for s in context_segs)
            merged_text = " ".join(s["text"] for s in context_segs)
            
            expanded_highlights.append({
                "start": merged_start,
                "end": merged_end,
                "text": merged_text
            })
    
    return expanded_highlights

def _merge_overlapping(highlights: List[Dict]) -> List[Dict]:
    """Merge overlapping highlights."""
    final_highlights = []
    for h in highlights:
        if final_highlights and h["start"] < final_highlights[-1]["end"]:
            final_highlights[-1]["end"] = max(final_highlights[-1]["end"], h["end"])
            final_highlights[-1]["text"] += " " + h["text"]
        else:
            final_highlights.append(h)
    return final_highlights

def _find_non_greeting_segment(
    segments: List[Dict],
    greeting_patterns: List[str],
    max_time: float,
    min_length: int
) -> Optional[Dict]:
    """Find first non-greeting segment within time window."""
    for seg in segments:
        if seg["end"] > max_time:
            break
        if not _is_greeting(seg["text"], greeting_patterns) and len(seg["text"].strip()) > min_length:
            return seg
    return None

def _find_problem_keyword_segment(
    segments: List[Dict],
    problem_keywords: List[str],
    max_time: float
) -> Optional[Dict]:
    """Find first segment containing problem keywords."""
    for seg in segments:
        if seg["end"] > max_time:
            break
        text_lower = seg["text"].lower()
        if any(keyword in text_lower for keyword in problem_keywords):
            return seg
    return None

def _find_opening_segment(
    segments: List[Dict],
    greeting_patterns: List[str],
    problem_keywords: List[str],
    opening_seconds: float
) -> Optional[Dict]:
    """Find the first substantive opening segment."""
    # First pass: look for non-greeting segments in opening window
    seg = _find_non_greeting_segment(segments, greeting_patterns, opening_seconds, 20)
    if seg:
        return seg
    
    # Second pass: extend search window
    seg = _find_non_greeting_segment(segments, greeting_patterns, opening_seconds * 2, 15)
    if seg:
        return seg
    
    # Third pass: look for segments with problem keywords
    return _find_problem_keyword_segment(segments, problem_keywords, opening_seconds * 2)

def _add_opening_highlight(
    segments: List[Dict],
    final_highlights: List[Dict],
    opening_seg: Dict,
    greeting_patterns: List[str]
) -> None:
    """Add opening segment to highlights if not already covered."""
    opening_covered = any(
        abs(h["start"] - opening_seg["start"]) < 2.0 
        for h in final_highlights
    )
    
    if opening_covered:
        return
    
    opening_idx = _find_segment_index(segments, opening_seg)
    if opening_idx is None:
        return
    
    start_idx = max(0, opening_idx - 1)
    context_segs = []
    
    for idx in range(start_idx, min(len(segments), opening_idx + 2)):
        seg = segments[idx]
        if idx == opening_idx:
            context_segs.append(seg)
        else:
            if not _is_greeting(seg["text"], greeting_patterns) or idx < opening_idx:
                context_segs.append(seg)
    
    if context_segs:
        opening_start = min(s["start"] for s in context_segs)
        opening_end = max(s["end"] for s in context_segs)
        opening_text = " ".join(s["text"] for s in context_segs)
        
        final_highlights.insert(0, {
            "start": opening_start,
            "end": opening_end,
            "text": opening_text
        })
        final_highlights.sort(key=lambda x: x["start"])

def summarize_segments(
        segments: List[Dict],
        max_highlights: int=5,
        context_segments: int=1,
        include_opening: bool=True,
        opening_seconds: float=15.0

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
    
    # Score and select top segments
    scored_segments = _score_segments(segments)
    top_segments = sorted(
        scored_segments,
        key=lambda x: x["score"],
        reverse=True
    )[:max_highlights]

    # Expand selected segments with context
    used_indices: Set[int] = set()
    expanded_highlights = _expand_with_context(
        segments, top_segments, context_segments, used_indices
    )

    # Sort by time and merge overlapping segments
    expanded_highlights.sort(key=lambda x: x["start"])
    final_highlights = _merge_overlapping(expanded_highlights)

    # Ensure opening context is included
    if include_opening and segments:
        config_dir = Path(__file__).parent / "config"
        greeting_patterns = _load_greeting_patterns(config_dir)
        problem_keywords = _load_problem_keywords(config_dir)
        
        opening_seg = _find_opening_segment(
            segments, greeting_patterns, problem_keywords, opening_seconds
        )
        
        if opening_seg:
            _add_opening_highlight(
                segments, final_highlights, opening_seg, greeting_patterns
            )

    return final_highlights