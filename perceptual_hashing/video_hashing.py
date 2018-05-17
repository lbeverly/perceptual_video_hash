#!/usr/bin/env python
import os
import subprocess

from .data_manager import VideoDataManager, Hash, VideoDistance
from .video_hamming_distance import hamming_distance

VIDEO_FORMATS = set(['avi', 'mpg', 'mov', 'mp4', 'mkv', 'wmv', 'flv', 'ogv',
                     'webm', 'vob', 'qt', 'm4v', 'mpv', '3gp', 'f4v'])


################################################################################
class VideoHasher:
    '''
    video hashing experiment part 1
    read in videos
    compute hash (outside modules)
    save video and hash
    '''

    ############################################################################
    __found_hashmethod_classes = None

    ############################################################################
    def __init__(self, path, manager=None, force=False):
        self.path = path
        self.force = force
        self._manager = manager
        if self._manager is None:
            self._manager = VideoDataManager()
        return

    ############################################################################
    @classmethod
    def find_all_subclasses(klass, cls=None):
        if cls is None:
            cls = klass
        found = list(cls.__subclasses__())
        for sc in cls.__subclasses__():
            found.extend(klass.find_all_subclasses(sc))
        return found

    ############################################################################
    @classmethod
    def get_hashmethod_class(cls, method):
        if cls.__found_hashmethod_classes is None:
            cls.__found_hashmethod_classes = {}
            for sc in cls.find_all_subclasses():
                cls.__found_hashmethod_classes[sc.hash_type()] = sc
        return cls.__found_hashmethod_classes[method]

    ############################################################################
    @classmethod
    def hash_type(self):
        raise NotImplementedError('hash_type')

    ############################################################################
    def hash_video(self, path, video):
        raise NotImplementedError('hash_video')

    ############################################################################
    def store_hash(self, video, hash_number):
        h = Hash(self.hash_type(), hash_number)
        video.hash_values.update({self.hash_type(): h})
        self._manager.video_dao.add_video_hashes(video)
        return

    ############################################################################
    def get_video(self, filename):
        video_name, fmt = os.path.splitext(filename)
        video_name = os.path.basename(video_name)
        fmt = fmt.replace('.', '')
        vdao = self._manager.video_dao
        video = vdao.video_by_name_and_format(video_name, fmt)

        if video is None:
            raise RuntimeError("Cannot hash a video that hasn't been added " +
                               "previously: {}".format(filename))
        return video

    ############################################################################
    def is_video_already_hashed(self, video):
        # if forced, we don't care if it's been hashed
        if self.force:
            return False

        if video.hash_values.get(self.hash_type()) is not None:
            return True
        return False

    ############################################################################
    def run(self):
        video_list = list(os.listdir(self.path))
        for v in video_list:
            if os.path.splitext(v)[1].replace('.', '') not in VIDEO_FORMATS:
                continue
            video = self.get_video(v)
            if self.is_video_already_hashed(video):
                continue
            filepath = os.path.join(self.path, v)
            self.hash_video(filepath, video)
        return


################################################################################
class PHash(VideoHasher):
    ############################################################################
    @classmethod
    def calculate_distance(cls, video1, video2):
        hash_id = video1.hash_values[cls.hash_type()].id
        v1 = video1.hash_values[cls.hash_type()].value
        v2 = video2.hash_values[cls.hash_type()].value
        distance = hamming_distance(v1, v2)
        return VideoDistance(video1, video2, hash_id, distance)

    ############################################################################
    @classmethod
    def hash_type(cls):
        return 'phash-video'

    ############################################################################
    @classmethod
    def max_threshold(cls):
        return 64

    ############################################################################
    def _run_phash(self, filepath):
        process = subprocess.Popen(["./phash", filepath],
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE)

        output, errs = process.communicate()
        if len(errs) > 0:
            raise RuntimeError(errs)

        if len(output) == 0:
            raise RuntimeError('No output from phash: on {}'.format(filepath))

        return int(output)

    ############################################################################
    def hash_video(self, filepath, video):
        hash_number = self._run_phash(filepath)
        self.store_hash(video, hash_number)
        return
