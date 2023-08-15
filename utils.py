import dataclasses
import json
import subprocess
from pathlib import Path
from typing import Optional


# TODO: create "ext-to-codec relation" dict as {"extension": "codec"} and select codec based on user selected extension
#  {"mp4": "libx264"}

@dataclasses.dataclass
class MediaFile:
    name: str
    width: int
    height: int
    sample_ar: str
    display_ar: str
    fps: int


def read_info(path: Path) -> Optional[dict]:
    try:
        json_s = subprocess.check_output(
            f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{path.as_posix()}"'
        )
        return json.loads(json_s)['streams'][0]
    except:  # todo: specify exceptions
        return


def get_file_info(path: Path) -> Optional[MediaFile]:
    res_dict = read_info(path)
    if res_dict:
        return MediaFile(
            name=path.name,
            width=res_dict['width'],
            height=res_dict['height'],
            sample_ar=res_dict.get('sample_aspect_ratio') or "1:1",
            display_ar=res_dict.get('display_aspect_ratio') or res_dict['width'] / res_dict['height'],
            fps=eval(str(res_dict.get('avg_frame_rate')))  # Can possibly be None
        )
    else:
        print(f"File {path.name} could not be read! Skipping...")
        return
