import datetime
import math
from scipy import misc, fftpack
from skvideo.io import FFmpegReader, ffprobe
from skimage import color, img_as_float
from skimage.filters import gaussian
from skimage.transform import resize
from sklearn.manifold import locally_linear_embedding
import numpy as np
from BitVector import BitVector
import warnings

from .video_hashing import VideoHasher
from .data_manager import VideoDistance
from .video_hamming_distance import hamming_distance
from .util import convert_to_hash


################################################################################
class LLE16x16PointHash(VideoHasher):
    ############################################################################
    width = 320
    height = 320
    point_x = 16
    point_y = 16
    grab_n_frames = 8
    wanted_dimensions = 2
    knn = 8
    n_dimensions_per_pixel = 3

    ############################################################################
    @classmethod
    def pixels_per_point(cls):
        return cls.point_x * cls.point_y

    ############################################################################
    @classmethod
    def dimensions(cls):
        return cls.pixels_per_point() * cls.n_dimensions_per_pixel

    ############################################################################
    @classmethod
    def points_per_frame(cls):
        return (cls.width * cls.height) // cls.pixels_per_point()

    ############################################################################
    @classmethod
    def points_per_video(cls):
        return cls.points_per_frame() * cls.grab_n_frames

    ############################################################################
    @classmethod
    def calculate_distance(cls, video1, video2):
        hash_id = video1.hash_values[cls.hash_type()].id
        v1 = video1.hash_values[cls.hash_type()].value
        v2 = video2.hash_values[cls.hash_type()].value
        distance = hamming_distance(v1, v2, size=cls.max_threshold(),
                                    hashtype='bitstring')
        return VideoDistance(video1, video2, hash_id, distance)

    ############################################################################
    @classmethod
    def hash_type(cls):
        return cls.__name__

    ############################################################################
    @classmethod
    def max_threshold(cls):
        return 480

    ############################################################################
    def _horizontal_bar(self, frame, blacklvl=16):
        x = 0
        for yidx, row in enumerate(frame):
            for xidx, c in enumerate(row):
                if sum(c) > blacklvl * self.n_dimensions_per_pixel * 1.15:
                    return x
            x += 1
        return x

    ############################################################################
    def _find_black_bars(self, frames):
        n_frames, rows, columns, colors = frames.shape
        frame_bars = []
        for frame in frames:
            top = self._horizontal_bar(frame)
            bottom = self._horizontal_bar(reversed(frame))
            T = np.transpose(frame, (1, 0, 2))
            left = self._horizontal_bar(T)
            right = self._horizontal_bar(reversed(T))
            frame_bars.append((top, bottom, left, right))

        top_bar = min([x[0] for x in frame_bars])
        bottom_bar = rows - min([x[1] for x in frame_bars])
        left_bar = min([x[2] for x in frame_bars])
        right_bar = columns - min([x[3] for x in frame_bars])
        return (top_bar, bottom_bar, left_bar, right_bar)

    ############################################################################
    def _crop_bars(self, frames):
        t, b, l, r = self._find_black_bars(frames)
        new_frames = np.ndarray(shape=(self.grab_n_frames, b-t, r-l, 3),
                                dtype=np.float64)
        for idx, frame in enumerate(frames):
            new_frames[idx] = frame[t:b, l:r]
        return new_frames

    ############################################################################
    def process_frame(self, n, filename, frame):
        misc.imsave('{}_{}_{}_0.jpg'.format(filename, n, self.hash_type()),
                    frame)
        frame = resize(frame, (self.height, self.width), mode='constant')
        misc.imsave('{}_{}_{}_1.jpg'.format(filename, n, self.hash_type()),
                    frame)
        frame = gaussian(frame, sigma=3.0, multichannel=True)
        misc.imsave('{}_{}_{}_2.jpg'.format(filename, n, self.hash_type()),
                    frame)
        xyz = color.convert_colorspace(frame, 'YUV', 'XYZ')
        misc.imsave('{}_{}_{}_3.jpg'.format(filename, n, self.hash_type()),
                    xyz)
        lab = color.xyz2lab(xyz)
        misc.imsave('{}_{}_{}_4.jpg'.format(filename, n, self.hash_type()),
                    lab)
        return lab

    ############################################################################
    def wanted(self, filename):
        info = ffprobe(filename)
        vinfo = info['video']

        avg = vinfo['@r_frame_rate']
        num = float(avg.split('/')[0])
        den = float(avg.split('/')[1])
        fps = float(num/den)

        duration = float(vinfo['@duration']) * 0.90
        n_frames = int(fps * duration)
        start = int(math.floor(float(vinfo['@duration']) * fps * 0.05))
        step = int(math.floor(n_frames / self.grab_n_frames))

        wanted = [n for n in range(start, n_frames, step)]
        return set(wanted[:self.grab_n_frames])

    ############################################################################
    def get_frames(self, filename, wanted):
        v = FFmpegReader(filename)  # , outputdict={'-pix_fmt': 'yuv444p'})

        frames = None
        n_frames = 0
        for n, frame in enumerate(v.nextFrame()):
            # the FFmpegReader API actually renders every frame; so it's rather
            # slow; but it ensures that every frame is rendered, not just
            # i-frames... getting i-frames would be faster, but might increase
            # false-negative rate due to picking out different frames from
            # different encodings
            if n not in wanted:
                continue
            if frames is None:
                frames = np.ndarray(shape=(self.grab_n_frames,) + frame.shape,
                                    dtype=np.float64)

            frames[n_frames] = frame
            n_frames += 1
            if n_frames == self.grab_n_frames:
                break
        v.close()

        if n_frames != self.grab_n_frames:
            raise RuntimeError(
                'Video has invalid number of frames: {}: {}'.format(
                    filename, len(frames)
                )
            )
        frames = self._crop_bars(frames)
        return [self.process_frame(n, filename, frame)
                for n, frame in enumerate(frames)]

    ############################################################################
    def get_point(self, frame, n):
        start_row = int((n * self.point_x) / self.width) * self.point_y
        col = (n * self.point_x) % self.width
        data = np.ndarray(shape=(self.dimensions(),), dtype=np.float64)
        idx = 0
        for row in range(start_row, start_row+self.point_x):
            for px in frame[row][col:col+self.point_y]:
                data[idx:idx + self.n_dimensions_per_pixel] = px
                idx += self.n_dimensions_per_pixel
        return data

    ############################################################################
    def frames_to_points(self, frames, k):
        points = np.ndarray(shape=(self.points_per_frame() * k,
                                   self.dimensions()),
                            dtype=np.float64)
        n = 0
        for frame in frames:
            for i in range(self.points_per_frame()):
                points[n] = self.get_point(frame, i)
                n += 1
        return points

    ############################################################################
    def get_embedding(self, points):
        n = self.wanted_dimensions
        try:
            embedding, errors = locally_linear_embedding(points,
                                                         n_neighbors=self.knn,
                                                         n_components=n,
                                                         eigen_solver='dense',
                                                         n_jobs=-1)
        except Exception:
            embedding, errors = locally_linear_embedding(points,
                                                         n_neighbors=self.knn,
                                                         n_components=n,
                                                         eigen_solver='dense',
                                                         n_jobs=-1)
        return (embedding, errors)

    ############################################################################
    def _distance(self, v):
        return math.sqrt((v[0] ** 2) + (v[1] ** 2))

    ############################################################################
    def _vectors_to_hash(self, norms):
        mx = 0
        mn = float('+inf')

        for n in norms:
            mx = max(n, mx)
            mn = min(n, mn)

        vec = [int(math.floor((n - mn) / (mx - mn) * 255)) for n in norms]
        if len(vec) != self.points_per_video():
            raise RuntimeError('Invalid # of points')
        return convert_to_hash(vec, 256, self.max_threshold())

    ############################################################################
    def lle_hash(self, points):
        size = self.max_threshold()
        embedding, errors = self.get_embedding(points)

        l2norm = [self._distance(v) for v in embedding]
        return BitVector(size=size, intVal=self._vectors_to_hash(l2norm))

    ############################################################################
    def output_points_as_images(self, points, filepath):
        pass

    ############################################################################
    def hash_video(self, filepath, video):
        print('{}: {}: file: {}'.format(datetime.datetime.now(),
                                        self.hash_type(), filepath))
        wanted = self.wanted(filepath)
        frames = self.get_frames(filepath, wanted)
        points = self.frames_to_points(frames, len(wanted))
        self.output_points_as_images(points, filepath)
        hash_value = self.lle_hash(points)
        print(hash_value)
        self.store_hash(video, hash_value)


