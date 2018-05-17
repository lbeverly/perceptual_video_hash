import unittest
import tempfile
import os
from perceptual_hashing.video_preprocessing import VideoTranscoder
from perceptual_hashing.data_manager import VideoDataManager


class testcase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        return

    def tearDown(self):
        for f in os.listdir(self.tempdir):
            os.unlink('{}/{}'.format(self.tempdir, f))
        os.rmdir(self.tempdir)
        return

    def verify_inout(self, m, cmd, name, infmt, outfmt):
        cmd.add_input_video()
        v = m.video_dao.video_by_name_and_format(name, infmt)
        self.assertIsNotNone(v)

        v = m.video_dao.video_by_name_and_format(name, outfmt)
        self.assertIsNone(v)

        cmd.add_output_video()
        v = m.video_dao.video_by_name_and_format(name, outfmt)
        self.assertIsNotNone(v)
        return

    def test_video_encoding_cmd(self):
        m = VideoDataManager(os.path.join(self.tempdir, 'test.db'))
        vt = VideoTranscoder(self.tempdir, m)
        cmd = vt._video_encoding_cmd('/some/path/to/foobar.mp4', 'avi')
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.cmd,
                         'ffmpeg -i /some/path/to/foobar.mp4 ' +
                         '-b:v 8M -maxrate 10M -bufsize 8M -an ' +
                         '/some/path/to/foobar.avi')

        self.verify_inout(m, cmd, 'foobar', 'mp4', 'avi')
        cmd = vt._video_encoding_cmd('/some/path/to/foobar.mp4', 'mpg')
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.cmd,
                         'ffmpeg -i /some/path/to/foobar.mp4 ' +
                         '-b:v 8M -maxrate 10M -bufsize 8M -an ' +
                         '/some/path/to/foobar.mpg')

        self.verify_inout(m, cmd, 'foobar', 'mp4', 'mpg')

    def test_video_set(self):
        m = VideoDataManager(os.path.join(self.tempdir, 'test.db'))
        vt = VideoTranscoder(self.tempdir, m)

        for fmt in ['avi', 'mpg', 'mov', 'mp4']:
            cmd = vt._video_encoding_cmd('/some/path/to/foobar.mp4', fmt)
            if cmd is not None:
                cmd.add_input_video()
                cmd.add_output_video()

        v = m.video_dao.video_by_name_and_format('foobar', 'mp4')
        self.assertIsNotNone(v)

        s = m.videoset_dao.get_video_set(v)
        self.assertIsNotNone(s)
        self.assertEqual(len(s.videos), 4)
