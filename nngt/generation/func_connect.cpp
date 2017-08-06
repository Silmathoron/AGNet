// connect.cpp
//
// Accelerated network generation functions

#include "func_connect.h"

#include <omp.h>

#define _USE_MATH_DEFINES
#include <limits>
#include <random>

#include <stdexcept>
#include <assert.h>


namespace generation {

void _init_seeds(std::vector<long>& seeds, unsigned int omp, long msd)
{
    for (size_t i=0; i < omp; i++)
    {
        seeds[i] = msd + i + 1;
    }
}


size_t _unique_1d(std::vector<size_t>& a,
                  std::unordered_map<size_t, size_t>& hash_map)
{
    size_t number;
    size_t total_unique = hash_map.size();

    for (size_t i = 0; i < a.size(); i++)
    {
        number = a[i];
        // check if this number is already in the map
        if (hash_map.find(number) == hash_map.end())
        {
            // it's not in there yet so add it and set the count to 1
            hash_map.insert({number, 1});
            a[total_unique] = a[i];
            total_unique += 1;
        }
    }

    return total_unique;
}


size_t _unique_2d(std::vector< std::vector<size_t> >& a, map_t& hash_map)
{
    size_t total_unique = hash_map.size();
    size_t num_edges = a[0].size();
    size_t s, t;
    edge_t edge;

    for (size_t i = total_unique; i < num_edges; i++)
    {
        s = a[0][i];
        t = a[1][i];
        edge = edge_t(s, t);
        // check if this number is already in the map
        if (hash_map.find(edge) == hash_map.end())
        {
            // it's not in there yet so add it and set the count to 1
            hash_map.insert({edge, 1});
            a[0][total_unique] = s;
            a[1][total_unique] = t;
            total_unique += 1;
        }
    }

    return total_unique;
}


//~ size_t _unique_2d(std::vector< std::vector<size_t> >& a, map_t& hash_map)
//~ {
    //~ size_t total_unique = hash_map.size();
    //~ size_t num_edges = a[0].size();
    //~ size_t s, t;

    //~ for (size_t i = total_unique; i < num_edges; i++)
    //~ {
        //~ s = a[0][i];
        //~ t = a[1][i];
        //~ // check if this number is already in the map
        //~ if (hash_map.find(s) == hash_map.end())
        //~ {
            //~ // it's not in there yet so add it and set the count to 1
            //~ std::unordered_map<size_t, int> newmap;
            //~ newmap[t] = 1;
            //~ hash_map.insert({s, newmap});
            //~ a[0][total_unique] = s;
            //~ a[1][total_unique] = t;
            //~ total_unique += 1;
        //~ }
        //~ else if (hash_map[s].find(t) == hash_map[s].end())
        //~ {
            //~ // it's not in there yet so add it and set the count to 1
            //~ hash_map[s].insert({t, 1});
            //~ a[0][total_unique] = s;
            //~ a[1][total_unique] = t;
            //~ total_unique += 1;
        //~ }
    //~ }

