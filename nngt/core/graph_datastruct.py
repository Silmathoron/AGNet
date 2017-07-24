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

""" Graph data strctures in NNGT """

from collections import OrderedDict
import logging
import weakref

import numpy as np
from numpy.random import randint, uniform
import scipy.sparse as ssp
import scipy.spatial as sptl

from nngt.lib import (InvalidArgument, nonstring_container, default_neuron,
                      default_synapse, POS, WEIGHT, DELAY, DIST, TYPE, BWEIGHT)
from nngt.lib.rng_tools import _eprop_distribution


__all__ = [
    'GroupProperty',
    'NeuralPop',
]


logger = logging.getLogger(__name__)


#-----------------------------------------------------------------------------#
# NeuralPop
#------------------------
#

class NeuralPop(OrderedDict):

    """
    The basic class that contains groups of neurons and their properties.

    :ivar has_models: :class:`bool`,
        ``True`` if every group has a ``model`` attribute.
    """

    #-------------------------------------------------------------------------#
    # Class attributes and methods

    @classmethod
    def from_network(cls, graph, *args):
        '''
        Make a NeuralPop object from a network. The groups of neurons are
        determined using instructions from an arbitrary number of
        :class:`~nngt.properties.GroupProperties`.
        '''
        return cls(parent=graph, graph=graph, group_prop=args)
    
    @classmethod
    def from_groups(cls, groups, names=None, parent=None, with_models=True):
        '''
        Make a NeuralPop object from a (list of) :class:`~nngt.NeuralGroup`
        object(s).

        Parameters
        ----------
        groups : list of :class:`~nngt.NeuralGroup` objects
            Groups that will be used to form the population.
        names : list of str, optional (default: None)
            Names that can be used as keys to retreive a specific group. If not
            provided, keys will be the position of the group in `groups`,
            stored as a string. In this case, the first group in a population
            named `pop` will be retreived by either `pop[0]` or `pop['0']`.
        parent : :class:`~nngt.Graph`, optional (default: None)
            Parent if the population is created from an exiting graph.

        Note
        ----
        If the population is not generated from an existing
        :class:`~nngt.Graph` and the groups do not contain explicit ids, then
        the ids will be generated upon population creation: the first group, of
        size N0, will be associated the indices 0 to N0 - 1, the second group
        (size N1), will get N0 to N0 + N1 - 1, etc.
        '''
        if not nonstring_container(groups):
            groups = [groups]
        gsize = len(groups)
        neurons = []
        names = [str(i) for i in range(gsize)] if names is None else names
        assert len(names) == gsize, "`names` and `groups` must have " +\
                                   "the same size."
        current_size = 0
        for g in groups:
            # generate the neuron ids if necessary
            ids = g.ids
            if len(ids) == 0:
                ids = list(range(current_size, current_size + g.size))
                g.ids = ids
            current_size += len(ids)
            neurons.extend(ids)
        neurons = list(set(neurons))
        pop = cls(current_size, parent=parent, with_models=with_models)
        for name, g in zip(names, groups):
            pop[name] = g
        return pop

    @classmethod
    def uniform(cls, size, neuron_model=default_neuron, neuron_param=None,
                syn_model=default_synapse, syn_param=None, parent=None):
        ''' Make a NeuralPop of identical neurons '''
        neuron_param = {} if neuron_param is None else neuron_param.copy()
        syn_param = {} if syn_param is None else syn_param.copy()
        pop = cls(size, parent)
        pop.create_group("default", range(size), 1, neuron_model, neuron_param,
           syn_model, syn_param)
        return pop

    @classmethod
    def exc_and_inhib(cls, size, iratio=0.2, en_model=default_neuron,
                      en_param=None, es_model=default_synapse, es_param=None,
                      in_model=default_neuron, in_param=None,
                      is_model=default_synapse, is_param=None, parent=None):
        '''
        Make a NeuralPop with a given ratio of inhibitory and excitatory
        neurons.
        '''
        num_exc_neurons = int(size*(1-iratio))
        pop = cls(size, parent)
        pop.create_group("excitatory", range(num_exc_neurons), 1, en_model,
                         en_param, es_model, es_param)
        pop.create_group("inhibitory", range(num_exc_neurons, size), -1,
                         in_model, in_param, is_model, es_param)
        return pop

    @classmethod
    def copy(cls, pop):
        ''' Copy an existing NeuralPop '''
        new_pop = cls.__init__(pop.has_models)
        for name, group in pop.items():
             new_pop.create_group(name, group.ids, group.model,
                               group.neuron_param)
        return new_pop

    #-------------------------------------------------------------------------#
    # Contructor and instance attributes

    def __init__(self, size, parent=None, with_models=True, **kwargs):
        '''
        Initialize NeuralPop instance

        Parameters
        ----------
        size : int
            Number of neurons that the population will contain.
        parent : :class:`~nngt.Network`, optional (default: None)
            Network associated to this population.
        with_models : :class:`bool`
            whether the population's groups contain models to use in NEST
        **kwargs : :class:`dict`

        Returns
        -------
        pop : :class:`~nngt.NeuralPop` object.
        '''
        self._is_valid = False
        self._size = size if parent is None else parent.node_nb()
        # array of strings containing the name of the group where each neuron
        # belongs
        self._neuron_group = np.empty(self._size, dtype=object)
        self._max_id = 0  # highest id among the existing neurons + 1
        super(NeuralPop, self).__init__()
        if "graph" in kwargs.keys():
            dic = _make_groups(kwargs["graph"], kwargs["group_prop"])
            self._is_valid = True
            self.update(dic)
        self._has_models = with_models
    
    def __getitem__(self, key):
        if isinstance(key, int):
            new_key = tuple(self.keys())[key]
            return OrderedDict.__getitem__(self, new_key)
        else:
            return OrderedDict.__getitem__(self, key)
    
    def __setitem__(self, key, value):
        self._validity_check(key, value)
        if isinstance(key, int):
            new_key = tuple(self.keys())[key]
            OrderedDict.__setitem__(self, new_key, value)
        else:
            OrderedDict.__setitem__(self, key, value)
        # update _max_id
        if len(value.ids) > 0:
            self._max_id = max(self._max_id, *value.ids) + 1
        # update the group node property
        self._neuron_group[value.ids] = key
        if None in list(self._neuron_group):
            self._is_valid = False
        else:
            self._is_valid = True

    @property
    def size(self):
        return self._size

    @property
    def has_models(self):
        return self._has_models

    @property
    def is_valid(self):
        return self._is_valid

    #-------------------------------------------------------------------------#
    # Methods

    def create_group(self, name, neurons, ntype=1, neuron_model=None,
                     neuron_param=None, syn_model=default_synapse,
                     syn_param=None):
        '''
        Create a new groupe from given properties.
        
        Parameters
        ----------
        name : str
            Name of the group.
        neurons : array-like
            List of the neurons indices.
        ntype : int, optional (default: 1)
            Type of the neurons : 1 for excitatory, -1 for inhibitory.
        neuron_model : str, optional (default: None)
            Name of a neuron model in NEST.
        neuron_param : dict, optional (default: None)
            Parameters for `neuron_model` in the NEST simulator. If None,
            default parameters will be used.
        syn_model : str, optional (default: "static_synapse")
            Name of a synapse model in NEST.
        syn_param : dict, optional (default: None)
            Parameters for `syn_model` in the NEST simulator. If None,
            default parameters will be used.
        '''
        neuron_param = {} if neuron_param is None else neuron_param.copy()
        syn_param = {} if syn_param is None else syn_param.copy()
        # create a group
        if isinstance(neurons, int):
            group_size = neurons
            neurons = list(range(self._max_id, self._max_id + group_size))
        group = NeuralGroup(neurons, ntype, neuron_model, neuron_param,
                            syn_model, syn_param)
        self[name] = group

    def set_model(self, model, group=None):
        '''
        Set the groups' models.

        Parameters
        ----------
        model : dict
            Dictionary containing the model type as key ("neuron" or "synapse")
            and the model name as value (e.g. {"neuron": "iaf_neuron"}).
        group : list of strings, optional (default: None)
            List of strings containing the names of the groups which models
            should be updated.

        Note
        ----
        By default, synapses are registered as "static_synapse"s in NEST;
        because of this, only the ``neuron_model`` attribute is checked by
        the ``has_models`` function: it will answer ``True`` if all groups
        have a 'non-None' ``neuron_model`` attribute.

        .. warning::
            No check is performed on the validity of the models, which means
            that errors will only be detected when building the graph in NEST.
        '''
        if group is None:
            group = self.keys()
        try:
            for key,val in iter(model.items()):
                for name in group:
                    if key == "neuron":
                        self[name].neuron_model = val
                    elif key == "synapse":
                        self[name].syn_model = val
                    else:
                        raise ValueError(
                            "Model type {} is not valid; choose among 'neuron'"
                            " or 'synapse'.".format(key))
        except:
            if model is not None:
                raise InvalidArgument(
                    "Invalid model dict or group; see docstring.")
        b_has_models = True
        if model is None:
            b_has_models = False
        for group in iter(self.values()):
            b_has_model *= group.has_model
        self._has_models = b_has_models

    def set_param(self, param, group=None):
        '''
        Set the groups' parameters.

        Parameters
        ----------
        param : dict
            Dictionary containing the model type as key ("neuron" or "synapse")
            and the model parameter as value (e.g. {"neuron": {"C_m": 125.}}).
        group : list of strings, optional (default: None)
            List of strings containing the names of the groups which models
            should be updated.

        .. warning::
            No check is performed on the validity of the parameters, which
            means that errors will only be detected when building the graph in
            NEST.
        '''
        if group is None:
            group = self.keys()
        try:
            for key,val in iter(param.items()):
                for name in group:
                    if key == "neuron":
                        self[name].neuron_param = val
                    elif key == "synapse":
                        self[name].syn_param = val
                    else:
                        raise ValueError(
                            "Model type {} is not valid; choose among 'neuron'"
                            " or 'synapse'.".format(key))
        except:
            raise InvalidArgument(
                "Invalid param dict or group; see docstring.")

    def get_param(self, groups=None, neurons=None, element="neuron"):
        '''
        Return the `element` (neuron or synapse) parameters for neurons or
        groups of neurons in the population.

        Parameters
        ----------
        groups : ``str``, ``int`` or array-like, optional (default: ``None``)
            Names or numbers of the groups for which the neural properties
            should be returned.
        neurons : int or array-like, optional (default: ``None``)
            IDs of the neurons for which parameters should be returned.
        element : ``list`` of ``str``, optional (default: ``"neuron"``)
            Element for which the parameters should be returned (either
            ``"neuron"`` or ``"synapse"``).

        Returns
        -------
        param : ``list``
            List of all dictionaries with the elements' parameters.
        '''
        if neurons is not None:
            groups = self._neuron_group[neurons]
        elif groups is None:
            groups = tuple(self.keys())
        key = "neuron_param" if element == "neuron" else "syn_param"
        if isinstance(groups, (str, int)):
            return self[groups].properties[key]
        else:
            param = []
            for group in groups:
                param.append(self[group].properties[key])
            return param

    def get_group(neurons, numbers=False):
        '''
        Return the group of the neurons.
        
        Parameters
        ----------
        neurons : int or array-like
            IDs of the neurons for which the group should be returned.
        numbers : bool, optional (default: False)
            Whether the group identifier should be returned as a number; if
            ``False``, the group names are returned.
        '''
        if not numbers:
            return self._neuron_group[neurons]
        elif isinstance(neurons, int):
            keys.index(self._neuron_group[neurons])
        else:
            keys = tuple(self.keys())
            return [keys.index(self._neuron_group[n]) for n in neurons]

    def add_to_group(self, group_name, ids):
        self[group_name].ids += list(ids)
        self._neuron_group[ids] = group_name
        if None in list(self._neuron_group):
            self._is_valid = False
        else:
            self._is_valid = True
    
    def _validity_check(self, name, group):
        if self._has_models and not group.has_model:
            raise AttributeError(
                "This NeuralPop requires group to have a model attribute that "
                "is not `None`; to disable this, use `set_models(None)` "
                "method on this NeuralPop instance.")
        elif group.has_model and not self._has_models:
            logger.warning(
                "This NeuralPop is not set to take models into account; use "
                "the `set_models` method to change its behaviour.")


