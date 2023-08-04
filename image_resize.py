import subprocess
from pathlib import Path
from typing import Optional


def resize_image(image_path: Path, resolution: tuple[int, int]) -> Optional[Path]:
    """
    Resize image to given resolution keeping original aspect ratio.
    If current resolution is lower than desired, does not upscale.
    :param image_path: Path to image to resize
    :param resolution: Target resolution as "(width, height)"
    :return: Path to resized image
    """
    if type(resolution) != tuple or len(resolution) != 2 or not all(isinstance(x, int) for x in resolution):
        print("Bad target resolution specified!")
        return

    width, height = resolution
    output_file = image_path.with_name(f"{image_path.stem}_{width}'x'{height}{image_path.suffix}")

    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -i "{image_path.as_posix()}" '
        f'-vf "scale=w={width}p:h={height}:force_original_aspect_ratio=decrease:force_divisible_by=2" '
        f'"{output_file.as_posix()}"'
    )
    p.wait()

    return output_file

# resize_image(Path(r"C:\Users\l.konstantin\Desktop\test\test.jpg"), (300, 300))
