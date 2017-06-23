#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# This file is part of the NNGT project to generate and analyze
# neuronal networks and their activity.
# Copyright (C) 2015-2017  Tanguy Fardet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Tools for graph analysis using the graph libraries """

import numpy as np
import scipy.sparse.linalg as spl

import nngt
from nngt.lib import InvalidArgument, nonstring_container
from .activity_analysis import _b2_from_data, _fr_from_data
from .bayesian_blocks import bayesian_blocks


__all__ = [
    "adjacency_matrix",
    "assortativity",
    "betweenness_distrib",
    "binning",
	"closeness",
	"clustering",
    "degree_distrib",
	"diameter",
    "local_clustering",
    "node_attributes",
	"num_iedges",
	"num_scc",
	"num_wcc",
	"reciprocity",
	"spectral_radius",
    "subgraph_centrality",
]


# ----------------- #
# Set the functions #
# ----------------- #

adjacency = nngt.analyze_graph["adjacency"]
assort = nngt.analyze_graph["assortativity"]
edge_reciprocity = nngt.analyze_graph["reciprocity"]
_closeness = nngt.analyze_graph["closeness"]
global_clustering = nngt.analyze_graph["clustering"]
local_clustering_coeff = nngt.analyze_graph["local_clustering"]
scc = nngt.analyze_graph["scc"]
wcc = nngt.analyze_graph["wcc"]
glib_diameter = nngt.analyze_graph["diameter"]


# ------------- #
# Distributions #
# ------------- #

def degree_distrib(graph, deg_type="total", node_list=None, use_weights=False,
                   log=False, num_bins='auto'):
    '''
    Degree distribution of a graph.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        the graph to analyze.
    deg_type : string, optional (default: "total")
        type of degree to consider ("in", "out", or "total").
    node_list : list or numpy.array of ints, optional (default: None)
        Restrict the distribution to a set of nodes (default: all nodes).
    use_weights : bool, optional (default: False)
        use weighted degrees (do not take the sign into account: all weights
        are positive).
    log : bool, optional (default: False)
        use log-spaced bins.

    Returns
    -------
    counts : :class:`numpy.array`
        number of nodes in each bin
    deg : :class:`numpy.array`
        bins
    '''
    degrees = graph.get_degrees(deg_type, node_list, use_weights)
    bins = binning(degrees, bins=num_bins, log=log)
    return np.histogram(degrees, bins)
    #~ nonzero = np.argwhere(counts)
    #~ nonzero_bins = list(nonzero) + [nonzero[-1] + 1]
    #~ return counts[nonzero], deg[nonzero_bins]


def betweenness_distrib(graph, use_weights=True, nodes=None, num_nbins='auto',
                        num_ebins='auto', log=False):
    '''
    Betweenness distribution of a graph.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        the graph to analyze.
    use_weights : bool, optional (default: True)
        use weighted degrees (do not take the sign into account : all weights
        are positive).
    nodes : list or numpy.array of ints, optional (default: all nodes)
        Restrict the distribution to a set of nodes (only impacts the node
        attribute).
    log : bool, optional (default: False)
        use log-spaced bins.

    Returns
    -------
    ncounts : :class:`numpy.array`
        number of nodes in each bin
    nbetw : :class:`numpy.array`
        bins for node betweenness
    ecounts : :class:`numpy.array`
        number of edges in each bin
    ebetw : :class:`numpy.array`
        bins for edge betweenness
    '''
    ia_nbetw, ia_ebetw = graph.get_betweenness(use_weights)
    if nodes is not None:
        ia_nbetw = ia_nbetw[nodes]
    ra_nbins = binning(ia_nbetw, bins=num_nbins, log=log)
    ra_ebins = binning(ia_ebetw, bins=num_ebins, log=log)
    ncounts, nbetw = np.histogram(ia_nbetw, ra_nbins)
    ecounts, ebetw = np.histogram(ia_ebetw, ra_ebins)
    return ncounts, nbetw, ecounts, ebetw


# --------------- #
# Node properties #
# --------------- #

def closeness(graph, nodes=None, use_weights=False):
    '''
    Return the closeness centrality for each node in `nodes`.
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` object
        Graph to analyze.
    nodes : array-like container with node ids, optional (default = all nodes)
        Nodes for which the local clustering coefficient should be computed.
    use_weights : bool, optional (default: False)
        Whether weighted closeness should be used.
    '''
    return _closeness(graph, nodes, use_weights)


def local_clustering(graph, nodes=None):
    '''
    Local clustering coefficient of the nodes, defined as

    .. math::
        c_i = 3 \\times \\frac{\\text{triangles}}{\\text{connected triples}}
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` object
        Graph to analyze.
    nodes : array-like container with node ids, optional (default = all nodes)
        Nodes for which the local clustering coefficient should be computed.
    '''
    if nngt._config["graph_library"] == "igraph":
        return graph.transitivity_local_undirected(nodes)
    else:
        return local_clustering_coeff(graph, nodes)