# ----------------------------- #
# NeuralGroup and GroupProperty #
# ----------------------------- #

class NeuralGroup:

    """
    Class defining groups of neurons.

    :ivar ids: :obj:`list` of :obj:`int`
        the ids of the neurons in this group.
    :ivar neuron_type: :class:`int`
        the default is ``1`` for excitatory neurons; ``-1`` is for interneurons
    :ivar model: :class:`string`, optional (default: None)
        the name of the model to use when simulating the activity of this group
    :ivar neuron_param: :class:`dict`, optional (default: {})
        the parameters to use (if they differ from the model's defaults)

    Note
    ----
    By default, synapses are registered as ``"static_synapse"`` in NEST;
    because of this, only the ``neuron_model`` attribute is checked by the
    ``has_model`` function.

    .. warning::
        Equality between :class:`~nngt.properties.NeuralGroup`s only compares
        the neuronal and synaptic ``model`` and ``param`` attributes, i.e.
        groups differing only by their ``ids`` will register as equal.
    """

    def __init__ (self, nodes=None, ntype=1, model=None, neuron_param=None,
                  syn_model=None, syn_param=None):
        '''
        Create a group of neurons (empty group is default, but it is not a
        valid object for most use cases).

        Parameters
        ----------
        nodes : int or array-like, optional (default: None)
            Desired size of the group or, a posteriori, NNGT indices of the
            neurons in an existing graph.
        ntype : int, optional (default: 1)
            Type of the neurons (1 for excitatory, -1 for inhibitory).
        model : str, optional (default: None)
            NEST model for the neuron.
        neuron_param : dict, optional (default: model defaults)
            Dictionary containing the parameters associated to the NEST model.
        syn_model : str, optional (default: "static_synapse")
            NEST model for the incoming synapses.
        syn_param : dict, optional (default: model defaults)
            Dictionary containing the parameters associated to the NEST model.

        Returns
        -------
        A new :class:`~nngt.core.NeuralGroup` instance.
        '''
        neuron_param = {} if neuron_param is None else neuron_param.copy()
        syn_param = {} if syn_param is None else syn_param.copy()
        self._has_model = False if model is None else True
        self._neuron_model = model
        if nodes is None:
            self._desired_size = None
            self._ids = []
        elif nonstring_container(nodes):
            self._desired_size = None
            self._ids = list(nodes)
        elif isinstance(nodes, int):
            self._desired_size = nodes
            self._ids = []
        else:
            raise InvalidArgument('`nodes` must be either array-like or int.')
        self._nest_gids = None
        if self._has_model:
            self.neuron_param = neuron_param
            self.neuron_type = ntype
            self.syn_model = (syn_model if syn_model is not None
                              else "static_synapse")
            self.syn_param = syn_param

    def __eq__ (self, other):
        if isinstance(other, NeuralGroup):
            same_nmodel = ( self.neuron_model == other.neuron_model *
                            self.neuron_param == other.neuron_param )
            same_smodel = ( self.syn_model == other.syn_model *
                            self.syn_param == other.syn_param )
            return same_nmodel * same_smodel
        else:
            return False

    def __len__(self):
        return self.size

    @property
    def neuron_model(self):
        return self._neuron_model

    @neuron_model.setter
    def neuron_model(self, value):
        self._neuron_model = value
        self._has_model = False if value is None else True

    @property
    def size(self):
        if self._desired_size is not None:
            return self._desired_size
        return len(self._ids)

    @property
    def ids(self):
        return self._ids

    @ids.setter
    def ids(self, value):
        if self._desired_size is not None:
            logger.warning('The length of the `ids` passed is not the'
                           'same as the initial size that was declared.'
                           'Setting `ids` anyway, but check your code!')
        self._ids = value
        self._desired_size = None

    @property
    def nest_gids(self):
        return self._nest_gids

    @property
    def has_model(self):
        return self._has_model

    @property
    def properties(self):
        dic = { "neuron_type": self.neuron_type,
                "neuron_model": self._neuron_model,
                "neuron_param": self.neuron_param,
                "syn_model": self.syn_model,
                "syn_param": self.syn_param }
        return dic


