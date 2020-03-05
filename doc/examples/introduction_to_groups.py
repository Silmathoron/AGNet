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

''' Introduction to neural groups '''

import numpy as np

import nngt
from nngt import MetaGroup, NeuralGroup, NeuralPop


''' ------------- #
# Creating groups #
# ------------- '''

# the default group is empty, which is not very useful in general
empty_group = nngt.NeuralGroup()
print(empty_group)
print("Group is empty?", empty_group.size == 0, "\nIt is therefore invalid?",
      "No!" if empty_group.is_valid else "Yes!", "\n")

# to create a useful group, one can just say how many neurons it should contain
group1 = NeuralGroup(500)  # a group with 500 neurons
print("Ids are not created", group1.ids,
      "but the size is stored:", group1.size, "\n")

# if you want to set the ids directly, you can pass them directly, otherwise
# they will be determine automatically when a Network is created using the group
group2 = NeuralGroup(range(10, 20))  # 10 neurons with ids from 10 to 19
print("Neuron ids are:", group2.ids, "\n")


''' ------------------- #
# More group properties #
# ------------------- '''

# group can have names
named_group = NeuralGroup(500, name="named_group")
print("I'm a named group!", named_group, "\n")

# more importantly, they can store whether neurons are excitatory or inhibitory
exc   = NeuralGroup(800, neuron_type=1)   # excitatory group (optional)
exc2  = NeuralGroup(800)                  # also excitatory
inhib = NeuralGroup(200, neuron_type=-1)  # inhibitory group
print("'exc2' is an excitatory group:", exc2.neuron_type == 1,
      "/ 'inhib' is an inhibitory group:", inhib.neuron_type == -1, "\n")


''' ---------------------------------- #
# Complete groups for NEST simulations #
# ---------------------------------- '''

# to make a complete group, one must include a valid neuronal model and
# (optionally) associated parameters

pyr = NeuralGroup(800, neuron_type=1, neuron_model="iaf_psc_alpha",
                  neuron_param={"tau_m": 50.}, name="pyramidal_cells")

fsi = NeuralGroup(200, neuron_type=-1, neuron_model="iaf_psc_alpha",
                  neuron_param={"tau_m": 20.},
                  name="fast_spiking_interneurons")


''' ------------------ #
# Creating populations #
# ------------------ '''

# making populations from scratch
pop = nngt.NeuralPop(with_models=False)              # empty population
pop.create_group(200, "first_group")                 # create excitatory group
pop.create_group(5, "second_group", neuron_type=-1)  # create inhibitory group

print("E/I population has size", pop.size, "and contains",
      len(pop), "groups:", pop.keys(), "\n")

# the two default populations
unif_pop = NeuralPop.uniform(1000)                     # only excitatory
ei_pop   = NeuralPop.exc_and_inhib(1000, iratio=0.25)  # 25% inhibitory

# check the groups inside
print("Uniform population has size", unif_pop.size, "and contains",
      len(unif_pop), "group:", unif_pop.keys(), "\n")
print("E/I population has size", ei_pop.size, "and contains",
      len(ei_pop), "groups:", ei_pop.keys(), "\n")

# A population can also be created from existing groups.
# Here we pass ``with_models=False`` to the population because these groups do
# not contain the information necessary to create a network in NEST (a valid
# neuron model).
print(exc.neuron_type, exc2.neuron_type, inhib.neuron_type)
ei_pop2 = NeuralPop.from_groups([exc, exc2, inhib], ["e1", "e2", "i"],
                                with_models=False)

print("E/I population has size", ei_pop2.size,
      "({} + {} + {}) and contains".format(exc.size, exc2.size, inhib.size),
      len(ei_pop2), "groups:", ei_pop2.keys(), "\n")


''' --------------------- #
# NEST-enabled population #
# --------------------- '''

# Let's create a population which will be used to make a network that can then
# be simulated with NEST.
# We create it from the pyramidal and fast spiking interneurons groups and
# add synaptic properties to the connections that will be made.
# (because the group already have names, we don't need to specify them again)

# optional synaptic properties
syn_spec = {
    'default': {"model": "tsodyks2_synapse"},           # default connections
    ("pyramidal_cells", "pyramidal_cells"): {"U": 0.6}  # change a parameter
}

nest_pop = NeuralPop.from_groups([pyr, fsi], syn_spec=syn_spec)


''' ------------------------------- #
# Complex population and metagroups #
# ------------------------------- '''

# Let's model part of a cortical column with
# - granule cells in layer 2 and 4
# - pyramidal cells and interneurons in layers 3 and 5
# - indiscriminate cells in layer 6

nmod = "iaf_psc_exp"

idsL2gc = range(100)
idsL3py, idsL3i = range(100, 200), range(200, 300)
idsL4gc = range(300, 400)
idsL5py, idsL5i = range(400, 500), range(500, 600)
idsL6 = range(600, 700)

L2GC = NeuralGroup(idsL2gc, neuron_model=nmod, name="L2GC")
L3Py = NeuralGroup(idsL3py, neuron_model=nmod, name="L3Py")
L3I  = NeuralGroup(idsL3i,  neuron_model=nmod, name="L3I", neuron_type=-1)
L4GC = NeuralGroup(idsL4gc, neuron_model=nmod, name="L4GC")
L5Py = NeuralGroup(idsL5py, neuron_model=nmod, name="L5Py")
L5I  = NeuralGroup(idsL5i,  neuron_model=nmod, name="L5I", neuron_type=-1)
L6c  = NeuralGroup(idsL6,   neuron_model=nmod, name="L6c")

# We can also group them by layers using metagroups (for L2/L3/L6 it is not
# really useful but it gives a coherent notation)
L2 = MetaGroup(idsL2gc, name="L2")
L3 = MetaGroup(L3Py.ids + L3I.ids, name="L3")
L4 = MetaGroup(idsL4gc, name="L4")
L5 = MetaGroup(L5Py.ids + L5I.ids, name="L5")
L6 = MetaGroup(idsL6, name="L6")

# Then we create the population from the groups
pop_column = NeuralPop.from_groups(
    [L2GC, L3Py, L3I, L4GC, L5Py, L5I, L6c], meta_groups=[L2, L3, L4, L5, L6])

# We can also add additional meta-groups for pyramidal, granule, and
# interneurons
pyr = MetaGroup(L3Py.ids + L5Py.ids, name="pyramidal")
pop_column.add_meta_group(pyr)  # add from existing meta-group

pop_column.create_meta_group(L3I.ids + L5I.ids, "interneurons")  # single line

pop_column.create_meta_group(L2GC.ids + L4GC.ids, "granule")

print("Column has meta-groups:", pop_column.meta_groups.keys())
