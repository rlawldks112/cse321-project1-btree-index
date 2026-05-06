# experiments/experiment_utils.py

import csv
import os
import random
import time


def load_student_records(csv_path):
    """
    Load student.csv into an in-memory array.

    The project manual requires:
    - Student ID as Key
    - array index as RID

    Returns:
        records: list[dict]
        key_rid_pairs: list[tuple[int, int]]
        key_to_rid: dict[int, int]
    """

    records = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row.")

        # Normalize column names because CSV files sometimes contain spaces/BOM.
        field_map = {name.strip(): name for name in reader.fieldnames}

        required_columns = [
            "Student ID",
            "Name",
            "Gender",
            "GPA",
            "Height",
            "Weight",
        ]

        for col in required_columns:
            if col not in field_map:
                raise ValueError(
                    f"Missing required column: {col}. "
                    f"Found columns: {reader.fieldnames}"
                )

        for rid, row in enumerate(reader):
            student_id = int(row[field_map["Student ID"]])
            name = row[field_map["Name"]]
            gender = row[field_map["Gender"]]
            gpa = float(row[field_map["GPA"]])
            height = float(row[field_map["Height"]])
            weight = float(row[field_map["Weight"]])

            records.append(
                {
                    "Student ID": student_id,
                    "Name": name,
                    "Gender": gender,
                    "GPA": gpa,
                    "Height": height,
                    "Weight": weight,
                }
            )

    key_rid_pairs = [
        (record["Student ID"], rid)
        for rid, record in enumerate(records)
    ]

    key_to_rid = {
        key: rid
        for key, rid in key_rid_pairs
    }

    if len(key_to_rid) != len(key_rid_pairs):
        raise ValueError("Duplicate Student ID detected in dataset.")

    return records, key_rid_pairs, key_to_rid


def make_fixed_samples(key_rid_pairs, seed=321, search_count=10000):
    """
    Create fixed random samples.

    Important:
    The same search/delete keys must be used for B-tree, B+ tree, and B* tree.
    Otherwise, the performance comparison is unfair.

    Returns:
        search_keys
        delete_10_keys
        delete_20_keys
        remaining_check_keys
    """

    all_keys = [key for key, _ in key_rid_pairs]

    if len(all_keys) == 0:
        raise ValueError("No keys available.")

    if len(all_keys) < search_count:
        raise ValueError(
            f"search_count={search_count} is larger than dataset size={len(all_keys)}"
        )

    rng = random.Random(seed)

    search_keys = rng.sample(all_keys, search_count)

    shuffled_keys = all_keys[:]
    rng.shuffle(shuffled_keys)

    delete_10_count = len(all_keys) // 10

    delete_10_keys = shuffled_keys[:delete_10_count]
    delete_20_keys = shuffled_keys[delete_10_count:delete_10_count * 2]

    deleted_set = set(delete_10_keys) | set(delete_20_keys)
    remaining_keys = [key for key in all_keys if key not in deleted_set]

    remaining_sample_size = min(10000, len(remaining_keys))
    remaining_check_keys = rng.sample(remaining_keys, remaining_sample_size)

    return search_keys, delete_10_keys, delete_20_keys, remaining_check_keys


def measure_seconds(func, *args, **kwargs):
    """
    Measure execution time for a function call.

    Returns:
        elapsed_seconds, result
    """

    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()

    return end - start, result


def safe_validate(tree):
    """
    Safely call tree.validate().

    Current tree implementations raise ValueError when invalid.
    This wrapper prevents the experiment from crashing immediately.

    Returns:
        valid: bool
        message: str
    """

    try:
        tree.validate()
        return True, "PASS"
    except Exception as e:
        return False, str(e)


def traverse_nodes(root):
    """
    Traverse all nodes in a tree.

    Works for BTree, BPlusTree, and BStarTree because all node classes have:
        - keys
        - children
        - is_leaf
    """

    nodes = []

    def dfs(node):
        nodes.append(node)

        if not getattr(node, "is_leaf", True):
            for child in getattr(node, "children", []):
                dfs(child)

    dfs(root)
    return nodes


def calculate_height(root):
    """
    Calculate tree height as number of levels.

    A single root leaf has height 1.
    """

    height = 0
    current = root

    while current is not None:
        height += 1

        if getattr(current, "is_leaf", True):
            break

        children = getattr(current, "children", [])
        if not children:
            break

        current = children[0]

    return height


def calculate_node_utilization(tree):
    """
    Calculate average node utilization.

    Formula:
        total_keys / (number_of_nodes * max_keys)

    This is a structural metric required by the experiment.
    """

    nodes = traverse_nodes(tree.root)
    node_count = len(nodes)

    max_keys = getattr(tree, "max_keys", None)

    if node_count == 0 or max_keys is None or max_keys == 0:
        return 0.0

    total_keys = sum(len(node.keys) for node in nodes)

    return total_keys / (node_count * max_keys)


def collect_tree_metrics(tree):
    """
    Collect metrics without requiring tree.get_metrics().

    Current classes do not define get_metrics(), so the experiment code
    collects the values externally.
    """

    nodes = traverse_nodes(tree.root)

    return {
        "height": calculate_height(tree.root),
        "node_count": len(nodes),
        "split_count": getattr(tree, "num_splits", 0),
        "redistribution_count": getattr(tree, "num_redistributions", 0),
        "two_to_three_split_count": getattr(tree, "num_2_to_3_splits", 0),
        "utilization": calculate_node_utilization(tree),
    }


