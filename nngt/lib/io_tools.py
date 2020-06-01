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

""" IO tools for NNGT """

import ast
import codecs
import logging
import pickle
import re
import sys
import types
import weakref

from collections import defaultdict

import numpy as np
import scipy.sparse as ssp

import nngt
from nngt.lib import InvalidArgument
from nngt.lib.logger import _log_message
from .test_functions import graph_tool_check, on_master_process
from ..geometry import Shape, _shapely_support


logger = logging.getLogger(__name__)


# -- #
# IO #
# -- #

def load_from_file(filename, fmt="auto", separator=" ", secondary=";",
                   attributes=None, attributes_types=None, notifier="@",
                   ignore="#", name="LoadedGraph", directed=True,
                   cleanup=False):
    '''
    Load a Graph from a file.

    .. versionchanged :: 2.0
        Added optional `attributes_types` and `cleanup` arguments.

    Parameters
    ----------
    filename: str
        The path to the file.
    fmt : str, optional (default: "neighbour")
        The format used to save the graph. Supported formats are: "neighbour"
        (neighbour list, default if format cannot be deduced automatically),
        "ssp" (scipy.sparse), "edge_list" (list of all the edges in the graph,
        one edge per line, represented by a ``source target``-pair), "gml"
        (gml format, default if `filename` ends with '.gml'), "graphml"
        (graphml format, default if `filename` ends with '.graphml' or '.xml'),
        "dot" (dot format, default if `filename` ends with '.dot'), "gt" (only
        when using `graph_tool`<http://graph-tool.skewed.de/>_ as library,
        detected if `filename` ends with '.gt').
    separator : str, optional (default " ")
        separator used to separate inputs in the case of custom formats (namely
        "neighbour" and "edge_list")
    secondary : str, optional (default: ";")
        Secondary separator used to separate attributes in the case of custom
        formats.
    attributes : list, optional (default: [])
        List of names for the attributes present in the file. If a `notifier`
        is present in the file, names will be deduced from it; otherwise the
        attributes will be numbered.
        For "edge_list", attributes may also be present as additional columns
        after the source and the target.
    attributes_types : dict, optional (default: str)
        Backup information if the type of the attributes is not specified
        in the file. Values must be callables (types or functions) that will
        take the argument value as a string input and convert it to the proper
        type.
    notifier : str, optional (default: "@")
        Symbol specifying the following as meaningfull information. Relevant
        information are formatted ``@info_name=info_value``, where
        ``info_name`` is in ("attributes", "directed", "name", "size") and
        associated ``info_value`` are of type (``list``, ``bool``, ``str``,
        ``int``).
        Additional notifiers are ``@type=SpatialGraph/Network/SpatialNetwork``,
        which must be followed by the relevant notifiers among ``@shape``,
        ``@population``, and ``@graph``.
    ignore : str, optional (default: "#")
        Ignore lines starting with the `ignore` string.
    name : str, optional (default: from file information or 'LoadedGraph')
        The name of the graph.
    directed : bool, optional (default: from file information or True)
        Whether the graph is directed or not.
    cleanup : bool, optional (default: False)
       If true, removes nodes before the first one that appears in the
       edges and after the last one and renumber the nodes from 0.

    Returns
    -------
    graph : :class:`~nngt.Graph` or subclass
        Loaded graph.
    '''
    return nngt.Graph.from_file(
        filename, fmt=fmt, separator=separator, secondary=secondary,
        attributes=attributes, attributes_types=attributes_types,
        notifier=notifier, ignore=ignore, name=name, directed=directed,
        cleanup=cleanup) 


