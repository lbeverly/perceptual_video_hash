#!/usr/bin/env python

import math
import decimal
from decimal import Decimal


################################################################################
def vector_to_integer(vec, radix=10):
    i = r = 0
    for v in reversed(vec):
        if v >= radix:
            s = 'Invalid digit value in vector: {} (radix: {})'.format(v, radix)
            raise RuntimeError(s)
        i += v * (radix ** r)
        r += 1
    return i


################################################################################
def convert_to_hash(vec, radix, bitsize=480):
    vec = vec.copy()
    n_digits = len(vec)

    # Increase significance to avoid zeroes
    r = 0
    while vec[0] == 0 and r < n_digits:
        vec = vec[1:] + vec[0:1]
        r += 1

    max_int = radix ** n_digits
    max_digits = len(str(max_int))
    decimal.setcontext(decimal.Context(prec=max_digits + 1))
    a = Decimal(vector_to_integer(vec, radix))
    b = Decimal(max_int)
    scaled = (a/b) * Decimal(2 ** bitsize)
    return int(math.floor(scaled))
