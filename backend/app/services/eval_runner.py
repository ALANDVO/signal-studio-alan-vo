import sys
from typing import List, Dict, Any
from app.services.tree_validator import validate_chat_tree, repair_chat_tree
from app.services.reasoning_filter import compile_prompt_messages, extract_reasoning_blocks
from app.services.content_extractor import extract_content, search_knowledge_chunks

BENCHMARK_DATASET = [
    {"id": "eval-tree-01", "category": "tree_integrity", "input": [{"id": "m1", "parent_id": None, "role": "user", "content": "What is RL?"}, {"id": "m2", "parent_id": "non-existent-999", "role": "assistant", "content": "RL is learning via feedback."}], "expected_corrupt": True, "expected_repair_valid": True},
    {"id": "eval-tree-02", "category": "tree_integrity", "input": [{"id": "root", "parent_id": None, "role": "user", "content": "Start"}, {"id": "c1", "parent_id": "c2", "role": "assistant", "content": "Cycle 1"}, {"id": "c2", "parent_id": "c1", "role": "user", "content": "Cycle 2"}], "expected_corrupt": True, "expected_repair_valid": True},
    {"id": "eval-tree-03", "category": "tree_integrity", "input": [{"id": "m1", "parent_id": None, "role": "user", "content": "Hello"}, {"id": "m2", "parent_id": "m1", "role": "assistant", "content": "Hi"}, {"id": "m3", "parent_id": "m2", "role": "user", "content": "Joke"}], "expected_corrupt": False, "expected_repair_valid": True},
    {"id": "eval-tree-04", "category": "tree_integrity", "input": [{"id": "m1", "parent_id": None, "role": "user", "content": "Q1"}, {"id": "m2", "parent_id": "orp-x", "role": "assistant", "content": "A1"}, {"id": "m3", "parent_id": "m2", "role": "user", "content": "F1"}, {"id": "m4", "parent_id": "orp-y", "role": "assistant", "content": "A2"}], "expected_corrupt": True, "expected_repair_valid": True},
    {"id": "eval-tree-05", "category": "tree_integrity", "input": [{"id": "m1", "parent_id": None, "role": "user", "content": "MDP"}, {"id": "m1", "parent_id": None, "role": "user", "content": "Dup"}], "expected_corrupt": True, "expected_repair_valid": True},
    {"id": "eval-reasoning-01", "category": "reasoning_isolation", "input_message": "<think>Analyze step by step.</think>The converted value is 42 km.", "expected_clean": "The converted value is 42 km.", "expected_thought_count": 1},
    {"id": "eval-reasoning-02", "category": "reasoning_isolation", "input_message": "```thought\nFactors: 2, 2, 5, 5.\n```The prime factors are 2 and 5.", "expected_clean": "The prime factors are 2 and 5.", "expected_thought_count": 1},
    {"id": "eval-reasoning-03", "category": "reasoning_isolation", "input_message": "Direct answer without thinking tags.", "expected_clean": "Direct answer without thinking tags.", "expected_thought_count": 0},
    {"id": "eval-reasoning-04", "category": "reasoning_isolation", "input_message": "<think>Draft proof</think>Theorem proved.<think>Check lemma 2</think>All lemmas verified.", "expected_clean": "Theorem proved.\n\nAll lemmas verified.", "expected_thought_count": 2},
    {"id": "eval-reasoning-05", "category": "reasoning_isolation", "input_message": "<think>Only internal thought</think>", "expected_clean": "", "expected_thought_count": 1},
    {"id": "eval-retrieval-01", "category": "knowledge_retrieval", "document_text": "# Machine Learning\n\nML models rely on tensor compute graphs.\n\n## Vector Embeddings\n\nHigh-dimensional dense vectors represent semantic similarity.\n\n## Quantization\n\nFP16 weights reduce memory.", "query": "dense vectors semantic similarity", "expected_heading": "Vector Embeddings"},
    {"id": "eval-retrieval-02", "category": "knowledge_retrieval", "document_text": "# Optimizer Selection\n\nAdamW applies decoupled weight decay.\n\n# Learning Rate Schedules\n\nCosine annealing decays step sizes.", "query": "decoupled weight decay AdamW", "expected_heading": "Optimizer Selection"},
    {"id": "eval-retrieval-03", "category": "knowledge_retrieval", "document_text": "Overview of RAG pipelines.\nRetrieval augmented generation pulls grounding chunks from vector indices.", "query": "grounding chunks vector indices", "strategy": "fast_text", "expected_keyword": "retrieval"},
    {"id": "eval-retrieval-04", "category": "knowledge_retrieval", "document_text": "Transformer self-attention maps query and key matrices. Softmax normalizes row distributions across tokens.", "query": "softmax normalizes attention weights", "strategy": "semantic_chunks", "expected_keyword": "attention"},
    {"id": "eval-retrieval-05", "category": "knowledge_retrieval", "document_text": "# Context Window\n\nLong-context needles require attention sinks.\n\n# Speculative Decoding\n\nDraft models generate candidate tokens.", "query": "speculative draft candidate tokens", "expected_heading": "Speculative Decoding"},
    {"id": "eval-prompt-01", "category": "prompt_compiler", "messages": [{"role": "user", "content": "Compute 15 * 4"}, {"role": "assistant", "content": "<think>15*4 is 60</think>Result is 60."}, {"role": "user", "content": "Add 10"}], "reinject_reasoning": False, "should_contain_think": False},
    {"id": "eval-prompt-02", "category": "prompt_compiler", "messages": [{"role": "user", "content": "Debug code"}, {"role": "assistant", "content": "<think>Null pointer check</think>Fixed index."}], "reinject_reasoning": True, "should_contain_think": True},
    {"id": "eval-prompt-03", "category": "prompt_compiler", "messages": [{"role": "user", "content": "Summarize"}, {"role": "assistant", "content": "<think>Plan</think>Summary."}, {"role": "user", "content": "Clarify"}, {"role": "assistant", "content": "<think>Examine</think>Details."}], "reinject_reasoning": False, "expected_pruned_count": 2},
    {"id": "eval-prompt-04", "category": "prompt_compiler", "messages": [{"role": "system", "content": "Assistant."}, {"role": "user", "content": "Query"}, {"role": "assistant", "content": "SELECT 1;"}], "reinject_reasoning": False, "expected_pruned_count": 0},
    {"id": "eval-prompt-05", "category": "prompt_compiler", "messages": [{"role": "user", "content": "Question"}, {"role": "assistant", "content": "<think>Only thought</think>"}], "reinject_reasoning": False, "should_contain_think": False},
]