def _load_from_file(filename, fmt="auto", separator=" ", secondary=";",
                    attributes=None, attributes_types=None,
                    notifier="@", ignore="#", cleanup=False):
    '''
    Load the main properties (edges, attributes...) from a file.

    Parameters
    ----------
    filename: str
        The path to the file.
    fmt : str, optional (default: "neighbour")
        The format used to save the graph. Supported formats are: "neighbour"
        (neighbour list, default if format cannot be deduced automatically),
        "ssp" (scipy.sparse), "edge_list" (list of all the edges in the graph,
        one edge per line, represented by a ``source target``-pair), "gml"
        (gml format, default if `filename` ends with '.gml'), "graphml"
        (graphml format, default if `filename` ends with '.graphml' or '.xml'),
        "dot" (dot format, default if `filename` ends with '.dot'), "gt" (only
        when using `graph_tool <http://graph-tool.skewed.de/>`_ as library,
        detected if `filename` ends with '.gt').
    separator : str, optional (default " ")
        separator used to separate inputs in the case of custom formats (namely
        "neighbour" and "edge_list")
    secondary : str, optional (default: ";")
        Secondary separator used to separate attributes in the case of custom
        formats.
    attributes : list, optional (default: [])
        List of names for the edge attributes present in the file. If a
        `notifier` is present in the file, names will be deduced from it;
        otherwise the attributes will be numbered.
    attributes_types : dict, optional (default: str)
        Backup information if the type of the attributes is not specified
        in the file. Values must be callables (types or functions) that will
        take the argument value as a string input and convert it to the proper
        type.
    notifier : str, optional (default: "@")
        Symbol specifying the following as meaningfull information. Relevant
        information are formatted ``@info_name=info_value``, where
        ``info_name`` is in ("attributes", "directed", "name", "size") and
        associated ``info_value`` are of type (``list``, ``bool``, ``str``,
        ``int``).
        Additional notifiers are ``@type=SpatialGraph/Network/SpatialNetwork``,
        which must be followed by the relevant notifiers among ``@shape``,
        ``@population``, and ``@graph``.
    ignore : str, optional (default: "#")
        Ignore lines starting with the `ignore` string.
    cleanup : bool, optional (default: False)
       If true, removes nodes before the first one that appears in the
       edges and after the last one and renumber the nodes from 0. 

    Returns
    -------
    edges : list of 2-tuples
        Edges of the graph.
    di_attributes : dict
        Dictionary containing the attribute name as key and its value as a
        list sorted in the same order as `edges`.
    pop : :class:`~nngt.NeuralPop`
        Population (``None`` if not present in the file).
    shape : :class:`~nngt.geometry.Shape`
        Shape of the graph (``None`` if not present in the file).
    positions : array-like of shape (N, d)
        The positions of the neurons (``None`` if not present in the file).
    '''
    # check for mpi
    if nngt.get_config("mpi"):
        raise NotImplementedError("This function is not ready for MPI yet.")

    # load
    lst_lines, pop, shape, positions = None, None, None, None
    fmt = _get_format(fmt, filename)

    with open(filename, "r") as filegraph:
        lst_lines = [_cleanup_line(line, separator)
                     for line in filegraph.readlines()]

    # notifier lines
    di_notif = _get_notif(lst_lines, notifier, attributes, fmt=fmt,
                          atypes=attributes_types)

    # get nodes attributes
    di_nattributes  = _get_node_attr(di_notif, separator, fmt=fmt,
                                     lines=lst_lines, atypes=attributes_types)

    # make edges and attributes
    eattributes     = di_notif["edge_attributes"]
    di_eattributes  = {name: [] for name in eattributes}
    di_edge_convert = _gen_convert(di_notif["edge_attributes"],
                                   di_notif["edge_attr_types"],
                                   attributes_types=attributes_types)

    # process file
    edges = di_get_edges[fmt](
        lst_lines, eattributes, ignore, notifier, separator, secondary,
        di_attributes=di_eattributes, di_convert=di_edge_convert,
        di_notif=di_notif)

    if cleanup:
        edges = np.array(edges) - np.min(edges)

    # add missing size information if necessary
    if "size" not in di_notif:
        di_notif["size"] = int(np.max(edges)) + 1

    # check whether a shape is present
    if 'shape' in di_notif:
        if _shapely_support:
            min_x, max_x = float(di_notif['min_x']), float(di_notif['max_x'])
            unit = di_notif['unit']
            shape = Shape.from_wkt(
                di_notif['shape'], min_x=min_x, max_x=max_x, unit=unit)
            # load areas
            try:
                def_areas      = ast.literal_eval(di_notif['default_areas'])
                def_areas_prop = ast.literal_eval(
                    di_notif['default_areas_prop'])

                for k in def_areas:
                    p = {key: float(v) for key, v in def_areas_prop[k].items()}
                    if "default_area" in k:
                        shape._areas["default_area"]._prop.update(p)
                        shape._areas["default_area"].height = p["height"]
                    else:
                        a = Shape.from_wkt(def_areas[k], unit=unit)
                        shape.add_area(a, height=p["height"], name=k,
                                       properties=p)

                ndef_areas      = ast.literal_eval(
                                      di_notif['non_default_areas'])
                ndef_areas_prop = ast.literal_eval(
                                      di_notif['non_default_areas_prop'])
                for i in ndef_areas:
                    p = {k: float(v) for k, v in ndef_areas_prop[i].items()}
                    a = Shape.from_wkt(ndef_areas[i], unit=unit)
                    shape.add_area(a, height=p["height"], name=i, properties=p)
            except KeyError:
                # backup compatibility with older versions
                pass
        else:
            _log_message(logger, "WARNING",
                         'A Shape object was present in the file but could '
                         'not be loaded because Shapely is not installed.')

    # check whether a population is present
    if 'population' in di_notif:
        str_enc = di_notif['population'].replace('~', '\n').encode()
        str_dec = codecs.decode(str_enc, "base64")
        try:
            pop = pickle.loads(str_dec)
        except UnicodeError:
            pop = pickle.loads(str_dec, encoding="latin1")

    if 'x' in di_notif:
        x = np.fromstring(di_notif['x'], sep=separator)
        y = np.fromstring(di_notif['y'], sep=separator)
        if 'z' in di_notif:
            z = np.fromstring(di_notif['z'], sep=separator)
            positions = np.array((x, y, z)).T
        else:
            positions = np.array((x, y)).T

    return (di_notif, edges, di_nattributes, di_eattributes, pop, shape,
            positions)


