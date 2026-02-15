# Imports
from pathlib import Path


def find_project_root(marker_file='pyproject.toml'):
    srch_dir = Path(__file__).resolve().parent
    itr = 10  # Specify max directory iterations
    for i in range(itr):
        for fp in Path(srch_dir).iterdir():
            if marker_file.lower() in str(fp.name).lower():
                return Path(fp).parent
        srch_dir = Path(srch_dir).parent
    
    return None
            