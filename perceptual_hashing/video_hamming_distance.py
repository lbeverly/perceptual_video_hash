#!/usr/bin/env python
from BitVector import BitVector


################################################################################
def hamming_distance(v1, v2, size=64, hashtype='intval'):
    '''
    perform hamming distance on two videos
    '''
    (bv1, bv2) = {
        'bitstring': lambda: (BitVector(bitstring=v1),
                              BitVector(bitstring=v2)),
        'intval': lambda: (BitVector(intVal=int(v1), size=size),
                           BitVector(intVal=int(v2), size=size))
    }[hashtype]()

    return bv1.hamming_distance(bv2)