def save_to_file(graph, filename, fmt="auto", separator=" ",
                 secondary=";", attributes=None, notifier="@"):
    '''
    Save a graph to file.

    @todo: implement gml, dot, xml, gt formats

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Graph to save.
    filename: str
        The path to the file.
    fmt : str, optional (default: "auto")
        The format used to save the graph. Supported formats are: "neighbour"
        (neighbour list, default if format cannot be deduced automatically),
        "ssp" (scipy.sparse), "edge_list" (list of all the edges in the graph,
        one edge per line, represented by a ``source target``-pair), "gml"
        (gml format, default if `filename` ends with '.gml'), "graphml"
        (graphml format, default if `filename` ends with '.graphml' or '.xml'),
        "dot" (dot format, default if `filename` ends with '.dot'), "gt" (only
        when using `graph_tool <http://graph-tool.skewed.de/>`_ as library,
        detected if `filename` ends with '.gt').
    separator : str, optional (default " ")
        separator used to separate inputs in the case of custom formats (namely
        "neighbour" and "edge_list")
    secondary : str, optional (default: ";")
        Secondary separator used to separate attributes in the case of custom
        formats.
    attributes : list, optional (default: ``None``)
        List of names for the edge attributes present in the graph that will be
        saved to disk; by default (``None``), all attributes will be saved.
    notifier : str, optional (default: "@")
        Symbol specifying the following as meaningfull information. Relevant
        information are formatted ``@info_name=info_value``, with
        ``info_name`` in ("attributes", "attr_types", "directed", "name",
        "size").
        Additional notifiers are ``@type=SpatialGraph/Network/SpatialNetwork``,
        which are followed by the relevant notifiers among ``@shape``,
        ``@population``, and ``@graph`` to separate the sections.

    Note
    ----
    Positions are saved as bytes by :func:`numpy.nparray.tostring`
    '''
    fmt = _get_format(fmt, filename)

    # check for mpi
    if nngt.get_config("mpi"):
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        size = comm.Get_size()
        rank = comm.Get_rank()
        # get the
        str_local, di_notif = _as_string(
            graph, separator=separator, fmt=fmt, secondary=secondary,
            attributes=attributes, notifier=notifier, return_info=True)
        # make notification string only on master thread
        str_notif = ""
        if on_master_process():
            for key, val in iter(di_notif.items()):
                str_notif += "{}{}={}\n".format(notifier, key, val)
        # strings need to start with a newline because MPI strips last
        str_local = "\n" + str_local
        # gather all strings sizes
        sizes = comm.allgather(
            _str_bytes_len(str_local) + _str_bytes_len(str_notif))
        # get rank-based offset
        offset = [_str_bytes_len(str_notif)]
        offset.extend(np.cumsum(sizes)[:-1])
        # open file and write
        if on_master_process():
            with open(filename, "w") as f_graph:
                f_graph.write(str_notif)
        # parallel write
        amode = MPI.MODE_WRONLY
        fh = MPI.File.Open(comm, filename, amode)
        fh.Write_at_all(offset[rank], str_local.encode('utf-8'))
        fh.Close()
    else:
        str_graph = _as_string(
            graph, separator=separator, fmt=fmt, secondary=secondary,
            attributes=attributes, notifier=notifier)
        with open(filename, "w") as f_graph:
            f_graph.write(str_graph)


