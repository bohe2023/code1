from multiprocessing import freeze_support, Lock
from typing import Iterable, List, Optional

from GlobalVar import setProgramDir, setResource, setSomeIPHead
from Process import logFileAnalyze, showGUI

import sys
from os import getcwd, listdir
from os.path import isfile, join

ANALYZER_VERSION = '2.78'


def _normalize_folder_path(path: str) -> str:
    """Ensure folder-like CLI parameters end with a backslash."""

    if path and path[-1] != '\\':
        return path + '\\'
    return path


def _collect_target_files(target_folder: str, target_file_list: Optional[List[str]]) -> Optional[List[str]]:
    """Return the absolute paths of files that should be processed."""

    if target_folder is None:
        return target_file_list

    if target_file_list is None:
        target_file_list = [
            f
            for f in listdir(target_folder)
            if isfile(join(target_folder, f))
            and (
                f.endswith('.pcap')
                or f.endswith('.pcapng')
                or f.endswith('.blf')
                or f.endswith('.asc')
            )
        ]

    return [target_folder + f for f in target_file_list]


def _parse_message_ids(param: str) -> List[int]:
    """Convert hexadecimal message identifiers to integers."""

    return [int(x, 16) for x in param.split(',')]


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Entry point compatible with setuptools console scripts."""

    freeze_support()  # for multiprocess with pyinstaller

    if argv is None:
        argv = sys.argv[1:]

    argv_list = list(argv)

    resource = {'mutex': Lock()}
    setResource(resource)  # 変数共有のため
    setProgramDir(getcwd())

    target_folder: Optional[str] = None
    target_file_list: Optional[List[str]] = None
    target_message_id: Optional[List[int]] = None
    output_folder: Optional[str] = None

    try:
        arg_index = 0
        while arg_index < len(argv_list):
            command = argv_list[arg_index]
            if arg_index + 1 >= len(argv_list):
                print('Invalid argment')
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
                print('Invalid argment')
                return 1

            arg_index += 2

        target_file_list = _collect_target_files(target_folder, target_file_list)
    except Exception:
        return 1

    showGUI('  v {0}  '.format(ANALYZER_VERSION))
    logFileAnalyze(target_file_list, target_message_id, output_folder)
    print('All complete. It is OK to close.')
    return 0


# -----------------------------------------------#
# ----   Main                                ----#
# -----------------------------------------------#
if __name__ == '__main__':
    sys.exit(main())
