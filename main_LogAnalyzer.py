from multiprocessing import freeze_support, Lock
from typing import Iterable, List, Optional
from GlobalVar import setProgramDir, setResource, setSomeIPHead
import sys
import os
from os import getcwd, listdir
from os.path import isfile, join

ANALYZER_VERSION = '2.78'


def _normalize_folder_path(path: str) -> str:
    """Ensure folder-like CLI parameters end with a separator."""
    if path and not path.endswith(os.sep):
        return path + os.sep
    return path


def _collect_target_files(target_folder: str, target_file_list: Optional[List[str]]) -> Optional[List[str]]:
    """Return the absolute paths of files that should be processed."""
    if target_folder is None:
        return target_file_list

    if target_file_list is None:
        target_file_list = [
            f for f in listdir(target_folder)
            if isfile(join(target_folder, f))
            and f.lower().endswith(('.pcap', '.pcapng', '.blf', '.asc'))
        ]

    return [join(target_folder, f) for f in target_file_list]


def _parse_message_ids(param: str) -> List[int]:
    """Convert hexadecimal message identifiers to integers."""
    return [int(x, 16) for x in param.split(',')]


def safe_import_process():
    """Try to import Process.showGUI (skip tkinter in headless)."""
    try:
        from Process import logFileAnalyze, showGUI
        return logFileAnalyze, showGUI
    except Exception:
        from Process import logFileAnalyze
        def showGUI(text):
            print(f"[no GUI available] {text}")
        return logFileAnalyze, showGUI


def main(argv: Optional[Iterable[str]] = None) -> int:
    freeze_support()
    if argv is None:
        argv = sys.argv[1:]

    argv_list = list(argv)

    resource = {'mutex': Lock()}
    setResource(resource)
    setProgramDir(getcwd())

    target_folder = None
    target_file_list = None
    target_message_id = None
    output_folder = None

    try:
        arg_index = 0
        while arg_index < len(argv_list):
            command = argv_list[arg_index]
            if arg_index + 1 >= len(argv_list):
                print('Invalid argument')
                return 1

            param = argv_list[arg_index + 1]
            if command == '-d':
                target_folder = _normalize_folder_path(param.strip())
            elif command == '-f':
                target_file_list = [x.strip() for x in param.split(',')]
            elif command == '-t':
                target_message_id = _parse_message_ids(param)
            elif command == '-o':
                output_folder = _normalize_folder_path(param.strip())
            elif command == '-someip':
                setSomeIPHead(int(param))
            else:
                print('Invalid argument')
                return 1
            arg_index += 2

        target_file_list = _collect_target_files(target_folder, target_file_list)
    except Exception as e:
        print(f'Argument parse error: {e}')
        return 1

    # ✅ Safe import
    logFileAnalyze, showGUI = safe_import_process()

    showGUI(f'v {ANALYZER_VERSION}')
    logFileAnalyze(target_file_list, target_message_id, output_folder)
    print('All complete. It is OK to close.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
