#!/usr/bin/env python
from .data_manager import VideoDataManager
from .video_hashing import VideoHasher


################################################################################
class CalculateAccuracy:
    ############################################################################
    def __init__(self, method, manager=None, verbose=True):
        self.verbose = verbose
        self._methodcls = VideoHasher.get_hashmethod_class(method)
        self._method = method
        self._manager = manager
        if self._manager is None:
            self._manager = VideoDataManager()
        self._methodid = self._manager.hash_dao.get_hash_method_by_name(method)
        self._memoized_distances = {}
        return

    ############################################################################
    def calculate_distances(self):
        videos = self._manager.video_dao.all_videos()
        for idx, a in enumerate(videos):
            for b in videos[idx+1:]:
                vd = self._methodcls.calculate_distance(a, b)
                self._manager.distance_dao.add_distance(vd)
        return

    ############################################################################
    def run(self):
        accuracy = self._manager.hash_dao.get_method_accuracy(self._methodid)
        if accuracy is not None and accuracy['accuracy'] is not None:
            print("{} Accuracy: {}".format(self._method, accuracy))
            return accuracy

        self.calculate_distances()
        accuracy = self.best_accuracy()
        print("{} Accuracy: {}".format(self._method, accuracy))
        self._manager.hash_dao.set_method_accuracy(self._methodid, accuracy)
        return accuracy['accuracy']

    ############################################################################
    def best_accuracy(self):
        best_score = 0.0
        best_threshold = 1
        last_score = 0.0
        score = 0.0
        best_tp = 0.0
        best_tn = 0.0
        best_fp = 0.0
        best_fn = 0.0

        for threshold in range(1, self._methodcls.max_threshold()):
            last_score = score
            score, tp, tn, fp, fn = self.accuracy(threshold)
            if score > best_score:
                best_score = score
                best_threshold = threshold
                best_tp = tp
                best_tn = tn
                best_fp = fp
                best_fn = fn
            if score < 0.6 and threshold > 10 and score < last_score:
                break
            if score >= 1.0:
                break

        return {
                'accuracy': best_score,
                'threshold': best_threshold / self._methodcls.max_threshold(),
                'true_positives': best_tp,
                'true_negatives': best_tn,
                'false_positives': best_fp,
                'false_negatives': best_fn,
               }

    ############################################################################
    def accuracy(self, threshold):
        c1, true_positives, false_negatives = self._true_positives(threshold)
        c2, false_positives, true_negatives = self._true_negatives(threshold)
        if self.verbose:
            print('Threshold: {}, TP: {}, TN: {}, FP: {}, FN: {}'.format(
                                                      threshold,
                                                      true_positives,
                                                      true_negatives,
                                                      false_positives,
                                                      false_negatives))

        return ((true_positives + true_negatives) / (c1 + c2),
                true_positives,
                true_negatives,
                false_positives,
                false_negatives)

    ############################################################################
    def get_distance(self, methodid, a, b):
        v = self._memoized_distances.get((methodid, a, b))
        if v is None:
            ddao = self._manager.distance_dao
            vd = ddao.get_distance(self._methodid, a, b)
            self._memoized_distances[(methodid, a, b)] = vd
            v = vd
        return v

    ############################################################################
    def _compare(self, a, b, positive, negative, threshold):
        vd = self.get_distance(self._methodid, a, b)
        if abs(vd.distance) < threshold:
            positive += 1
        else:
            negative += 1
        return (positive, negative)

    ############################################################################
    def _true_positives(self, threshold):
        count = 0
        positive = 0
        negative = 0
        for s in self._manager.videoset_dao.get_video_all_sets():
            for idx, a in enumerate(s.videos):
                for b in list(s.videos)[idx+1:]:
                    count += 1
                    positive, negative = self._compare(a, b, positive,
                                                       negative,
                                                       threshold)

        return (count, positive, negative)

    ############################################################################
    def _true_negatives(self, threshold):
        vsdao = self._manager.videoset_dao
        count = 0
        positive = 0
        negative = 0
        video_sets = vsdao.get_video_all_sets()
        for n, s1 in enumerate(video_sets):
            for a in s1.videos:
                for s2 in video_sets[n+1:]:
                    count += len(s2.videos)
                    for b in s2.videos:
                        positive, negative = self._compare(a, b, positive,
                                                           negative,
                                                           threshold)

        return (count, positive, negative)