# --------------------- #
# String representation #
# --------------------- #

def _as_string(graph, fmt="neighbour", separator=" ", secondary=";",
              attributes=None, notifier="@", return_info=False):
    '''
    Full string representation of the graph.

    .. versionchanged:: 0.7
        Added support to write position and Shape when saving
        :class:`~nngt.SpatialGraph`. Note that saving Shape requires shapely.

    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Graph to save.
    fmt : str, optional (default: "auto")
        The format used to save the graph. Supported formats are: "neighbour"
        (neighbour list, default if format cannot be deduced automatically),
        "ssp" (:mod:`scipy.sparse`), "edge_list" (list of all the edges in the
        graph, one edge per line, represented by a ``source target``-pair),
        "gml" (gml format, default if `filename` ends with '.gml'), "graphml"
        (graphml format, default if `filename` ends with '.graphml' or '.xml'),
        "dot" (dot format, default if `filename` ends with '.dot'), "gt" (only
        when using `graph_tool`<http://graph-tool.skewed.de/>_ as library,
        detected if `filename` ends with '.gt').
    separator : str, optional (default " ")
        separator used to separate inputs in the case of custom formats (namely
        "neighbour" and "edge_list")
    secondary : str, optional (default: ";")
        Secondary separator used to separate attributes in the case of custom
        formats.
    attributes : list, optional (default: all)
        List of names for the edge attributes present in the graph that will be
        saved to disk; by default, all attributes will be saved.
    notifier : str, optional (default: "@")
        Symbol specifying the following as meaningfull information. Relevant
        information are formatted ``@info_name=info_value``, with
        ``info_name`` in ("attributes", "attr_types", "directed", "name",
        "size").
        Additional notifiers are ``@type=SpatialGraph/Network/SpatialNetwork``,
        which are followed by the relevant notifiers among ``@shape``, ``@x``,
        ``@y``, ``@z``, ``@population``, and ``@graph`` to separate the
        sections.

    Returns
    -------
    str_graph : string
        The full graph representation as a string.
    '''
    # checks
    if separator == secondary:
        raise InvalidArgument("`separator` and `secondary` strings must be "
                              "different.")

    if notifier == separator or notifier == secondary:
        raise InvalidArgument("`notifier` string should differ from "
                              "`separator` and `secondary`.")

    # temporarily disable numpy cut threshold to save string
    old_threshold = np.get_printoptions()['threshold']
    np.set_printoptions(threshold=sys.maxsize)

    # data
    if attributes is None:
        attributes = [a for a in graph.edge_attributes if a != "bweight"]

    nattributes = [a for a in graph.node_attributes]

    additional_notif = {
        "directed": graph.is_directed(),
        "node_attributes": nattributes,
        "node_attr_types": [
            graph.get_attribute_type(nattr, "node") for nattr in nattributes
        ],
        "edge_attributes": attributes,
        "edge_attr_types": [
            graph.get_attribute_type(attr, "edge") for attr in attributes
        ],
        "name": graph.name,
        "size": graph.node_nb()
    }

    # add node attributes to the notifications
    for nattr in additional_notif["node_attributes"]:
        key                   = "na_" + nattr
        additional_notif[key] = np.array2string(
                graph.get_node_attributes(name=nattr), max_line_width=np.NaN,
                separator=separator)[1:-1]

    # save positions for SpatialGraph (and shape if Shapely is available)
    if graph.is_spatial():
        if _shapely_support:
            additional_notif['shape'] = graph.shape.wkt
            additional_notif['default_areas'] = \
                {k: v.wkt for k, v in graph.shape.default_areas.items()}
            additional_notif['default_areas_prop'] = \
                {k: v.properties for k, v in graph.shape.default_areas.items()}
            additional_notif['non_default_areas'] = \
                {k: v.wkt for k, v in graph.shape.non_default_areas.items()}
            additional_notif['non_default_areas_prop'] = \
                {k: v.properties
                 for k, v in graph.shape.non_default_areas.items()}
            additional_notif['unit'] = graph.shape.unit
            min_x, min_y, max_x, max_y = graph.shape.bounds
            additional_notif['min_x'] = min_x
            additional_notif['max_x'] = max_x
        else:
            _log_message(logger, "WARNING",
                         'The `shape` attribute of the graph could not be '
                         'saved to file because Shapely is not installed.')

        pos = graph.get_positions()
        additional_notif['x'] = np.array2string(
            pos[:, 0], max_line_width=np.NaN, separator=separator)[1:-1]
        additional_notif['y'] = np.array2string(
            pos[:, 1], max_line_width=np.NaN, separator=separator)[1:-1]
        if pos.shape[1] == 3:
            additional_notif['z'] = np.array2string(
                pos[:, 2], max_line_width=np.NaN, separator=separator)[1:-1]

    if graph.is_network():
        # temporarily remove weakrefs
        graph.population._parent = None
        for g in graph.population.values():
            g._pop = None
            g._net = None
        # save as string
        if nngt.get_config("mpi"):
            if nngt.get_config("mpi_comm").Get_rank() == 0:
                additional_notif["population"] = codecs.encode(
                    pickle.dumps(graph.population, protocol=2),
                                 "base64").decode().replace('\n', '~')
        else:
            additional_notif["population"] = codecs.encode(
                pickle.dumps(graph.population, protocol=2),
                             "base64").decode().replace('\n', '~')
        # restore weakrefs
        graph.population._parent = weakref.ref(graph)
        for g in graph.population.values():
            g._pop = weakref.ref(graph.population)
            g._net = weakref.ref(graph)

    str_graph = di_format[fmt](graph, separator=separator,
                               secondary=secondary, attributes=attributes)

    # set numpy cut threshold back on
    np.set_printoptions(threshold=old_threshold)

    if return_info:
        return str_graph, additional_notif

    # format the info into the string
    info_str = format_graph_info[fmt](additional_notif, notifier, graph=graph)

    return info_str + str_graph


