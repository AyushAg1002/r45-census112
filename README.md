# The 112-edge layer of Ramsey(4,5,22)

This workspace contains a reproducible first phase of a proposed census of

\[
\mathcal R(4,5,22,112)
=\{G: |V(G)|=22,\ e(G)=112,\ K_4\nsubseteq G,\ I_5\nsubseteq G\}.
\]

It establishes two exact computational results:

1. There are exactly **785,888 nonisomorphic non-\(K_4\)-saturated** graphs
   in \(\mathcal R(4,5,22,112)\), conditional on the published completeness
   of the 30,976-member 113-edge input catalogue.
2. Every graph in the full 112-edge layer has minimum degree at least 7,
   conditional on the published completeness of the 106- and 107-edge
   order-21 input catalogues.

The full 112-edge census is **not complete**. A SAT witness proves that the
\(K_4\)-saturated residue is nonempty, so the 785,888 graphs are a proper
subclass and the full layer contains at least 785,889 graphs. The exact
saturated count is the remaining paper-level target.

## Exact nonsaturated-sector theorem

A graph is \(K_4\)-saturated if adding any missing edge creates a \(K_4\).
If \(F\in\mathcal R(4,5,22,112)\) is not saturated, some missing edge can be
added without creating a \(K_4\). Adding an edge cannot create an independent
set, so the enlarged graph lies in \(\mathcal R(4,5,22,113)\). Conversely,
every valid edge deletion from a 113-edge Ramsey graph produces a
nonsaturated 112-edge graph. Therefore the complete published 113-edge
catalogue gives a complete generation route for this sector.

The exact computation was:

| stage | records |
|---|---:|
| published \(e=113\) inputs | 30,976 |
| all edge deletions | 3,500,288 |
| deletions still in \(\mathcal R(4,5)\) | 887,138 |
| nonisomorphic outputs | **785,888** |

A standalone C++20 program with its own graph6 parser, encoder, deletion
loop, and independent-set filter reproduces all 887,138 valid deletion
records byte-for-byte. Ordinary nauty and the distinct Traces
canonical-labeling algorithm then both return 785,888 classes. Mapping the
Traces output back through ordinary-nauty canonicalization produces a file
byte-for-byte identical to the primary catalogue. A separate standard-library
Python checker validates every output graph and every nonsaturation witness.

The final catalogue is
`data/r4522.112.nonsaturated.g6`, with SHA-256

```text
d2c556f52d13dd4d38ed955bedd3db5f52b883faafc45fe5561e611afa5cd6a2
```

The distributable gzip file is `data/r4522.112.nonsaturated.g6.gz`
(SHA-256 `fcb0ef605eee3150d95d5b91535934ba9b711450a2edb7e55fd39a37ec3211d5`).

Its number of addable nonedges has the exact distribution:

| addable nonedges | graphs |
|---:|---:|
| 1 | 695,535 |
| 2 | 86,374 |
| 3 | 3,868 |
| 4 | 106 |
| 5 | 5 |

As a regression test, applying the same route to the 133 published 114-edge
graphs gives 4,077 valid deletions and 3,296 nonisomorphic 113-edge graphs.
All 3,296 occur in the published 30,976-member catalogue. Thus that catalogue
itself splits into 3,296 nonsaturated and 27,680 saturated graphs.

## Minimum-degree theorem

If \(v\) has minimum degree \(d\) in a hypothetical member of the 112-edge
layer, deleting \(v\) gives a graph in
\(\mathcal R(4,5,21,112-d)\). The published value
\(E(4,5,21)=107\) first gives \(d\ge5\). Exhaustive extension of all 31
order-21 seeds at 107 edges and all 10,188 seeds at 106 edges eliminates
\(d=5\) and \(d=6\), respectively.

Two structurally different implementations agree:

- `verify_low_degree.py` uses a triangle-pruned hypergraph-transversal search;
- `src/extend_from_min_vertex.cpp` directly tests all subsets, including all
  \(552,841,632\) six-subsets across the 10,188 seeds.

The direct search finds 443 six-subsets meeting every independent 4-set; all
443 contain a triangle. Hence

