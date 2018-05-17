import unittest
import numpy as np
from perceptual_hashing.llehash import LLE16x16in256x256PointHash

np.set_printoptions(threshold=50)

frames = np.ndarray(shape=(16, 256, 256, 3), dtype=np.uint8)
for f in range(16):
    for r in range(256):
        for c in range(256):
            frames[f][r][c][0:3] = (f, r, c)


def make_row(f, r, c):
    v = [
            #               #                     #                 #           #  # noqa: E501
            0,   r,  c,      0,   r,   c + 1,  0,   r,   c + 2,  0,   r,   c + 3,  # noqa: E501
            0,   r,  c + 4,  0,   r,   c + 5,  0,   r,   c + 6,  0,   r,   c + 7,  # noqa: E501
            0,   r,  c + 8,  0,   r,   c + 9,  0,   r,  c + 10,  0,   r,  c + 11,  # noqa: E501
            0,   r,  c + 12, 0,   r,  c + 13,  0,   r,  c + 14,  0,   r,  c + 15,  # noqa: E501
        ]
    return v


################################################################################
class testcase(unittest.TestCase):
    def test_get_point(self):
        h = LLE16x16in256x256PointHash('/path/to/nowhere', None, None)
        wanted = []
        for n in range(16):
            wanted.extend(make_row(0, n, 0))

        self.assertListEqual(h.get_point(frames[0], 0).tolist(), wanted)

    def test_second_point(self):
        h = LLE16x16in256x256PointHash('/path/to/nowhere', None, None)
        wanted = []
        for n in range(16):
            wanted.extend(make_row(0, n, 16))
        self.assertListEqual(h.get_point(frames[0], 1).tolist(), wanted)

    def test_second_row_point(self):
        h = LLE16x16in256x256PointHash('/path/to/nowhere', None, None)
        wanted = []
        for n in range(16, 32):
            wanted.extend(make_row(0, n, 0))
        self.assertListEqual(h.get_point(frames[0], 16).tolist(), wanted)
