import re
import subprocess
from pathlib import Path
from typing import Optional

from utils import get_file_info


def create_from_seq(seq_path: Path,
                    out_ext: str,
                    user_fps: float = None,
                    codec: str = 'libx264',  # todo: switch to automatic codec selection based on output extension?
                    quality: str = 'normal') -> Optional[Path]:
    """
    Create videofile from sequence of frames saved in .exr.
    Output FPS is selected automatically if not specified by user.
    :param seq_path: Path to sequence folder
    :param out_ext: Output video extention
    :param user_fps: Output video FPS
    :param codec: Output video codec
    :param quality: Output video quality
    :return: Path to output video
    """
    seq_path = Path(seq_path)
    if not seq_path.exists():
        print("Invalid input path!")
        return

    # Selecting output videofile quality
    quality_num = 15
    match str(quality).lower():
        case "high":
            quality_num = 8
        case "normal":
            quality_num = 15
        case 'low':
            quality_num = 30

    # Selecting sequence filename mask
    pattern = re.compile(r"(.*)\.(\d+)\.(.*)", re.IGNORECASE)
    name, num_len, input_ext = None, None, None
    for file in sorted(seq_path.iterdir()):
        match = pattern.match(file.name)
        if match:
            name, num_len, input_ext = match.groups()
            num_len = len(num_len)  # Number of digits in frame name
            input_ext = input_ext.split('.')[0]
            break
    if name and num_len and input_ext:
        filename = sorted(seq_path.glob(f"{name}.[0-9]*.{input_ext}"))
        if filename:
            filename = filename[0]
        else:
            print("No suitable sequence frames found in selected directory!")
            return
    else:
        print("No suitable sequence frames found in selected directory!")
        return

    # Selecting output file FPS. 1st priority is user input, 2nd is autodetect.
    fps = user_fps
    if not fps:
        seq_info = get_file_info(filename)
        if seq_info and seq_info.fps:
            fps = seq_info.fps
        else:
            fps = 24  # fallback option
            print(f"Couldn't select FPS automatically and got no user-specified value. "
                  f"Using fallback {fps} FPS option.")

    output_file = seq_path.parent.joinpath(f"{seq_path.name}.{out_ext.strip('.')}")

    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -r {fps} -i "{seq_path.as_posix()}/{name}.%0{num_len}d.{input_ext}" '
        f'-crf {quality_num} -vcodec {codec} -preset slow -threads 10 "{output_file.as_posix()}'
    )
    p.wait()

    return output_file

# print(create_from_seq(Path(r"C:\Users\l.konstantin\Desktop\test\blood_mist_shoot001"),
#                       out_ext='mp4',
#                       quality='high'))
