#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# This file is part of the NNGT project to generate and analyze
# neuronal networks and their activity.
# Copyright (C) 2015-2019  Tanguy Fardet
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

""" Generation of multi-group networks """

import nngt
import nngt.generation as ng

import numpy as np


'''
Make a mixed excitatory and inhibitory population, then subdived it in subgroups
'''

num_neurons = 1000

pop = nngt.NeuralPop.exc_and_inhib(num_neurons)

# create two separated subgroups associated to two shapes where the neurons
# will be seeded

# we select 500 random nodes for the left group
left_nodes = np.random.choice([i for i in range(num_neurons)],
                              500, replace=False)
left = nngt.NeuralGroup(left_nodes, ntype=None)  # here we first create...
pop.add_meta_group("left", left)  # ... then add

# right group is the complement
right_nodes = list(set(pop.ids).difference(left_nodes))
right = pop.create_meta_group("right", right_nodes)  # here we do both in one call

# create another pair of random metagroups

# we select 500 random nodes for the left group
group1 = pop.create_meta_group("g1", [i for i in range(500)])
group2 = pop.create_meta_group("g2", [i for i in range(500, num_neurons)])


'''
We then create the shapes associated to the left and right groups and seed
the neurons accordingly in the network
'''

left_shape  = nngt.geometry.Shape.disk(300, (-300, 0))
right_shape = nngt.geometry.Shape.rectangle(800, 200, (300, 0))

left_pos  = left_shape.seed_neurons(left.size)
right_pos = right_shape.seed_neurons(right.size)

# we order the positions according to the neuron ids
positions = np.empty((num_neurons, 2))

for i, p in zip(left_nodes, left_pos):
    positions[i] = p

for i, p in zip(right_nodes, right_pos):
    positions[i] = p

# create network from this population
net = nngt.Network(population=pop, positions=positions)


'''
Plot the graph
'''

if nngt.get_config("with_plot"):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()

    nngt.plot.draw_network(net, restrict_nodes=left_nodes, axis=ax, show_environment=False, simple_nodes=True)
    nngt.plot.draw_network(net, restrict_nodes=right_nodes, nshape="s", axis=ax, show_environment=False, simple_nodes=True)

    plt.show()
