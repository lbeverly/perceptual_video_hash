#!/usr/bin/env python
import ffmpy
import os
import pymediainfo

from .data_manager import VideoDataManager, Video


# video preprocessing step, will take a video and convert the video into
# different file formats (mp4 -> avi, mpeg)

# ffmpeg -i input.avi -b:v 8192k -bufsize 64k output.avi
# to check to see what ff will do, ff.cmd
# to run, ff.run()
################################################################################
class VideoTranscoder:
    ############################################################################
    target_formats = ['avi', 'mpg', 'mp4']

    ############################################################################
    def __init__(self, path, manager=None, force=False):
        self._path = path
        self._manager = manager
        if self._manager is None:
            self._manager = VideoDataManager()
        self.force = force

        return

    ############################################################################
    def is_video(self, path):
        file_info = pymediainfo.MediaInfo.parse(path)
        for track in file_info.tracks:
            if track.track_type == "Video":
                return True
        return False

    ############################################################################
    def run(self):
        video_list = list(os.listdir(self._path))

        for v in video_list:
            filepath = os.path.join(self._path, v)
            if os.path.isfile(filepath) and self.is_video(filepath):
                if (not filepath.endswith('smaller.mp4')
                        and not filepath.endswith('bigger.mp4')):
                    for fmt in self.target_formats:
                        self.transcode_video(filepath, fmt)

                    self.transcode_video(filepath, 'mp4',
                                         opts='-vf scale=iw*0.9375:ih*0.9375',
                                         output_suffix='_smaller')
                    self.transcode_video(filepath, 'mp4',
                                         opts='-vf scale=iw*1.0625:ih*1.0625',
                                         output_suffix='_bigger')

        return

    ############################################################################
    def _video_encoding_cmd(self, video_input, fmt, opts='', output_suffix=''):
        video_name, inputfmt = os.path.splitext(video_input)
        inputfmt = inputfmt.replace('.', '')
        video_basename = os.path.basename(video_name)
        video_dirname = os.path.dirname(video_name)
        setdao = self._manager.videoset_dao
        vdao = self._manager.video_dao
        output_name = video_basename + output_suffix

        if inputfmt == fmt and output_suffix == '':
            return None

        if not self.force:
            video = vdao.video_by_name_and_format(output_name, fmt)
            if video is not None:
                return None

        video_set_r = []

        def add_input_video():
            video = vdao.add_video_if_new(Video(video_basename, inputfmt))
            video_set_r.append(setdao.add_video_to_set(video))

        def add_output_video():
            if len(video_set_r) == 0:
                raise RuntimeError('must call add_input_video before ' +
                                   'add_output_video')
            video_set = video_set_r[0]
            video = vdao.add_video_if_new(Video(output_name, fmt))
            setdao.add_video_to_set(video, video_set)

        cmd = ffmpy.FFmpeg(
                inputs={video_input: None},
                outputs={os.path.join(video_dirname, output_name) +
                         '.' + fmt: opts +
                         ' -b:v 8M -maxrate 10M -bufsize 8M -an'}
                )

        cmd.add_input_video = add_input_video
        cmd.add_output_video = add_output_video
        return cmd

    ############################################################################
    def transcode_video(self, video_input, fmt, opts='', output_suffix=''):
        cmd = self._video_encoding_cmd(video_input, fmt, opts, output_suffix)
        if cmd is not None:
            print(cmd.cmd)
            cmd.add_input_video()
            print("Transcoding: " + video_input)
            cmd.run()
            cmd.add_output_video()
        return
