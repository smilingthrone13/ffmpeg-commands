import subprocess
from pathlib import Path


def split_to_seq(video_path: Path) -> Path:
    """
    Split video file to sequence of frames with .exr extension
    :param video_path: Path to video to split
    :return:
    """
    output_file = video_path.parent.joinpath("seq")
    if not output_file.exists():
        output_file.mkdir()

    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -i "{video_path.as_posix()}" '
        f'-compression 3 "{output_file.as_posix()}/sequence.%08d.exr"'  # todo: maybe add input filename to output?
    )
    p.wait()

    return output_file
