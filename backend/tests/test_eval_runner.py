from app.services.eval_runner import run_benchmark_suite


def test_eval_benchmark_suite_execution():
    results = run_benchmark_suite()
    assert results["benchmark_name"] == "signal-reasoning-tree-v1"
    assert results["sample_count"] == 20
    assert results["structural_integrity_score"] >= 0.95
    assert results["reasoning_isolation_score"] >= 0.95
    assert results["retrieval_f1_score"] >= 0.95
    assert results["accuracy_score"] >= 0.95
    assert len(results["details"]) == 20
