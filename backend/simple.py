#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
First version by Thomas Britz 27.10.2014
Mercilessly hacked by Catherine Greenhill, starting 27.10.2014
Edited 29.10.2014, CSG
Last edited 30.6.2016, CSG, to get some information about why cutset
targetting seems to perform better WITH adaptation...

Main change, 11 March 2016: regroup our output data.
Introduce some other "no adapt" strategies, to allow us to rule out
"no adapt" early (i.e., show it has an effect by looking at more than
just one strategy)
1 April 2016, include a "no adapt" strategy for RANDOM, and plot.

Slashed by Thomas in April 2018 to trim plots not needed in app conversion

"""

import sys
#import math
import json
import random
import itertools
import networkx as nx
#import matplotlib.pyplot as plt
#import matplotlib.ticker as mtick
from operator import itemgetter
import pprint as pp

def initialise_network(filename):
    """
    This function sets up the criminal network and node attributes, using
    data from the master spreadsheet.

    ID1 is the list of "from" nodes for each directed edge in the network:
    so node 1 has out-degree 4

    ID2 is the list of "to" nodes for each directed edge in the network:
    so the out-neighbours of node 1 are 66, 67, 79 and 122.

    node_attributes is a list of lists in the form [[v,b1,..,b8],..].
    Here v is the node ID, b1, .., b8 are boolean representing attributes:
    money, drugs, premises, equipment, precursors, information,
    skills/knowledge, labour.  The order matches the master spreadsheet.
    """

    with open(filename, 'r') as f:
        data = json.load(f)

    ID1 = data['ID1']
    ID2 = data['ID2']
    node_attributes = data['node_attributes']

    # Create the original criminal network
    n = 128  # the number of vertices: equals 128 for our network
    m = len(ID1)  # the number of edges
    G = nx.Graph()
    nodelist = [i for i in range(1, n+1)]  # 129 = 128 + 1
    edgelist = [(ID1[i], ID2[i]) for i in range(m)]
    G.add_nodes_from(nodelist)
    G.add_edges_from(edgelist)

    return (G, node_attributes)


def degree_centralisation(H):
    """
    Calculate degree centralization of a graph H.

    Calculate the list of vertex degree centrality dictionaries,
    following [Freeman 1979]'s definition of C_D
    """

    if len(H.nodes()) <= 2:
        return 0
    centralities = nx.degree_centrality(H)
    centrality_values = [centralities[u] for u in list(centralities.keys())]
    centrality_max = max(centrality_values)
    nn = len(centrality_values)
    # Standard norm;
    # nn**2 - 3*nn + 2 = (nn-1)*(nn-2);
    # nn-1 is already divided by nx.degree_centrality(H)
    norm = nn - 2

    return (nn*centrality_max - sum([centrality_values[j] for j in range(nn)]))/norm


def betweenness_centralisation(H):
    """
    Calculate betweenness centralization of a graph H.

    Calculate the list of vertex betweenness centrality dictionaries,
    following [Freeman 1979]'s definition of C_B
    """

    if len(H.nodes()) <= 2:
        return 0
    centralities = nx.betweenness_centrality(H, None, False)
    centrality_values = [centralities[u] for u in list(centralities.keys())]
    centrality_max = max(centrality_values)
    nn = len(centrality_values)
    norm = (nn-1)**2 * (nn-2)  # Standard norm; nn**3 - 4*nn*nn + 5*nn - 2

    return (nn*centrality_max - sum([centrality_values[j] for j in range(nn)]))/norm


def calc_attributes(V, node_attributes, ignore_equipment):
    """
    Calculate set of attributes for a set of vertices.

    Avector is a vector of length 9, first entry 0 (placeholder) and the
    other entries give the number of nodes in V which have that attribute.

    The function returns a list of those attributes which were present
    """

    Avector = [0] + [sum([node_attributes[v-1][j] for v in V]) for j in range(1, 9)]
    if ignore_equipment == 1:
        # To ignore equipment, do this?
        return [j for j in range(1, 9) if (Avector[j] > 0) and (j != 4)]
    else:
        return [j for j in range(1, 9) if Avector[j] > 0]


def weighted_choice(weights, random=random):
    """
    Given a list of weights [w_0, w_1, ..., w_{n-1}], return an index i in
    range(n) with probability proportional to w_i.

    CSG: I found this code on
    http://stackoverflow.com/questions/13047806/weighted-random-sample-in-python

    We can use it to choose nodes for repair a component, inversely
    proportional to their distance to the component.

    random.random gives a random real number from [0,1), so if you multiply
    by the sum of the weights then you get a random real number rnd in
    [0,sum(w_i)).  Keep subtracting w_i from rnd until rnd first becomes 0,
    at that point return i.  Then Pr(i) is proportional to w_i.
    """

    rnd = random.random() * sum(weights)

    for i, w in enumerate(weights):
        if w < 0:
            raise ValueError("Negative weight encountered")
        rnd -= w
        if rnd < 0:
            return i

    raise ValueError("Sum of weights is not positive")


"""
The targeting functions: all take a graph H as input and return a node v
to be deleted.

