import argparse
import sys
import os
from pathlib import Path
import code_3_run as runner
def main():
    ap = argparse.ArgumentParser(
        description="Launch code_3_run.py with explicit input root."
    )
    ap.add_argument(
        "--input", required=True,
        help="Root folder that contains 'Profile Message.csv' (JPN/US output root)"
    )
    ap.add_argument(
        "--message-name", default="Profile Message",
        help="File name (without .csv). Default: 'Profile Message'"
    )
    args = ap.parse_args()
    runner.csv_save_path = args.input
    runner.message_file_name = args.message_name
    if not Path(args.input).exists():
        print(f"[ERROR] input not found: {args.input}")
        return 1
    return runner.main()

if __name__ == "__main__":
    sys.exit(main())