# ---------------- #
# Graph properties #
# ---------------- #

def assortativity(graph, deg_type="total"):
    '''
    Assortativity of the graph.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    deg_type : string, optional (default: 'total')
        Type of degree to take into account (among 'in', 'out' or 'total').

    Returns
    -------
    a float quantifying the graph assortativity.
    '''
    if nngt._config["graph_library"] == "igraph":
        return graph.assortativity_degree(graph._directed)
    elif nngt._config["graph_library"] == "graph_tool":
        return assort(graph,"total")[0]
    else:
        return assort(graph)


def reciprocity(graph):
    '''
    Graph reciprocity, defined as :math:`E^\leftrightarrow/E`,
    where :math:`E^\leftrightarrow` and :math:`E` are, respectively, the number
    of bidirectional edges and the total number of edges in the graph.

    Returns
    -------
    a float quantifying the reciprocity.
    '''
    if nngt._config["graph_library"] == "igraph":
        return graph.reciprocity()
    else:
        return edge_reciprocity(graph)


def clustering(graph):
    '''
    Global clustering coefficient of the graph, defined as

    .. math::
        c = 3 \\times \\frac{\\text{triangles}}{\\text{connected triples}}
    '''
    if nngt._config["graph_library"] == "igraph":
        return graph.transitivity_undirected()
    else:
        return global_clustering(graph)


def num_iedges(graph):
    ''' Returns the number of inhibitory connections. '''
    num_einhib = len(graph["type"].a < 0)
    return float(num_einhib)/graph.edge_nb()


def num_scc(graph, listing=False):
    '''
    Returns the number of strongly connected components, i.e. ensembles where
    all nodes inside the ensemble can reach any other node in the ensemble
    using the directed edges.

    See also
    --------
    num_wcc
    '''
    lst_histo = None
    if nngt._config["graph_library"] == "graph_tool":
        vprop_comp, lst_histo = scc(graph,directed=True)
    elif nngt._config["graph_library"] == "igraph":
        lst_histo = graph.clusters()
        lst_histo = [ cluster for cluster in lst_histo ]
    else:
        lst_histo = [ comp for comp in scc(graph) ]
    if listing:
        return len(lst_histo), lst_histo
    else:
        return len(lst_histo)


def num_wcc(graph, listing=False):
    '''
    Connected components if the directivity of the edges is ignored (i.e. all
    edges are considered as bidirectional).

    See also
    --------
    num_scc
    '''
    lst_histo = None
    if nngt._config["graph_library"] == "graph_tool":
        vprop_comp, lst_histo = wcc(graph,directed=False)
    elif nngt._config["graph_library"] == "igraph":
        lst_histo = graphclusters("WEAK")
        lst_histo = [ cluster for cluster in lst_histo ]
    else:
        lst_histo = [ comp for comp in wcc(graph) ]
    if listing:
        return len(lst_histo), lst_histo
    else:
        return len(lst_histo)


def diameter(graph):
    ''' Pseudo-diameter of the graph @todo: weighted diameter'''
    if nngt._config["graph_library"] == "igraph":
        return graph.diameter()
    elif nngt._config["graph_library"] == "networkx":
        return glib_diameter(graph)
    else:
        return glib_diameter(graph)[0]


# ------------------- #
# Spectral properties #
# ------------------- #

def spectral_radius(graph, typed=True, weighted=True):
    '''
    Spectral radius of the graph, defined as the eigenvalue of greatest module.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    typed : bool, optional (default: True)
        Whether the excitatory/inhibitory type of the connnections should be
        considered.
    weighted : bool, optional (default: True)
        Whether the weights should be taken into account.

    Returns
    -------
    the spectral radius as a float.
    '''
    weights = None
    if typed and "type" in graph.eproperties.keys():
        weights = graph.eproperties["type"].copy()
    if weighted and "weight" in graph.eproperties.keys():
        if weights is not None:
            weights = np.multiply(weights,
                                  graph.eproperties["weight"])
        else:
            weights = graph.eproperties["weight"].copy()
    mat_adj = adjacency(graph,weights)
    eigenval = [0]
    try:
        eigenval = spl.eigs(mat_adj,return_eigenvectors=False)
    except spl.eigen.arpack.ArpackNoConvergence as err:
        eigenval = err.eigenvalues
    if len(eigenval):
        return np.amax(np.absolute(eigenval))
    else:
        raise spl.eigen.arpack.ArpackNoConvergence()


