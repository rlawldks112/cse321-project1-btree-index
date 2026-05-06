# experiments/final_experiment.py

import os
import sys


# ------------------------------------------------------------
# Make project root importable.
# This helps when running:
#   python experiments/final_experiment.py
# from the project root on Windows / VS Code / zsh.
# ------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from src.btree import BTree
from src.bplustree import BPlusTree
from src.bstartree import BStarTree

from experiments.experiment_utils import (
    load_student_records,
    make_fixed_samples,
    measure_seconds,
    safe_validate,
    collect_tree_metrics,
    verify_search_results,
    brute_force_range_stats,
    tree_range_stats,
    verify_range_stats,
    delete_keys,
    verify_deleted_keys_absent,
    verify_remaining_keys_found,
    write_csv,
    print_section,
    print_step,
    print_pass_fail,
)


DATA_PATH = os.path.join(PROJECT_ROOT, "data", "student.csv")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

INSERTION_RESULTS_PATH = os.path.join(RESULTS_DIR, "insertion_results.csv")
SEARCH_RESULTS_PATH = os.path.join(RESULTS_DIR, "search_results.csv")
RANGE_RESULTS_PATH = os.path.join(RESULTS_DIR, "range_results.csv")
DELETION_RESULTS_PATH = os.path.join(RESULTS_DIR, "deletion_results.csv")
SUMMARY_RESULTS_PATH = os.path.join(RESULTS_DIR, "experiment_summary.csv")


TREE_CLASSES = {
    "BTree": BTree,
    "BPlusTree": BPlusTree,
    "BStarTree": BStarTree,
}


ORDERS = [3, 5, 10]
RANDOM_SEED = 321
SEARCH_COUNT = 10000

RANGE_LOW_KEY = 202278651
RANGE_HIGH_KEY = 202419537
RANGE_GENDER_FILTER = "Male"


def build_tree_with_all_records(tree, key_rid_pairs):
    for key, rid in key_rid_pairs:
        tree.insert(key, rid)


def run_single_insertion_experiment(tree_name, tree_class, d, records, key_rid_pairs):
    print_section(f"INSERTION EXPERIMENT: {tree_name} | d={d}")

    print_step(f"Creating {tree_name}(d={d})")
    tree = tree_class(d=d)

    print_step(f"Inserting all records into {tree_name}(d={d})")
    insert_time, _ = measure_seconds(
        build_tree_with_all_records,
        tree,
        key_rid_pairs,
    )

    print_step(f"Validating {tree_name}(d={d}) after insertion")
    valid, message = safe_validate(tree)
    metrics = collect_tree_metrics(tree)

    print_pass_fail("Validation after insertion", valid, message)

    print()
    print("[Insertion Metrics]")
    print(f"tree_type: {tree_name}")
    print(f"d: {d}")
    print(f"record_count: {len(records)}")
    print(f"insertion_time_sec: {insert_time:.6f}")
    print(f"split_count: {metrics['split_count']}")
    print(f"redistribution_count: {metrics['redistribution_count']}")
    print(f"two_to_three_split_count: {metrics['two_to_three_split_count']}")
    print(f"node_count: {metrics['node_count']}")
    print(f"height: {metrics['height']}")
    print(f"utilization: {metrics['utilization']:.6f}")

    return {
        "tree_name": tree_name,
        "d": d,
        "tree": tree,
        "valid": valid,
        "message": message,
        "insert_time": insert_time,
        "metrics": metrics,
    }


def run_single_search_experiment(insertion_result, search_keys, key_to_rid):
    tree_name = insertion_result["tree_name"]
    d = insertion_result["d"]
    tree = insertion_result["tree"]

    print_section(f"POINT SEARCH EXPERIMENT: {tree_name} | d={d}")
    print_step(f"Searching {len(search_keys)} fixed random existing keys")

    search_time, search_result = measure_seconds(
        verify_search_results,
        tree,
        search_keys,
        key_to_rid,
    )

    found_count, correct_count = search_result
    mean_search_time = search_time / len(search_keys)

    search_pass = (
        found_count == len(search_keys)
        and correct_count == len(search_keys)
    )

    print_pass_fail(
        "Point search correctness",
        search_pass,
        f"found={found_count}/{len(search_keys)}, correct={correct_count}/{len(search_keys)}",
    )

    return {
        "tree_name": tree_name,
        "d": d,
        "query_count": len(search_keys),
        "total_search_time": search_time,
        "mean_search_time": mean_search_time,
        "found_count": found_count,
        "correct_count": correct_count,
        "accuracy": correct_count / len(search_keys),
        "valid": search_pass,
    }