class GroupProperty:

    """
    Class defining the properties needed to create groups of neurons from an
    existing :class:`~nngt.GraphClass` or one of its subclasses.

    :ivar size: :class:`int`
        Size of the group.
    :ivar constraints: :class:`dict`, optional (default: {})
        Constraints to respect when building the
        :class:`~nngt.properties.NeuralGroup` .
    :ivar neuron_model: :class:`string`, optional (default: None)
        name of the model to use when simulating the activity of this group.
    :ivar neuron_param: :class:`dict`, optional (default: {})
        the parameters to use (if they differ from the model's defaults)
    """

    def __init__ (self, size, constraints={}, neuron_model=None,
                  neuron_param={}, syn_model=None, syn_param={}):
        '''
        Create a new instance of GroupProperties.

        Notes
        -----
        The constraints can be chosen among:
            - "avg_deg", "min_deg", "max_deg" (:class:`int`) to constrain the
              total degree of the nodes
            - "avg/min/max_in_deg", "avg/min/max_out_deg", to work with the
              in/out-degrees
            - "avg/min/max_betw" (:class:`double`) to constrain the betweenness
              centrality
            - "in_shape" (:class:`nngt.geometry.Shape`) to chose neurons inside
              a given spatial region

        Examples
        --------
        >>> di_constrain = { "avg_deg": 10, "min_betw": 0.001 }
        >>> group_prop = GroupProperties(200, constraints=di_constrain)
        '''
        self.size = size
        self.constraints = constraints
        self.neuron_model = neuron_model
        self.neuron_param = neuron_param
        self.syn_model = syn_model
        self.syn_param = syn_param