def adjacency_matrix(graph, types=True, weights=True):
    '''
    Adjacency matrix of the graph.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    types : bool, optional (default: True)
        Whether the excitatory/inhibitory type of the connnections should be
        considered (only if the weighing factor is the synaptic strength).
    weights : bool or string, optional (default: True)
        Whether weights should be taken into account; if True, then connections
        are weighed by their synaptic strength, if False, then a binary matrix
        is returned, if `weights` is a string, then the ponderation is the
        correponding value of the edge attribute (e.g. "distance" will return
        an adjacency matrix where each connection is multiplied by its length).

    Returns
    -------
    a :class:`~scipy.sparse.csr_matrix`.
    '''
    return graph.adjacency_matrix(types, weights)


def subgraph_centrality(graph, weights=True, normalize="max_centrality"):
    '''
    Subgraph centrality, accordign to [Estrada2005], for each node in the
    graph.

    **[Estrada2005]:** Ernesto Estrada and Juan A. Rodríguez-Velázquez,
    Subgraph centrality in complex networks, PHYSICAL REVIEW E 71, 056103
    (2005),
    `available on ArXiv <http://www.arxiv.org/pdf/cond-mat/0504730>`_.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    weights : bool or string, optional (default: True)
        Whether weights should be taken into account; if True, then connections
        are weighed by their synaptic strength, if False, then a binary matrix
        is returned, if `weights` is a string, then the ponderation is the
        correponding value of the edge attribute (e.g. "distance" will return
        an adjacency matrix where each connection is multiplied by its length).
    normalize : str, optional (default: "max_centrality")
        Whether the centrality should be normalized. Accepted normalizations
        are "max_eigenvalue" and "max_centrality"; the first rescales the
        adjacency matrix by the its largest eigenvalue before taking the
        exponential, the second sets the maximum centrality to one.

    Returns
    -------
    centralities : :class:`numpy.ndarray`
        The subgraph centrality of each node.
    '''
    adj_mat = graph.adjacency_matrix(types=False, weights=weights)
    centralities = None
    if normalize == "max_centrality":
        centralities = spl.expm(adj_mat / adj_mat.max()).diagonal()
        centralities /= centralities.max()
    elif normalize == "max_eigenvalue":
        norm, _ = spl.eigs(adj_mat, k=1)
        centralities = spl.expm(adj_mat / norm).diagonal()
    else:
        raise InvalidArgument('`normalize` should be either False, "eigenmax",'
                              ' or "centralmax".')
    return centralities


# ----------------------- #
# Get all node properties #
# ----------------------- #

def node_attributes(network, attributes, nodes=None):
    '''
    Return node `attributes` for a set of `nodes`.
    
    Parameters
    ----------
    network : :class:`~nngt.Graph`
        The graph where the `nodes` belong.
    attributes : str or list
        Attributes which should be returned, among:
        * "betweenness"
        * "clustering"
        * "in-degree", "out-degree", "total-degree"
        * "subgraph_centrality"
    nodes : list, optional (default: all nodes)
        Nodes for which the attributes should be returned.
    
    Returns
    -------
    values : array-like or dict
        Returns the attributes, either as an array if only one attribute is
        required (`attributes` is a :obj:`str`) or as a :obj:`dict` of arrays.
    '''
    if nonstring_container(attributes):
        values = {}
        for attr in attributes:
            values[attr] = _get_attribute(network, attr, nodes)
        return values
    else:
        return _get_attribute(network, attributes, nodes)

    
