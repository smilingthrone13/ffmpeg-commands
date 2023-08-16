import re
import subprocess
from pathlib import Path
from typing import Optional

from utils import get_file_info


def concat_videos(ext: str, videos_list: list[Path | str]) -> Optional[Path]:
    """
    Concatenate any number of given videos into one. Files will be joined in given order.
    If input files have different resolutions, aspect ratios or FPS, output video will select video w/
    the highest res from inputs as a "key video" and use its res and aspect ratio. For FPS, it will select the
    lowest one and force it. Any videos that does not match "key video" params won't be stretched - instead it
    will remain in original size w/ black bars added.
    Note: this works only for video stream, any audio will be dropped!
    :param ext: Output video file extension
    :param videos_list: List of paths to videos to concatenate
    :return: Path to output video
    """
    if not videos_list:
        print("No inputs provided!")
        return
    inputs = [Path(x) for x in videos_list]
    output_file = inputs[0].parent.joinpath('result', f'concat_output.{ext.strip(".")}')

    if not output_file.parent.exists():
        output_file.parent.mkdir()

    # Skipping files that returned exception on info reading
    files_info = []
    for file in inputs:
        res = get_file_info(file)
        if res:
            files_info.append(res)
    if not files_info:
        print("No suitable video files found!")
        return

    # Selecting video w/ the highest resolution to be used as a key reference
    key_video = sorted(files_info, key=lambda x: x.height * x.width)[-1]

    # Selecting the lowest FPS across all videos
    lowest_fps = sorted(files_info, key=lambda x: x.fps)[0].fps

    # Estimating total number of frames to be encoded - for progress bar
    total_frames = round(sum(float(x.duration) * lowest_fps for x in files_info))
    if total_frames == 0:
        total_frames = 1

    # Warning user if any videos have different properties from key video
    files_to_warn = []
    for file in files_info:
        if any([file.width != key_video.width,
                file.height != key_video.height,
                file.sample_ar != key_video.sample_ar,
                file.display_ar != key_video.display_ar]):
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
        f"setsar={key_video.sample_ar},fps={lowest_fps}[v{i}]" for i in range(len(inputs))
    ]

    cmd = f'ffmpeg -loglevel 0 -stats -y {" ".join(input_streams)} ' \
          f'-filter_complex "{";".join(filters)};{"".join(stream_names)}concat=n={len(input_streams)}:v=1[outv]" ' \
          f'-map "[outv]" -c:v "libx264" -fps_mode vfr -crf 15 -preset slow -threads 10 {output_file.as_posix()}'

    # Running ffmpeg command
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
    while True:
        stderr_chunk = p.stderr.readline().strip()

        if stderr_chunk == '' and p.poll() is not None:
            print('Videos concatenated!')
            break

        if stderr_chunk:
            match = re.search(r'frame=\s*(\d+)', stderr_chunk)
            if match:
                current_frame = int(match.group(1))
                print(f"Current progress: {current_frame / total_frames * 100:.2f}%", end='\r', flush=True)

    return output_file

# files_to_concat = [x for x in Path(r"C:\Users\l.konstantin\Desktop\test").iterdir() if x.is_file()]
# concat_videos('mp4', files_to_concat)
