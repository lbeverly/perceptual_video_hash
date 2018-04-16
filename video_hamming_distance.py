#!/usr/bin/env python
from BitVector import BitVector

# perform hamming distance on two videos
# u, v need to be 1-D numpy arrays for the hamming function

def video_hamming_distance(video_1_hash, video_2_hash):
    bv_1 = BitVector(intVal = video_1_hash)
    bv_2 = BitVector(intVal = video_2_hash)
    return bv_1.hamming_distance(bv_2)



print(video_hamming_distance(video_1_hash, video_2_hash))
