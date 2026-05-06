# CSE321 Project 1: B-tree, B+ tree, and B* tree Index Structures

## 1. Project Overview

This project implements and evaluates three tree-based index structures:

- B-tree
- B+ tree
- B* tree

The index key is the `Student ID` field from `student.csv`, and the Record Identifier (RID) is the array index of each record after loading the CSV file into memory.

The experiments compare insertion performance, point search performance, range query performance, deletion performance, and structural properties across the three tree structures.

## 2. Environment

The code was tested with:

- Python 3.13.12
- WSL2 Linux
- Intel Core Ultra 7 155H
- 15 GiB RAM

No external Python packages are required.  
This project uses only the Python standard library.

Recommended execution environment:

- Linux
- WSL
- macOS terminal

Windows Git Bash may incorrectly use the Windows Store Python alias. If running `python experiments/final_experiment.py` only prints `Python` and does not execute the experiment, use WSL or a properly installed Python interpreter.

## 3. File Structure

```text
cse321-project1-btree-index/
├── data/
│   └── student.csv
├── experiments/
│   ├── final_experiment.py
│   └── experiment_utils.py
├── src/
│   ├── __init__.py
│   ├── btree.py
│   ├── bplustree.py
│   ├── bstartree.py
│   └── record_loader.py
├── results/
│   ├── insertion_results.csv
│   ├── search_results.csv
│   ├── range_results.csv
│   ├── deletion_results.csv
│   └── experiment_summary.csv
├── report/
├── README.md
├── requirements.txt
└── .gitignore
```

## 4. Implemented Index Structures

### 4.1 B-tree

The B-tree stores key-RID pairs in both internal and leaf nodes. Therefore, point search may terminate at an internal node.

Supported operations:

- Insert
- Search
- Delete
- Validation

For range query evaluation, the experiment code performs an inorder traversal because the B-tree class itself does not maintain linked leaves.

### 4.2 B+ tree

The B+ tree stores RIDs only in leaf nodes. Internal nodes store separator keys and child pointers only.

Supported operations:

- Insert
- Search
- Delete
- Range Query
- Validation

Leaf nodes are connected through `next` pointers to support efficient range scans.

### 4.3 B* tree

The B* tree is implemented as a B-tree-based structure. Internal nodes may store key-RID pairs, and search may terminate at internal nodes.

Supported operations:

- Insert
- Search
- Delete
- Range Query
- Validation

For insertion, the B* tree attempts sibling redistribution before splitting. If redistribution is not possible, it performs a 2-to-3 split.

## 5. Dataset

The dataset must be placed at:

```text
data/student.csv
```

The experiment assumes the following columns exist:

```text
Student ID, Name, Gender, GPA, Height, Weight
```

The storage model is:

```text
Key = Student ID
RID = array index of the record after loading student.csv
```

## 6. How to Clone

Clone the repository and move into the project directory:

```bash
git clone https://github.com/rlawldks112/cse321-project1-btree-index.git
cd cse321-project1-btree-index
```

## 7. How to Check Python

Before running the experiment, check that Python is correctly installed.

```bash
python --version
```

Expected output should look like:

```text
Python 3.x.x
```

If `python` is not linked to Python 3, try:

```bash
python3 --version
```

If you are using Windows Git Bash and the command only prints `Python`, your terminal is likely using the Windows Store Python alias instead of a real Python interpreter.

In that case, use WSL or install Python properly and make sure it appears in your PATH.

You can also check which Python executable is being used:

```bash
which python
type python
```

A problematic Windows Store alias may look like:

```text
/c/Users/<username>/AppData/Local/Microsoft/WindowsApps/python
```

If this happens, run the project in WSL instead.

## 8. How to Run the Final Experiment

From the project root directory, run:

```bash
python experiments/final_experiment.py
```

If your environment uses `python3` instead of `python`, run:

```bash
python3 experiments/final_experiment.py
```

This command executes all required experiments:

1. Insertion & Parameter Tuning
2. Point Search
3. Range Query
4. Deletion & Structural Integrity

The tested tree orders are:

```text
d = 3, 5, 10
```

The tested tree types are:

```text
BTree, BPlusTree, BStarTree
```

The final experiment may take several minutes because it builds and validates all three tree structures for all tested order values.

## 9. Experiment Details

### 9.1 Insertion & Parameter Tuning

For each tree type and each order `d`, all 100,000 records are inserted into an initially empty tree.

Measured metrics:

- Total insertion time
- Number of node splits
- Number of redistributions
- Number of 2-to-3 splits
- Tree height
- Number of nodes
- Node utilization

### 9.2 Point Search

The experiment randomly selects 10,000 existing Student IDs using a fixed random seed.

Measured metrics:

- Total search time
- Mean search time
- Found count
- Correct count
- Search accuracy

### 9.3 Range Query

The analytical range query is:

```text
202278651 <= Student ID <= 202419537
Gender == Male
```

The query computes:

- Number of matched records
- Average GPA
- Average Height

The tree-based result is compared with a brute-force scan over `student.csv`.

### 9.4 Deletion & Structural Integrity

The deletion experiment is performed in two phases:

1. Delete 10% of the dataset, which is 10,000 records.
2. Delete an additional 10%, resulting in 20,000 deleted records in total.

After each phase, the experiment checks:

- Deleted keys are no longer searchable.
- Sampled non-deleted keys are still searchable.
- Tree validation passes.
- Structural metrics are recorded.

## 10. Output Files

After running the final experiment, the following files are generated under `results/`:

```text
results/insertion_results.csv
results/search_results.csv
results/range_results.csv
results/deletion_results.csv
results/experiment_summary.csv
```

The main summary file is:

```text
results/experiment_summary.csv
```

This file combines the key metrics from insertion, search, range query, and deletion experiments into one table.

The CSV files are included in the repository so that the experiment results can be inspected without rerunning the full experiment.

## 11. Expected Output and Key Results

A successful run should end with:

```text
STEP 40 OVERALL: PASS
```

The summary file should contain 9 experiment rows:

```text
3 tree types × 3 order values = 9 rows
```

A successful run should satisfy:

```text
overall_pass = True for all rows
search_accuracy = 1.000000000 for all rows
delete_10_valid = True for all rows
delete_20_valid = True for all rows
```

The range query result should be identical for all tree/order combinations:

```text
range_matched_count = 10031
range_avg_gpa = 3.297161798
range_avg_height = 173.972734523
```

Representative summary values from `experiment_summary.csv`:

| Tree | d | Insert(s) | Search Avg(s) | Range(s) | Utilization | Overall |
|---|---:|---:|---:|---:|---:|---|
| BTree | 3 | 0.676765691 | 0.000007499498 | 0.109096857 | 0.672305065 | True |
| BPlusTree | 3 | 1.748843042 | 0.000005931870 | 0.059435247 | 0.713946898 | True |
| BStarTree | 3 | 2.380688248 | 0.000006672727 | 0.102692935 | 0.801127988 | True |
| BTree | 10 | 0.357719856 | 0.000006309685 | 1.528637001 | 0.678044249 | True |
| BPlusTree | 10 | 0.320040322 | 0.000003306945 | 0.031978329 | 0.714875700 | True |
| BStarTree | 10 | 0.695765051 | 0.000003676028 | 0.053563685 | 0.851100047 | True |

Runtime values may vary slightly across machines and runs. However, structural metrics, correctness results, search accuracy, range query counts, and validation results should remain consistent.

## 12. Reproducibility

The experiment uses a fixed random seed:

```text
321
```

This ensures that the same search and deletion keys are used across B-tree, B+ tree, and B* tree, enabling fair comparison.

## 13. Optional Local Tests

The directory below may contain local development tests:

```text
src/tests/
```

These files are not required to run the final experiment and are excluded from GitHub submission through `.gitignore`.

## 14. Notes

- `results/*.csv` files are included to provide the measured outputs used for analysis.
- `src/tests/` is excluded because it contains local development tests that are not required for the final experiment.
- The final experiment can be reproduced by running `python experiments/final_experiment.py` from the project root in a proper Python environment.
- If Windows Git Bash only prints `Python`, use WSL or fix the Python PATH before running the experiment.
