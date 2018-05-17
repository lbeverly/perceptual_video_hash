import unittest
import tempfile
import os
from perceptual_hashing.video_hashing import PHash
from perceptual_hashing.data_manager import VideoDataManager, Video, VideoSet


################################################################################
class testcase(unittest.TestCase):
    ############################################################################
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        return

    ############################################################################
    def tearDown(self):
        for f in os.listdir(self.tempdir):
            os.unlink('{}/{}'.format(self.tempdir, f))
        os.rmdir(self.tempdir)
        return

    ############################################################################
    #def test_