# ------------ #
# Saving tools #
# ------------ #

def _get_format(fmt, filename):
    if fmt == "auto":
        if filename.endswith('.gml'):
            fmt = 'gml'
        elif filename.endswith('.graphml') or filename.endswith('.xml'):
            fmt = 'graphml'
        elif filename.endswith('.dot'):
            fmt = 'dot'
        elif (filename.endswith('.gt') and
              nngt._config["backend"] == "graph-tool"):
            fmt = 'gt'
        elif filename.endswith('.nn'):
            fmt = 'neighbour'
        elif filename.endswith('.el'):
            fmt = 'edge_list'
        else:
            raise InvalidArgument('Could not determine format from filename '
                                  'please specify `fmt`.')
    return fmt


def _neighbour_list(graph, separator, secondary, attributes):
    '''
    Generate a string containing the neighbour list of the graph as well as a
    dict containing the notifiers as key and the associated values.
    @todo: speed this up!
    '''
    lst_neighbours = list(graph.adjacency_matrix().tolil().rows)
    for v1 in range(graph.node_nb()):
        for i, v2 in enumerate(lst_neighbours[v1]):
            str_edge = str(v2)
            eattr    = graph.get_edge_attributes((v1, v2))
            for attr in attributes:
                str_edge += "{}{}".format(secondary, eattr[attr])
            lst_neighbours[v1][i] = str_edge
        lst_neighbours[v1] = "{}{}{}".format(
            v1, separator, separator.join(lst_neighbours[v1]))
    str_neighbours = "\n".join(lst_neighbours)
    return str_neighbours