def run_single_range_experiment(insertion_result, records, brute_stats):
    tree_name = insertion_result["tree_name"]
    d = insertion_result["d"]
    tree = insertion_result["tree"]

    print_section(f"RANGE QUERY EXPERIMENT: {tree_name} | d={d}")

    print_step(
        f"Running range query: {RANGE_LOW_KEY} <= Student ID <= {RANGE_HIGH_KEY}, "
        f"Gender == {RANGE_GENDER_FILTER}"
    )

    range_time, stats = measure_seconds(
        tree_range_stats,
        tree,
        records,
        RANGE_LOW_KEY,
        RANGE_HIGH_KEY,
        RANGE_GENDER_FILTER,
    )

    correct = verify_range_stats(stats, brute_stats)

    print_pass_fail(
        "Range query correctness",
        correct,
        (
            f"tree_count={stats['count']}, brute_count={brute_stats['count']}, "
            f"tree_avg_gpa={stats['avg_gpa']:.9f}, brute_avg_gpa={brute_stats['avg_gpa']:.9f}, "
            f"tree_avg_height={stats['avg_height']:.9f}, brute_avg_height={brute_stats['avg_height']:.9f}"
        ),
    )

    return {
        "tree_name": tree_name,
        "d": d,
        "low_key": RANGE_LOW_KEY,
        "high_key": RANGE_HIGH_KEY,
        "gender_filter": RANGE_GENDER_FILTER,
        "range_time": range_time,
        "matched_count": stats["count"],
        "avg_gpa": stats["avg_gpa"],
        "avg_height": stats["avg_height"],
        "raw_pair_count": stats["raw_pair_count"],
        "brute_count": brute_stats["count"],
        "brute_avg_gpa": brute_stats["avg_gpa"],
        "brute_avg_height": brute_stats["avg_height"],
        "valid": correct,
    }


def run_single_deletion_phase(
    insertion_result,
    phase_name,
    delete_keys_for_phase,
    all_deleted_keys_so_far,
    remaining_check_keys,
    key_to_rid,
):
    tree_name = insertion_result["tree_name"]
    d = insertion_result["d"]
    tree = insertion_result["tree"]

    print_section(f"DELETION EXPERIMENT: {tree_name} | d={d} | {phase_name}")

    print_step(f"Deleting {len(delete_keys_for_phase)} keys")
    delete_time, deleted_success_count = measure_seconds(
        delete_keys,
        tree,
        delete_keys_for_phase,
    )

    print_step("Validating tree after deletion")
    valid_after_delete, validation_message = safe_validate(tree)

    print_step("Checking deleted keys are absent")
    absent_count = verify_deleted_keys_absent(tree, all_deleted_keys_so_far)

    print_step("Checking remaining sample keys are still searchable")
    remaining_found_count = verify_remaining_keys_found(
        tree,
        remaining_check_keys,
        key_to_rid,
    )

    metrics_after_delete = collect_tree_metrics(tree)

    deleted_absent_pass = absent_count == len(all_deleted_keys_so_far)
    remaining_found_pass = remaining_found_count == len(remaining_check_keys)

    phase_pass = (
        deleted_success_count == len(delete_keys_for_phase)
        and valid_after_delete
        and deleted_absent_pass
        and remaining_found_pass
    )

    print_pass_fail(
        "Deletion phase correctness",
        phase_pass,
        (
            f"deleted_success={deleted_success_count}/{len(delete_keys_for_phase)}, "
            f"deleted_absent={absent_count}/{len(all_deleted_keys_so_far)}, "
            f"remaining_found={remaining_found_count}/{len(remaining_check_keys)}, "
            f"validate={valid_after_delete}"
        ),
    )

    return {
        "tree_name": tree_name,
        "d": d,
        "phase": phase_name,
        "delete_count": len(delete_keys_for_phase),
        "total_deleted_so_far": len(all_deleted_keys_so_far),
        "deletion_time": delete_time,
        "deleted_success_count": deleted_success_count,
        "deleted_absent_count": absent_count,
        "remaining_sample_count": len(remaining_check_keys),
        "remaining_sample_found_count": remaining_found_count,
        "height_after_delete": metrics_after_delete["height"],
        "node_count_after_delete": metrics_after_delete["node_count"],
        "split_count_after_delete": metrics_after_delete["split_count"],
        "redistribution_count_after_delete": metrics_after_delete["redistribution_count"],
        "two_to_three_split_count_after_delete": metrics_after_delete["two_to_three_split_count"],
        "utilization_after_delete": metrics_after_delete["utilization"],
        "valid_after_delete": valid_after_delete,
        "validation_message": validation_message,
        "deleted_absent_pass": deleted_absent_pass,
        "remaining_found_pass": remaining_found_pass,
        "valid": phase_pass,
    }


