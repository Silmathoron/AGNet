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

""" Sorting tools """

import numpy as np

from .errors import InvalidArgument


def find_idx_nearest(array, values):
    '''
    Find the indices of the nearest elements of `values` in a sorted `array`.

    .. warning::
        Both ``array`` and ``values`` should be `numpy.array` objects and
        `array` MUST be sorted in increasing order.

    Parameters
    ----------
    array : reference list or np.ndarray
    values : double, list or array of values to find in `array`

    Returns
    -------
    idx : int or array representing the index of the closest value in `array`
    '''
    idx = np.searchsorted(array, values, side="left") # get the interval
    # return the index of the closest
    if isinstance(values, float) or isinstance(values, int):
        if idx == len(array):
            return idx-1
        else:
            idx -= (np.abs(values-array[idx-1]) < np.abs(values-array[idx]))
            return idx
    else:
        # find where it is idx_max+1
        overflow = (idx == len(array))
        idx[overflow] -= 1
        # for the others, find the nearest
        tmp = idx[~overflow]
        idx[~overflow] = tmp - (np.abs(values[~overflow] - array[tmp-1])
                                < np.abs(values[~overflow] - array[tmp]))
        return idx


def _sort_neurons(sort, gids, network, data=None, return_attr=False):
    '''
    Sort the neurons according to the `sort` property.

    If `sort` is "firing_rate" or "B2", then data must contain the `senders`
    and `times` list given by a NEST ``spike_recorder``.

    Parameters
    ----------
    sort : str or array
        Sorting method or indices
    gids : array-like
        NEST gids
    network : the network
    data : numpy.array of shape (N, 2)
        Senders on column 1, times on column 2.

    Returns
    -------
    For N neurons, labeled from ``GID_MIN`` to ``GID_MAX``, returns a`sorting`
    array of size ``GID_MAX``, where ``sorting[gids]`` gives the sorted ids of
    the neurons, i.e. an integer between 1 and N.
    '''
    from nngt.analysis import node_attributes, get_b2
    min_nest_gid = network.nest_gid.min()
    max_nest_gid = network.nest_gid.max()
    sorting = np.zeros(max_nest_gid + 1)
    attribute = None
    if isinstance(sort, str):
        sorted_ids = None
        if sort == "firing_rate":
            # compute number of spikes per neuron
            spikes = np.bincount(data[:, 0].astype(int))
            if spikes.shape[0] < max_nest_gid: # one entry per neuron
                spikes.resize(max_nest_gid)
            # sort them (neuron with least spikes arrives at min_nest_gid)
            sorted_ids = np.argsort(spikes)[min_nest_gid:] - min_nest_gid
            # get attribute
            idx_min = np.min(data[:, 0])
            attribute = spikes[idx_min:] \
                        / (np.max(data[:, 1]) - np.min(data[:, 1]))
        elif sort.lower() == "b2":
            attribute = get_b2(network, data=data, nodes=gids)
            sorted_ids = np.argsort(attribute)
            # check for non-spiking neurons
            num_b2 = attribute.shape[0]
            if num_b2 < network.node_nb():
                spikes = np.bincount(data[:, 0])
                non_spiking = np.where(spikes[min_nest_gid] == 0)[0]
                sorted_ids.resize(network.node_nb())
                for i, n in enumerate(non_spiking):
                    sorted_ids[sorted_ids >= n] += 1
                    sorted_ids[num_b2 + i] = n
        else:
            attribute = node_attributes(network, sort)
            sorted_ids = np.argsort(attribute)
        num_sorted = 1
        _, sorted_groups = _sort_groups(network.population)
        for group in sorted_groups:
            gids = network.nest_gid[group.ids]
            order = np.argsort(sorted_ids[group.ids])
            sorting[gids] = num_sorted + order
            num_sorted += len(group.ids)
    else:
        sorting[network.nest_gid] = np.argsort(sort)
    if return_attr:
        return sorting.astype(int), attribute
    else:
        return sorting.astype(int)


def _sort_groups(pop):
    '''
    Sort the groups of a NeuralPop by decreasing size.
    '''
    names, groups = [], []
    for name, group in iter(pop.items()):
        names.append(name)
        groups.append(group)
    sizes = [len(g.ids) for g in groups]
    order = np.argsort(sizes)[::-1]
    return [names[i] for i in order], [groups[i] for i in order]