def _edge_list(graph, separator, secondary, attributes):
    ''' Generate a string containing the edge list and their properties. '''
    edges = graph.edges_array
    di_attributes = {
        k: v for k, v in graph.edge_attributes.items()
        if k != 'bweight'
    }
    end_strings = (len(attributes) - 1)*[secondary]
    end_strings.append('')
    lst_edges = []
    for i, e in enumerate(edges):
        str_edge = "{}{}{}".format(e[0], separator, e[1])
        if attributes:
            str_edge += separator
        for end, attr in zip(end_strings, attributes):
            str_edge += "{}{}".format(di_attributes[attr][i], end)
        lst_edges.append(str_edge)
    str_edges = "\n".join(lst_edges)
    return str_edges


def _dot(graph, attributes, **kwargs):
    pass


def _gml(graph, *args, **kwargs):
    ''' Generate a string containing the edge list and their properties. '''
    node_str = "  node\n  [\n    id {id}{attr}\n  ]"
    edge_str = "  edge\n  [\n    source {s}\n    target {t}\n{attr}\n  ]"
    attr_str = "    {key} {val}"

    indent = "    "

    # set nodes
    lst_elements = []

    for i in range(graph.node_nb()):
        lst_attr = []

        for k, v in graph.node_attributes.items():
            lst_attr.append(attr_str.format(key=k, val=v[i]))

        nattr = "\n" + "\n".join(lst_attr)

        lst_elements.append(node_str.format(id=i, attr=nattr))

    # set edges
    edges = graph.edges_array

    for i, e in enumerate(edges):
        lst_attr = []

        for k, v in graph.edge_attributes.items():
            lst_attr.append(attr_str.format(key=k, val=v[i]))

        eattr = "\n".join(lst_attr)

        lst_elements.append(edge_str.format(s=e[0], t=e[1], attr=eattr))

    str_gml = "\n".join(lst_elements)

    str_gml += "\n]"

    return str_gml


def _xml(graph, attributes, **kwargs):
    pass


def _gt(graph, attributes, **kwargs):
    pass


def _custom_info(graph_info, notifier, *args, **kwargs):
    ''' Format the graph information for custom formats '''
    info_str = ""

    for key, val in iter(graph_info.items()):
        info_str += "{}{}={}\n".format(notifier, key, val)

    return info_str


def _gml_info(graph_info, *args, **kwargs):
    ''' Format the graph information for the GML format '''
    info_str = "graph\n[\n"

    indent = "  "

    for key, val in iter(graph_info.items()):
        if not key.startswith("na_"):
            val = 1 if val is True else (0 if val is False else val)
            info_str += "{}{} {}\n".format(indent, key, val)

    return info_str


# ------------- #
# Loading tools #
# ------------- #

def _format_notif(notif_name, notif_val):
    attr = (
        "node_attributes", "edge_attributes", "node_attr_types",
        "edge_attr_types"
    )
    if notif_name in attr:
        lst = notif_val[1:-1].split(", ")
        if lst != ['']:  # check empty string
            return [val.strip("'\"") for val in lst]
        else:
            return []
    elif notif_name == "size":
        return int(notif_val)
    elif notif_name == "directed":
        return False if notif_val in ("False", "0") else True
    else:
        return notif_val


def _get_notif(lines, notifier, attributes, fmt=None, atypes=None):
    di_notif = {
        "node_attributes": [], "edge_attributes": [], "node_attr_types": [],
        "edge_attr_types": [],
    }

    # special case for GML
    if fmt == "gml":
        start = 0

        for i, l in enumerate(lines):
            if l == "graph":
                start = i
                break

        # nodes
        nodes = [i for i, l in enumerate(lines) if l == "node" and i > start]
        num_nodes = len(nodes)

        di_notif["size"]  = num_nodes
        di_notif["nodes"] = nodes

        # node attributes
        diff = np.diff(nodes) - 4  # number of lines other than node spec

        num_nattr = diff[0]

        if not np.all(diff == num_nattr):
            raise RuntimeError("All nodes should have the same attributes.")

        if num_nattr > len(di_notif["node_attributes"]):
            for i in range(nodes[0] + 3, nodes[0] + num_nattr + 3):
                name = lines[i].split(" ")[0]
                di_notif["node_attributes"].append(name)
                # default type is object
                if atypes is not None:
                    di_notif["node_attr_types"].append(
                        _string_from_object(atypes.get(name, object)))
                else:
                    di_notif["node_attr_types"].append("object")

        # graph attributes
        for line in lines[:nodes[0]]:
            first_space = line.find(" ")
            key, val = line[:first_space], line[first_space + 1:]

            di_notif[key] = _format_notif(key, val)

        # edges
        edges = [i for i, l in enumerate(lines) if l == "edge" and i > start]

        di_notif["edges"] = edges

        diff = np.diff(edges) - 5  # number of lines other than edge spec

        num_eattr = diff[0]

        if not np.all(diff == num_eattr):
            raise RuntimeError("All edges should have the same attributes.")

        if num_eattr > len(di_notif["edge_attributes"]):
            for i in range(edges[0] + 4, edges[0] + num_eattr + 4):
                name = lines[i].split(" ")[0]
                di_notif["edge_attributes"].append(name)
                # default type is object
                if atypes is not None:
                    di_notif["edge_attr_types"].append(
                        _string_from_object(atypes.get(name, object)))
                else:
                    di_notif["edge_attr_types"].append("object")
    else:
        for line in lines:
            if line.startswith(notifier):
                idx_eq = line.find("=")
                notif_name = line[len(notifier):idx_eq]
                notif_val = line[idx_eq+1:]
                di_notif[notif_name] = _format_notif(notif_name, notif_val)
            else:
                break

        if attributes is not None:
            di_notif["edge_attributes"] = attributes

    return di_notif