def run_deletion_experiments_for_tree(
    insertion_result,
    delete_10_keys,
    delete_20_keys,
    remaining_check_keys,
    key_to_rid,
):
    deletion_results = []

    first_deleted_so_far = list(delete_10_keys)

    phase_1_result = run_single_deletion_phase(
        insertion_result=insertion_result,
        phase_name="delete_10_percent",
        delete_keys_for_phase=delete_10_keys,
        all_deleted_keys_so_far=first_deleted_so_far,
        remaining_check_keys=remaining_check_keys,
        key_to_rid=key_to_rid,
    )

    deletion_results.append(phase_1_result)

    second_deleted_so_far = list(delete_10_keys) + list(delete_20_keys)

    phase_2_result = run_single_deletion_phase(
        insertion_result=insertion_result,
        phase_name="delete_20_percent_total",
        delete_keys_for_phase=delete_20_keys,
        all_deleted_keys_so_far=second_deleted_so_far,
        remaining_check_keys=remaining_check_keys,
        key_to_rid=key_to_rid,
    )

    deletion_results.append(phase_2_result)

    return deletion_results


def make_insertion_csv_row(result, record_count):
    metrics = result["metrics"]

    return {
        "tree_type": result["tree_name"],
        "d": result["d"],
        "record_count": record_count,
        "insertion_time_sec": f"{result['insert_time']:.9f}",
        "split_count": metrics["split_count"],
        "redistribution_count": metrics["redistribution_count"],
        "two_to_three_split_count": metrics["two_to_three_split_count"],
        "node_count": metrics["node_count"],
        "height": metrics["height"],
        "utilization": f"{metrics['utilization']:.9f}",
        "valid": result["valid"],
        "validation_message": result["message"],
    }


def make_search_csv_row(result):
    return {
        "tree_type": result["tree_name"],
        "d": result["d"],
        "query_count": result["query_count"],
        "total_search_time_sec": f"{result['total_search_time']:.9f}",
        "mean_search_time_sec": f"{result['mean_search_time']:.12f}",
        "found_count": result["found_count"],
        "correct_count": result["correct_count"],
        "accuracy": f"{result['accuracy']:.9f}",
        "valid": result["valid"],
    }


def make_range_csv_row(result):
    return {
        "tree_type": result["tree_name"],
        "d": result["d"],
        "low_key": result["low_key"],
        "high_key": result["high_key"],
        "gender_filter": result["gender_filter"],
        "range_time_sec": f"{result['range_time']:.9f}",
        "matched_count": result["matched_count"],
        "avg_gpa": f"{result['avg_gpa']:.9f}",
        "avg_height": f"{result['avg_height']:.9f}",
        "raw_pair_count": result["raw_pair_count"],
        "brute_count": result["brute_count"],
        "brute_avg_gpa": f"{result['brute_avg_gpa']:.9f}",
        "brute_avg_height": f"{result['brute_avg_height']:.9f}",
        "valid": result["valid"],
    }


def make_deletion_csv_row(result):
    return {
        "tree_type": result["tree_name"],
        "d": result["d"],
        "phase": result["phase"],
        "delete_count": result["delete_count"],
        "total_deleted_so_far": result["total_deleted_so_far"],
        "deletion_time_sec": f"{result['deletion_time']:.9f}",
        "deleted_success_count": result["deleted_success_count"],
        "deleted_absent_count": result["deleted_absent_count"],
        "remaining_sample_count": result["remaining_sample_count"],
        "remaining_sample_found_count": result["remaining_sample_found_count"],
        "height_after_delete": result["height_after_delete"],
        "node_count_after_delete": result["node_count_after_delete"],
        "split_count_after_delete": result["split_count_after_delete"],
        "redistribution_count_after_delete": result["redistribution_count_after_delete"],
        "two_to_three_split_count_after_delete": result["two_to_three_split_count_after_delete"],
        "utilization_after_delete": f"{result['utilization_after_delete']:.9f}",
        "valid_after_delete": result["valid_after_delete"],
        "deleted_absent_pass": result["deleted_absent_pass"],
        "remaining_found_pass": result["remaining_found_pass"],
        "valid": result["valid"],
        "validation_message": result["validation_message"],
    }