def run_benchmark_suite() -> Dict[str, Any]:
    tree_passed = tree_total = reasoning_passed = reasoning_total = 0
    retrieval_passed = retrieval_total = prompt_passed = prompt_total = 0
    detailed_results: List[Dict[str, Any]] = []

    for test in BENCHMARK_DATASET:
        category, test_id = test["category"], test["id"]
        if category == "tree_integrity":
            tree_total += 1
            msgs = test["input"]
            valid, _, _, orphans, cycles = validate_chat_tree(msgs)
            corrupt = (not valid) or (orphans > 0) or cycles
            repaired = repair_chat_tree(msgs)
            rep_v, _, _, rep_o, rep_c = validate_chat_tree(repaired)
            success = (corrupt == test["expected_corrupt"]) and (rep_v and rep_o == 0 and not rep_c)
            if success:
                tree_passed += 1
            detail: Dict[str, Any] = {"id": test_id, "category": category, "success": success}
            if not success:
                detail["expected_corrupt"] = test["expected_corrupt"]
                detail["actual_corrupt"] = corrupt
                detail["expected_repair_valid"] = test["expected_repair_valid"]
                detail["actual_repair_valid"] = rep_v and rep_o == 0 and not rep_c
            detailed_results.append(detail)
        elif category == "reasoning_isolation":
            reasoning_total += 1
            clean, thoughts = extract_reasoning_blocks(test["input_message"])
            expected_clean = test["expected_clean"].strip()
            actual_clean = clean.strip()
            expected_count = test["expected_thought_count"]
            actual_count = len(thoughts)
            success = (actual_clean == expected_clean) and (actual_count == expected_count)
            if success:
                reasoning_passed += 1
            detail = {"id": test_id, "category": category, "success": success}
            if not success:
                detail["expected_clean"] = expected_clean
                detail["actual_clean"] = actual_clean
                detail["expected_thought_count"] = expected_count
                detail["actual_thought_count"] = actual_count
            detailed_results.append(detail)
        elif category == "knowledge_retrieval":
            retrieval_total += 1
            chunks = extract_content(test["document_text"], strategy=test.get("strategy", "structured_markdown"))
            matches = search_knowledge_chunks(chunks, test["query"], limit=1)
            success = False
            top = matches[0] if matches else None
            if top:
                if "expected_heading" in test:
                    success = top.get("heading") == test["expected_heading"]
                elif "expected_keyword" in test:
                    success = test["expected_keyword"].lower() in top.get("text", "").lower()
            if success:
                retrieval_passed += 1
            detail = {"id": test_id, "category": category, "success": success}
            if not success:
                detail["query"] = test["query"]
                detail["strategy"] = test.get("strategy", "structured_markdown")
                if "expected_heading" in test:
                    detail["expected_heading"] = test["expected_heading"]
                    detail["actual_heading"] = top.get("heading") if top else None
                elif "expected_keyword" in test:
                    detail["expected_keyword"] = test["expected_keyword"]
                    detail["actual_text_snippet"] = top.get("text", "")[:200] if top else None
            detailed_results.append(detail)
        elif category == "prompt_compiler":
            prompt_total += 1
            compiled, pruned, _ = compile_prompt_messages(test["messages"], reinject_reasoning=test.get("reinject_reasoning", False))
            text = " ".join(m["content"] for m in compiled).lower()
            success = True
            failure_reasons = []
            if "should_contain_think" in test and ("you" in text) != test["should_contain_think"]:
                success = False
                failure_reasons.append(f"think tag presence: expected={test['should_contain_think']}, actual={'you' in text}")
            if "expected_pruned_count" in test and pruned != test["expected_pruned_count"]:
                success = False
                failure_reasons.append(f"pruned count: expected={test['expected_pruned_count']}, actual={pruned}")
            if success:
                prompt_passed += 1
            detail = {"id": test_id, "category": category, "success": success}
            if not success:
                detail["failure_reasons"] = failure_reasons
            detailed_results.append(detail)

    total = len(BENCHMARK_DATASET)
    passed = tree_passed + reasoning_passed + retrieval_passed + prompt_passed
    return {
        "benchmark_name": "signal-reasoning-tree-v1",
        "sample_count": total,
        "structural_integrity_score": round(tree_passed / max(tree_total, 1), 4),
        "reasoning_isolation_score": round(reasoning_passed / max(reasoning_total, 1), 4),
        "retrieval_f1_score": round(retrieval_passed / max(retrieval_total, 1), 4),
        "accuracy_score": round(passed / max(total, 1), 4),
        "metrics": {
            "tree_tests": {"passed": tree_passed, "total": tree_total},
            "reasoning_tests": {"passed": reasoning_passed, "total": reasoning_total},
            "retrieval_tests": {"passed": retrieval_passed, "total": retrieval_total},
            "prompt_tests": {"passed": prompt_passed, "total": prompt_total},
        },
        "details": detailed_results,
    }

def main():
    r = run_benchmark_suite()
    print("=" * 60)
    print("SIGNAL STUDIO AI/ML BENCHMARK EVALUATION RESULTS")
    print(f"Benchmark: {r['benchmark_name']} (N={r['sample_count']})")
    print(f"Structural Integrity Score: {r['structural_integrity_score'] * 100:.1f}%")
    print(f"Reasoning Isolation Score:  {r['reasoning_isolation_score'] * 100:.1f}%")
    print(f"Knowledge Retrieval F1:     {r['retrieval_f1_score'] * 100:.1f}%")
    print(f"Overall Accuracy:           {r['accuracy_score'] * 100:.1f}%")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
