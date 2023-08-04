import subprocess
from pathlib import Path


def resize_image(image_path: Path, resolution: tuple[int, int]) -> Path:
    """
    Resize image to given resolution keeping original aspect ratio.
    If current resolution is lower than desired, does not upscale.
    :param image_path: Path to image to resize
    :param resolution: Target resolution as "(width, height)"
    :return: Path to resized image
    """
    output_file = image_path.with_name(
        f"{image_path.stem}_{'x'.join([str(x) for x in list(resolution)])}{image_path.suffix}"
    )

    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -i "{image_path.as_posix()}" '
        f'-vf "scale=w={resolution[0]}p:h={resolution[1]}:force_original_aspect_ratio=decrease:force_divisible_by=2" '
        f'"{output_file.as_posix()}"'
    )
    p.wait()

    return output_file

# resize_image(Path(r"C:\Users\l.konstantin\Desktop\test\test.jpg"), (300, 300))
