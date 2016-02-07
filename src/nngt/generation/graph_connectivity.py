#!/usr/bin/env python
#-*- coding:utf-8 -*-

""" Connectivity generators for Graph """

import numpy as np

import nngt
from nngt.core import GraphObject
from nngt.lib.connect_tools import *



def _set_options(graph, weighted, population, shape, positions):
    if weighted:
        graph.set_weights()
    if issubclass(graph.__class__, nngt.Network):
        Connections.delays(graph)
    elif population is not None:
        nngt.Network.make_network(graph, population)
    if shape is not None:
        nngt.SpatialGraph.make_spatial(graph, shape, positions)


#-----------------------------------------------------------------------------#
# Fixed degree
#------------------------
#

def fixed_degree(degree, degree_type='in', nodes=0, reciprocity=-1.,
                 weighted=True, directed=True, multigraph=False, name="ER",
                 shape=None, positions=None, population=None, from_graph=None,
                 **kwargs):
    """
    Generate a random graph with constant in- or out-degree.

    Parameters
    ----------
    degree : int
        The value of the constant degree.
    degree_type : str, optional (default: 'in')
        The type of the fixed degree, among 'in', 'out' or 'total' (@todo: not 
        implemented yet).
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
    shape : :class:`~nngt.core.Shape`, optional (default: None)
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

    Notes
    -----
    `nodes` is required unless `from_graph` or `population` is provided.
    If an `from_graph` is provided, all preexistant edges in the
    object will be deleted before the new connectivity is implemented.
    """
    # set node number and library graph
    graph_obj_fd, graph_fd = None, from_graph
    if graph_fd is not None:
        nodes = graph_fd.node_nb()
        graph_fd.clear_edges()
        graph_obj_fd = graph_fd.graph
    else:
        nodes = population.size if population is not None else nodes
        graph_obj_fd = GraphObject(nodes, directed=True)
        graph_fd = nngt.Graph(name=name, libgraph=graph_obj_fd, **kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _fixed_degree(ids, ids, degree, degree_type, reciprocity,
                                 directed, multigraph)
        graph_fd.add_edges(ia_edges)
    _set_options(graph_fd, weighted, population, shape, positions)
    graph_fd._graph_type = "fixed_{}_degree".format(degree_type)
    return graph_fd
    

#-----------------------------------------------------------------------------#
# Erdos-Renyi
#------------------------
#

def erdos_renyi(nodes=0, density=0.1, edges=-1, avg_deg=-1., reciprocity=-1.,
                weighted=True, directed=True, multigraph=False, name="ER",
                shape=None, positions=None, population=None, from_graph=None,
                **kwargs):
    """
    Generate a random graph as defined by Erdos and Renyi but with a
    reciprocity that can be chosen.

    Parameters
    ----------
    nodes : int, optional (default: None)
        The number of nodes in the graph.
    density : double, optional (default: 0.1)
        Structural density given by `edges` / `nodes`:math:`^2`.
    edges : int (optional)
        The number of edges between the nodes
    avg_deg : double, optional
        Average degree of the neurons given by `edges` / `nodes`.
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
    shape : :class:`~nngt.core.Shape`, optional (default: None)
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

    Notes
    -----
    `nodes` is required unless `from_graph` or `population` is provided.
    If an `from_graph` is provided, all preexistant edges in the
    object will be deleted before the new connectivity is implemented.
    """
    # set node number and library graph
    graph_obj_er, graph_er = None, from_graph
    if graph_er is not None:
        nodes = graph_er.node_nb()
        graph_er.clear_edges()
        graph_obj_er = graph_er.graph
    else:
        nodes = population.size if population is not None else nodes
        graph_obj_er = GraphObject(nodes, directed=directed)
        graph_er = nngt.Graph(name=name, libgraph=graph_obj_er, **kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _erdos_renyi(ids, ids, density, edges, avg_deg, reciprocity,
                                directed, multigraph)
        graph_er.add_edges(ia_edges)
    _set_options(graph_er, weighted, population, shape, positions)
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
        :math:`p(k_i) \propto k_i^{-\gamma_i}
    out_exp : float
        Absolute value of the out-degree exponent :math:`\gamma_o`, such that
        :math:`p(k_o) \propto k_o^{-\gamma_o}
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
        nodes. can contain multiple edges between two
    name : string, optional (default: "ER")
        Name of the created graph.
    shape : :class:`~nngt.core.Shape`, optional (default: None)
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
    
    Notes
    -----
    As reciprocity increases, requested values of `in_exp` and `out_exp` will
    be less and less respected as the distribution will converge to a common
    exponent :math:`\gamma = \frac{\gamma_i + \gamma_o}{2}`.
    Parameter `nodes` is required unless `from_graph` or `population` is
    provided.
    """
    # set node number and library graph
    graph_obj_rsf, graph_rsf = None, from_graph
    if graph_rsf is not None:
        nodes = graph_rsf.node_nb()
        graph_rsf.clear_edges()
        graph_obj_rsf = graph_rsf.graph
    else:
        nodes = population.size if population is not None else nodes
        graph_obj_rsf = GraphObject(nodes, directed=directed)
        graph_rsf = nngt.Graph(name=name, libgraph=graph_obj_rsf, **kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _random_scale_free(ids, ids, in_exp, out_exp, density,
                          edges, avg_deg, reciprocity, directed, multigraph)
        graph_rsf.add_edges(ia_edges)
    _set_options(graph_rsf, weighted, population, shape, positions)
    graph_rsf._graph_type = "random_scale_free"
    return graph_rsf

def price_scale_free(m, c=None, gamma=1, nodes=0, weighted=True, directed=True,
                     seed_graph=None, multigraph=False, name="PriceSF",
                     shape=None, positions=None, population=None,
                     from_graph=None, **kwargs):
    """
    @todo: make the algorithm.
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
    shape : :class:`~nngt.core.Shape`, optional (default: None)
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
    
    Notes
    -----
    `nodes` is required unless `from_graph` or `population` is provided.
    """
    nodes = ( ( population.size if population is not None else nodes )
              if from_graph is None else from_graph.node_nb() )
    #~ c = c if c is not None else 0 if directed else 1
    
    graph_obj_price = GraphObject.to_graph_object(
                        price_network(nodes,m,c,gamma,directed,seed_graph))
    if from_graph is not None:
        from_graph.graph = graph_obj_price
    
    graph_price = (nngt.Graph(name=name, libgraph=graph_obj_price, **kwargs)
                   if from_graph is None else from_graph)
    
    _set_options(graph_price, weighted, population, shape, positions)
    graph_price._graph_type = "price_scale_free"
    return graph_price

#
#---
# Small-world models
#------------------------

def newman_watts(coord_nb, proba_shortcut, nodes=0, directed=True,
                 multigraph=False, name="ER", shape=None, positions=None,
                 population=None, from_graph=None, **kwargs):
    """
    Generate a small-world graph using the Newman-Watts algorithm.
    @todo: generate the edges of a circular graph to not replace the graph
    of the `from_graph` and implement chosen reciprocity.
    
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
    shape : :class:`~nngt.core.Shape`, optional (default: None)
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
    
    Notes
    -----
    `nodes` is required unless `from_graph` or `population` is provided.
    """
    # set node number and library graph
    graph_obj_nw, graph_nw = None, from_graph
    if graph_nw is not None:
        nodes = graph_nw.node_nb()
        graph_nw.clear_edges()
        graph_obj_nw = graph_nw.graph
    else:
        nodes = population.size if population is not None else nodes
        graph_obj_nw = GraphObject(nodes, directed=directed)
        graph_nw = nngt.Graph(name=name, libgraph=graph_obj_nw, **kwargs)
    # add edges
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _newman_watts(ids, ids, coord_nb, proba_shortcut, directed,
                                 multigraph)
        graph_nw.add_edges(ia_edges)
    _set_options(graph_nw, weighted, population, shape, positions)
    graph_nw._graph_type = "newman_watts"
    return graph_nw


#
#---
# Distance-based models
#------------------------

def distance_rule(scale, rule="exp", shape=None, neuron_density=1000., nodes=0,
                  density=0.1, edges=-1, avg_deg=-1., weighted=True,
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
        Choose among "exp" (exponential), "lin" (linear, not implemented yet),
        "power" (power-law, not implemented yet).
    shape : :class:`~nngt.core.Shape`, optional (default: None)
        Shape of the neurons' environment. If not specified, a square will be
        created with the appropriate dimensions for the number of neurons and
        the neuron spatial density.
    neuron_density : float, optional (default: 1000.)
        Density of neurons in space (:math:`neurons \cdot mm^{-2}).
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
    name : string, optional (default: "DR")
        Name of the created graph.
    positions : :class:`numpy.ndarray`, optional (default: None)
        A 2D or 3D array containing the positions of the neurons in space.
    population : :class:`~nngt.NeuralPop`, optional (default: None)
        Population of neurons defining their biological properties (to create a
        :class:`~nngt.Network`).
    from_graph : :class:`Graph` or subclass, optional (default: None)
        Initial graph whose nodes are to be connected.
    """
    # set node number and library graph
    graph_obj_dr, graph_dr = None, from_graph
    if graph_dr is not None:
        nodes = graph_dr.node_nb()
        graph_dr.clear_edges()
        graph_obj_dr = graph_dr.graph
    else:
        nodes = population.size if population is not None else nodes
        graph_obj_dr = GraphObject(nodes, directed=directed)
    # generate container
    h = w = np.sqrt(float(nodes)/neuron_density)
    if graph_dr is None:
        shape = shape if shape is not None else nngt.Shape.rectangle(None,h,w)
        graph_dr = nngt.SpatialGraph(name=name, libgraph=graph_obj_dr, shape=shape,
                                **kwargs)
    else:
        if not issubclass(graph_dr.__class__, nngt.SpatialGraph):
            shape = shape if shape is not None else nngt.Shape.rectangle(self,h,w)
            nngt.SpatialGraph.make_spatial(graph_dr, shape, positions)
    # add edges
    positions = graph_dr.position
    ia_edges = None
    if nodes > 1:
        ids = range(nodes)
        ia_edges = _distance_rule(ids, ids, density, edges, avg_deg, scale,
                                  rule, shape, positions, directed, multigraph)
        print(ia_edges)
        graph_dr.add_edges(ia_edges)
    # set options
    _set_options(graph_dr, weighted, population, shape=None, positions=None)
    graph_dr._graph_type = "{}_distance_rule".format(rule)
    return graph_dr


#-----------------------------------------------------------------------------#
# Connecting groups
#------------------------
#

di_gen_func = { "erdos_renyi": _erdos_renyi, 
    "random_scale_free": _random_scale_free,
    "price_scale_free": _price_scale_free,
    "newman_watts": _newman_watts }

di_default = {  "density": 0.1,
                "edges": -1,
                "avg_deg": -1,
                "reciprocity": -1,
                "directed": True,
                "multigraph": False }

one_pop_models = ("newman_watts",)

def connect_neural_types(network, source_type, target_type, graph_model,
                         model_param, weighted=True):
    '''
    Function to connect excitatory and inhibitory population with a given graph
    model.
    @todo: make the modifications for only a set of edges
    
    Parameters
    ----------
    network : :class:`Network` or :class:`SpatialNetwork`
        The network to connect.
    source_type : int
        The type of source neurons (``1`` for excitatory, ``-1 for 
        inhibitory neurons).
    source_type : int
        The type of target neurons.
    graph_model : string
        The name of the connectivity model (among "erdos_renyi", 
        "random_scale_free", "price_scale_free", and "newman_watts").
    model_param : dict
        Dictionary containing the model parameters (the keys are the keywords
        of the associated generation function --- see above).
    weighted : bool, optional (default: True)
        @todo
        Whether the graph edges have weights.
    '''
    edges, source_ids, target_ids = None, [], []
    di_param = di_default.copy()
    di_param.update(model_param)
    for group in network._population.itervalues():
        if group.neuron_type == source_type:
            source_ids.extend(group._id_list)
        elif group.neuron_type == target_type:
            target_ids.extend(group._id_list)
    if source_type == target_type:
        edges = di_gen_func[graph_model](source_ids,source_ids,**di_param)
        network.add_edges(edges)
    else:
        edges = di_gen_func[graph_model](source_ids,target_ids,**di_param)
        network.add_edges(edges)
    #~ network.set_weights(edges)
    if weighted:
        network.set_weights()
    #~ Connections.delays(network, elist=edges)
    Connections.delays(network)
    if issubclass(network.__class__, nngt.SpatialGraph):
        Connections.distances(network)
    network._graph_type += "_neural_type_connect"

def connect_neural_groups(network, source_groups, target_groups, graph_model,
                         model_param):
    '''
    Function to connect excitatory and inhibitory population with a given graph
    model.
    @todo: make the modifications for only a set of edges
    
    Parameters
    ----------
    network : :class:`Network` or :class:`SpatialNetwork`
        The network to connect.
    source_groups : tuple of strings
        Names of the source groups (which contain the pre-synaptic neurons)
    target_groups : tuple of strings
        Names of the target groups (which contain the post-synaptic neurons)
    graph_model : string
        The name of the connectivity model (among "erdos_renyi", 
        "random_scale_free", "price_scale_free", and "newman_watts").
    model_param : dict
        Dictionary containing the model parameters (the keys are the keywords
        of the associated generation function --- see above).
    '''
    edges, source_ids, target_ids = None, [], []
    di_param = di_default.copy()
    di_param.update(model_param)
    for name, group in network._population.iteritems():
        if name in source_groups:
            source_ids.extend(group._id_list)
        elif name in target_groups:
            target_ids.extend(group._id_list)
    if source_groups == target_groups:
        edges = di_gen_func[graph_model](source_ids,source_ids,**di_param)
        network.add_edges(edges)
    else:
        edges = di_gen_func[graph_model](source_ids, target_ids, **di_param)
        network.add_edges(edges)
    #~ network.set_weights(edges)
    network.set_weights()
    #~ Connections.delays(network, elist=edges)
    Connections.delays(network)
    if issubclass(network.__class__, nngt.SpatialGraph):
       Connections.distances(network)
    network._graph_type += "_neural_group_connect"
