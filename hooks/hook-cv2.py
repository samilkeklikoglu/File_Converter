"""Collect OpenCV without its unused video/FFmpeg runtime."""

import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# pdf2docx uses OpenCV's matrix and image-processing APIs. It never opens or
# writes video, so the separately loaded 30 MB FFmpeg DLL is unnecessary.
hiddenimports = ["numpy", "cv2.cv2"]
hiddenimports += collect_submodules(
    "cv2",
    filter=lambda name: name != "cv2.load_config_py2",
)
excludedimports = ["cv2.load_config_py2"]
datas = collect_data_files(
    "cv2",
    include_py_files=True,
    includes=[
        "config.py",
        f"config-{sys.version_info[0]}.{sys.version_info[1]}.py",
        "config-3.py",
        "load_config_py3.py",
    ],
)
module_collection_mode = "py"
