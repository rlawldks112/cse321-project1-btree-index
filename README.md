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

- Python 3.x
- No external Python packages required
- Linux / WSL / macOS compatible shell environment

The implementation uses only the Python standard library.

## 3. File Structure

```text
cse321_project1/
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

## 6. How to Run the Final Experiment

From the project root directory, run:

```bash
python experiments/final_experiment.py
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

## 7. Experiment Details

### 7.1 Insertion & Parameter Tuning

For each tree type and each order `d`, all 100,000 records are inserted into an initially empty tree.

Measured metrics:

- Total insertion time
- Number of node splits
- Number of redistributions
- Number of 2-to-3 splits
- Tree height
- Number of nodes
- Node utilization

### 7.2 Point Search

The experiment randomly selects 10,000 existing Student IDs using a fixed random seed.

Measured metrics:

- Total search time
- Mean search time
- Found count
- Correct count
- Search accuracy

### 7.3 Range Query

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

### 7.4 Deletion & Structural Integrity

The deletion experiment is performed in two phases:

1. Delete 10% of the dataset, which is 10,000 records.
2. Delete an additional 10%, resulting in 20,000 deleted records in total.

After each phase, the experiment checks:

- Deleted keys are no longer searchable.
- Sampled non-deleted keys are still searchable.
- Tree validation passes.
- Structural metrics are recorded.

## 8. Output Files

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

## 9. Reproducibility

The experiment uses a fixed random seed:

```text
321
```

This ensures that the same search and deletion keys are used across B-tree, B+ tree, and B* tree, enabling fair comparison.

## 10. Optional Local Tests

The directory below may contain local development tests:

```text
src/tests/
```

These files are not required to run the final experiment and are excluded from GitHub submission through `.gitignore`.

## 11. Notes

- `results/*.csv` files are included to provide the measured outputs used for analysis.
- `src/tests/` is excluded because it contains local development tests that are not required for the final experiment.
- The final experiment can be reproduced by running `python experiments/final_experiment.py` from the project root.