#!/usr/bin/env python
import ffmpy
import os
import sys
import pymediainfo

# video preprocessing step, will take a video and convert the video into
# different file formats (mp4 -> avi, mpeg)

# ffmpeg -i input.avi -b:v 8192k -bufsize 64k output.avi
# to check to see what ff will do, ff.cmd
# to run, ff.run()

def is_video(path):
    file_info = pymediainfo.MediaInfo.parse(path)
    for track in file_info.tracks:
        if track.track_type == "Video":
            return True
    return False


def transcode_directory(path):
    video_list = list(os.listdir(path))
    for v in video_list:
        filepath = os.path.join(path, v)
        if os.path.isfile(filepath) and is_video(filepath):
            print("Transcoding: " + filepath)
            transcode_video(filepath, 'avi')
            transcode_video(filepath, 'mpg')


def transcode_video(video_input, fmt):
    video_output = os.path.splitext(video_input)[0]
    ff = ffmpy.FFmpeg(
            inputs = {video_input: None},
            outputs = {video_output + '.' + fmt: '-b:v 8192K'}
            )
    print(ff.cmd)
    ff.run()


if __name__ == '__main__':
    if len(sys.argv) < 1 or not os.path.isdir(sys.argv[1]):
        sys.stderr.write("Must specify directory as first argument")
        sys.exit(1)

    transcode_directory(sys.argv[1])