def _to_list(string):
    separators = (';', ',', ' ', '\t')
    count = -np.Inf
    chosen = -1
    for i, delim in enumerate(separators):
        current = string.count(delim)
        if count < current:
            count = current
            chosen = separators[i]
            break
    return string.split(chosen)


def _to_int(string):
    try:
        return int(string)
    except ValueError:
        return int(float(string))


def _to_string(byte_string):
    ''' Convert bytes to string '''
    if isinstance(byte_string, bytes):
        return str(byte_string.decode())
    return byte_string


def _string_from_object(obj):
    ''' Return a type string from an object (usually a class) '''
    if obj.__class__ == type:
        # dealing with a class
        if issubclass(obj, float):
            return "double"

        if issubclass(obj, (int, np.integer)):
            return "int"

        if issubclass(obj, str):
            return "string"

        return "object"
    elif issubclass(obj.__class__, (types.FunctionType, types.MethodType)):
        # dealing with a function
        return "object"

    raise ValueError("Cannot deduce class string from '{}'.".format(obj))


def _gen_convert(attributes, attr_types, attributes_types=None):
    '''
    Generate a conversion dictionary that associates the right type to each
    attribute
    '''
    di_convert = {}

    if attributes and not attr_types:
        attr_types.extend(("string" for _ in attributes))

    for attr, attr_type in zip(attributes, attr_types):
        if attributes_types is not None and attr in attributes_types:
            # user defined converter
            di_convert[attr] = attributes_types[attr]
        elif attr_type in ("double", "float", "real"):
            di_convert[attr] = float
        elif attr_type in ("str", "string"):
            di_convert[attr] = lambda x: str(x).strip("\"'")
        elif attr_type in ("int", "integer"):
            di_convert[attr] = _to_int
        elif attr_type in ("lst", "list", "tuple", "array"):
            di_convert[attr] = _to_list
        else:
            raise TypeError("Invalid attribute type.")

    return di_convert


def _np_dtype(attribute_type):
    '''
    Return a relevant numpy dtype entry.
    '''
    if attribute_type in ("double", "float", "real"):
        return float
    elif attribute_type in ("int", "integer"):
        return int

    return object


def _type_converter(attribute_type):
    if not isinstance(attribute_type, str):
        return attribute_type

    return _np_dtype(attribute_type)


def _get_edges_neighbour(lst_lines, attributes, ignore, notifier, separator,
                         secondary, di_attributes, di_convert, **kwargs):
    '''
    Add edges and attributes to `edges` and `di_attributes` for the "neighbour"
    format.
    '''
    edges = []

    lst_lines = lst_lines[::-1]

    while lst_lines:
        line = lst_lines.pop()

        if line and not (line.startswith(notifier) or line.startswith(ignore)):
            len_first_delim = line.find(separator)
            source = int(line[:len_first_delim])
            len_first_delim += 1

            if len_first_delim:
                neighbours = line[len_first_delim:].split(separator)

                for stub in neighbours:
                    content = stub.split(secondary)
                    target = int(content[0])

                    edges.append((source, target))

                    attr_val = content[1:] if len(content) > 1 else []

                    for name, val in zip(attributes, attr_val):
                        di_attributes[name].append(di_convert[name](val))

    return edges


