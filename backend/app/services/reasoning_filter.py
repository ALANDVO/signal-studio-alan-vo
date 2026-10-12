import re
from typing import List, Dict, Any, Tuple


THINK_REGEX = re.compile(r"<think>(.*?)</think>", flags=re.DOTALL | re.IGNORECASE)
ALT_THOUGHT_REGEX = re.compile(r"```thought\s*(.*?)\s*```", flags=re.DOTALL | re.IGNORECASE)


def extract_reasoning_blocks(raw_text: str) -> Tuple[str, List[str]]:
    if not raw_text:
        return "", []

    thoughts: List[str] = []
    
    # Extract <think>...</think>
    for match in THINK_REGEX.finditer(raw_text):
        content = match.group(1).strip()
        if content:
            thoughts.append(content)

    clean_text = THINK_REGEX.sub("\n\n", raw_text)

    # Extract ```thought ... ```
    for match in ALT_THOUGHT_REGEX.finditer(clean_text):
        content = match.group(1).strip()
        if content:
            thoughts.append(content)

    clean_text = ALT_THOUGHT_REGEX.sub("\n\n", clean_text)
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

    return clean_text, thoughts


def strip_reasoning_tags(content: str) -> str:
    clean, _ = extract_reasoning_blocks(content)
    return clean


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # Deterministic standard estimation: 1 token ~= 4 characters or whitespace tokens
    words = len(text.split())
    char_estimate = len(text) // 4
    return max(words, char_estimate)


def compile_prompt_messages(
    messages: List[Dict[str, Any]],
    reinject_reasoning: bool = False,
    max_context_messages: int = 50,
) -> Tuple[List[Dict[str, Any]], int, int]:
    pruned_count = 0
    compiled: List[Dict[str, Any]] = []

    # Slice to max context messages
    target_messages = messages[-max_context_messages:] if len(messages) > max_context_messages else messages

    for msg in target_messages:
        role = msg.get("role", "user")
        raw_content = msg.get("content", "")
        stored_reasoning = msg.get("reasoning")

        if role == "assistant" and not reinject_reasoning:
            clean_content, extracted_thoughts = extract_reasoning_blocks(raw_content)
            if extracted_thoughts or (stored_reasoning and stored_reasoning.strip()):
                pruned_count += 1
            final_content = clean_content if clean_content else "I have analyzed your request."
        else:
            final_content = raw_content

        compiled.append({
            "role": role,
            "content": final_content,
        })

    total_tokens = sum(estimate_tokens(m.get("content", "")) for m in compiled)
    return compiled, pruned_count, total_tokens
