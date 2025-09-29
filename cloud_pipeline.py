"""One-click pipeline to convert BLF logs into JPN/US CSV bundles.

This script orchestrates the Code① (BLF -> CSV) and Code③ (CSV ->
detail CSV) steps so that a single command can convert every ``.blf``
log in a directory. The detailed CSVs are separated into ``JPN`` and
``US`` folders, and each log file gets its own sub-folder under those
regions.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List


HERE = Path(__file__).resolve().parent
CODE1_SRC = HERE / "code_1"
if str(CODE1_SRC) not in sys.path:
    sys.path.insert(0, str(CODE1_SRC))


# Lazily import Process.py so ``--help`` works even when optional
# dependencies (dpkt, etc.) are missing in the current environment.
try:
    from Process import logFileAnalyze  # type: ignore  # pylint: disable=import-error
    PROCESS_IMPORT_ERROR: Exception | None = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    logFileAnalyze = None  # type: ignore[assignment]
    PROCESS_IMPORT_ERROR = exc


if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

try:
    from code_3_run import convert_profile_message_file  # type: ignore  # pylint: disable=import-error
    CODE3_IMPORT_ERROR: Exception | None = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    convert_profile_message_file = None  # type: ignore[assignment]
    CODE3_IMPORT_ERROR = exc


DEFAULT_IDS = (
    "0x0000010A,0xCAF0054C,0xCAF0036D,0xCAF00370,0xCAF0025E,0xCAF0036A"
)


def parse_ids(ids: str) -> List[int]:
    values: List[int] = []
    for raw in ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        values.append(int(raw, 16))
    return values


def iter_blf_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.glob("*.blf")):
        if path.is_file():
            yield path


def run_code1(blf_file: Path, output_dir: Path, target_ids: List[int]) -> None:
    if logFileAnalyze is None:
        raise RuntimeError(
            "Process.py could not be imported. Install its dependencies (e.g. dpkt) before running the pipeline."
        ) from PROCESS_IMPORT_ERROR
    print(f"[code1] converting {blf_file}")
    cwd = Path.cwd()
    try:
        logFileAnalyze([str(blf_file)], target_ids, str(output_dir))
    finally:
        os.chdir(cwd)


def run_code3(profile_csv: Path, output_root: Path, message_name: str, encoding: str) -> None:
    if convert_profile_message_file is None:
        raise RuntimeError(
            "code_3_run.py could not be imported. Install its dependencies (e.g. pandas) before running the pipeline."
        ) from CODE3_IMPORT_ERROR
    print(f"[code3] refining {profile_csv}")
    convert_profile_message_file(
        profile_csv,
        message_name=message_name,
        target_root=output_root,
        output_encoding=encoding,
    )


def find_profile_csv(intermediate_dir: Path, dataset_name: str, message_name: str) -> Path:
    candidate = intermediate_dir / dataset_name / f"{message_name}.csv"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Profile CSV not found: {candidate}. Check the message name or conversion results."
    )


def process_single_file(
    blf_file: Path,
    *,
    target_ids: List[int],
    intermediate_root: Path,
    final_root: Path,
    message_name: str,
    encoding: str,
    keep_intermediate: bool,
) -> None:
    dataset_name = blf_file.stem
    intermediate_dir = intermediate_root / dataset_name
    if intermediate_dir.exists():
        shutil.rmtree(intermediate_dir)
    intermediate_dir.parent.mkdir(parents=True, exist_ok=True)

    run_code1(blf_file, intermediate_dir, target_ids)

    profile_csv = find_profile_csv(intermediate_dir, dataset_name, message_name)
    run_code3(profile_csv, final_root, message_name, encoding)

    if not keep_intermediate:
        shutil.rmtree(intermediate_dir, ignore_errors=True)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert every BLF file in <input> into region-split CSV bundles.",
    )
    parser.add_argument(
        "--input",
        default=str(HERE / "data"),
        help="Folder that contains BLF files (default: ./data)",
    )
    parser.add_argument(
        "--output",
        default=str(HERE / "cloud_outputs"),
        help="Destination root for the region folders (default: ./cloud_outputs)",
    )
    parser.add_argument(
        "--ids",
        default=DEFAULT_IDS,
        help="Comma separated list of message IDs for code① (hex values)",
    )
    parser.add_argument(
        "--message-name",
        default="Profile Message",
        help="Profile CSV base name without extension (default: 'Profile Message')",
    )
    parser.add_argument(
        "--encoding",
        default="cp932",
        help="Encoding used for the final CSV files",
    )
    parser.add_argument(
        "--workdir",
        help="Directory for intermediate code① outputs (default: <output>/_intermediate)",
    )
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Keep intermediate code① outputs instead of deleting them",
    )
    args = parser.parse_args(argv)

    input_root = Path(args.input)
    if not input_root.exists():
        print(f"[error] input directory not found: {input_root}")
        return 1

    final_root = Path(args.output)
    final_root.mkdir(parents=True, exist_ok=True)

    intermediate_root = Path(args.workdir) if args.workdir else final_root / "_intermediate"
    intermediate_root.mkdir(parents=True, exist_ok=True)

    target_ids = parse_ids(args.ids)
    if not target_ids:
        print("[error] no message IDs were provided")
        return 1

    blf_files = list(iter_blf_files(input_root))
    if not blf_files:
        print(f"[warn] no .blf files found under {input_root}")
        return 0

    for blf_file in blf_files:
        try:
            process_single_file(
                blf_file,
                target_ids=target_ids,
                intermediate_root=intermediate_root,
                final_root=final_root,
                message_name=args.message_name,
                encoding=args.encoding,
                keep_intermediate=args.keep_intermediate,
            )
        except Exception as exc:  # noqa: BLE001 - bubble up after logging
            print(f"[error] failed to process {blf_file}: {exc}")
            return 1

    print(f"[done] processed {len(blf_files)} file(s). Results stored in {final_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
