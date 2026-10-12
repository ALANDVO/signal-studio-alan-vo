import math
import re
from typing import List, Dict, Any


def estimate_word_tokens(text: str) -> int:
    return len(text.split())


def chunk_fast_text(text: str, max_words: int = 250) -> List[Dict[str, Any]]:
    paragraphs = text.split("\n\n")
    chunks: List[Dict[str, Any]] = []
    current_chunk: List[str] = []
    current_count = 0
    chunk_index = 0

    for p in paragraphs:
        cleaned = p.strip()
        if not cleaned:
            continue
        words = cleaned.split()
        p_len = len(words)

        if current_count + p_len > max_words and current_chunk:
            combined = "\n\n".join(current_chunk)
            chunks.append({
                "chunk_index": chunk_index,
                "text": combined,
                "token_count": estimate_word_tokens(combined),
                "heading": None,
                "metadata": {"strategy": "fast_text", "paragraph_count": len(current_chunk)},
            })
            chunk_index += 1
            current_chunk = [cleaned]
            current_count = p_len
        else:
            current_chunk.append(cleaned)
            current_count += p_len

    if current_chunk:
        combined = "\n\n".join(current_chunk)
        chunks.append({
            "chunk_index": chunk_index,
            "text": combined,
            "token_count": estimate_word_tokens(combined),
            "heading": None,
            "metadata": {"strategy": "fast_text", "paragraph_count": len(current_chunk)},
        })

    return chunks


def chunk_structured_markdown(text: str, max_words: int = 350) -> List[Dict[str, Any]]:
    lines = text.split("\n")
    chunks: List[Dict[str, Any]] = []
    current_heading = "General"
    current_lines: List[str] = []
    chunk_index = 0

    heading_regex = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        match = heading_regex.match(line.strip())
        if match:
            # When hitting a new heading, if we already have lines, flush them
            if current_lines:
                combined = "\n".join(current_lines).strip()
                if combined:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "text": combined,
                        "token_count": estimate_word_tokens(combined),
                        "heading": current_heading,
                        "metadata": {"strategy": "structured_markdown", "heading": current_heading},
                    })
                    chunk_index += 1
                current_lines = []
            current_heading = match.group(2).strip()
            current_lines.append(line)
        else:
            current_lines.append(line)
            # If section exceeds word limit, break chunk while preserving heading context
            if estimate_word_tokens("\n".join(current_lines)) > max_words:
                combined = "\n".join(current_lines).strip()
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": combined,
                    "token_count": estimate_word_tokens(combined),
                    "heading": current_heading,
                    "metadata": {"strategy": "structured_markdown", "heading": current_heading},
                })
                chunk_index += 1
                current_lines = []

    if current_lines:
        combined = "\n".join(current_lines).strip()
        if combined:
            chunks.append({
                "chunk_index": chunk_index,
                "text": combined,
                "token_count": estimate_word_tokens(combined),
                "heading": current_heading,
                "metadata": {"strategy": "structured_markdown", "heading": current_heading},
            })

    return chunks


def chunk_semantic_sliding(text: str, window_words: int = 200, overlap_words: int = 40) -> List[Dict[str, Any]]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    accumulated_sentences: List[str] = []
    current_words = 0

    for sentence in sentences:
        s_clean = sentence.strip()
        if not s_clean:
            continue
        s_words = len(s_clean.split())
        accumulated_sentences.append(s_clean)
        current_words += s_words

        if current_words >= window_words:
            combined = " ".join(accumulated_sentences)
            chunks.append({
                "chunk_index": chunk_index,
                "text": combined,
                "token_count": current_words,
                "heading": None,
                "metadata": {"strategy": "semantic_chunks", "overlap_words": overlap_words},
            })
            chunk_index += 1

            # Retain overlap sentences
            overlap_acc: List[str] = []
            overlap_cnt = 0
            for s in reversed(accumulated_sentences):
                s_len = len(s.split())
                if overlap_cnt + s_len <= overlap_words:
                    overlap_acc.insert(0, s)
                    overlap_cnt += s_len
                else:
                    break
            accumulated_sentences = overlap_acc
            current_words = overlap_cnt

    if accumulated_sentences:
        combined = " ".join(accumulated_sentences)
        if combined.strip():
            chunks.append({
                "chunk_index": chunk_index,
                "text": combined,
                "token_count": current_words,
                "heading": None,
                "metadata": {"strategy": "semantic_chunks", "overlap_words": overlap_words},
            })

    return chunks


def extract_content(text: str, strategy: str = "structured_markdown") -> List[Dict[str, Any]]:
    if strategy == "fast_text":
        return chunk_fast_text(text)
    elif strategy == "semantic_chunks":
        return chunk_semantic_sliding(text)
    else:
        return chunk_structured_markdown(text)


def score_bm25_text(query: str, text: str, heading: str = "") -> float:
    query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not query_terms:
        return 0.0

    text_lower = text.lower()
    text_words = re.findall(r"\w+", text_lower)
    total_words = max(len(text_words), 1)

    score = 0.0
    heading_lower = (heading or "").lower()

    for term in query_terms:
        tf = text_words.count(term)
        if tf > 0:
            # Term frequency saturation
            tf_score = (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * (total_words / 200.0)))
            score += tf_score
        if heading_lower and term in heading_lower:
            score += 1.5

    return round(score, 4)


def search_knowledge_chunks(chunks: List[Dict[str, Any]], query: str, limit: int = 5) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for ch in chunks:
        score = score_bm25_text(query, ch.get("text", ""), ch.get("heading", ""))
        if score > 0:
            scored.append({**ch, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