################################################################################
class LLE16x16LuminosityPointHash(LLE16x16PointHash):
    n_dimensions_per_pixel = 1

    ############################################################################
    def process_frame(self, n, filename, frame):
        frame = resize(frame, (self.height, self.width), mode='constant')
        misc.imsave('{}_{}_{}_0.jpg'
                    .format(filename, n, self.hash_type()), frame)
        frame = gaussian(frame, sigma=3.0, multichannel=True)
        misc.imsave('{}_{}_{}_1.jpg'
                    .format(filename, n, self.hash_type()), frame)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            frame = img_as_float(color.rgb2gray(color.yuv2rgb(frame)))
        misc.imsave('{}_{}_{}_2.jpg'
                    .format(filename, n, self.hash_type()), frame)
        return frame


################################################################################
class LLE16x16OneDimensionHash(LLE16x16PointHash):
    ############################################################################
    wanted_dimensions = 1

    ############################################################################
    def _distance(self, v):
        return abs(v[0])


################################################################################
class LLE16x16OneDimensionLuminHash(LLE16x16LuminosityPointHash):
    ############################################################################
    wanted_dimensions = 1

    ############################################################################
    def _distance(self, v):
        return abs(v[0])


################################################################################
class LLE16x16in256x256PointHash(LLE16x16PointHash):
    ############################################################################
    width = 256
    height = 256
    point_x = 16
    point_y = 16
    grab_n_frames = 8
    wanted_dimensions = 2
    knn = 8
    n_dimensions_per_pixel = 3


