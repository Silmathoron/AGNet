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

""" Connectivity generators for nngt.Graph """

from copy import deepcopy
import logging

import numpy as np

import nngt
from nngt.geometry.geom_utils import conversion_magnitude
from nngt.lib.connect_tools import _set_options

# try to import multithreaded algorithms

using_mt_algorithms = False

if nngt.get_config("multithreading"):
    logger = logging.getLogger(__name__)
    try:
        from .cconnect import *
        from .connect_algorithms import price_network
        using_mt_algorithms = True
        logger.debug("Using multithreaded algorithms compiled on install.")
    except Exception as e:
        try:
            import cython
            import pyximport; pyximport.install()
            from .cconnect import *
            from .connect_algorithms import price_network
            using_mt_algorithms = True
            logger.debug(
                str(e) + "\n\tMultithreaded algorithms compiled on-the-run.")
        except Exception as e2:
            logger.debug(
                str(e) + "\n\t" + str(e2) + "\n\t" +
                "Cython import failed, using non-multithreaded algorithms.")
if not using_mt_algorithms:
    from .connect_algorithms import *



__all__ = [
    'connect_neural_groups',
    'connect_neural_types',
	'distance_rule',
	'erdos_renyi',
    'fixed_degree',
    'gaussian_degree',
	'newman_watts',
	'random_scale_free',
	'price_scale_free',
]


# ----------------------------- #
# Specific degree distributions #
# ----------------------------- #

