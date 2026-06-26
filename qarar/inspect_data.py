"""Step 0: inspect every CSV in ./data/ before building downstream logic."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    if not DATA_DIR.exists():
        raise SystemExit(f"Data directory not found: {DATA_DIR}")

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No CSV files found in {DATA_DIR}")

    for path in csv_files:
        print("=" * 72)
        print(f"FILE: {path.name}")
        df = pd.read_csv(path)
        print(f"SHAPE: {df.shape}")
        print("DTYPES:")
        print(df.dtypes.to_string())
        print("\nHEAD(3):")
        print(df.head(3).to_string())
        print()


if __name__ == "__main__":
    main()