################################################################################
class LLE16x16in256x256KNN16Hash(LLE16x16in256x256PointHash):
    knn = 16


################################################################################
class LLE16x16in256x256OneDimensionLuminHash(LLE16x16LuminosityPointHash):
    ############################################################################
    width = 256
    height = 256
    point_x = 16
    point_y = 16
    grab_n_frames = 8
    knn = 8
    n_dimensions_per_pixel = 3

    wanted_dimensions = 1

    ############################################################################
    def _distance(self, v):
        return abs(v[0])


################################################################################
class LLE16x16in256x256LowGauss1d(LLE16x16in256x256OneDimensionLuminHash):
    ############################################################################
    def process_frame(self, n, filename, frame):
        frame = resize(frame, (self.height, self.width), mode='constant')
        misc.imsave('{}_{}_{}_0.jpg'
                    .format(filename, n, self.hash_type()), frame)
        frame = gaussian(frame, sigma=5.0, multichannel=True)
        misc.imsave('{}_{}_{}_1.jpg'
                    .format(filename, n, self.hash_type()), frame)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            frame = img_as_float(color.rgb2gray(color.yuv2rgb(frame)))
        misc.imsave('{}_{}_{}_2.jpg'
                    .format(filename, n, self.hash_type()), frame)
        return frame


