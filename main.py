import dataclasses
import json
import subprocess
from pathlib import Path
from typing import Optional


# TODO: заготовить мапу в виде {"extension": "codec"} и выбирать кодек автоматически в зависимости от выбранного пользователем расширения
#  {"mp4": "libx264"}


def create_from_seq(seq_path: Path,
                    ext: str,
                    codec: str = 'libx264',
                    fps: int = 24,
                    quality: str = 'normal') -> Path:
    """
    Create videofile from sequence of frames saved in .exr
    :param seq_path: Path to sequence folder
    :param ext: Output video extention
    :param codec: Output video codec
    :param fps: Output video fps
    :param quality: Output video quality
    :return: Path to output video
    """
    quality_num = 20
    match str(quality).lower():
        case "high":
            quality_num = 10
        case "normal":
            quality_num = 20
        case 'low':
            quality_num = 30
    video_path = seq_path.parent.joinpath(f"{seq_path.parent.with_suffix(ext).name}")
    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -r 24 -i "{seq_path.as_posix()}/sequence.%08d.exr" -vf fps={fps} '
        f'-crf {quality_num} -vcodec {codec} "{video_path.as_posix()}'
    )
    p.wait()

    return video_path


def split_to_seq(video_path: Path) -> Path:
    """
    Split videofile to sequence of frames with .exr extension
    :param video_path: Path to video to split
    :return:
    """
    seq_path = video_path.parent.joinpath("seq")
    if not seq_path.exists():
        seq_path.mkdir()

    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -i "{video_path.as_posix()}" '
        f'-compression 3 "{seq_path.as_posix()}/sequence.%08d.exr"'
    )
    p.wait()

    return seq_path


@dataclasses.dataclass
class VideoFile:
    name: str
    width: int
    height: int
    aspect_ratio: str
    fps: int


def file_info(path: Path) -> dict:
    json_s = subprocess.check_output(
        f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{path.as_posix()}"'
    )
    return json.loads(json_s)['streams'][0]


def video_info(path: Path) -> Optional[VideoFile]:
    try:
        res_dict = file_info(path)
        return VideoFile(
            name=path.name,
            width=res_dict['width'],
            height=res_dict['height'],
            aspect_ratio=res_dict.get('display_aspect_ratio') or "16:9",  # fallback if file has no aspect ratio tag
            fps=int(round(eval(res_dict.get('avg_frame_rate') or 24)))
        )
    except:
        print(f"File {path.name} could not be read! Skipping...")
        return


def concat_videos(output_format: str, *args: Path | str):
    """
    Concatinate any number of given videos into one. Files will be joined in given order.
    If input files have different resolutions, aspect ratios or fps, output video will select video w/
    the highest res from inputs as a "key video" and use its res and aspect ratio. For fps, it will select the
    lowest one and force it. Any videos that does not match "key video" params won't be stretched - instead it
    will remain in original size w/ blackbars added.
    Note: this works only for video stream, any audio will be dropped!
    :param output_format: Output videofile format
    :param args: Paths to videos to concatinate
    :return: Path to output video
    """
    inputs = [Path(x) for x in args]
    output_file = inputs[0].parent.joinpath('result', f'concat_output.{output_format}')

    if not output_file.parent.exists():
        output_file.parent.mkdir()

    # Skipping files that returned exception on info reading
    files_info = []
    for file in inputs:
        res = video_info(file)
        if res:
            files_info.append(res)

    # Selecting video w/ the highest resolution to be used as a key reference
    key_video = sorted(files_info, key=lambda x: x.height * x.width)[-1]

    # Selecting the lowest fps across all videos
    lowest_fps = sorted(files_info, key=lambda x: x.fps)[0].fps

    # Warning user if any videos have different properties from key video
    files_to_warn = []
    for file in files_info:
        if any([file.width != key_video.width,
                file.height != key_video.height,
                file.fps != lowest_fps,
                file.aspect_ratio != key_video.aspect_ratio]):
            files_to_warn.append(file)
    if files_to_warn:
        print(f"Following files may result in black bars or wrong aspect ratio "
              f"due to different properties from key file {key_video.name}:\n"
              f"{', '.join([x.name for x in files_to_warn])}")

    # Creating ffmpeg arguments
    input_streams = [f'-i "{x.as_posix()}"' for x in inputs]
    stream_names = [f"[v{i}]" for i in range(len(inputs))]
    filters = [
        f"[{i}:v:0]scale='min({key_video.width},iw)':'min({key_video.height},ih)':force_original_aspect_ratio=decrease,"
        f"pad={key_video.width}:{key_video.height}:-1:-1:color=black,"
        f"setsar={key_video.aspect_ratio},fps={lowest_fps}[v{i}]" for i in range(len(inputs))
    ]

    # Running ffmpeg command
    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y {" ".join(input_streams)} '
        f'-filter_complex "{";".join(filters)};{"".join(stream_names)}concat=n={len(input_streams)}:v=1[outv]" '
        f'-map "[outv]" -c:v "libx264" -crf 15 -preset slow -threads 10 {output_file.as_posix()}'
    )
    p.wait()

    return output_file


# files_to_concat = [x for x in Path(r"C:\Users\l.konstantin\Desktop\test").iterdir() if x.is_file()]
# concat_videos('mp4', *files_to_concat)

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


resize_image(Path(r"C:\Users\l.konstantin\Desktop\test\test.jpg"), (2000, 2000))
