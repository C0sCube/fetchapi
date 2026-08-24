import os
from pathlib import Path

from programs.utils import Helper

# __file__ is the current script path (e.g., 'root/app/script.py')
current_file = Path(__file__).resolve()
# .parent gets 'app', and the next .parent gets 'root'
ROOT_DIR = current_file.parent.parent

# .name extracts only the folder string (e.g., 'root')
ROOT_DIR_NAME = ROOT_DIR.name
pth = "paths.json5"


utils = Helper()


config = utils.load_json5(pth)
SECRET_KEY_GOOGLE = config["path_google_key"]
DOCUMENT_AI_PROJECT = (
    "projects/502266563041/" "locations/us/" "processors/a75509e926783125"
)