def make_summary_csv_rows(insertion_results, search_results, range_results, deletion_results):
    """
    Merge insertion/search/range/deletion results into one summary table.

    One row per:
        tree_type, d
    """

    rows = []

    for insertion_result, search_result, range_result in zip(
        insertion_results,
        search_results,
        range_results,
    ):
        tree_name = insertion_result["tree_name"]
        d = insertion_result["d"]
        metrics = insertion_result["metrics"]

        related_deletions = [
            result
            for result in deletion_results
            if result["tree_name"] == tree_name and result["d"] == d
        ]

        delete_10 = None
        delete_20 = None

        for deletion_result in related_deletions:
            if deletion_result["phase"] == "delete_10_percent":
                delete_10 = deletion_result
            elif deletion_result["phase"] == "delete_20_percent_total":
                delete_20 = deletion_result

        deletion_pass = (
            delete_10 is not None
            and delete_20 is not None
            and delete_10["valid"]
            and delete_20["valid"]
        )

        overall_pass = (
            insertion_result["valid"]
            and search_result["valid"]
            and range_result["valid"]
            and deletion_pass
        )

        row = {
            "tree_type": tree_name,
            "d": d,
            "record_count": 100000,
            "insert_time_sec": f"{insertion_result['insert_time']:.9f}",
            "search_query_count": search_result["query_count"],
            "search_mean_time_sec": f"{search_result['mean_search_time']:.12f}",
            "search_accuracy": f"{search_result['accuracy']:.9f}",
            "range_low_key": range_result["low_key"],
            "range_high_key": range_result["high_key"],
            "range_gender_filter": range_result["gender_filter"],
            "range_time_sec": f"{range_result['range_time']:.9f}",
            "range_matched_count": range_result["matched_count"],
            "range_avg_gpa": f"{range_result['avg_gpa']:.9f}",
            "range_avg_height": f"{range_result['avg_height']:.9f}",
            "delete_10_time_sec": f"{delete_10['deletion_time']:.9f}" if delete_10 else "",
            "delete_20_total_second_phase_time_sec": f"{delete_20['deletion_time']:.9f}" if delete_20 else "",
            "delete_10_valid": delete_10["valid"] if delete_10 else False,
            "delete_20_valid": delete_20["valid"] if delete_20 else False,
            "split_count": metrics["split_count"],
            "redistribution_count": metrics["redistribution_count"],
            "two_to_three_split_count": metrics["two_to_three_split_count"],
            "node_count_after_insert": metrics["node_count"],
            "height_after_insert": metrics["height"],
            "utilization_after_insert": f"{metrics['utilization']:.9f}",
            "height_after_20_percent_delete": delete_20["height_after_delete"] if delete_20 else "",
            "node_count_after_20_percent_delete": delete_20["node_count_after_delete"] if delete_20 else "",
            "utilization_after_20_percent_delete": f"{delete_20['utilization_after_delete']:.9f}" if delete_20 else "",
            "overall_pass": overall_pass,
        }

        rows.append(row)

    return rows


def save_insertion_results(results, record_count):
    rows = [make_insertion_csv_row(result, record_count) for result in results]

    fieldnames = [
        "tree_type",
        "d",
        "record_count",
        "insertion_time_sec",
        "split_count",
        "redistribution_count",
        "two_to_three_split_count",
        "node_count",
        "height",
        "utilization",
        "valid",
        "validation_message",
    ]

    write_csv(INSERTION_RESULTS_PATH, rows, fieldnames)
    print_step(f"Insertion results saved to: {INSERTION_RESULTS_PATH}")


def save_search_results(results):
    rows = [make_search_csv_row(result) for result in results]

    fieldnames = [
        "tree_type",
        "d",
        "query_count",
        "total_search_time_sec",
        "mean_search_time_sec",
        "found_count",
        "correct_count",
        "accuracy",
        "valid",
    ]

    write_csv(SEARCH_RESULTS_PATH, rows, fieldnames)
    print_step(f"Search results saved to: {SEARCH_RESULTS_PATH}")