class LLEMosaicHash(LLE16x16PointHash):
    ############################################################################
    wanted_dimensions = 1
    n_dimensions_per_pixel = 3

    ############################################################################
    @classmethod
    def dimensions(cls):
        return cls.n_dimensions_per_pixel

    ############################################################################
    def _distance(self, v):
        return abs(v[0])

    ############################################################################
    def process_frame(self, n, filename, frame):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            frame = img_as_float(resize(frame, (self.height, self.width),
                                        mode='constant'))
        misc.imsave('{}_{}_{}_0.jpg'
                    .format(filename, n, self.hash_type()), frame)
        return frame

    ############################################################################
    def draw_frame(self, filepath, points, n):
        if self.n_dimensions_per_pixel > 1:
            img = np.ndarray(shape=(self.height, self.width,
                             self.n_dimensions_per_pixel), dtype=np.float64)
        else:
            img = np.ndarray(shape=(self.height, self.width), dtype=np.float64)

        start = n * self.points_per_frame()
        end = start + self.points_per_frame()

        v = points[start:end].reshape(self.height // self.point_y,
                                      self.width // self.point_x,
                                      self.n_dimensions_per_pixel)
        for j, r in enumerate(v):
            for k, c in enumerate(r):
                h = j * self.point_y
                w = k * self.point_x
                block = np.array(c.tolist() * self.point_x * self.point_y)
                if self.n_dimensions_per_pixel > 1:
                    block = block.reshape(self.point_y, self.point_x,
                                          self.n_dimensions_per_pixel)
                else:
                    block = block.reshape(self.point_y, self.point_x)
                img[h:h+self.point_y, w:w+self.point_x] = block

        misc.imsave('{}_{}_{}_9_mosaic.jpg'
                    .format(filepath, n, self.hash_type()), img)
        return

    ############################################################################
    def output_points_as_images(self, points, filepath):
        for n in range(self.grab_n_frames):
            self.draw_frame(filepath, points, n)
        return

    ############################################################################
    def get_point(self, frame, n):
        start_row = int((n * self.point_x) / self.width) * self.point_y
        col = (n * self.point_x) % self.width
        avg = [0] * self.dimensions()
        for row in range(start_row, start_row+self.point_x):
            for px in frame[row][col:col+self.point_y]:
                try:
                    for idx, value in enumerate(px):
                        avg[idx] += value
                except TypeError:
                    avg[0] += px

        data = np.array([x / self.pixels_per_point() for x in avg],
                        dtype=np.float64)

        return data


################################################################################
class LLEMosaicHashGrayScale(LLEMosaicHash):
    ############################################################################
    wanted_dimensions = 1
    n_dimensions_per_pixel = 1

    ############################################################################
    def process_frame(self, n, filename, frame):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            frame = img_as_float(resize(frame, (self.height, self.width),
                                        mode='constant'))
            frame = img_as_float(color.rgb2gray(color.yuv2rgb(frame)))

        misc.imsave('{}_{}_{}_0.jpg'
                    .format(filename, n, self.hash_type()), frame)
        return frame


################################################################################
class LLEDCTHash(LLE16x16PointHash):
    point_x = 32
    point_y = 32

    ############################################################################
    def process_frame(self, n, filename, frame):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            frame = img_as_float(resize(frame, (self.height, self.width),
                                        mode='constant'))
            misc.imsave('{}_{}_{}_0.jpg'
                        .format(filename, n, self.hash_type()), frame)
            frame = gaussian(frame, sigma=1.0, multichannel=True)
            misc.imsave('{}_{}_{}_1.jpg'.format(filename, n, self.hash_type()),
                        frame)
        return frame

    ############################################################################
    def _diagonalize(self, data):
        new_data = np.ndarray(shape=(data.shape[0],
                                     data.shape[1] * data.shape[2]),
                              dtype=data.dtype)

        for idx, sc in enumerate(data):
            new_data[idx] = np.concatenate(
                    [np.diagonal(sc[::-1, :], k)[::(2*(k % 2)-1)]
                        for k in range(1-sc.shape[0], sc.shape[0])])
        return new_data

    ############################################################################
    def get_point(self, frame, n):
        data = super().get_point(frame, n)
        data = np.transpose(data.reshape(self.point_y,
                                         self.point_x,
                                         self.n_dimensions_per_pixel),
                            (2, 0, 1))

        for idx, subchannel in enumerate(data):
            data[idx] = fftpack.dct(subchannel, 2)
        data = self._diagonalize(data)
        data = data.reshape(self.n_dimensions_per_pixel, self.point_y,
                            self.point_x)
        data = np.transpose(data, (1, 2, 0))
        return data.reshape(self.point_y * self.point_x *
                            self.n_dimensions_per_pixel)


################################################################################
class LLEDCT16x16Hash(LLE16x16PointHash):
    point_x = 16
    point_y = 16


################################################################################
class LLEDCT8x8Hash(LLE16x16PointHash):
    point_x = 8
    point_y = 8
