#!/usr/bin/env python
#-*- coding:utf-8 -*-

# test_analysis.py

# This file is part of the NNGT module
# Distributed as a free software, in the hope that it will be useful, under the
# terms of the GNU General Public License.

""" Test the graph analysis functions """

import os

import numpy as np
import pytest

import nngt
import nngt.analysis as na
import nngt.generation as ng


methods = ('barrat', 'continuous', 'onnela')


@pytest.mark.mpi_skip
def test_binary_undirected_clustering():
    '''
    Check that directed local clustering returns undirected value if graph is
    not directed.
    '''
    g = ng.erdos_renyi(avg_deg=10, nodes=100, directed=False)

    ccu = na.local_clustering_binary_undirected(g)
    cc  = na.local_clustering(g)

    assert np.all(np.isclose(cc, ccu))


@pytest.mark.mpi_skip
def test_weighted_undirected_clustering():
    '''
    Check relevant properties of weighted clustering:

    * give back the binary definition if all weights are one
    * corner cases for specific networks, see [Saramaki2007]
    * equivalence between no edge and zero-weight edge for 'continuous' method

    Note: onnela and barrat are already check against networkx and igraph
    implementations in libarry_compatibility.py
    '''
    g = ng.erdos_renyi(avg_deg=10, nodes=100, directed=False)

    # recover binary
    ccb = na.local_clustering_binary_undirected(g)

    for method in methods:
        ccw = na.local_clustering(g, weights='weight', method=method)

        assert np.all(np.isclose(ccb, ccw))

    # corner cases
    eps = 1e-20

    # 3 nodes
    num_nodes = 3
    edge_list = [(0, 1), (1, 2), (2, 0)]

    # all epsilon
    weights = [eps, eps, eps]

    g = nngt.Graph(nodes=num_nodes, directed=False)
    g.new_edges(edge_list, attributes={"weight": weights})

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)
        assert np.array_equal(cc, [1, 1, 1])

    # one weight is one
    g.set_weights(np.array([eps, eps, 1]))

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)

        if method == "barrat":
            assert np.all(np.isclose(cc, 1))
        else:
            assert np.all(np.isclose(cc, 0))

    # two weights are one
    g.set_weights(np.array([eps, eps, 1]))

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)

        if method == "barrat":
            assert np.all(np.isclose(cc, 1))
        else:
            assert np.all(np.isclose(cc, 0))

    # 4 nodes
    num_nodes = 4
    edge_list = [(0, 1), (1, 2), (2, 0), (2, 3)]

    g = nngt.Graph(nodes=num_nodes, directed=False)
    g.new_edges(edge_list)

    # out of triangle edge is epsilon
    g.set_weights([1, 1, 1, eps])

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)

        if method == 'barrat':
            assert np.all(np.isclose(cc, [1, 1, 0.5, 0]))
        elif method == "continuous":
            assert np.all(np.isclose(cc, [1, 1, 1, 0]))
        else:
            assert np.all(np.isclose(cc, [1, 1, 1/3, 0]))

    # out of triangle edge is 1 others are epsilon
    g.set_weights([eps, eps, eps, 1])

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)

        if method == 'barrat':
            assert np.all(np.isclose(cc, [1, 1, 0, 0]))
        else:
            assert np.all(np.isclose(cc, 0))

    # opposite triangle edge is 1 others are epsilon
    g.set_weights([1, eps, eps, eps])

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)

        if method == 'barrat':
            assert np.all(np.isclose(cc, [1, 1, 1/3, 0]))
        else:
            assert np.all(np.isclose(cc, 0))

    # adjacent triangle edge is 1 others are epsilon
    g.set_weights([eps, 1, eps, eps])

    for method in methods:
        cc = na.local_clustering(g, weights='weight', method=method)

        if method == 'barrat':
            assert np.all(np.isclose(cc, [1, 1, 1/2, 0]))
        else:
            assert np.all(np.isclose(cc, 0))

    # check zero-weight edge/no edge equivalence for continuous method
    num_nodes = 6
    edge_list = [(0, 1), (1, 2), (2, 0), (2, 3), (4, 5)]

    g = nngt.Graph(nodes=num_nodes, directed=False)
    g.new_edges(edge_list)

    g.set_weights([1/4, 1/9, 1/4, 1/9, 1])

    expected = [1/36, 1/24, 1/64, 0, 0, 0]

    cc = na.local_clustering(g, weights='weight', method='continuous')

    assert np.all(np.isclose(cc, expected))

    # 0-weight case
    g.set_weights([1/4, 1/9, 1/4, 0, 1])

    cc0 = na.local_clustering(g, weights='weight', method='continuous')

    # no-edge case
    edge_list = [(0, 1), (1, 2), (2, 0), (4, 5)]

    g = nngt.Graph(nodes=num_nodes, directed=False)
    g.new_edges(edge_list)
    g.set_weights([1/4, 1/9, 1/4, 1])

    expected = [1/36, 1/24, 1/24, 0, 0, 0]

    ccn = na.local_clustering(g, weights='weight', method='continuous')

    assert np.all(np.isclose(cc0, ccn))
    assert np.all(np.isclose(cc0, expected))