def save_range_results(results):
    rows = [make_range_csv_row(result) for result in results]

    fieldnames = [
        "tree_type",
        "d",
        "low_key",
        "high_key",
        "gender_filter",
        "range_time_sec",
        "matched_count",
        "avg_gpa",
        "avg_height",
        "raw_pair_count",
        "brute_count",
        "brute_avg_gpa",
        "brute_avg_height",
        "valid",
    ]

    write_csv(RANGE_RESULTS_PATH, rows, fieldnames)
    print_step(f"Range query results saved to: {RANGE_RESULTS_PATH}")


def save_deletion_results(results):
    rows = [make_deletion_csv_row(result) for result in results]

    fieldnames = [
        "tree_type",
        "d",
        "phase",
        "delete_count",
        "total_deleted_so_far",
        "deletion_time_sec",
        "deleted_success_count",
        "deleted_absent_count",
        "remaining_sample_count",
        "remaining_sample_found_count",
        "height_after_delete",
        "node_count_after_delete",
        "split_count_after_delete",
        "redistribution_count_after_delete",
        "two_to_three_split_count_after_delete",
        "utilization_after_delete",
        "valid_after_delete",
        "deleted_absent_pass",
        "remaining_found_pass",
        "valid",
        "validation_message",
    ]

    write_csv(DELETION_RESULTS_PATH, rows, fieldnames)
    print_step(f"Deletion results saved to: {DELETION_RESULTS_PATH}")


def save_summary_results(insertion_results, search_results, range_results, deletion_results):
    rows = make_summary_csv_rows(
        insertion_results=insertion_results,
        search_results=search_results,
        range_results=range_results,
        deletion_results=deletion_results,
    )

    fieldnames = [
        "tree_type",
        "d",
        "record_count",
        "insert_time_sec",
        "search_query_count",
        "search_mean_time_sec",
        "search_accuracy",
        "range_low_key",
        "range_high_key",
        "range_gender_filter",
        "range_time_sec",
        "range_matched_count",
        "range_avg_gpa",
        "range_avg_height",
        "delete_10_time_sec",
        "delete_20_total_second_phase_time_sec",
        "delete_10_valid",
        "delete_20_valid",
        "split_count",
        "redistribution_count",
        "two_to_three_split_count",
        "node_count_after_insert",
        "height_after_insert",
        "utilization_after_insert",
        "height_after_20_percent_delete",
        "node_count_after_20_percent_delete",
        "utilization_after_20_percent_delete",
        "overall_pass",
    ]

    write_csv(SUMMARY_RESULTS_PATH, rows, fieldnames)
    print_step(f"Summary results saved to: {SUMMARY_RESULTS_PATH}")


