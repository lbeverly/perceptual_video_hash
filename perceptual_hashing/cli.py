#!/usr/bin/env python
import sys
import os
from optparse import OptionParser

# flake8: noqa: F401
from .video_hashing import VideoHasher, PHash
from .llehash import (LLE16x16PointHash,
                      LLE16x16LuminosityPointHash,
                      LLE16x16OneDimensionHash,
                      LLE16x16OneDimensionLuminHash,
                      LLE16x16in256x256PointHash,
                      LLE16x16in256x256KNN16Hash,
                      LLE16x16in256x256OneDimensionLuminHash,
                      LLE16x16in256x256LowGauss1d,
                      )
from .video_preprocessing import VideoTranscoder
from .data_manager import VideoDataManager
from .accuracy import CalculateAccuracy


################################################################################
LLE16x16PointHash.hash_type()

################################################################################
class CLI:
    ############################################################################
    def get_partition_list(self, n, n_parts, filter_set):
        if n > n_parts:
            raise RuntimeError('Invalid partitioning')

        all_algos = filter(lambda cl: cl.__name__ in filter_set, 
                           sorted(VideoHasher.find_all_subclasses(),
                                  key=lambda cl: cl.__name__))
        return [cl for idx, cl in enumerate(all_algos) if idx % n_parts == n-1]

    ############################################################################
    def __init__(self, argv):
        parser = OptionParser()
        parser.add_option('--force',
                          action='store_true',
                          dest='force',
                          default=False,
                          help='Force reprocessing sources that have ' +
                               'already been processed')
        parser.add_option('--part',
                          action='store',
                          dest='part',
                          default=1,
                          help='Parition number')
        parser.add_option('--n_parts',
                          action='store',
                          dest='n_parts',
                          default=1,
                          help='Parition number')
        parser.add_option('--experiments',
                          action='store',
                          dest='experiments',
                          default='all',
                          help='Comma separted list of experiments | "all"')


        (opts, args) = parser.parse_args()
        if len(args) < 1 or not os.path.isdir(args[0]):
            sys.stderr.write("Must specify directory as first argument\n")
            sys.exit(1)

        self.experiments = set([cl.__name__
                                for cl in VideoHasher.find_all_subclasses()])

        if opts.experiments != 'all':
            self.experiments = set(opts.experiments.split(','))

        self.parts = self.get_partition_list(int(opts.part),
                                             int(opts.n_parts),
                                             self.experiments)
        self.force = opts.force
        self.path = args[0]
        self.manager = VideoDataManager()

    ############################################################################
    def run(self):
        self.runSetupSteps()
        self.runHashingSteps()
        self.runAccuracySteps()
        return

    ############################################################################
    def runSetupSteps(self):
        steps = [VideoTranscoder(self.path, self.manager, force=self.force)]

        for step in steps:
            step.run()
        return

    ############################################################################
    def runHashingSteps(self):
        steps = [cl(self.path, self.manager, force=self.force)
                 for cl in self.parts]

        for step in steps:
            step.run()
        return

    ############################################################################
    def runAccuracySteps(self):
        steps = [CalculateAccuracy(cl.hash_type(), self.manager)
                 for cl in self.parts]

        for step in steps:
            print('Running accuracy for {}'.format(step._method))
            step.run()

        return
