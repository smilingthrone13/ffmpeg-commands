import subprocess
from pathlib import Path

from utils import get_file_info


def create_from_seq(seq_path: Path,
                    ext: str,
                    user_fps: int = None,
                    codec: str = 'libx264',  # todo: switch to automatic codec selection based on output extension?
                    quality: str = 'normal') -> Path:
    """
    Create videofile from sequence of frames saved in .exr.
    Output FPS is selected automatically if not specified by user.
    :param seq_path: Path to sequence folder
    :param ext: Output video extention
    :param user_fps: Output video FPS
    :param codec: Output video codec
    :param quality: Output video quality
    :return: Path to output video
    """
    # Selecting output videofile quality
    quality_num = 20
    match str(quality).lower():
        case "high":
            quality_num = 10
        case "normal":
            quality_num = 20
        case 'low':
            quality_num = 30

    # Selecting output file FPS. 1st priority is user input, 2nd is autodetect.
    fps = user_fps
    if not fps:
        seq_info = get_file_info(seq_path)
        if seq_info and seq_info.fps:
            fps = seq_info.fps
        else:
            fps = 24  # fallback option
            print(f"Couldn't select FPS automatically and got no user-specified value. "
                  f"Using fallback {fps} FPS option.")

    output_file = seq_path.parent.joinpath(f"{seq_path.parent.with_suffix(ext).name}")
    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -r {fps} -i "{seq_path.as_posix()}/sequence.%08d.exr" '
        f'-crf {quality_num} -vcodec {codec} "{output_file.as_posix()}'
    )
    p.wait()

    return output_file
