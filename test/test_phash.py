import unittest
import tempfile
import os
from perceptual_hashing.video_hashing import PHash, VideoHasher
from perceptual_hashing.data_manager import VideoDataManager, Video, Hash


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
    def test_video_hashmethod_lookup(self):
        cl = VideoHasher.get_hashmethod_class(PHash.hash_type())
        self.assertEqual(PHash, cl)

    ############################################################################
    def test_video_hasher(self):
        m = VideoDataManager(os.path.join(self.tempdir, 'test.db'))
        ph = PHash(self.tempdir, m)
        ph._run_phash = lambda f: 123456789

        for n in range(10):
            filename = 'file{}'.format(n)
            fmt = 'mp4'
            basepath = os.path.join(self.tempdir, filename)
            with open('{}.{}'.format(basepath, fmt), 'w') as fd:
                fd.write("Dummy file")
            m.video_dao.add_video(Video(filename, fmt))

        ph.run()

        for n in range(10):
            filename = 'file{}'.format(n)
            fmt = 'mp4'
            v = m.video_dao.video_by_name_and_format(filename, fmt)
            self.assertIsNotNone(v)
            self.assertEqual(len(v.hash_values), 1)
            self.assertIn(ph.hash_type(), v.hash_values)
            self.assertEqual(v.hash_values[ph.hash_type()],
                             Hash('phash-video', '123456789', 1))

        return
