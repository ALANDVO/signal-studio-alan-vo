from app.services.tree_validator import validate_chat_tree, repair_chat_tree, build_nested_tree


def test_valid_linear_tree():
    messages = [
        {"id": "m1", "parent_id": None, "role": "user", "content": "Hello"},
        {"id": "m2", "parent_id": "m1", "role": "assistant", "content": "Hi there"},
        {"id": "m3", "parent_id": "m2", "role": "user", "content": "How are you?"},
    ]
    is_valid, errors, warnings, orphan_count, cycle_detected = validate_chat_tree(messages)
    assert is_valid is True
    assert len(errors) == 0
    assert orphan_count == 0
    assert cycle_detected is False


def test_orphan_message_detection_issue_15189():
    # Reproduces Open WebUI issue #15189 where orphan messages with missing parentId break frontend
    messages = [
        {"id": "m1", "parent_id": None, "role": "user", "content": "Question 1"},
        {"id": "orphan_msg", "parent_id": "missing_parent_999", "role": "assistant", "content": "Broken answer"},
    ]
    is_valid, errors, warnings, orphan_count, cycle_detected = validate_chat_tree(messages)
    assert is_valid is False
    assert orphan_count == 1
    assert any("is an orphan" in err for err in errors)


def test_cycle_detection_in_dag():
    messages = [
        {"id": "a", "parent_id": "b", "role": "user", "content": "A"},
        {"id": "b", "parent_id": "a", "role": "assistant", "content": "B"},
    ]
    is_valid, errors, warnings, orphan_count, cycle_detected = validate_chat_tree(messages)
    assert is_valid is False
    assert cycle_detected is True
    assert any("Cycle detected" in err for err in errors)


def test_repair_chat_tree_relinks_orphans_and_breaks_cycles():
    corrupted_messages = [
        {"id": "root", "parent_id": None, "role": "user", "content": "Root message"},
        {"id": "c1", "parent_id": "c2", "role": "assistant", "content": "Cycle 1"},
        {"id": "c2", "parent_id": "c1", "role": "user", "content": "Cycle 2"},
        {"id": "orphan1", "parent_id": "ghost_id_404", "role": "assistant", "content": "Orphan content"},
    ]

    repaired = repair_chat_tree(corrupted_messages)
    is_valid, errors, _, orphan_count, cycle_detected = validate_chat_tree(repaired)

    assert is_valid is True
    assert orphan_count == 0
    assert cycle_detected is False
    assert len(repaired) == 4


def test_build_nested_tree_structure():
    messages = [
        {"id": "m1", "parent_id": None, "role": "user", "content": "Root prompt"},
        {"id": "m2", "parent_id": "m1", "role": "assistant", "content": "Branch A"},
        {"id": "m3", "parent_id": "m1", "role": "assistant", "content": "Branch B"},
    ]
    tree = build_nested_tree(messages)
    assert len(tree) == 1
    assert tree[0]["id"] == "m1"
    assert len(tree[0]["children"]) == 2
