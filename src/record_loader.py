import os
import pandas as pd


def load_student_records(csv_path):

    if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv__path}")

    df = pd.read_csv(csv_path)

    df.columns = df.columns.str.strip()

    print("CSV loaded successfully.")
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())

    required_columns = [
        "Student ID",
        "Name",
        "Gender",
        "GPA",
        "Height",
        "Weight",
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
        
    records = []
    key_rid_pairs = []

    for _, row in df.iterrows():
        student_id = int(row["Student ID"])

        record = {
            "student_id": student_id,
            "name": str(row["Name"]),
            "gender": str(row["Gender"]),
            "gpa": float(row["GPA"]),
            "height": float(row["Height"]),
            "weight": float(row["Weight"]),
        }

        rid = len(records)
        records.append(record)
        key_rid_pairs.append((student_id, rid))

    return records, key_rid_pairs

def validate_records(records, key_rid_pairs):

    if len(records) != 100000:
        raise ValueError(f"Expected 100000 records, but got {len(records)}")

    if len(records) != len(key_rid_pairs):
        raise ValueError(
            f"records and key_rid_pairs length mismatch: "
            f"{len(records)} vs {len(key_rid_pairs)}"
        )

    student_ids = [record["student_id"] for record in records]

    if len(student_ids) != len(set(student_ids)):
        raise ValueError("Duplicate Student IDs found")

    for key, rid in key_rid_pairs:
        if rid < 0 or rid >= len(records):
            raise ValueError(f"Invalid RID: {rid}")

        if records[rid]["student_id"] != key:
            raise ValueError(
                f"Key-RID mismatch: key={key}, "
                f"records[{rid}]['student_id']={records[rid]['student_id']}"
            )

    print("Validation: PASS")

def print_data_summary(records, key_rid_pairs):

    print("Data Summary")
    print("------------")
    print("Loaded records:", len(records))
    print("Key-RID pairs:", len(key_rid_pairs))

    if records:
        print("First record:", records[0])
        print("Last record:", records[-1])

    if key_rid_pairs:
        print("First key-RID pair:", key_rid_pairs[0])
        print("Last key-RID pair:", key_rid_pairs[-1])

if __name__ == "__main__":
    records, key_rid_pairs = load_student_records("data/student.csv")
    validate_records(records, key_rid_pairs)
    print_data_summary(records, key_rid_pairs)