CSG, March 2016, added some new "no adapt" strategies here

 (0) cut_set_targeting
 (1) max_degree_targeting
 (2) max_betweenness_targeting
 (3) money_targeting            TB: attribute_targeting added on 02.11.2014
 (4) random_targeting
 (5) precursor_targeting        Added November 2015, requested by AR and DB
 (6) MaxDegree_No_adapt
 (7) CutSetThenMaxDegree        hybrid strategy, added November 2015
 (8) CutSetThenBetweenness      hybrid strategy, added November 2015
 (9) MaxBetweenness_No_adapt    CSG added, 11 March 2016
(10) CutSet_No_adapt            CSG added, 11 March 2016
(11) Money_No_adapt             CSG added, 11 March 2016
(12) Precursors_No_adapt        CSG added, 11 March 2016
(13) Random_No_Adapt            CSG added,  1 April 2016
"""


def cut_set_targeting(H, cutset):
    """
    Cut set targeting.  First, an essay by Thomas (-:

    Ideal approach
    --------------

    · Find minimal cutsets
    · Possibly discard cutsets that are too big
    · Discard cutsets for which there are fewer than 2 remaining components of
      size 5 (below this size, it is unlikely that a full set of attributes is
      achievable)
    · From remaining cutsets, choose one of smallest size at random
    · From this component, choose a random vertex and delete it from the
      network
    · Allow adaptability: the network may try to repair any component that now
      lacks attributes, by connecting to vertices of the component (each at
      random) some vertex in the remaining graph whose attributes include those
      missing
    · This vertex will be chosen to have minimum distance to the component
      among choosable vertices
    · Delete components without full attribute sets (these do not produce drugs)
    · Repeat until no components remain

    Along the way, record deleted vertices, deleted components, minimum sizes
    of cutsets, betweenness centrality of components, degree centrality of
    components.

    Also calculate number of vertices deleted.

    Actual approach
    ---------------

    NetworkX only has algorithms for finding minimum cardinality cut sets;
    this is not nearly sufficient for our purposes.  To sort-of get around
    this problem, we first find two non-adjacent vertices uu and vv with
    |N(uu) \ N(vv)| x |N(vv) \ N(uu)| maximal, and find the minimum cutset
    that separates these vertices.

    We will work through deleting the elements of "cutset" until none are left,
    so we need to pass this set in as a parameter if it's already been found.
    Initially, set "cutset" = {}, and only look for a cutset in that case.
    Discard any inactive vertices from the cutset before proceeding.
    (This seems to work well, compared with starting from scratch at each step)
    """

    if len(cutset) == 0:
        # Find two non-adjacent vertices with highest possible degrees
        # print('looking for a new cutset')
        LC = list(nx.connected_component_subgraphs(H))
        # find max component, break ties randomly
        Cmax = max([len(Ctemp.nodes()) for Ctemp in LC])
        CC = random.choice([Ctemp for Ctemp in LC if len(Ctemp.nodes()) == Cmax])
        degree_sequence = sorted(CC.degree_iter(), key=itemgetter(1), reverse=True)
        all_non_equal_pairs = itertools.combinations(degree_sequence, 2)
        max_so_far = 0
        for uv in all_non_equal_pairs:
            u = uv[0]
            v = uv[1]
            # nonadjacent pair
            if ((u[0], v[0]) not in CC.edges()) and ((v[0], u[0]) not in CC.edges()):
                uNbsNotv = list(set(CC.neighbors(u[0])) - set(CC.neighbors(v[0])))
                vNbsNotu = list(set(CC.neighbors(v[0])) - set(CC.neighbors(u[0])))
                if len(uNbsNotv)*len(vNbsNotu) > max_so_far:
                    max_so_far = len(uNbsNotv)*len(vNbsNotu)
                    uu = u[0]
                    vv = v[0]
        cutset = {}
        # If two such vertices were found, then find a minimum cutset that
        # separates these vertices
        if max_so_far > 0:
            # print('highest degree-product pair ', uu, ',', vv, ', degree product', maxdegsofar)
            cutset = nx.minimum_node_cut(H, uu, vv)
            # print('cutset vertices', cutset)

    # If Cutset is not empty, then choose from it a random vertex
    if len(cutset) > 0:
        v = random.choice(list(cutset))
        # print('From cutset we chose ', v)
        cutset.discard(v)
        # print('Now cutset equals ', cutset)
    else:
        v = degree_sequence[0][0]
        # print('Cutset was empty! We chose highest degree vertex ', v)

    return [v, cutset]


def max_degree_targeting(H):
    """
    Given a graph H, this function returns a randomly chosen node of maximum
    degree.  This simulates targeting the most visible actor in the criminal
    network.

    Find a vertex with highest possible degree
    CSG: now breaks ties randomly
    """

    if H.nodes() == []:
        raise ValueError("Graph is empty")

    # CSG: I found the line below on
    # https://groups.google.com/forum/#!topic/networkx-discuss/Bai-YcHQdqg
    # It returns the (node,degree) list in decreasing order of degree
    degree_sequence = sorted(H.degree_iter(), key=itemgetter(1), reverse=True)
    max_degree = degree_sequence[0][1]
    highest_degree_nodes = [n for (n, d) in degree_sequence if d == max_degree]
    v = random.choice(highest_degree_nodes)
    # print('deleting', v)

    return v


def max_betweenness_targeting(H):
    """
    Given a graph H, this function returns a randomly chosen node of maximum
    betweenness.  This simulates targeting the brokers in the criminal network.

    Find a vertex with highest possible betweenness, breaking ties randomly
    (though ties are unlikely)
    """

    if H.nodes() == []:
        raise ValueError("Graph is empty")

    centralities = nx.betweenness_centrality(H, None, False)
    betweenness_sequence = sorted(centralities.items(), key=itemgetter(1), reverse=True)
    max_betweenness = betweenness_sequence[0][1]
    highest_betweenness_nodes = [n for (n, d) in betweenness_sequence if d == max_betweenness]
    v = random.choice(highest_betweenness_nodes)

    return v


def money_targeting(H, node_attributes, ignore_equipment):
    """
    Given a graph H, this function returns a node with the "Money" attribute,
    chosen by highest degree in H, and breaking ties randomly.  This simulates
    targeting the flow of money in the criminal network.  Should be the same
    as attribute_targeting(H, 1, node_attributes)

    Find a vertex with the "money" attribute and with highest possible degree.
    Break ties randomly.
    """

    if H.nodes() == []:
        raise ValueError("Graph is empty")

    # CSG: I found the line below on
    # https://groups.google.com/forum/#!topic/networkx-discuss/Bai-YcHQdqg
    # It returns the (node, degree) list in decreasing order of degree
    degree_sequence = sorted(H.degree_iter(), key=itemgetter(1), reverse=True)
    money_degree_sequence = [(n, d) for (n, d) in degree_sequence if (1 in calc_attributes([n], node_attributes, ignore_equipment))]

    if money_degree_sequence == []:
        # no more vertices with attribute "Money" left
        v = random.choice(H.nodes())
    else:
        max_degree = money_degree_sequence[0][1]
        highest_degree_money_nodes = [n for (n, d) in money_degree_sequence if d == max_degree]
        v = random.choice(highest_degree_money_nodes)

    return v


def precursor_targeting(H, node_attributes, ignore_equipment):
    """
    Added, 8 July 2015, but just noticed that the attribute_targeting function
    would have done the job.  Should be the same as
    attribute_targeting(H, 5, node_attributes)

    Given a graph H, this function returns a node with the "precursor"
    attribute, chosen by highest degree in H, and breaking ties randomly.
    This simulates targeting the flow of precursors in the criminal network.

    Find a vertex with the "precursor" attribute and with highest possible
    degree.  Break ties randomly.
    """

    if H.nodes() == []:
        raise ValueError("Graph is empty")

    # CSG: I found the line below on
    # https://groups.google.com/forum/#!topic/networkx-discuss/Bai-YcHQdqg
    # It returns the (node, degree) list in decreasing order of degree
    degree_sequence = sorted(H.degree_iter(), key=itemgetter(1), reverse=True)
    precursor_degree_sequence = [(n, d) for (n, d) in degree_sequence if (5 in calc_attributes([n], node_attributes, ignore_equipment))]

    if precursor_degree_sequence == []:
        # no more vertices with attribute "precursor" left
        v = random.choice(H.nodes())
    else:
        max_degree = precursor_degree_sequence[0][1]
        highest_degree_precursor_nodes = [n for (n, d) in precursor_degree_sequence if d == max_degree]
        v = random.choice(highest_degree_precursor_nodes)
        # print("deleting", v)

    return v


def attribute_targeting(H, attribute, node_attributes, ignore_equipment):
    """
    Given a graph H, this function returns a node with a specified attribute
    (between 1 and 8), chosen by highest degree in H, and breaking ties
    randomly.  This simulates targeting a particular attribute in the
    criminal network.

    Find a vertex with the specified attribute and with highest possible
    degree.  Break ties randomly.
    """

    if H.nodes() == []:
        raise ValueError("Graph is empty")

    # CSG: I found the line below on
    # https://groups.google.com/forum/#!topic/networkx-discuss/Bai-YcHQdqg
    # It returns the (node, degree) list in decreasing order of degree
    degree_sequence = sorted(H.degree_iter(), key=itemgetter(1), reverse=True)
    attribute_degree_sequence = [(n, d) for (n, d) in degree_sequence if (attribute in calc_attributes([n], node_attributes, ignore_equipment))]

    if attribute_degree_sequence == []:
        # no more vertices with the chosen attribute left
        v = random.choice(H.nodes())
    else:
        max_degree = attribute_degree_sequence[0][1]
        highest_degree_attribute_nodes = [n for (n, d) in attribute_degree_sequence if d == max_degree]
        v = random.choice(highest_degree_attribute_nodes)

    return v


def random_targeting(H):
    """
    Given a graph G, this function returns a randomly chosen node
    (no other conditions: just random choice over all nodes)

    This acts as a baseline for all other simulations: it could be argued
    that this simulates non-strategic law enforcement interventions.
    """

    if H.nodes() == []:
        raise ValueError("Graph is empty")
    v = random.choice(H.nodes())

    return v


def intervention_adaptation_simulation(G, node_attributes, tar, badapt, p,
                                       ignore_equipment):
    """
    This simulation deletes a node chosen according to one of the strategies
    above.

    After deletion, any critical component (now missing a resource) is given
    a chance to adapt.

    Along the way, record deleted vertices, deleted components, minimum sizes
    of cutsets, betweenness centralization of components, degree centralisation
    of components.

    Also calculate number of vertices deleted.

    G is a graph
    node_attributes is a list of [v, b1,.., b8] indicating whether a given
    attribute is present (as described above initialise_network())
    tar indicates which targeting method is to be used:  There are now 14,
    including no-adapt variations:

     (0) cut set
     (1) max degree
     (2) max betweenness
     (3) money targeting
     (4) random
     (5) precursor targeting       added July 2015
     (6) max degree no adapt       here we do not let the network adapt
     (7) cutset + max degree       a hybrid strategy, added November 2015
     (8) cutset + betweenness      a hybrid strategy, added November 2015
     (9) betweenness no adapt
    (10) cutset no adapt
    (11) money no adapt
    (12) precursors no adapt
    (13) random no adapt

    badapt is True if the network is allowed to adapt at each step
    i is the given number of the run (out of 100, for instance), used in the
    output file name
    p scales the probability that an edge is added between added vertices
    and each attribute-deficient component vertex
    """
    print "in simulation"
    GG = G.copy()
    S = []
    cutset = {}
    while GG.nodes() != []:
        # Remove node v from G, using the indicated targeting method
        # Find components and record v and components' centralization measures
        # [and whatever other information that one might wish to add]
        # The following is revolting but it has evolved this way.
        if (tar == 0) or (tar == 10):
            vS = cut_set_targeting(GG, cutset)
            v = vS[0]
            cutset = vS[1]
        elif (tar == 1) or (tar == 6):
            v = max_degree_targeting(GG)
        elif (tar == 2) or (tar == 9):
            v = max_betweenness_targeting(GG)
        elif (tar == 3) or (tar == 11):
            v = money_targeting(GG, node_attributes, ignore_equipment)
        elif (tar == 4) or (tar == 13):
            v = random_targeting(GG)
        elif (tar == 5) or (tar == 12):
            v = precursor_targeting(GG, node_attributes, ignore_equipment)
        elif tar == 7:
            if nx.number_of_nodes(GG) > nx.number_of_nodes(G)/2.0:
                vS = cut_set_targeting(GG, cutset)
                v = vS[0]
                cutset = vS[1]
            else:
                v = max_degree_targeting(GG)
        else:
            # tar == 8:
            if nx.number_of_nodes(GG) > nx.number_of_nodes(G)/2.0:
                vS = cut_set_targeting(GG, cutset)
                v = vS[0]
                cutset = vS[1]
            else:
                v = max_betweenness_targeting(GG)
        Gprev = GG.copy()
        GG.remove_node(v)
        LC = list(nx.connected_component_subgraphs(GG))
        # If network is allowed to adapt (badapt = True),
        # then for any component lacking attributes,
        # find the vertices AddNodes with these missing attributes.
        if badapt and (len(LC) > 1):
            for CC in LC:
                CCnodes = CC.nodes()
                Att = calc_attributes(CCnodes, node_attributes, ignore_equipment)
                # TEST!!
                # Let's test what happens if we ignore the "Equipment"
                # attribute
                if len(Att) + ignore_equipment < 8:
                    # print('adapt? Attributes = ', Att, 'nr nodes in component = ', len(CCnodes))
                    # Try this: OK to adapt to vt if it replaces all missing
                    # attributes, with the possible exception of equipment (4)
                    AddNodes = [vt for vt in GG.nodes() if (vt not in CCnodes) and (len(set(Att + [j for j in range(1, 9) if node_attributes[vt-1][j] > 0])) + ignore_equipment == 8) and nx.has_path(Gprev, vt, CCnodes[0])]
                    # Choose a vertex from AddNodes with probability
                    # proportional to the inverse of the min distance to CC
                    if AddNodes != []:
                        distAll = {vtemp1: nx.single_source_shortest_path_length(Gprev, vtemp1) for vtemp1 in AddNodes}
                        dminAll = {vtemp2: min([distAll[vtemp2][vv] for vv in CCnodes]) for vtemp2 in AddNodes}
                        weightsCC = [1.0/dminAll[vtemp3] for vtemp3 in AddNodes]
                        j = weighted_choice(weightsCC)
                        vadd = AddNodes[j]
                        # print('vertex to add = ', vadd, ', attributes ', calc_attributes([vadd], node_attributes))
                        for cv in CCnodes:
                            # only allow former neighbours of v to link to
                            # vadd, and only with probability p
                            CutOff = random.random()
                            if (cv in Gprev.neighbors(v)):
                                # print('?')
                                if CutOff < p:
                                    GG.add_edge(vadd, cv)
                                    # for debugging purposes CSG 1.4.2016
                                    # print("*")

        # Now all ailing components have had a chance to adapt. Let's see if
        # they have succeeded.
        # Remove components that are too small or that still lack some
        # attributes (i.e., their attempt to recover has failed)
        # Calculate connected components again, since GG may have changed.
        LC = list(nx.connected_component_subgraphs(GG))
        # print('After adaptation, before pruning, now # components =',len(LC))
        bad_vertices = []
        for CC in LC:
            CCnodes = CC.nodes()
            Att = calc_attributes(CCnodes, node_attributes, ignore_equipment)

            # TEST!!
            # Let's test what happens if we ignore the "Equipment" attribute
            # The component lacks some attributes
            if len(Att) + ignore_equipment < 8:
                bad_vertices = bad_vertices + CCnodes
                # This may seem repetitive but it will also show what
                # components are missing at the very last step of the
                # simulation.
                # print('Component of size',len(CCnodes),'now inactive, delete: attributes',Att)
                # print('Components consisted of vertices',CCnodes)
        if bad_vertices != []:
            # Remove nodes bad_vertices from G
            GG.remove_nodes_from(bad_vertices)
            # We should also remove any bad_vertices nodes from the cutset,
            # if we are doing cutset targeting
            if (tar == 0) or (tar == 10):
                for j in bad_vertices:
                    cutset.discard(j)

        # The tidy-up is finished now, so we can add the data from the current
        # graph to the list
        # Recalculate Cmax in case it has changed.
        LC = list(nx.connected_component_subgraphs(GG))
        nCC = nx.number_connected_components(GG)
        if nCC > 1:
          print('More than 1 component, actually ',nCC)
        if LC == []:
            Cmax = 0
        else:
            Cmax = max([len(Ctemp.nodes()) for Ctemp in LC])
        S = S + [[v, betweenness_centralisation(GG), degree_centralisation(GG), nCC, Cmax]]

    return S


def main():
    (G, node_attributes) = initialise_network('criminal.txt')
    # number of targeting strategies, usually equal to
    # len(OUTPUT_FILENAME_BY_TARGET)
    ntarget = 14

    # number of runs per targeting method
    nn = 100
    # For debugging purposes, makes it quicker!!
    # nn = 5

    # reset the random seed using the system time
    random.seed()
    # [2016-07-09:MT] Need repeatable results for comparison with old version
    #                 of code
    #random.seed(1)

    # Do we want to ignore the Equipment attribute?
    # For now, let's keep considering it.
    # To ignore it, put 1 here.
    ignoreEquip = 0

#    SS = [[0 for i in range(nn)] for tar in range(ntarget)]

    # Simulate for each targeting method, allowing adaptation
    for tar in range(ntarget):
        # CSG 16.7.2015, added as a check that program is progressing
#        print(OUTPUT_FILENAME_BY_TARGET[tar])
        for i in range(nn):
            print('Run number ', i)

            # No-adaptation strategies
            if tar in (6, 9, 10, 11, 12, 13):
                adaptation = False
            else:
                adaptation = True

            RunValues = intervention_adaptation_simulation(
                G, node_attributes, tar, adaptation, 0.5, ignoreEquip)

#            # Adding zeros here makes averaging easier
#            SS[tar][i] = RunValues + [[0, 0, 0, 0, 0] for j in range(padding)]

#    # Averages
#    nmin = [min([len(SS[tartemp][i])-padding for i in range(nn)]) for tartemp in range(ntarget)]
#    nmax = [max([len(SS[tartemp][i])-padding for i in range(nn)]) for tartemp in range(ntarget)]
#    Sfreq = [0 for i in range(ntarget)]
#    SSav = [0 for i in range(ntarget)]

    # with or without adaptation
#    nmaxglobal1 = max(nmax)

    # only with adaptation
    # nmaxglobal2 = max([nmax[tar] for tar in [0,1,2,3,4,5,7,8]])

    # no random, only with adaptation
#    nmaxglobal2 = max([nmax[tar] for tar in [0, 1, 2, 3, 5, 7, 8]])
    #nmaxglobal2 = max([nmax[tar] for tar in [0,1,2,3,5]])

    #nmaxglobal3 = max([nmax[tar] for tar in [0,1,2,7,8]])

    #nmaxglobal = [nmaxglobal1,nmaxglobal2,nmaxglobal3]
#    nmaxglobal = [nmaxglobal1, nmaxglobal2]

    print("All good!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
