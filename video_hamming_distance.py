#!/usr/bin/env python
from scipy.spatial import distance 

# perform hamming distance on two video fimming(u, v):
 
# Computes the Hamming distance between two 1-D arrays.
# The Hamming distance between 1-D arrays `u` and `v`, is simply the
# proportion of disagreeing components in `u` and `v`. If `u` and `v` are
# boolean vectors, the Hamming distance is
#  .. math::
#       \\frac{c_{01} + c_{10}}{n}
#    where :math:`c_{ij}` is the number of occurrences of
#    :math:`\\mathtt{u[k]} = i` and :math:`\\mathtt{v[k]} = j` for
#    :math:`k < n`.
#    Parameters
#    ----------
#    u : (N,) array_like
#        Input array.
#    v : (N,) array_like
#        Input array.
#    Returns
#    -------
#    hamming : double
#        The Hamming distance between vectors `u` and `v`.


def hamming(u, v):
	u = _validate_vector(u)
	v = _validate_vector(v)
	return (u != v).mean()
