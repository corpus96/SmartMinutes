import re
import json
from collections import Counter
from pathlib import Path
from typing import List, Dict

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

    # Pick top segments
    top_segments = sorted(
        scored_segments,
        key=lambda x: x["score"],
        reverse=True
    )[:max_highlights]

    # Expand selected segments with context
    expanded_highlights = []
    used_indices = set()
    
    for top_seg in top_segments:
        # Find the index of this segment in the original list
        seg_index = None
        for i, seg in enumerate(segments):
            if (abs(seg["start"] - top_seg["start"]) < 0.1 and 
                abs(seg["end"] - top_seg["end"]) < 0.1 and
                seg["text"] == top_seg["text"]):
                seg_index = i
                break
        
        if seg_index is None:
            continue
        
        # Include context: previous and next segments
        start_idx = max(0, seg_index - context_segments)
        end_idx = min(len(segments) - 1, seg_index + context_segments)
        
        # Collect all segments in the context window
        context_segs = []
        for idx in range(start_idx, end_idx + 1):
            if idx not in used_indices:
                context_segs.append(segments[idx])
                used_indices.add(idx)
        
        if context_segs:
            # Merge context segments into one highlight
            merged_start = min(s["start"] for s in context_segs)
            merged_end = max(s["end"] for s in context_segs)
            merged_text = " ".join(s["text"] for s in context_segs)
            
            expanded_highlights.append({
                "start": merged_start,
                "end": merged_end,
                "text": merged_text
            })

    # Sort by time (easier for ffmpeg)
    expanded_highlights.sort(key=lambda x: x["start"])
    
    # Remove duplicates and merge overlapping segments
    final_highlights = []
    for h in expanded_highlights:
        # Check if this highlight overlaps with the previous one
        if final_highlights and h["start"] < final_highlights[-1]["end"]:
            # Merge with previous highlight
            final_highlights[-1]["end"] = max(final_highlights[-1]["end"], h["end"])
            final_highlights[-1]["text"] += " " + h["text"]
        else:
            final_highlights.append(h)

    # Ensure opening context is included
    # Sometimes model give segment of solution but not initial problem.
    if include_opening and segments:
        # Load greeting patterns from config file
        config_dir = Path(__file__).parent / "config"
        greeting_patterns_file = config_dir / "greeting_patterns.json"
        
        try:
            with open(greeting_patterns_file, "r", encoding="utf-8") as f:
                greeting_patterns = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback to default patterns if file not found
            greeting_patterns = [
                r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b',
                r'\b(thank you|thanks|thank)\b.*\b(coming|for coming)\b',
                r'\b(let\'?s|let us)\s+(get started|begin|start)\b',
                r'\b(welcome|welcomed)\b',
                r'^(hello|hi|hey|thanks|thank you)',
            ]
        
        # Find the first substantive segment (skipping greetings)
        opening_seg = None
        for seg in segments:
            if seg["end"] > opening_seconds:
                break
            
            text_lower = seg["text"].lower()
            # Check if this segment is mostly greetings
            is_greeting = False
            for pattern in greeting_patterns:
                if re.search(pattern, text_lower):
                    is_greeting = True
                    break
            
            # If not a greeting and has some content, use it
            if not is_greeting and len(seg["text"].strip()) > 20:
                opening_seg = seg
                break
        
        # If no good opening found, use first non-greeting segment
        if opening_seg is None:
            for seg in segments:
                if seg["end"] > opening_seconds * 2:  # Extend search window
                    break
                text_lower = seg["text"].lower()
                is_greeting = any(re.search(p, text_lower) for p in greeting_patterns)
                if not is_greeting and len(seg["text"].strip()) > 15:
                    opening_seg = seg
                    break
        
        # If still no good segment, use first segment that mentions problem keywords
        if opening_seg is None:
            # Load problem keywords from config file
            problem_keywords_file = config_dir / "problem_keywords.json"
            
            try:
                with open(problem_keywords_file, "r", encoding="utf-8") as f:
                    problem_keywords = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                raise FileNotFoundError(f"Problem keywords file not found or invalid: {problem_keywords_file}") from e
            for seg in segments:
                if seg["end"] > opening_seconds * 2:
                    break
                text_lower = seg["text"].lower()
                if any(keyword in text_lower for keyword in problem_keywords):
                    opening_seg = seg
                    break
        
        # If we found a good opening segment, include it with context
        if opening_seg:
            # Check if opening is already covered
            opening_covered = False
            for h in final_highlights:
                if abs(h["start"] - opening_seg["start"]) < 2.0:
                    opening_covered = True
                    break
            
            # If opening not covered, add it with some context
            if not opening_covered:
                # Find index of opening segment
                opening_idx = None
                for i, seg in enumerate(segments):
                    if abs(seg["start"] - opening_seg["start"]) < 0.1:
                        opening_idx = i
                        break
                
                if opening_idx is not None:
                    # Include 1-2 segments before for context (but skip if they're greetings)
                    start_idx = max(0, opening_idx - 1)
                    context_segs = []
                    
                    # Add context segments (skip pure greetings)
                    for idx in range(start_idx, min(len(segments), opening_idx + 2)):
                        seg = segments[idx]
                        if idx == opening_idx:
                            context_segs.append(seg)
                        else:
                            text_lower = seg["text"].lower()
                            is_greeting = any(re.search(p, text_lower) for p in greeting_patterns)
                            if not is_greeting or idx < opening_idx:  # Include before even if greeting
                                context_segs.append(seg)
                    
                    if context_segs:
                        opening_start = min(s["start"] for s in context_segs)
                        opening_end = max(s["end"] for s in context_segs)
                        opening_text = " ".join(s["text"] for s in context_segs)
                        
                        # Insert at pos 0 (beginning)
                        final_highlights.insert(0, {
                            "start": opening_start,
                            "end": opening_end,
                            "text": opening_text
                        })
                        
                        # Re-sort after insertion
                        final_highlights.sort(key=lambda x: x["start"])

    return final_highlights