\[
G\in\mathcal R(4,5,22,112)\implies 7\le\delta(G)\le10.
\]

## Saturated witness

The deterministic CNF in `data/r4522.112.saturated.cnf` has 69,992 variables
and 356,482 clauses. Kissat found the following canonical graph6 witness:

```text
U?owqT_T@EelPxeXTiU\goB}QztebfjO\yxgJmq_
```

It has degree sequence \((11^9,10^9,9^3,8)\), clique number 3, independence
number 4, and is \(K_4\)-saturated. Ordinary nauty and Traces canonicalize
the solver-produced witness, and separately implemented combinatorial and
bit-parallel audits validate it. Its newline-inclusive SHA-256 is

```text
9f94ad40db08993931c1b798b16e2601afbea7530f2122a0ff6b08a45e017ca4
```

## Reproduction

The public release does not redistribute the third-party Ramsey input
catalogues. Fetch and hash-check those inputs and nauty 2.9.3 from their
authors' sites with:

```sh
./scripts/fetch_inputs.sh
```

Then configure and build nauty and run the fast tests with:

```sh
make test
```

The `test` target performs the nauty configure/build step automatically.

Install `requirements-sat.txt` to run the optional exhaustive
small-instance cardinality-encoding test and to regenerate the SAT witness.

To rerun both complete minimum-degree implementations:

```sh
make verify-low-degree
```

To regenerate, cross-canonicalize, and validate the nonsaturated
catalogue:

```sh
make reproduce-nonsaturated
```

To repeat the deletion and Ramsey filtering without `deledgeg` or `pickg`
and compare both the raw and canonical streams byte-for-byte:

```sh
make independent-deletion-crosscheck
```

With `python-sat==1.9.dev15` installed, one command reruns the complete
test and reproduction suite and writes a hash-pinned summary to
`results/reproduction_summary.json`:

```sh
make reproduce-all
```

After compiling `paper/main.tex` to `output/pdf/main.pdf`, the following
builds deterministic public-release archives under `release/public/`:

```sh
make release
```

The complete reproduction takes a few minutes on the recorded Apple-silicon
machine; most of that time is the separate per-graph Python audit.

## Author, repository, and licenses

Ayush Agarwal (Independent Researcher, Bangalore, India) is the sole author.
The public repository is
<https://github.com/AyushAg1002/r45-census112>.
The versioned archival release is
<https://doi.org/10.5281/zenodo.22057247>.

- manuscript and documentation: CC BY 4.0;
- original code: MIT;
- derived graph catalogue and original manifests: CC0 1.0.

See `LICENSE` for the scope and official license links. Third-party Ramsey
input catalogues and nauty are not redistributed and remain under their own
terms.

## Remaining publishability boundary

These results are real, exact progress, but they are not yet a full census
paper. The missing class is the \(K_4\)-saturated residue. Two complete routes
are specified here:

- `GLUING_ROUTE.md` gives a maximum-degree rooted construction with
  11,003,872 seed pairs after safe pruning;
- `notes/SAT_CERTIFICATION.md` gives a 356,482-clause saturated-residue CNF
  and a route through SAT Modulo Symmetries plus checked coverage proofs.

The current package supports a short computational/data note about the exact
nonsaturated sector and the full-layer minimum-degree theorem. Completing the
saturated census would materially strengthen it into a full-layer census
paper.

## Sources and trusted boundary

The source catalogues are from Brendan McKay's
[Ramsey graph page](https://users.cecs.anu.edu.au/~bdm/data/ramsey.html).
The published counts and generation method are in Angeltveit and McKay,
[\(R(5,5)\le46\)](https://onlinelibrary.wiley.com/doi/full/10.1002/jgt.70029),
especially Section 3.3 and Table 1.

The claims depend on the published catalogues being complete. Exhaustive
deletion and filtering are implemented twice; canonical labeling remains
inside a deliberately redundant nauty/Traces trusted boundary. Direct
graph-property validation uses neither library. A targeted literature search
did not find the two statements, but novelty should not be asserted before
expert review or contact with the catalogue authors.
