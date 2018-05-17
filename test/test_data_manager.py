import unittest
import tempfile
import os
from perceptual_hashing.data_manager import VideoDataManager, Video, Hash
from perceptual_hashing.data_manager import VideoDistance


class testcase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        return

    def tearDown(self):
        for f in os.listdir(self.tempdir):
            os.unlink('{}/{}'.format(self.tempdir, f))
        os.rmdir(self.tempdir)
        return

    def test_schema(self):
        try:
            VideoDataManager(self.tempdir + '/testdata.db')
        except Exception as err:
            self.fail(err)

    def test_videodao_add_video(self):
        m = VideoDataManager(self.tempdir + '/testdata.db')
        dao = m.video_dao
        v = dao.add_video(Video("foobar", "baz"))
        self.assertEqual(v.name, "foobar")
        self.assertEqual(v.format, "baz")
        self.assertIsNotNone(v.id)
        return m

    def test_get_nonexisting_videos_by_name(self):
        m = VideoDataManager(self.tempdir + '/testdata.db')
        dao = m.video_dao
        v = dao.videos_by_name("nonexistent", "nope")
        self.assertListEqual(v, [])

    def test_videodao_add_video_hash(self):
        m = self.test_videodao_add_video()
        dao = m.video_dao
        v = dao.videos_by_name("foobar", "baz")[0]
        v.hash_values["FOOMETHOD"] = Hash("FOOMETHOD", 123456789)

        nv = dao.add_video_hashes(v)
        self.assertEqual(v, nv)

        v.hash_values["BARMETHOD"] = Hash('BARMETHOD', 987654321)
        nnv = dao.add_video_hashes(v)
        self.assertEqual(v, nnv)

    def test_get_video_set_empty(self):
        m = self.test_videodao_add_video()
        vdao = m.video_dao
        v = vdao.videos_by_name("foobar", "baz")[0]

        setdao = m.videoset_dao
        s = setdao.get_video_set(v)

        self.assertIsNone(s)

    def test_add_video_to_set(self):
        m = self.test_videodao_add_video()
        vdao = m.video_dao
        v = vdao.videos_by_name("foobar", "baz")[0]

        setdao = m.videoset_dao
        s = setdao.get_video_set(v)
        self.assertIsNone(s)
        s = setdao.add_video_to_set(v)
        self.assertIsNotNone(s)
        self.assertEqual(len(s.videos), 1)
        self.assertEqual(list(s.videos)[0], v)
        s = setdao.add_video_to_set(v)
        self.assertIsNotNone(s)
        self.assertEqual(len(s.videos), 1)
        self.assertEqual(list(s.videos)[0], v)

    def test_add_multiple_videos_to_set(self):
        m = self.test_videodao_add_video()
        vdao = m.video_dao
        setdao = m.videoset_dao

        v1 = vdao.videos_by_name("foobar", "baz")[0]
        v2 = vdao.add_video(Video('fred', 'fred'))
        s = setdao.add_video_to_set(v1)
        s = setdao.add_video_to_set(v2, s)

        self.assertEqual(len(s.videos), 2)

    def test_get_video_set(self):
        m = self.test_videodao_add_video()
        vdao = m.video_dao
        v = vdao.video_by_name_and_format("foobar", "baz")
        self.assertIsNotNone(v)

        s1 = m.videoset_dao.add_video_to_set(v)
        self.assertIsNotNone(s1)

        s2 = m.videoset_dao.get_video_set(v)
        self.assertIsNotNone(s2)
        self.assertEqual(s1, s2)

    def test_get_all_videos(self):
        m = VideoDataManager(self.tempdir + '/testdata.db')
        dao = m.video_dao
        v1 = dao.add_video(Video("foobar", "baz"))
        v2 = dao.add_video(Video("foobar", "quux"))
        v3 = dao.add_video(Video("baz", "quux"))

        videos = sorted(dao.all_videos())
        self.assertListEqual(videos, sorted([v1, v2, v3]))

    def test_distances(self):
        m = VideoDataManager(self.tempdir + '/testdata.db')
        vdao = m.video_dao
        hdao = m.hash_dao
        ddao = m.distance_dao
        method_id = hdao.get_hash_method_by_name('foobar-method')

        v1 = vdao.add_video(Video("foobar", "baz"))
        v2 = vdao.add_video(Video("foobar", "quux"))
        v3 = vdao.add_video(Video("baz", "quux"))

        vd1 = VideoDistance(v1, v2, method_id, 12345)
        ddao.add_distance(vd1)
        vd2 = VideoDistance(v2, v3, method_id, 54321)
        ddao.add_distance(vd2)

        q1 = ddao.get_distance(method_id, v1, v2)
        print(q1)
        q2 = ddao.get_distance(method_id, v2, v3)
        print(q2)

        self.assertEqual(q1, vd1)
        self.assertEqual(q2, vd2)