def fixed_degree(degree, degree_type='in', nodes=0, reciprocity=-1.,
                 weighted=True, directed=True, multigraph=False, name="FD",
                 shape=None, positions=None, population=None, from_graph=None,
                 **kwargs):
    """
    Generate a random graph with constant in- or out-degree.

    Parameters
    ----------
    degree : int
        The value of the constant degree.
    degree_type : str, optional (default: 'in')
        The type of the fixed degree, among ``'in'``, ``'out'`` or ``'total'``.
        
        @todo
			`'total'` not implemented yet.
			
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    reciprocity : double, optional (default: -1 to let it free)
        @todo: not implemented yet. Fraction of edges that are bidirectional 
        (only for directed graphs -- undirected graphs have a reciprocity of 
        1 by definition)
    weighted : bool, optional (default: True)
        Whether the graph edges have weights.
    directed : bool, optional (default: True)
        @todo: only for directed graphs for now. Whether the graph is directed
        or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes.
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment.
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.

    Note
    ----
	`nodes` is required unless `from_graph` or `population` is provided.
	If an `from_graph` is provided, all preexistant edges in the
	object will be deleted before the new connectivity is implemented.

    Returns
    -------
    graph_fd : :class:`~nngt.Graph`, or subclass
        A new generated graph or the modified `from_graph`.
    """
    degree = int(degree)
    # set node number and library graph
    graph_fd = from_graph
    if graph_fd is not None:
        nodes = graph_fd.node_nb()
        graph_fd.clear_all_edges()
    else:
        nodes = population.size if population is not None else nodes
        graph_fd = nngt.Graph(
            name=name, nodes=nodes, directed=directed, **kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = np.arange(nodes, dtype=np.uint)
        ia_edges = _fixed_degree(ids, ids, degree, degree_type, reciprocity,
                                 directed, multigraph)
        graph_fd.new_edges(ia_edges)
    _set_options(graph_fd, population, shape, positions)
    graph_fd._graph_type = "fixed_{}_degree".format(degree_type)
    return graph_fd


def gaussian_degree(avg, std, degree_type='in', nodes=0, reciprocity=-1.,
                    weighted=True, directed=True, multigraph=False, name="GD",
                    shape=None, positions=None, population=None,
                    from_graph=None, **kwargs):
    """
    Generate a random graph with constant in- or out-degree.
    @todo: adapt it for undirected graphs!

    Parameters
    ----------
    avg : float
        The value of the average degree.
    std : float
		The standard deviation of the Gaussian distribution.
    degree_type : str, optional (default: 'in')
        The type of the fixed degree, among 'in', 'out' or 'total'
        @todo: Implement 'total' degree
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    reciprocity : double, optional (default: -1 to let it free)
        @todo: not implemented yet. Fraction of edges that are bidirectional 
        (only for directed graphs -- undirected graphs have a reciprocity of 
        1 by definition)
    weighted : bool, optional (default: True)
        Whether the graph edges have weights.
    directed : bool, optional (default: True)
        @todo: only for directed graphs for now. Whether the graph is directed
        or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes.
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment.
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.

    Returns
    -------
    graph_gd : :class:`~nngt.Graph`, or subclass
        A new generated graph or the modified `from_graph`.

    Note
    ----
	`nodes` is required unless `from_graph` or `population` is provided.
	If an `from_graph` is provided, all preexistant edges in the object
	will be deleted before the new connectivity is implemented.
    """
    # set node number and library graph
    graph_gd = from_graph
    if graph_gd is not None:
        nodes = graph_gd.node_nb()
        graph_gd.clear_all_edges()
    else:
        nodes = population.size if population is not None else nodes
        graph_gd = nngt.Graph(name=name,nodes=nodes,directed=directed,**kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = np.arange(nodes, dtype=np.uint)
        ia_edges = _gaussian_degree(ids, ids, avg, std, degree_type,
                                    reciprocity, directed, multigraph)
        graph_gd.new_edges(ia_edges)
    _set_options(graph_gd, population, shape, positions)
    graph_gd._graph_type = "gaussian_{}_degree".format(degree_type)
    return graph_gd


#-----------------------------------------------------------------------------#
# Erdos-Renyi
#------------------------
#

def erdos_renyi(density=-1., nodes=0, edges=-1, avg_deg=-1., reciprocity=-1.,
                weighted=True, directed=True, multigraph=False, name="ER",
                shape=None, positions=None, population=None, from_graph=None,
                **kwargs):
    """
    Generate a random graph as defined by Erdos and Renyi but with a
    reciprocity that can be chosen.

    Parameters
    ----------
    density : double, optional (default: -1.)
        Structural density given by `edges / nodes`:math:`^2`. It is also the
        probability for each possible edge in the graph to exist.
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    edges : int (optional)
        The number of edges between the nodes
    avg_deg : double, optional
        Average degree of the neurons given by `edges / nodes`.
    reciprocity : double, optional (default: -1 to let it free)
        Fraction of edges that are bidirectional (only for
        directed graphs -- undirected graphs have a reciprocity of 1 by
        definition)
    weighted : bool, optional (default: True)
        Whether the graph edges have weights.
    directed : bool, optional (default: True)
        Whether the graph is directed or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes.
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment.
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.

    Returns
    -------
    graph_er : :class:`~nngt.Graph`, or subclass
        A new generated graph or the modified `from_graph`.

    Note
    ----
	`nodes` is required unless `from_graph` or `population` is provided.
	If an `from_graph` is provided, all preexistant edges in the
	object will be deleted before the new connectivity is implemented.
    """
    # set node number and library graph
    graph_er = from_graph
    if graph_er is not None:
        nodes = graph_er.node_nb()
        graph_er.clear_all_edges()
    else:
        nodes = population.size if population is not None else nodes
        graph_er = nngt.Graph(
            name=name, nodes=nodes, directed=directed, **kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _erdos_renyi(ids, ids, density, edges, avg_deg, reciprocity,
                                directed, multigraph)
        graph_er.new_edges(ia_edges)
    _set_options(graph_er, population, shape, positions)
    graph_er._graph_type = "erdos_renyi"
    return graph_er


#
#---
# Scale-free models
#------------------------

def random_scale_free(in_exp, out_exp, nodes=0, density=0.1, edges=-1,
                      avg_deg=-1, reciprocity=0., weighted=True, directed=True,
                      multigraph=False, name="RandomSF", shape=None, 
                      positions=None, population=None, from_graph=None,
                      **kwargs):
    """
    Generate a free-scale graph of given reciprocity and otherwise
    devoid of correlations.
	
    Parameters
    ----------
    in_exp : float
        Absolute value of the in-degree exponent :math:`\gamma_i`, such that
        :math:`p(k_i) \propto k_i^{-\gamma_i}`
    out_exp : float
        Absolute value of the out-degree exponent :math:`\gamma_o`, such that
        :math:`p(k_o) \propto k_o^{-\gamma_o}`
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    density: double, optional (default: 0.1)
        Structural density given by `edges / (nodes*nodes)`.
    edges : int (optional)
        The number of edges between the nodes
    avg_deg : double, optional
        Average degree of the neurons given by `edges / nodes`.
    weighted : bool, optional (default: True)
        @todo
        Whether the graph edges have weights.
    directed : bool, optional (default: True)
        Whether the graph is directed or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes. can contain multiple edges between two
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment.
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`)
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.

    Returns
    -------
    graph_fs : :class:`~nngt.Graph`
    
    Note
    ----
	As reciprocity increases, requested values of `in_exp` and `out_exp`
	will be less and less respected as the distribution will converge to a
	common exponent :math:`\gamma = (\gamma_i + \gamma_o) / 2`.
	Parameter `nodes` is required unless `from_graph` or `population` is
	provided.
    """
    # set node number and library graph
    graph_rsf = from_graph
    if graph_rsf is not None:
        nodes = graph_rsf.node_nb()
        graph_rsf.clear_all_edges()
    else:
        nodes = population.size if population is not None else nodes
        graph_rsf = nngt.Graph(
            name=name,nodes=nodes,directed=directed,**kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _random_scale_free(ids, ids, in_exp, out_exp, density,
                          edges, avg_deg, reciprocity, directed, multigraph)
        graph_rsf.new_edges(ia_edges)
    _set_options(graph_rsf, population, shape, positions)
    graph_rsf._graph_type = "random_scale_free"
    return graph_rsf


def price_scale_free(m, c=None, gamma=1, nodes=0, weighted=True, directed=True,
                     seed_graph=None, multigraph=False, name="PriceSF",
                     shape=None, positions=None, population=None,
                     from_graph=None, **kwargs):
    """
    @todo
    make the algorithm.
        
    Generate a Price graph model (Barabasi-Albert if undirected).

    Parameters 
    ----------
    m : int
        The number of edges each new node will make.
    c : double
        Constant added to the probability of a vertex receiving an edge.
    gamma : double
        Preferential attachment power.
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    weighted : bool, optional (default: True)
        @todo
			Whether the graph edges have weights.
    directed : bool, optional (default: True)
        Whether the graph is directed or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes.
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`~nngt.Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.
    
    Returns
    -------
    graph_price : :class:`~nngt.Graph` or subclass.
    
    Note
    ----
	`nodes` is required unless `from_graph` or `population` is provided.
    """
    nodes = ( ( population.size if population is not None else nodes )
              if from_graph is None else from_graph.node_nb() )
    #~ c = c if c is not None else 0 if directed else 1

    g = price_network(nodes,m,c,gamma,directed,seed_graph)
    graph_obj_price = nngt.GraphObject.to_graph_object(g)
    if from_graph is not None:
        from_graph.graph = graph_obj_price

    graph_price = nngt.Graph.from_library(g)
    #~ graph_price = (nngt.Graph(name=name, libgraph=graph_obj_price, **kwargs)
                   #~ if from_graph is None else from_graph)
    
    _set_options(graph_price, population, shape, positions)
    graph_price._graph_type = "price_scale_free"
    return graph_price

#
#---
# Small-world models
#------------------------

def newman_watts(coord_nb, proba_shortcut, nodes=0, weighted=True,
                 directed=True,multigraph=False, name="NW", shape=None,
                 positions=None, population=None, from_graph=None, **kwargs):
    """
    Generate a small-world graph using the Newman-Watts algorithm.
    
    @todo
        generate the edges of a circular graph to not replace the graph of the
        `from_graph` and implement chosen reciprocity.
    
    Parameters
    ----------
    coord_nb : int
        The number of neighbours for each node on the initial topological 
        lattice.
    proba_shortcut : double
        Probability of adding a new random (shortcut) edge for each existing 
        edge on the initial lattice.
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    density: double, optional (default: 0.1)
        Structural density given by `edges` / (`nodes`*`nodes`).
    edges : int (optional)
        The number of edges between the nodes
    avg_deg : double, optional
        Average degree of the neurons given by `edges` / `nodes`.
    weighted : bool, optional (default: True)
        @todo
        Whether the graph edges have weights.
    directed : bool, optional (default: True)
        Whether the graph is directed or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes.
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.
    
    Returns
    -------
    graph_nw : :class:`~nngt.Graph` or subclass
    
    Note
    ----
	`nodes` is required unless `from_graph` or `population` is provided.
    """
    # set node number and library graph
    graph_nw = from_graph
    if graph_nw is not None:
        nodes = graph_nw.node_nb()
        graph_nw.clear_all_edges()
    else:
        nodes = population.size if population is not None else nodes
        graph_nw = nngt.Graph(name=name,nodes=nodes,directed=directed,**kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _newman_watts(ids, ids, coord_nb, proba_shortcut, directed,
                                 multigraph)
        graph_nw.new_edges(ia_edges)
    _set_options(graph_nw, population, shape, positions)
    graph_nw._graph_type = "newman_watts"
    return graph_nw


#
#---
# Distance-based models
#------------------------

def distance_rule(scale, rule="exp", shape=None, neuron_density=1000., nodes=0,
                  density=-1., edges=-1, avg_deg=-1., unit='um', weighted=True,
                  directed=True, multigraph=False, name="DR", positions=None,
                  population=None, from_graph=None, **kwargs):
    """
    Create a graph using a 2D distance rule to create the connection between
    neurons. Available rules are linear and exponential.

    Parameters
    ----------
    scale : float
        Characteristic scale for the distance rule. E.g for linear distance-
        rule, :math:`P(i,j) \propto (1-d_{ij}/scale))`, whereas for the
        exponential distance-rule, :math:`P(i,j) \propto e^{-d_{ij}/scale}`.
    rule : string, optional (default: 'exp')
        Rule that will be apply to draw the connections between neurons.
        Choose among "exp" (exponential), "lin" (linear),
        "power" (power-law, not implemented yet).
    shape : :class:`~nngt.geometry.Shape`, optional (default: None)
        Shape of the neurons' environment. If not specified, a square will be
        created with the appropriate dimensions for the number of neurons and
        the neuron spatial density.
    neuron_density : float, optional (default: 1000.)
        Density of neurons in space (:math:`neurons \cdot mm^{-2}`).
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    density: double, optional (default: 0.1)
        Structural density given by `edges` / (`nodes` * `nodes`).
    edges : int (optional)
        The number of edges between the nodes
    avg_deg : double, optional
        Average degree of the neurons given by `edges` / `nodes`.
    unit : string (default: 'um')
        Unit for the length `scale` among 'um' (:math:`\mu m`), 'mm', 'cm',
        'dm', 'm'.
    weighted : bool, optional (default: True)
        @todo
        Whether the graph edges have weights.
    directed : bool, optional (default: True)
        Whether the graph is directed or not.
    multigraph : bool, optional (default: False)
        Whether the graph can contain multiple edges between two
        nodes.
    name : string, optional (default: "DR")
        Name of the created graph.
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D (N, 2) or 3D (N, 3) shaped array containing the positions of the
        neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.
    """
    # set node number and library graph
    graph_dr = from_graph
    if graph_dr is not None:
        nodes = graph_dr.node_nb()
        graph_dr.clear_all_edges()
    else:
        nodes = population.size if population is not None else nodes
    # check shape
    if shape is None:
        h = w = np.sqrt(float(nodes)/neuron_density)
        shape = nngt.geometry.Shape.rectangle(h, w)
    if graph_dr is None:
        graph_dr = nngt.SpatialGraph(
            name=name, nodes=nodes, directed=directed, shape=shape,
            positions=positions, **kwargs)
    else:
        Graph.make_spatial(graph_dr, shape, positions=positions)
    positions = graph_dr.get_positions().T
    # add edges
    ia_edges = None
    conversion_factor = conversion_magnitude(shape.unit, unit)
    if unit != shape.unit:
        positions = np.multiply(conversion_factor, positions)
    if nodes > 1:
        ids = np.arange(0, nodes, dtype=np.uint)
        ia_edges = _distance_rule(ids, ids, density, edges, avg_deg, scale,
                                  rule, shape, positions, conversion_factor,
                                  directed, multigraph, **kwargs)
        graph_dr.new_edges(ia_edges)
    # set options (graph has already been made spatial)
    _set_options(graph_dr, population, None, None)
    graph_dr._graph_type = "{}_distance_rule".format(rule)
    return graph_dr


# -------------------- #
# Polyvalent generator #
# -------------------- #

_di_generator = {
    "distance_rule": distance_rule,
    "erdos_renyi": erdos_renyi,
    "fixed_degree": fixed_degree,
    "gaussian_degree": gaussian_degree,
    "newman_watts": newman_watts,
    "price_scale_free": price_scale_free,
    "random_scale_free": random_scale_free
}


def generate(di_instructions, **kwargs):
    '''
    Generate a :class:`~nngt.Graph` or one of its subclasses from a ``dict``
    containing all the relevant informations.
    
    Parameters
    ----------
    di_instructions : ``dict``
        Dictionary containing the instructions to generate the graph. It must
        have at least ``"graph_type"`` in its keys, with a value among
        ``"distance_rule", "erdos_renyi", "fixed_degree", "newman_watts",
        "price_scale_free", "random_scale_free"``. Depending on the type,
        `di_instructions` should also contain at least all non-optional
        arguments of the generator function.
    
    See also
    --------
    :mod:`~nngt.generation`
    '''
    graph_type = di_instructions["graph_type"]
    instructions = deepcopy(di_instructions)
    instructions.update(kwargs)
    return _di_generator[graph_type](**instructions)


#-----------------------------------------------------------------------------#
# Connecting groups
#------------------------
#

_di_gen_edges = {
    "distance_rule": _distance_rule,
    "erdos_renyi": _erdos_renyi,
    "fixed_degree": _fixed_degree,
    "gaussian_degree": _gaussian_degree,
    "newman_watts": _newman_watts,
    "price_scale_free": _price_scale_free,
    "random_scale_free": _random_scale_free
}


_di_default = {  "density": -1.,
                "edges": -1,
                "avg_deg": -1,
                "reciprocity": -1,
                "directed": True,
                "multigraph": False }


_one_pop_models = ("newman_watts",)


def connect_neural_types(network, source_type, target_type, graph_model,
                         model_param):
    '''
    Function to connect excitatory and inhibitory population with a given graph
    model.
    
    @todo
        make the modifications for only a set of edges
    
    Parameters
    ----------
    network : :class:`Network` or :class:`SpatialNetwork`
        The network to connect.
    source_type : int
        The type of source neurons (``1`` for excitatory, ``-1`` for
        inhibitory neurons).
    source_type : int
        The type of target neurons.
    graph_model : string
        The name of the connectivity model (among "erdos_renyi", 
        "random_scale_free", "price_scale_free", and "newman_watts").
    model_param : dict
        Dictionary containing the model parameters (the keys are the keywords
        of the associated generation function --- see above).
    '''
    edges, source_ids, target_ids = None, [], []
    di_param = _di_default.copy()
    di_param.update(model_param)
    for group in iter(network._population.values()):
        if group.neuron_type == source_type:
            source_ids.extend(group.ids)
        elif group.neuron_type == target_type:
            target_ids.extend(group.ids)
    if source_type == target_type:
        edges = _di_gen_edges[graph_model](source_ids, source_ids, **di_param)
    else:
        edges = _di_gen_edges[graph_model](source_ids, target_ids, **di_param)
    network.new_edges(edges)
    if issubclass(network.__class__, nngt.SpatialGraph):
        nngt.Connections.distances(network)
    network._graph_type += "_neural_type_connect"


def connect_neural_groups(network, source_groups, target_groups, graph_model,
                          model_param):
    '''
    Function to connect excitatory and inhibitory population with a given graph
    model.
    
    @todo
        make the modifications for only a set of edges
    
    Parameters
    ----------
    network : :class:`Network` or :class:`SpatialNetwork`
        The network to connect.
    source_groups : str or tuple
        Names of the source groups (which contain the pre-synaptic neurons)
    target_groups : str or tuple
        Names of the target groups (which contain the post-synaptic neurons)
    graph_model : string
        The name of the connectivity model (among "erdos_renyi", 
        "random_scale_free", "price_scale_free", and "newman_watts").
    model_param : dict
        Dictionary containing the model parameters (the keys are the keywords
        of the associated generation function --- see above).
    '''
    edges, source_ids, target_ids = None, [], []
    di_param = _di_default.copy()
    di_param.update(model_param)
    if isinstance(source_groups, str):
        source_groups = [source_groups]
    if isinstance(target_groups, str):
        target_groups = [target_groups]
    for name, group in iter(network._population.items()):
        if name in source_groups:
            source_ids.extend(group.ids)
        elif name in target_groups:
            target_ids.extend(group.ids)
    if source_groups == target_groups:
        edges = _di_gen_edges[graph_model](source_ids, source_ids, **di_param)
    else:
        edges = _di_gen_edges[graph_model](source_ids, target_ids, **di_param)
    network.new_edges(edges)
    if issubclass(network.__class__, nngt.SpatialGraph):
       nngt.Connections.distances(network)
    network._graph_type += "_neural_group_connect"