def _make_groups(graph, group_prop):
    '''
    Divide `graph` into groups using `group_prop`, a list of group properties
    @todo
    '''
    pass


# ----------- #
# Connections #
# ----------- #

class Connections:

    """
    The basic class that computes the properties of the connections between
    neurons for graphs.
    """

    #-------------------------------------------------------------------------#
    # Class methods

    @staticmethod
    def distances(graph, elist=None, pos=None, dlist=None, overwrite=False):
        '''
        Compute the distances between connected nodes in the graph. Try to add
        only the new distances to the graph. If they overlap with previously
        computed distances, recomputes everything.

        Parameters
        ----------
        graph : class:`~nngt.Graph` or subclass
            Graph the nodes belong to.
        elist : class:`numpy.array`, optional (default: None)
            List of the edges.
        pos : class:`numpy.array`, optional (default: None)
            Positions of the nodes; note that if `graph` has a "position"
            attribute, `pos` will not be taken into account.
        dlist : class:`numpy.array`, optional (default: None)
            List of distances (for user-defined distances)

        Returns
        -------
        new_dist : class:`numpy.array`
            Array containing *ONLY* the newly-computed distances.
        '''
        n = graph.node_nb()
        elist = graph.edges_array if elist is None else elist
        if dlist is not None:
            assert isinstance(dlist, np.ndarray), "numpy.ndarray required in "\
                                                  "Connections.distances"
            graph.set_edge_attribute(DIST, value_type="double", values=dlist)
            return dlist
        else:
            pos = graph._pos if hasattr(graph, "_pos") else pos
            # compute the new distances
            if graph.edge_nb():
                ra_x = pos[elist[:,0], 0] - pos[elist[:,1], 0]
                ra_y = pos[elist[:,0], 1] - pos[elist[:,1], 1]
                ra_dist = np.sqrt( np.square(ra_x) + np.square(ra_y) )
                #~ ra_dist = np.tile( , 2)
                # update graph distances
                graph.set_edge_attribute(DIST, value_type="double",
                                         values=ra_dist, edges=elist)
                return ra_dist
            else:
                return []

    @staticmethod
    def delays(graph=None, dlist=None, elist=None, distribution="constant",
               parameters=None, noise_scale=None):
        '''
        Compute the delays of the neuronal connections.

        Parameters
        ----------
        graph : class:`~nngt.Graph` or subclass
            Graph the nodes belong to.
        dlist : class:`numpy.array`, optional (default: None)
            List of user-defined delays).
        elist : class:`numpy.array`, optional (default: None)
            List of the edges which value should be updated.
        distribution : class:`string`, optional (default: "constant")
            Type of distribution (choose among "constant", "uniform",
            "lognormal", "gaussian", "user_def", "lin_corr", "log_corr").
        parameters : class:`dict`, optional (default: {})
            Dictionary containing the distribution parameters.
        noise_scale : class:`int`, optional (default: None)
            Scale of the multiplicative Gaussian noise that should be applied
            on the weights.

        Returns
        -------
        new_delays : class:`scipy.sparse.lil_matrix`
            A sparse matrix containing *ONLY* the newly-computed weights.
        '''
        elist = np.array(elist) if elist is not None else elist
        if dlist is not None:
            assert isinstance(dlist, np.ndarray), "numpy.ndarray required in "\
                                                  "Connections.delays"
            num_edges = graph.edge_nb() if elist is None else elist.shape[0]
            if len(dlist) != num_edges:
                raise InvalidArgument("`dlist` must have one entry per edge.")
        else:
            parameters["btype"] = parameters.get("btype", "edge")
            parameters["use_weights"] = parameters.get("use_weights", False)
            dlist = _eprop_distribution(graph, distribution, elist=elist,
                                        **parameters)
        # add to the graph container
        if graph is not None:
            graph.set_edge_attribute(
                DELAY, value_type="double", values=dlist, edges=elist)
        return dlist

    @staticmethod
    def weights(graph=None, elist=None, wlist=None, distribution="constant",
                parameters={}, noise_scale=None):
        '''
        Compute the weights of the graph's edges.
        @todo: take elist into account

        Parameters
        ----------
        graph : class:`~nngt.Graph` or subclass
            Graph the nodes belong to.
        elist : class:`numpy.array`, optional (default: None)
            List of the edges (for user defined weights).
        wlist : class:`numpy.array`, optional (default: None)
            List of the weights (for user defined weights).
        distribution : class:`string`, optional (default: "constant")
            Type of distribution (choose among "constant", "uniform",
            "lognormal", "gaussian", "user_def", "lin_corr", "log_corr").
        parameters : class:`dict`, optional (default: {})
            Dictionary containing the distribution parameters.
        noise_scale : class:`int`, optional (default: None)
            Scale of the multiplicative Gaussian noise that should be applied
            on the weights.

        Returns
        -------
        new_weights : class:`scipy.sparse.lil_matrix`
            A sparse matrix containing *ONLY* the newly-computed weights.
        '''
        parameters["btype"] = parameters.get("btype", "edge")
        parameters["use_weights"] = parameters.get("use_weights", False)
        elist = np.array(elist) if elist is not None else elist
        if wlist is not None:
            assert isinstance(wlist, np.ndarray), "numpy.ndarray required in "\
                                                  "Connections.weights"
            num_edges = graph.edge_nb() if elist is None else elist.shape[0]
            if len(wlist) != num_edges:
                raise InvalidArgument(
                    '''`wlist` must have one entry per edge. For graph {},
there are {} edges while {} values where provided'''.format(
                    graph.name, num_edges, len(wlist)))
        else:
            wlist = _eprop_distribution(graph, distribution, elist=elist,
                                        **parameters)
        # add to the graph container
        bwlist = (np.max(wlist) - wlist if np.any(wlist)
                  else np.repeat(0., len(wlist)))
        if graph is not None:
            graph.set_edge_attribute(
                WEIGHT, value_type="double", values=wlist, edges=elist)
            graph.set_edge_attribute(
                BWEIGHT, value_type="double", values=bwlist, edges=elist)
        return wlist

    @staticmethod
    def types(graph, inhib_nodes=None, inhib_frac=None):
        '''
        @todo

        Define the type of a set of neurons.
        If no arguments are given, all edges will be set as excitatory.

        Parameters
        ----------
        graph : :class:`~nngt.Graph` or subclass
            Graph on which edge types will be created.
        inhib_nodes : int, float or list, optional (default: `None`)
            If `inhib_nodes` is an int, number of inhibitory nodes in the graph
            (all connections from inhibitory nodes are inhibitory); if it is a
            float, ratio of inhibitory nodes in the graph; if it is a list, ids
            of the inhibitory nodes.
        inhib_frac : float, optional (default: `None`)
            Fraction of the selected edges that will be set as refractory (if
            `inhib_nodes` is not `None`, it is the fraction of the nodes' edges
            that will become inhibitory, otherwise it is the fraction of all
            the edges in the graph).

        Returns
        -------
        t_list : :class:`~numpy.ndarray`
            List of the edges' types.
        '''
        t_list = np.repeat(1.,graph.edge_nb())
        edges = graph.edges_array
        num_inhib = 0
        idx_inhib = []
        if inhib_nodes is None and inhib_frac is None:
            graph.new_edge_attribute("type", "double", val=1.)
            return t_list
        else:
            n = graph.node_nb()
            if inhib_nodes is None:
                # set inhib_frac*num_edges random inhibitory connections
                num_edges = graph.edge_nb()
                num_inhib = int(num_edges*inhib_frac)
                num_current = 0
                while num_current < num_inhib:
                    new = randint(0,num_edges,num_inhib-num_current)
                    idx_inhib = np.unique(np.concatenate((idx_inhib, new)))
                    num_current = len(idx_inhib)
                t_list[idx_inhib.astype(int)] *= -1.
            else:
                # get the dict of inhibitory nodes
                num_inhib_nodes = 0
                idx_nodes = {}
                if hasattr(inhib_nodes, '__iter__'):
                    idx_nodes = { i:-1 for i in inhib_nodes }
                    num_inhib_nodes = len(idx_nodes)
                if issubclass(inhib_nodes.__class__, float):
                    if inhib_nodes > 1:
                        raise InvalidArgument(
                            "Inhibitory ratio (float value for `inhib_nodes`) "
                            "must be smaller than 1.")
                        num_inhib_nodes = int(inhib_nodes*n)
                if issubclass(inhib_nodes.__class__, int):
                    num_inhib_nodes = int(inhib_nodes)
                while len(idx_nodes) != num_inhib_nodes:
                    indices = randint(0,n,num_inhib_nodes-len(idx_nodes))
                    di_tmp = { i:-1 for i in indices }
                    idx_nodes.update(di_tmp)
                for v in edges[:,0]:
                    if v in idx_nodes:
                        idx_inhib.append(v)
                idx_inhib = np.unique(idx_inhib)
                # set the inhibitory edge indices
                for v in idx_inhib:
                    idx_edges = np.argwhere(edges[:,0]==v)
                    n = len(idx_edges)
                    if inhib_frac is not None:
                        idx_inh = []
                        num_inh = n*inhib_frac
                        i = 0
                        while i != num_inh:
                            ids = randint(0,n,num_inh-i)
                            idx_inh = np.unique(np.concatenate((idx_inh,ids)))
                            i = len(idx_inh)
                        t_list[idx_inh] *= -1.
                    else:
                        t_list[idx_edges] *= -1.
            graph.set_edge_attribute("type", value_type="double", values=t_list)
            return t_list