def btree_range_query_by_traversal(tree, low_key, high_key):
    """
    Range query helper for BTree.

    BTree currently does not have range_query().
    Since BTree stores real key-RID pairs in internal and leaf nodes,
    an inorder traversal can collect all keys in range.
    """

    if low_key > high_key:
        return []

    result = []

    def dfs(node):
        if node.is_leaf:
            for key, rid in zip(node.keys, node.rids):
                if low_key <= key <= high_key:
                    result.append((key, rid))
            return

        for i in range(len(node.keys)):
            dfs(node.children[i])

            key = node.keys[i]
            rid = node.rids[i]

            if low_key <= key <= high_key:
                result.append((key, rid))

        dfs(node.children[-1])

    dfs(tree.root)
    return result


def range_query_any_tree(tree, low_key, high_key):
    """
    Unified range query wrapper.

    - BPlusTree has range_query()
    - BStarTree has range_query()
    - BTree does not, so we use inorder traversal helper
    """

    if hasattr(tree, "range_query"):
        return tree.range_query(low_key, high_key)

    return btree_range_query_by_traversal(tree, low_key, high_key)


def brute_force_range_stats(records, low_key, high_key, gender_filter="Male"):
    """
    Compute correct analytical range query result by scanning student.csv.

    Query:
        low_key <= Student ID <= high_key
        Gender == gender_filter

    Returns:
        dict with count, avg_gpa, avg_height
    """

    matched = []

    for record in records:
        student_id = record["Student ID"]

        if (
            low_key <= student_id <= high_key
            and record["Gender"] == gender_filter
        ):
            matched.append(record)

    if not matched:
        return {
            "count": 0,
            "avg_gpa": 0.0,
            "avg_height": 0.0,
        }

    return {
        "count": len(matched),
        "avg_gpa": sum(record["GPA"] for record in matched) / len(matched),
        "avg_height": sum(record["Height"] for record in matched) / len(matched),
    }


def tree_range_stats(tree, records, low_key, high_key, gender_filter="Male"):
    """
    Run tree range query and calculate analytical result.

    The tree returns (key, rid).
    We use rid to access the original record.
    """

    pairs = range_query_any_tree(tree, low_key, high_key)

    matched = []

    for key, rid in pairs:
        record = records[rid]

        if record["Gender"] == gender_filter:
            matched.append(record)

    if not matched:
        return {
            "count": 0,
            "avg_gpa": 0.0,
            "avg_height": 0.0,
            "raw_pair_count": len(pairs),
        }

    return {
        "count": len(matched),
        "avg_gpa": sum(record["GPA"] for record in matched) / len(matched),
        "avg_height": sum(record["Height"] for record in matched) / len(matched),
        "raw_pair_count": len(pairs),
    }


def compare_float(a, b, eps=1e-9):
    """
    Compare floating point numbers safely.
    """

    return abs(a - b) <= eps


def verify_range_stats(tree_stats, brute_stats):
    """
    Verify tree range query result against brute-force scan.
    """

    return (
        tree_stats["count"] == brute_stats["count"]
        and compare_float(tree_stats["avg_gpa"], brute_stats["avg_gpa"])
        and compare_float(tree_stats["avg_height"], brute_stats["avg_height"])
    )


def verify_search_results(tree, search_keys, key_to_rid):
    """
    Verify point search correctness.

    Returns:
        found_count
        correct_count
    """

    found_count = 0
    correct_count = 0

    for key in search_keys:
        actual_rid = tree.search(key)
        expected_rid = key_to_rid[key]

        if actual_rid is not None:
            found_count += 1

        if actual_rid == expected_rid:
            correct_count += 1

    return found_count, correct_count


def delete_keys(tree, keys):
    """
    Delete multiple keys.

    Returns:
        deleted_success_count
    """

    deleted_success_count = 0

    for key in keys:
        if tree.delete(key):
            deleted_success_count += 1

    return deleted_success_count


def verify_deleted_keys_absent(tree, deleted_keys):
    """
    Check that deleted keys are no longer searchable.
    """

    absent_count = 0

    for key in deleted_keys:
        if tree.search(key) is None:
            absent_count += 1

    return absent_count


def verify_remaining_keys_found(tree, remaining_keys, key_to_rid):
    """
    Check that non-deleted keys are still searchable.
    """

    correct_count = 0

    for key in remaining_keys:
        if tree.search(key) == key_to_rid[key]:
            correct_count += 1

    return correct_count


def ensure_results_dir(results_dir):
    """
    Create results directory if needed.
    """

    os.makedirs(results_dir, exist_ok=True)


def write_csv(path, rows, fieldnames):
    """
    Write experiment results to CSV.
    """

    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(row)


def print_section(title):
    """
    Print a readable section header.
    """

    line = "=" * 70
    print()
    print(line)
    print(title)
    print(line)


def print_step(message):
    """
    Print a readable step message.
    """

    print(f"[STEP] {message}")


def print_pass_fail(label, passed, detail=""):
    """
    Print PASS/FAIL message.
    """

    status = "PASS" if passed else "FAIL"

    if detail:
        print(f"[{label}] {status} | {detail}")
    else:
        print(f"[{label}] {status}")