def _get_edges_elist(lst_lines, attributes, ignore, notifier, separator,
                     secondary, di_attributes, di_convert, **kwargs):
    '''
    Add edges and attributes to `edges` and `di_attributes` for the "neighbour"
    format.
    '''
    edges = []

    lst_lines = lst_lines[::-1]

    while lst_lines:
        line = lst_lines.pop()

        if line and not (line.startswith(notifier) or line.startswith(ignore)):
            data = line.split(separator)
            source, target = int(data[0]), int(data[1])
            edges.append((source, target))

            # different ways of loading the attributes
            if len(data) == 3 and secondary in data[2]:  # secondary notifier
                attr_data = data[2].split(secondary)
                for name, val in zip(attributes, attr_data):
                    di_attributes[name].append(di_convert[name](val))
            elif len(data) == len(attributes) + 2:  # regular columns
                for name, val in zip(attributes, data[2:]):
                    di_attributes[name].append(di_convert[name](val))

    return edges


def _get_edges_gml(lst_lines, attributes, *args, di_attributes=None,
                   di_convert=None, di_notif=None):
    '''
    Add edges and attributes to `edges` and `di_attributes` for the "neighbour"
    format.
    '''
    edges = []

    edge_lines = di_notif["edges"]
    num_eattr  = len(di_attributes)

    for line_num in edge_lines:
        source = int(lst_lines[line_num + 2][7:])
        target = int(lst_lines[line_num + 3][7:])

        edges.append((source, target))

        for i, name in zip(range(num_eattr), attributes):
            lnum  = line_num + 4 + i
            start = lst_lines[lnum].find(" ") + 1
            attr  = lst_lines[lnum][start:]
            di_attributes[name].append(di_convert[name](attr))

    return edges


def _get_node_attr(di_notif, separator, fmt=None, lines=None, atypes=None):
    '''
    Return node attributes.

    For custom formats, attributes are stored under @na_{attr_name} in the
    file, so they are stored under the coresponding key in `di_notif`.

    For GML, need to get them from the nodes.
    '''
    di_nattr   = {}

    if fmt == "gml":
        node_lines = di_notif["nodes"]
        num_nattr  = node_lines[1] - node_lines[0] - 3  # lines other than attr

        has_types = len(di_notif["node_attr_types"]) == num_nattr

        if num_nattr:
            for line_num in node_lines:
                for i in range(num_nattr):
                    l = lines[line_num + i + 2]
                    first_space = l.find(" ")

                    # get attribute name and value
                    name = l[:first_space]
                    val  = l[first_space + 1:]

                    if name not in di_nattr:
                        di_nattr[name] = []

                    dtype = str if atypes is None else atypes.get(name, str)

                    if has_types:
                        dtype = _type_converter(di_notif["node_attr_types"][i])

                    di_nattr[name].append(dtype(val))
    else:
        nattr_name = {str("na_" + k): k for k in di_notif["node_attributes"]}
        nattr_type = di_notif["node_attr_types"]

        for k, s in di_notif.items():
            if k in nattr_name:
                attr           = nattr_name[k]
                idx            = di_notif["node_attributes"].index(attr)
                dtype          = _np_dtype(nattr_type[idx])
                di_nattr[attr] = np.fromstring(s, sep=separator, dtype=dtype)

    return di_nattr


def _str_bytes_len(s):
    return len(s.encode('utf-8'))
 

def _cleanup_line(string, char):
    ''' Replace multiple occurrences of a separator and remove line ends '''
    pattern = char + '+'
    string = re.sub(pattern, char, string)
    return string.strip()


# ---------- #
# Formatting #
# ---------- #

di_get_edges = {
    "neighbour": _get_edges_neighbour,
    "edge_list": _get_edges_elist,
    "gml": _get_edges_gml,
}

di_format = {
    "neighbour": _neighbour_list,
    "edge_list": _edge_list,
    "gml": _gml
}

format_graph_info = defaultdict(lambda: _custom_info)
format_graph_info["gml"] = _gml_info