def run_step_40_full_manual_experiment_with_summary():
    print_section("STEP 40: Full Manual Experiment with Summary CSV")

    print_step(f"Loading dataset from: {DATA_PATH}")
    records, key_rid_pairs, key_to_rid = load_student_records(DATA_PATH)

    print(f"Loaded records: {len(records)}")
    print(f"First key-RID pair: {key_rid_pairs[0]}")
    print(f"Last key-RID pair: {key_rid_pairs[-1]}")

    if len(records) != 100000:
        print_pass_fail(
            "Dataset size",
            False,
            f"Expected 100000 records, got {len(records)}",
        )
        return False

    print_pass_fail("Dataset size", True, "100000 records")

    print_step(
        f"Creating fixed samples with seed={RANDOM_SEED}, search_count={SEARCH_COUNT}"
    )

    search_keys, delete_10_keys, delete_20_keys, remaining_check_keys = make_fixed_samples(
        key_rid_pairs=key_rid_pairs,
        seed=RANDOM_SEED,
        search_count=SEARCH_COUNT,
    )

    print(f"Search sample size: {len(search_keys)}")
    print(f"Delete 10% sample size: {len(delete_10_keys)}")
    print(f"Additional delete 10% sample size: {len(delete_20_keys)}")
    print(f"Remaining check sample size: {len(remaining_check_keys)}")

    print_step("Computing brute-force range query result")
    brute_time, brute_stats = measure_seconds(
        brute_force_range_stats,
        records,
        RANGE_LOW_KEY,
        RANGE_HIGH_KEY,
        RANGE_GENDER_FILTER,
    )

    print(
        f"Brute-force range result: count={brute_stats['count']}, "
        f"avg_gpa={brute_stats['avg_gpa']:.9f}, "
        f"avg_height={brute_stats['avg_height']:.9f}, "
        f"time={brute_time:.6f}s"
    )

    insertion_results = []
    search_results = []
    range_results = []
    deletion_results = []

    for d in ORDERS:
        for tree_name, tree_class in TREE_CLASSES.items():
            insertion_result = run_single_insertion_experiment(
                tree_name=tree_name,
                tree_class=tree_class,
                d=d,
                records=records,
                key_rid_pairs=key_rid_pairs,
            )

            insertion_results.append(insertion_result)

            if insertion_result["valid"]:
                search_result = run_single_search_experiment(
                    insertion_result=insertion_result,
                    search_keys=search_keys,
                    key_to_rid=key_to_rid,
                )

                range_result = run_single_range_experiment(
                    insertion_result=insertion_result,
                    records=records,
                    brute_stats=brute_stats,
                )

                deletion_result_for_tree = run_deletion_experiments_for_tree(
                    insertion_result=insertion_result,
                    delete_10_keys=delete_10_keys,
                    delete_20_keys=delete_20_keys,
                    remaining_check_keys=remaining_check_keys,
                    key_to_rid=key_to_rid,
                )
            else:
                search_result = {
                    "tree_name": tree_name,
                    "d": d,
                    "query_count": len(search_keys),
                    "total_search_time": 0.0,
                    "mean_search_time": 0.0,
                    "found_count": 0,
                    "correct_count": 0,
                    "accuracy": 0.0,
                    "valid": False,
                }

                range_result = {
                    "tree_name": tree_name,
                    "d": d,
                    "low_key": RANGE_LOW_KEY,
                    "high_key": RANGE_HIGH_KEY,
                    "gender_filter": RANGE_GENDER_FILTER,
                    "range_time": 0.0,
                    "matched_count": 0,
                    "avg_gpa": 0.0,
                    "avg_height": 0.0,
                    "raw_pair_count": 0,
                    "brute_count": brute_stats["count"],
                    "brute_avg_gpa": brute_stats["avg_gpa"],
                    "brute_avg_height": brute_stats["avg_height"],
                    "valid": False,
                }

                deletion_result_for_tree = []

            search_results.append(search_result)
            range_results.append(range_result)
            deletion_results.extend(deletion_result_for_tree)

    save_insertion_results(insertion_results, record_count=len(records))
    save_search_results(search_results)
    save_range_results(range_results)
    save_deletion_results(deletion_results)
    save_summary_results(insertion_results, search_results, range_results, deletion_results)

    print_section("STEP 40 SUMMARY")

    overall_pass = True

    for insertion_result, search_result, range_result in zip(
        insertion_results,
        search_results,
        range_results,
    ):
        tree_name = insertion_result["tree_name"]
        d = insertion_result["d"]

        related_deletions = [
            result
            for result in deletion_results
            if result["tree_name"] == tree_name and result["d"] == d
        ]

        deletion_pass = (
            len(related_deletions) == 2
            and all(result["valid"] for result in related_deletions)
        )

        pair_pass = (
            insertion_result["valid"]
            and search_result["valid"]
            and range_result["valid"]
            and deletion_pass
        )

        overall_pass = overall_pass and pair_pass

        detail = (
            f"insert_time={insertion_result['insert_time']:.6f}s, "
            f"splits={insertion_result['metrics']['split_count']}, "
            f"height={insertion_result['metrics']['height']}, "
            f"search_correct={search_result['correct_count']}/{search_result['query_count']}, "
            f"range_count={range_result['matched_count']}, "
            f"deletion_pass={deletion_pass}"
        )

        print_pass_fail(f"{tree_name} d={d}", pair_pass, detail)

    for path, label in [
        (INSERTION_RESULTS_PATH, "Insertion CSV output"),
        (SEARCH_RESULTS_PATH, "Search CSV output"),
        (RANGE_RESULTS_PATH, "Range CSV output"),
        (DELETION_RESULTS_PATH, "Deletion CSV output"),
        (SUMMARY_RESULTS_PATH, "Summary CSV output"),
    ]:
        if os.path.exists(path):
            print_pass_fail(label, True, path)
        else:
            print_pass_fail(label, False, f"{path} was not created")
            overall_pass = False

    return overall_pass


def main():
    passed = run_step_40_full_manual_experiment_with_summary()

    print()
    if passed:
        print("STEP 40 OVERALL: PASS")
    else:
        print("STEP 40 OVERALL: FAIL")


if __name__ == "__main__":
    main()