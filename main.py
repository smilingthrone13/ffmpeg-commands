import dataclasses
import json
import subprocess
from pathlib import Path
from typing import Optional


# TODO: заготовить мапу в виде {"extension": "codec"} и выбирать кодек автоматически в зависимости от выбранного пользователем расширения


def create_from_seq(seq_path: Path,
                    ext: str,
                    codec: str = 'libx264',  # todo добавить проверку кодеков?
                    fps: int = 24,
                    quality: str = 'normal') -> Path:
    quality_num = 20
    match str(quality).lower():
        case "high":
            quality_num = 10
        case "normal":
            quality_num = 20
        case 'low':
            quality_num = 30
    video_path = seq_path.parent.joinpath(f"{seq_path.parent.name}.{ext}")
    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y -r 24 -i "{seq_path.as_posix()}/sequence.%08d.exr" -vf fps={fps} '
        f'-crf {quality_num} -vcodec {codec} "{video_path.as_posix()}')
    p.wait()

    return video_path


def split_to_seq(video_path: Path) -> Path:
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
    json_s = subprocess.check_output(f'ffprobe -v quiet -show_streams -select_streams v:0 -of json "{path.as_posix()}"')
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
    inputs = [Path(x) for x in args]

    # Skipping files that returned exception on info reading
    files_info = []
    for file in inputs:
        res = video_info(file)
        if res:
            files_info.append(res)

    # Selecting video w/ the highest resolution to be used as a key reference
    files_info.sort(key=lambda x: x.height * x.width)
    key_video = files_info[-1]

    # Selecting the lowest fps across all videos
    files_info.sort(key=lambda x: x.fps)
    lowest_fps = files_info[0].fps

    # Warning user if any videos have different properties from key video
    for file in files_info:
        if any([file.width != key_video.width,
                file.height != key_video.height,
                file.fps != lowest_fps,
                file.aspect_ratio != key_video.aspect_ratio]):
            print(f"File {file.name} may result in black bars or wrong aspect ratio "
                  f"due to different properties from key file {key_video.name}!")

    # Creating ffmpeg arguments
    input_streams = [f"-i {x.as_posix()}" for x in inputs]
    stream_names = [f"[v{i}]" for i in range(len(inputs))]
    filters = [
        f"[{i}:v:0]scale='min({key_video.width},iw)':'min({key_video.height},ih)':force_original_aspect_ratio=decrease,"
        f"pad={key_video.width}:{key_video.height}:-1:-1:color=black,"
        f"setsar={key_video.aspect_ratio},fps={lowest_fps}[v{i}]" for i in range(len(inputs))
    ]
    output_file = inputs[0].parent.joinpath('result', f'concat_output.{output_format}')

    if not output_file.parent.exists():
        output_file.parent.mkdir()

    p = subprocess.Popen(
        f'ffmpeg -loglevel 0 -y {" ".join(input_streams)} '
        f'-filter_complex "{";".join(filters)};{"".join(stream_names)}concat=n={len(input_streams)}:v=1[outv]" '
        f'-map "[outv]" -c:v "libx264" -crf 15 -preset slow -threads 10 {output_file.as_posix()}'
    )
    p.wait()

    return output_file


files_to_concat = [x for x in Path(r"C:\Users\l.konstantin\Desktop\test").iterdir() if x.is_file()]
concat_videos('mp4', *files_to_concat)