    //~ return total_unique;
//~ }


std::vector<size_t> _gen_edge_complement(
  std::mt19937& generator, const std::vector<size_t>& nodes, size_t other_end,
  size_t degree, const std::vector< std::vector<size_t> >* existing_edges,
  bool multigraph)
{
    // Initialize the RNG
    size_t min_idx = *std::min_element(nodes.begin(), nodes.end());
    size_t max_idx = *std::max_element(nodes.begin(), nodes.end());
    std::uniform_int_distribution<size_t> uniform_(min_idx, max_idx);

    // generate the complements
    std::vector<size_t> result;
    size_t ecurrent = 0;

    // check the existing edges
    const size_t num_old_edges = existing_edges ? existing_edges[0].size() : 0;
    for (size_t i=0; i < num_old_edges; i++)
    {
        if (existing_edges->at(0)[i] == other_end)
        {
            result.push_back(existing_edges->at(1)[i]);
        }
    }
    ecurrent = result.size();
    result.resize(ecurrent + degree);
    
    size_t remaining = degree;
    size_t cplt, j;
    const size_t target_degree = ecurrent + degree;
    std::unordered_map<size_t, size_t> hash_map;
    
    assert(target_degree == degree);
    
    while (ecurrent < target_degree)
    {
        remaining = target_degree - ecurrent;
        j = 0;
        while (j < remaining)
        {
            cplt = uniform_(generator);
            if (cplt != other_end)
            {
                result[ecurrent + j] = cplt;
                j++;
            }
        }
        // update ecurrent and (potentially) the results
        ecurrent = multigraph ? target_degree : _unique_1d(result, hash_map);
    }

    return result;
}


void _gen_edges(
  size_t* ia_edges, const std::vector<size_t>& first_nodes,
  const std::vector<size_t>& degrees, const std::vector<size_t>& second_nodes,
  const std::vector< std::vector<size_t> >& existing_edges, unsigned int idx,
  bool multigraph, bool directed, long msd, unsigned int omp)
{
    // Initialize secondary seeds
    std::vector<long> seeds(omp);
    _init_seeds(seeds, omp, msd);

    // compute the cumulated sum of the degrees
    std::vector<size_t> cum_degrees(degrees.size());
    std::partial_sum(degrees.begin(), degrees.end(), cum_degrees.begin());

    // generate the edges
    #pragma omp parallel num_threads(omp)
    {
        std::mt19937 generator_(seeds[omp_get_thread_num()]);
        
        #pragma omp for schedule(static)
        for (size_t node=0; node < first_nodes.size(); node++)
        {
            // generate the vector of complementary nodes
            std::vector<size_t> res_tmp = _gen_edge_complement(
              generator_, second_nodes, node, degrees[node], &existing_edges,
              multigraph);
            // fill the edges
            size_t idx_start = cum_degrees[node] - degrees[node];
            for (size_t j = 0; j < degrees[node]; j++)
            {
                ia_edges[2*(idx_start + j) + idx] = node;
                ia_edges[2*(idx_start + j) + 1 - idx] = res_tmp[j];
            }
        }
    }
}


/*
* Distance-rule algorithms
*/

void _cdistance_rule(size_t* ia_edges, const std::vector<size_t>& source_nodes,
  const std::vector<std::vector<size_t>>& target_nodes,
  const std::string& rule, float scale, const std::vector<float>& x,
  const std::vector<float>& y, float area, size_t num_neurons,
  size_t num_edges, const std::vector< std::vector<size_t> >& existing_edges,
  bool multigraph, long msd, unsigned int num_omp)
{
    float inv_scale = 1. / scale;
    // Initialize secondary seeds and RNGs
    std::vector<long> seeds(num_omp);
    _init_seeds(seeds, num_omp, msd);

    std::uniform_real_distribution<float> rnd_uniform(0., 1.);

    // rule into int
    int rule_type = (rule == "lin" ? 0 : 1);

    size_t initial_enum = existing_edges.empty() ?
        0 : existing_edges[0].size();               // initial number of edges
    size_t current_enum = initial_enum;             // current number of edges
    size_t ecount_fill = 0;             // current number of edges
    size_t target_enum = current_enum + num_edges;  // target number of edges

    // set the number of tests associated to each node proportionnaly to its
    // number of neighbours
    size_t tot_neighbours = 0;

    for (size_t i=0; i < target_nodes.size(); i++)
    {
        tot_neighbours += target_nodes[i].size();
    }
    double norm = 1. / tot_neighbours;

    // if not using multigraph, assert that we have enough neighbours
    if (tot_neighbours < target_enum)
    {
        throw std::invalid_argument("Scale is too small: there are not enough "
                                    "close neighbours to create the required "
                                    "number of connections. Increase `scale` "
                                    "or `neuron_density`.");
    }

    // create the edges
    #pragma omp parallel num_threads(num_omp)
    {
        float distance, proba;
        size_t src, tgt, local_tests, nln, rnd;
        std::vector<size_t> local_tgts;
        std::mt19937 generator_(seeds[omp_get_thread_num()]);
        // thread local edges
        map_t hash_map;
        //~ edge_t edge;
        size_t num_elocal = 0;
        std::vector< std::vector<size_t> > local_edges(2,
                                                       std::vector<size_t>());
        std::vector< std::vector<size_t> > elocal_tmp(2,
                                                      std::vector<size_t>());

        // initialize the hash map and the local edges with the existing edges
        // the static schedule is CAPITAL: each thread must always handle
        // the same nodes
        //~ #pragma omp for schedule(static)
        //~ for (size_t i=0; i<source_nodes.size(); i++)
        //~ {
            //~ size_t s1 = source_nodes[i];
            //~ size_t j = 0;
            //~ for (auto s2 : existing_edges[0])
            //~ {
                //~ if (s1 == s2)
                //~ {
                    //~ edge = edge_t(s1, existing_edges[1][j]);
                    //~ hash_map.insert({edge, 1});
                //~ }
                //~ j++;
            //~ }
        //~ }
                                                      
        do {
            // reset edge number (recomute it each time)
            #pragma omp single
            {
                //~ printf("reset current enum\n");
                current_enum = initial_enum;
                //~ printf("reseted\n");
            }
            #pragma omp barrier
            #pragma omp flush(current_enum)
            //~ printf("t %u has %lu\n", omp_get_thread_num(), current_enum);
            
            // the static schedule is CAPITAL: each thread must always handle
            // the same nodes
            #pragma omp for schedule(static)
            for (size_t i=0; i<target_nodes.size(); i++)
            {
                local_tests = target_nodes[i].size()
                              * (target_enum - current_enum) * norm;
                local_tests = std::max(local_tests, 1lu);
                elocal_tmp[0].reserve(local_tests);
                elocal_tmp[1].reserve(local_tests);
                // initialize source; set target generator
                src = source_nodes[i];
                local_tgts = target_nodes[i];
                nln = local_tgts.size();  // number of local neighbours
                std::uniform_int_distribution<size_t> rnd_target(0, nln - 1);

                for (size_t j=0; j<local_tests; j++)
                {
                    tgt = src;
                    while (tgt == src)
                    {
                        rnd = rnd_target(generator_);
                        tgt = local_tgts[rnd];
                    }
                    distance = std::sqrt((x[tgt] - x[src])*(x[tgt] - x[src]) +
                                         (y[tgt] - y[src])*(y[tgt] - y[src]));
                    proba = _proba(rule_type, inv_scale, distance);
                    if (proba >= rnd_uniform(generator_))
                    {
                        elocal_tmp[0].push_back(src);
                        elocal_tmp[1].push_back(tgt);
                    }
                }
            }

            local_edges[0].insert(local_edges[0].end(),
                                  elocal_tmp[0].begin(), elocal_tmp[0].end());
            local_edges[1].insert(local_edges[1].end(),
                                  elocal_tmp[1].begin(), elocal_tmp[1].end());
            num_elocal = multigraph
                         ? local_edges[0].size()
                         : _unique_2d(local_edges, hash_map);

            local_edges[0].resize(num_elocal);
            local_edges[1].resize(num_elocal);

            //~ #pragma omp single
            //~ printf("before reduction/ %lu\n", current_enum);

            #pragma omp atomic
            current_enum += num_elocal;

            #pragma omp barrier              // make sure everyone is ready
            #pragma omp flush(current_enum)  // and gets last value
            #pragma omp barrier              // for sure

            //~ #pragma omp single
            //~ {
                //~ #pragma omp flush(current_enum)  // and gets last value
                //~ printf("after reduction/ %lu\n", current_enum);
            //~ }
        } while (current_enum < target_enum);

        // fill the edge container: first with the existing edges
        //~ printf("out of loop (%u) with %lu\n", omp_get_thread_num(), current_enum);
        #pragma omp single
        {
            for (size_t i=0; i<initial_enum; i++)
            {
                ia_edges[2*i]     = existing_edges[0][i];
                ia_edges[2*i + 1] = existing_edges[1][i];
            }
            ecount_fill += initial_enum;
        }
        // then, once this is done
        #pragma omp barrier
        // each thread successively adds its local edges
        #pragma omp critical
        {
            //~ printf("in critical %lu, %lu\n", ecount_fill, target_enum);
            size_t i = 0;
            #pragma omp flush(ecount_fill)
            while (i < num_elocal && ecount_fill < target_enum)
            {
                
                ia_edges[2*ecount_fill]     = local_edges[0][i];
                ia_edges[2*ecount_fill + 1] = local_edges[1][i];
                ecount_fill += 1;
                i += 1;
            }
            //~ printf("done\n");
        }
    }
}

}