def find_nodes(network, attributes, equal=None, upper_bound=None,
               lower_bound=None, upper_fraction=None, lower_fraction=None,
               data=None):
    '''
    Return the nodes in the graph which fulfill the given conditions.
    
    Parameters
    ----------
    network : :class:`~nngt.Graph`
        The graph where the `nodes` belong.
    attributes : str or list
        Properties on which the conditions apply, among:
        * "B2" (requires NEST or `data` entry)
        * "betweenness"
        * "clustering"
        * "firing_rate" (requires NEST or `data` entry)
        * "in-degree", "out-degree", "total-degree"
        * "subgraph_centrality"
        * any custom property formerly set by the user
    equal : optional (default: None)
        Value to which `attributes` should be equal. For a given
        property, this entry is cannot be used together with any of the
        others.
    upper_bound : optional (default: None)
        Value which should strictly major `attributes` in the desired
        nodes. Can be combined with all other entries, except `equal`.
    lower_bound : optional (default: None)
        Value which should minor or be equal to the value of `attributes`
        in the desired nodes. Can be combined with all other entries,
        except `equal`.
    upper_fraction : optional (default: None)
        Only the nodes that belong to the `upper_fraction` with the highest
        values for `attributes` are kept.
    lower_fraction : optional (default: None)
        Only the nodes that belong to the `lower_fraction` with the lowest
        values for `attributes` are kept.
    
    Notes
    -----
    When combining both `*_fraction` and `*_bound` entries, their effects
    are cumulated, i.e. only the nodes belonging to the fraction AND
    displaying a value that is consistent with the boundary are kept.
    
    Examples
    --------
    
        nodes = g.find("in-degree", upper_bound=15, lower_bound=10)
        nodes2 = g.find(["total-degree", "clustering"], equal=[20, None],
            lower=[None, 0.1])
    '''
    if not nonstring_container(attributes):
        attributes = [attributes]
        equal = [equal]
        upper_bound = [upper_bound]
        lower_bound = [lower_bound]
        upper_fraction = [upper_fraction]
        lower_fraction = [lower_fraction]
        assert not np.any([
            len(attributes)-len(equal), len(upper_bound)-len(equal),
            len(lower_bound)-len(equal), len(upper_fraction)-len(equal), 
            len(lower_fraction)-len(equal)])
    nodes = set(range(self.node_nb()))
    # find the nodes
    di_attr = node_attributes(self, attributes)
    keep = np.ones(self.node_nb(), dtype=bool)
    for i in range(len(attributes)):
        attr, eq = attributes[i], equal[i]
        ub, lb = upper_bound[i], lower_bound[i]
        uf, lf = upper_fraction[i], lower_fraction[i]
        # check that the combination is valid
        if eq is not None:
            assert (ub is None)*(lb is None)*(uf is None)*(lf is None), \
            "`equal` entry is incompatible with all other entries."
            keep *= (_get_attribute(self, attr) == eq)
        if ub is not None:
            keep *= (_get_attribute(self, attr) < ub)
        if lb is not None:
            keep *= (_get_attribute(self, attr) >= lb)
        values = None
        if uf is not None or lf is not None:
            values = _get_attribute(self, attr)
        if uf is not None:
            num_keep = int(self.node_nb()*uf)
            sort = np.argsort(values)[:-num_keep]
            keep_tmp = np.ones(self.node_nb(), dtype=bool)
            keep_tmp[sort] = 0
            keep *= keep_tmp
        if lf is not None:
            num_keep = int(self.node_nb()*lf)
            sort = np.argsort(values)[:num_keep]
            keep_tmp = np.zeros(self.node_nb(), dtype=bool)
            keep_tmp[sort] = 1
            keep *= keep_tmp
    nodes = nodes.intersection_update(np.array(nodes)[keep])
    return nodes


# ----- #
# Tools #
# ----- #

def binning(x, bins='auto', log=False):
    """
    Binning function providing automatic binning using Bayesian blocks in
    addition to standard linear and logarithmic uniform bins.

    Parameters
    ----------
    x : array-like
        Array of data to be histogrammed
    bins : int or list or 'auto', optional (default: 'auto')
        If `bins` is 'auto', in use bayesian blocks for dynamic bin widths; if
        it is an int, the interval will be separated into 
    log : bool, optional (default: False)
        Whether the bins should be evenly spaced on a logarithmic scale.
    """
    x = np.asarray(x)
    new_bins = None

    if bins == 'auto':
        return bayesian_blocks(x)
    elif nonstring_container(bins):
        return bins
    elif isinstance(bins, int):
        if log:
            return np.logspace(np.log10(np.maximum(x.min(), 1e-10)),
                               np.log10(x.max()), bins)
        else:
            return np.linspace(x.min(), x.max(), bins)
    else:
        raise ValueError("unrecognized bin code: '" + str(bins) + "'.")


def _get_attribute(network, attribute, nodes=None, data=None):
    if attribute.lower() == "b2":
        if data is None:
            from nngt.simulation import get_b2
            return get_b2(network, nodes=nodes)
        else:
            if nodes is None:
                raise InvalidArgument(
                    "`nodes` entry is required when using `data`.")
            return _b2_from_data(nodes, data)
    elif attribute == "betweenness":
        betw = network.get_betweenness("node")
        if nodes is not None:
            return betw[nodes]
        return betw
    elif attribute == "closeness":
        return closeness(network, nodes=nodes)
    elif attribute == "clustering":
        return local_clustering(network, nodes=nodes)
    elif "degree" in attribute.lower():
        dtype = attribute[:attribute.index("-")]
        return network.get_degrees(dtype, node_list=nodes)
    if attribute == "firing_rate":
        if data is None:
            from nngt.simulation import get_firing_rate
            return get_firing_rate(network, nodes=nodes)
        else:
            if nodes is None:
                raise InvalidArgument(
                    "`nodes` entry is required when using `data`.")
            return _fr_from_data(nodes, data)
    elif attribute == "subgraph_centrality":
        sc = subgraph_centrality(network)
        if nodes is not None:
            return sc[nodes]
        return sc
    else:
        raise RuntimeError(
            "Attribute '{}' is not available.".format(attribute))