@pytest.mark.mpi_skip
def test_weighted_directed_clustering():
    num_nodes = 6
    edge_list = [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 3), (4, 5)]

    g = nngt.Graph(nodes=num_nodes)
    g.new_edges(edge_list)

    # continuous
    g.set_weights([1/4, 1/9, 1/4, 1/9, 1/4, 1/9, 1])

    # expected triangles and triplets
    # s_sqrt_tot  = np.array([11/6, 4/3, 3/2, 1/3, 1, 1])
    # s_tot       = np.array([31/36, 11/18, 7/12, 1/9, 1, 1])
    # s_recip     = np.array([5/12, 1/4, 1/6, 0, 0, 0])
    # triplets_c  = np.square(s_sqrt_tot) - s_tot - 2*s_recip
    triangles_c = np.array([13/648, 13/648, 13/648, 0, 0, 0])
    triplets_c  = np.array([15/9, 2/3, 4/3, 0, 0, 0])

    assert np.all(np.isclose(
        triangles_c,
        na.triangle_count(g, weights='weight', method='continuous')))

    assert np.all(np.isclose(
        triplets_c,
        na.triplet_count(g, weights='weight', method='continuous')))

    triplets_c[-3:] = 1
    expected = triangles_c / triplets_c

    cc = na.local_clustering(g, weights='weight', method='continuous')

    assert np.all(np.isclose(cc, expected))

    # barrat (clemente version for reciprocal strength)
    # d_tot       = np.array([4, 3, 4, 1, 1, 1])
    # s_recip     = np.array([31/72, 1/4, 0, 0, 0])
    # triplets_b  = s_tot*(d_tot - 1) - s_recip
    triangles_b = np.array([31/36, 13/18, 7/12, 0, 0, 0])
    triplets_b  = np.array([31/18, 13/18, 25/18, 0, 0, 0])

    assert np.all(np.isclose(
        triangles_b, na.triangle_count(g, weights='weight', method='barrat')))

    assert np.all(np.isclose(
        triplets_b, na.triplet_count(g, weights='weight', method='barrat')))

    triplets_b[-3:] = 1
    expected = triangles_b / triplets_b

    cc = na.local_clustering(g, weights='weight', method='barrat')

    assert np.all(np.isclose(cc, expected))

    # onnela
    triplets_o  = np.array([8, 4, 10, 0, 0, 0])
    triangles_o = np.array(
        [0.672764902429877, 0.672764902429877, 0.672764902429877, 0, 0, 0])

    assert np.array_equal(triplets_o, na.triplet_count(g))

    assert np.all(np.isclose(
        triangles_o, na.triangle_count(g, weights='weight', method="onnela")))
    
    triplets_o[-3:] = 1
    expected = triangles_o / triplets_o

    cc = na.local_clustering(g, weights='weight', method='onnela')

    assert np.all(np.isclose(cc, expected))


if __name__ == "__main__":
    if not nngt.get_config("mpi"):
        test_binary_undirected_clustering()
        test_weighted_undirected_clustering()
        test_weighted_directed_clustering()
