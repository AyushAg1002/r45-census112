# Exact gluing route for the 112-edge census

This note records an exhaustive route to generate
\(\mathcal R(4,5,22,e=112)\). It is a specification for the next computation,
not a completed census.

## Use a maximum-degree root

If \(G\in\mathcal R(4,5,22)\) has 112 edges, its average degree is
\(224/22>10\), so \(G\) has a vertex \(v\) of degree at least 11. Since
\(G[N(v)]\in\mathcal R(3,5,d(v))\) and \(R(3,5)=14\), every degree is at
most 13. Choosing \(v\) to have maximum degree leaves just

\[
d=d(v)\in\{11,12,13\}.
\]

Put

\[
A=G[N(v)]\in\mathcal R(3,5,d),\qquad
B=G[V(G)\setminus(N(v)\cup\{v\})]
  \in\mathcal R(4,4,21-d).
\]

All required seed catalogues are complete and public. Their raw Cartesian
products are:

| \(d\) | \(|\mathcal R(3,5,d)|\) | \(|\mathcal R(4,4,21-d)|\) | seed pairs |
|---:|---:|---:|---:|
| 11 | 105 | 103,706 | 10,889,130 |
| 12 | 12 | 14,701 | 176,412 |
| 13 | 1 | 2,079 | 2,079 |
| **total** | | | **11,067,621** |

This is much smaller than rooting at a minimum-degree vertex. After the
separate minimum-degree computation proves \(\delta(G)\ge7\), the
per-vertex degree intervals below eliminate 63,749 of the \(d=11\) pairs and
none of the other pairs, leaving 11,003,872 necessary seed pairs.

## Cross-edge variables and exact cardinality

For \(a\in A\), \(b\in B\), let \(x_{ab}=1\) when \(ab\in E(G)\). If
\(a=e(A)\), \(b=e(B)\), the number of cross edges is forced to be

\[
c=112-d-a-b.
\]

Thus every job includes \(\sum x_{ab}=c\). Because \(v\) has maximum degree
\(d\), and because the verified low-degree lemma gives \(\delta(G)\ge7\),
the row and column sums obey

\[
\max(0,6-d_A(a))
\le \sum_{b\in B}x_{ab}
\le d-1-d_A(a),
\]

\[
\max(0,7-d_B(b))
\le \sum_{a\in A}x_{ab}
\le d-d_B(b).
\]

These inequalities are safe pruning constraints. For an implementation that
does not wish to trust the low-degree lemma, replace 6 and 7 in the lower
bounds by 4 and 5 respectively; completeness is unchanged.

## Necessary and sufficient mixed-subgraph clauses

The seed properties already exclude forbidden subgraphs contained entirely
inside \(A\), \(B\), or containing \(v\). The following clauses exclude all
remaining cases, so together with the seed checks they are necessary and
sufficient.

To exclude \(K_4\):

1. For each \(a\in A\) and triangle \(T\subseteq B\), require
   \(\bigvee_{b\in T}\neg x_{ab}\).
2. For each edge \(aa'\in E(A)\) and edge \(bb'\in E(B)\), require
   \[
   \neg x_{ab}\vee\neg x_{ab'}\vee
   \neg x_{a'b}\vee\neg x_{a'b'}.
   \]

There is no three-\(A\), one-\(B\) case because \(A\) is triangle-free.

To exclude independent 5-sets:

1. For each independent 4-set \(I\subseteq A\) and \(b\in B\), require
   \(\bigvee_{a\in I}x_{ab}\).
2. For each independent 3-set \(I\subseteq A\) and nonedge \(bb'\) of
   \(B\), require
   \(\bigvee_{a\in I}(x_{ab}\vee x_{ab'})\).
3. For each nonedge \(aa'\) of \(A\) and independent 3-set \(J\subseteq B\),
   require
   \(\bigvee_{b\in J}(x_{ab}\vee x_{a'b})\).

There is no one-\(A\), four-\(B\) case because \(B\) has no independent
4-set. An independent 5-set containing \(v\) is excluded for the same reason.

## Backtracking order

A compact exhaustive generator can attach the vertices of \(B\) one at a
time. Before search, enumerate every feasible cone \(C_b\subseteq A\) with

\[
\max(0,7-d_B(b))\le|C_b|\le d-d_B(b)
\]

that meets every independent 4-set of \(A\). Then order the vertices of
\(B\) by decreasing cone size and by density of the already attached part of
\(B\), as in Section 3 of Angeltveit--McKay. During attachment, propagate the
mixed clauses, row capacities, and remaining edge-cardinality interval.
Canonicalize completed graphs with nauty; automorphisms of \(A\) and \(B\)
can also be used to select one cone tuple from each orbit.

The minimum transversal size for the independent-4 hypergraph of \(A\) is 3
for every order-11 seed, 4 for every order-12 seed, and 5 for the unique
order-13 seed. These are cheap additional cone checks, although the forced
cross-edge totals are already above the resulting aggregate lower bounds.

## Independent verification route

A credible census should use two disjoint paths:

1. **Primary generator:** the cone-tree/backtracking construction above,
   producing canonical graph6 records and a manifest for every seed pair.
2. **Independent checker:** encode each cross matrix as SAT using the exact
   clauses above, or adapt the HOL4 gluing framework used for the formal proof
   of \(R(4,5)=25\). Check that every primary output is accepted and that every
   seed pair's solution-orbit count agrees.

For an especially small trusted boundary, retain a CNF plus LRAT/FRAT proof
for every seed pair reported unsatisfiable. For satisfiable pairs, directly
validate every output graph, canonicalize it independently, and compare the
sorted graph6 census byte-for-byte.

The vertex-deletion route through
\(\mathcal R(4,5,21,e=102,\ldots,107)\) is exact but is less attractive as a
primary method because only the 106- and 107-edge layers are presently in the
public edge-extreme package. It remains valuable as an independent audit once
the missing order-21 layers have themselves been generated.

## Input hashes

| file | records | SHA-256 |
|---|---:|---|
| `r35_11.g6` | 105 | `d5c52b2209e25080868adeef2dd52fa32835e5143208aceef129332c9184f16e` |
| `r35_12.g6` | 12 | `322e7a54e67f4201bd37998ab420afb3eee41b1dcd6b277b7f055bda152da95e` |
| `r35_13.g6` | 1 | `eb4d3f787f07ed14c0a82a83bee170ed096c24b6a7e971fded185ca1a760798f` |
| `r44_10.g6.gz` | 103,706 | `c34980e1ce734573d3a92486c6071144e154ee53e049b0e050cb1f8ffe0f6691` |
| `r44_9.g6` | 14,701 | `fcdcf01e586bf1d34860e4bd6d8f8d4ad91a02baa9acfea73ab7593f7c214287` |
| `r44_8.g6` | 2,079 | `b27389f7b1c70f823161a2cca629bed3f4fbf058a43907637c0f9ce2e0cc4ab3` |

Sources: McKay's [public Ramsey graph catalogues](https://users.cecs.anu.edu.au/~bdm/data/ramsey.html),
Angeltveit--McKay's [high-edge census method](https://arxiv.org/html/2409.15709),
and the [formal R(4,5)=25 gluing implementation](https://github.com/barakeel/ramsey).
