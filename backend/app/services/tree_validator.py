from typing import List, Dict, Any, Tuple, Set


def validate_chat_tree(messages: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str], int, bool]:
    errors: List[str] = []
    warnings: List[str] = []
    orphan_count = 0
    cycle_detected = False

    if not messages:
        return True, errors, warnings, 0, False

    message_ids: Set[str] = set()
    id_counts: Dict[str, int] = {}
    
    for msg in messages:
        msg_id = str(msg.get("id", ""))
        if not msg_id:
            errors.append("Encountered message without a valid 'id' property.")
            continue
        id_counts[msg_id] = id_counts.get(msg_id, 0) + 1
        message_ids.add(msg_id)

    for msg_id, count in id_counts.items():
        if count > 1:
            errors.append(f"Duplicate message id '{msg_id}' detected ({count} occurrences).")

    # Check for orphan messages
    for msg in messages:
        msg_id = str(msg.get("id", ""))
        parent_id = msg.get("parent_id")
        if parent_id is not None and parent_id != "":
            parent_id_str = str(parent_id)
            if parent_id_str not in message_ids:
                orphan_count += 1
                errors.append(
                    f"Message '{msg_id}' is an orphan: parent_id '{parent_id_str}' does not exist in the chat tree."
                )

    # Detect cycles in the parent-child DAG using DFS
    parent_map: Dict[str, str] = {}
    for msg in messages:
        m_id = str(msg.get("id", ""))
        p_id = msg.get("parent_id")
        if p_id:
            parent_map[m_id] = str(p_id)

    visited: Set[str] = set()
    recursion_stack: Set[str] = set()

    for node in message_ids:
        if node not in visited:
            curr = node
            path: List[str] = []
            while curr:
                if curr in recursion_stack:
                    cycle_detected = True
                    cycle_path = " -> ".join(path + [curr])
                    errors.append(f"Cycle detected in message tree: {cycle_path}")
                    break
                if curr in visited or curr not in parent_map:
                    break
                recursion_stack.add(curr)
                path.append(curr)
                curr = parent_map.get(curr)
            
            for item in recursion_stack:
                visited.add(item)
            recursion_stack.clear()

    is_valid = len(errors) == 0
    return is_valid, errors, warnings, orphan_count, cycle_detected


def repair_chat_tree(messages: List[Dict[str, Any]], repair_strategy: str = "relink_chronological") -> List[Dict[str, Any]]:
    if not messages:
        return []

    repaired: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    id_map: Dict[str, Dict[str, Any]] = {}

    # Deduplicate and ensure IDs
    for idx, msg in enumerate(messages):
        msg_copy = dict(msg)
        msg_id = str(msg_copy.get("id", "")).strip()
        if not msg_id or msg_id in seen_ids:
            msg_id = f"msg-repaired-{idx}-{abs(hash(str(msg_copy.get('content', '')))) % 1000000}"
            msg_copy["id"] = msg_id
        seen_ids.add(msg_id)
        repaired.append(msg_copy)
        id_map[msg_id] = msg_copy

    # Identify and break cycles
    for msg in repaired:
        curr_id = msg["id"]
        visited = {curr_id}
        parent = msg.get("parent_id")
        while parent and str(parent) in id_map:
            p_str = str(parent)
            if p_str in visited:
                # Cycle detected: break cycle by setting parent_id to None
                msg["parent_id"] = None
                break
            visited.add(p_str)
            parent = id_map[p_str].get("parent_id")

    # Repair orphans
    valid_parents = set(id_map.keys())
    last_valid_id = None

    for msg in repaired:
        p_id = msg.get("parent_id")
        if p_id is not None and str(p_id) != "":
            if str(p_id) not in valid_parents:
                if repair_strategy == "relink_chronological" and last_valid_id:
                    msg["parent_id"] = last_valid_id
                else:
                    msg["parent_id"] = None
        last_valid_id = msg["id"]

    return repaired


def build_nested_tree(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not messages:
        return []

    node_map: Dict[str, Dict[str, Any]] = {}
    for msg in messages:
        m_id = str(msg.get("id", ""))
        node_map[m_id] = {**msg, "children": []}

    roots: List[Dict[str, Any]] = []
    for msg in messages:
        m_id = str(msg.get("id", ""))
        p_id = msg.get("parent_id")
        if p_id and str(p_id) in node_map:
            node_map[str(p_id)]["children"].append(node_map[m_id])
        else:
            roots.append(node_map[m_id])

    return roots
