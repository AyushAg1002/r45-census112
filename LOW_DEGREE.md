# Low-minimum-degree exclusion for R(4,5,22,112)

## Result

Two exhaustive implementations establish, conditional only on the
completeness of the two cited public input catalogues,

\[
G\in\mathcal R(4,5,22),\quad e(G)=112
\quad\Longrightarrow\quad \delta(G)\ge 7.
\]

This is a useful census lemma, not by itself a claim that the full
\(\mathcal R(4,5,22,e=112)\) census has been completed. A targeted literature
search did not locate this statement explicitly, but novelty has not been
established and should not be claimed without a broader review and contact
with the catalogue authors.

## Exact reduction

Let \(v\) be a minimum-degree vertex and put \(d=d(v)\). Since
\(G-v\in\mathcal R(4,5,21)\) and the published exact value is
\(E(4,5,21)=107\),

\[
112-d=e(G-v)\le107,
\]

so \(d\ge5\). On the other hand, the average degree is \(224/22<11\),
so \(d\le10\).

For a fixed seed \(H=G-v\), write \(S=N_G(v)\). The graph obtained by adding
\(v\) to \(H\) is in \(\mathcal R(4,5)\) if and only if

1. \(|S|=d\);
2. \(H[S]\) is triangle-free, since a triangle in \(S\) makes a \(K_4\)
   together with \(v\); and
3. \(S\) meets every independent 4-set of \(H\), since an independent
   4-set in \(V(H)\setminus S\) makes an independent 5-set together with
   \(v\).

For \(d=5\), the seed must be one of the 31 public members of
\(\mathcal R(4,5,21,e=107)\). For \(d=6\), it must be one of the 10,188
public members of \(\mathcal R(4,5,21,e=106)\). Exhaustive hypergraph
transversal search finds no valid neighborhood in either layer.

## Reproduction

Both implementations check input hashes and dimensions and validate the
Ramsey constraints before extension. The Python implementation uses only the
standard library and performs triangle-pruned hypergraph-transversal search;
the C++20 implementation directly enumerates every candidate subset.

```sh
cd /path/to/r45_census112
make verify-low-degree
```

On the frozen Apple-silicon run, the Python search completed both layers in
36.79 seconds. It visited 24,653 states for degree 5 and 22,311,336 states for
degree 6 and found no valid labelled neighborhood. The independent C++20
program directly tested all 630,819 five-subsets and all 552,841,632
six-subsets in 3.68 seconds total. Exactly 443 six-subsets met every
independent 4-set, and all 443 contained a triangle; hence none was valid.

The recorded outputs are `results/low_degree_transversal.json` and
`results/low_degree_direct_cpp.txt`.

## Input provenance

Both catalogues come from Brendan McKay's public
[Ramsey graph page](https://users.cecs.anu.edu.au/~bdm/data/ramsey.html),
which describes the edge-extreme files as complete. The counts
\(|\mathcal R(4,5,21,e=107)|=31\) and
\(|\mathcal R(4,5,21,e=106)|=10{,}188\) also appear in Angeltveit and
McKay's [`R(5,5) <= 46`](https://arxiv.org/html/2409.15709).

| file | records | SHA-256 |
|---|---:|---|
| `r4521.107.g6` | 31 | `6ef8619d5d6be9efa15cb9a5ccb6b0da7304cfbfd57fff29bb0dec2e46f81bef` |
| `r4521.106.g6` | 10,188 | `2be4df6ba89b1c55743624fb6e8141741aef82b06a922aa0a069923942389593` |

The second complete implementation therefore covers every candidate subset,
not only a sample. Completeness of the published input catalogues remains an
explicit trusted boundary of the theorem.
