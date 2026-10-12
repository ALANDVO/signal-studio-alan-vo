from app.services.reasoning_filter import (
    extract_reasoning_blocks,
    strip_reasoning_tags,
    compile_prompt_messages,
    estimate_tokens,
)


def test_extract_think_tags_separates_thoughts():
    raw_response = "<think>Calculating steps:\nStep 1: check inputs\nStep 2: finalize</think>The final output is ready."
    clean, thoughts = extract_reasoning_blocks(raw_response)

    assert clean == "The final output is ready."
    assert len(thoughts) == 1
    assert "Calculating steps:" in thoughts[0]


def test_extract_alt_thought_blocks():
    raw_response = "```thought\nInternal deliberation\n```Solution."
    clean, thoughts = extract_reasoning_blocks(raw_response)
    assert clean == "Solution."
    assert len(thoughts) == 1
    assert "Internal deliberation" in thoughts[0]


def test_strip_reasoning_tags_returns_clean_text():
    raw = "<think>Some thought</think>Direct answer."
    clean = strip_reasoning_tags(raw)
    assert clean == "Direct answer."


def test_compile_prompt_without_reasoning_reinjection_issue_23339():
    # Resolves issue #23339: prevents <think> imitation by filtering out thoughts in history
    history = [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "<think>France capital is Paris.</think>The capital is Paris."},
        {"role": "user", "content": "What is its population?"},
    ]

    compiled, pruned_count, total_tokens = compile_prompt_messages(history, reinject_reasoning=False)
    assert pruned_count == 1
    assert len(compiled) == 3
    # Check that assistant content does NOT contain <think>
    assert "<think>" not in compiled[1]["content"]
    assert compiled[1]["content"] == "The capital is Paris."
    assert total_tokens > 0


def test_compile_prompt_with_reasoning_reinject_enabled():
    history = [
        {"role": "user", "content": "Query"},
        {"role": "assistant", "content": "<think>Preserve me</think>Answer"},
    ]
    compiled, pruned_count, _ = compile_prompt_messages(history, reinject_reasoning=True)
    assert pruned_count == 0
    assert "<think>Preserve me</think>" in compiled[1]["content"]


def test_estimate_tokens():
    assert estimate_tokens("hello world") >= 2
    assert estimate_tokens("") == 0
