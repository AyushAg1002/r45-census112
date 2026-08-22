# Certified saturated-residue route for R(4,5,22,e=112)

## Why the saturated residue is the right search

Let `G` be a graph in `R(4,5,22,e=112)`.  If some nonedge `uv` can be
added without creating a `K4`, then `G+uv` is in
`R(4,5,22,e=113)`: adding an edge cannot create an independent set.
Consequently every non-`K4`-saturated member of the 112-edge layer is a
valid one-edge deletion of a member of the certified 113-edge layer.

The local public 113-edge catalogue has 30,976 graphs.  Direct deletion
produces 3,500,288 records.  Exactly 887,138 deletion records remain in
`R(4,5,22,e=112)` after rejecting those that create an independent 5-set.
Ordinary nauty 2.9.3 canonicalisation gives 785,888 non-isomorphic graphs
in this nonsaturated part.  The remaining task is an exhaustive census of
the `K4`-saturated residue; that residue is nonempty.

## Explicit SAT instance

Run:

```sh
python3 src/saturated_cnf.py \
  --cnf data/r4522.112.saturated.cnf \
  --manifest results/saturated_cnf_manifest.json
python3 -m unittest tests/test_saturated_cnf.py -v
```

The deterministic formula has the following dimensions:

| component | variables | clauses |
|---|---:|---:|
| graph edges | 231 | 0 |
| no `K4` | 0 | 7,315 |
| no independent 5-set | 0 | 26,334 |
| exactly 112 edges | 25,871 auxiliary | 103,152 |
| `K4`-saturation | 43,890 witnesses | 219,681 |
| **total** | **69,992** | **356,482** |

The generated CNF has SHA-256
`e65db47cc9bc70924b6ea7550cc93d8b8370bffc32b16c4275ca7d5b9d70297f`.
Kissat 4.0.4 found a saturated witness, independently audited without the SAT
auxiliary assignment.  Its canonical graph6 record is

```text
U?owqT_T@EelPxeXTiU\goB}QztebfjO\yxgJmq_
```

It has degree sequence `(11^9,10^9,9^3,8)`, clique number 3, independence
number 4, and SHA-256
`9f94ad40db08993931c1b798b16e2601afbea7530f2122a0ff6b08a45e017ca4`.

For each nonedge `uv`, the saturation encoding introduces one witness
`w(uv,xy)` for every pair `xy` of the other 20 vertices.  The long clause

```text
e(uv) OR w(uv,x1y1) OR ... OR w(uv,x190y190)
```

requires a witness when `uv` is absent.  Five binary clauses make a true
witness imply the edges `ux,uy,vx,vy,xy`.  Thus adding `uv` creates the
`K4` on `u,v,x,y`.  Reverse witness implications are deliberately
unnecessary: the encoding is existential in the witness variables.

The exact-edge counter is a direct transcription of the formally proved
`LeanSMS.Encode.encodeExactlyK` construction, not a solver-specific
cardinality primitive.  The first 231 DIMACS variables use SMS's required
row-major edge order.

## SMS census commands

SMS is officially supported on Linux.  Pin the versions before production:

```sh
git clone https://github.com/markirch/sat-modulo-symmetries.git
cd sat-modulo-symmetries
git checkout 63958bd09a871e484c59270a1d0f22d482dc5770
git submodule update --init --recursive
./build-and-install.sh -l
```

From this project directory, enumerate the residue without a minimality
cutoff (a cutoff can leave duplicate labelings):

```sh
smsg --vertices 22 \
  --dimacs data/r4522.112.saturated.cnf \
  --all-graphs \
  --sym-break-clauses results/saturated.symmetry.json \
  --cadical-config no-binary \
  > results/saturated.sms.models
```

For a large run, stdout must be streamed as raw SMS edge lists.  PySMS's
`graph6_format=True` implementation buffers the complete output and should
not be used for a potentially large catalogue.  Convert and audit each
record afterward, then compare nauty and Traces canonicalisations.

The streaming converter and coverage-CNF builder are exercised with:

```sh
python3 src/prepare_sms_coverage.py extract \
  --models results/saturated.sms.models \
  --graph6-out results/saturated.sms-labelled.g6 \
  --manifest results/saturated.sms-labelled.json

# The second input below must contain only clauses accepted by LeanSMS.
python3 src/prepare_sms_coverage.py cover \
  --base data/r4522.112.saturated.cnf \
  --verified-symmetry results/saturated.verified-symmetry.cnf \
  --catalogue results/saturated.sms-labelled.g6 \
  --output results/saturated.covered.cnf \
  --manifest results/saturated.covered.json
```

## Turning enumeration into a checked coverage theorem

An SMS `UNSAT` exit after `--all-graphs` is not by itself an independently
checkable proof, because dynamic symmetry clauses are not RUP consequences
of the base CNF.  Use this two-phase pipeline:

1. Pin LeanSMS at commit
   `f5e95289e85fd7b019e768ef759a11f736802f30`.
2. Parse every SMS clause/permutation pair from `saturated.symmetry.json`.
   LeanSMS's `verifyDominationFull` proves that every lexicographically
   minimal graph satisfies each clause.
3. Validate every output graph directly: order 22, exactly 112 edges, no
   `K4`, no independent 5-set, and saturated.
4. Add one edge-only blocking clause for every SMS-labelled output.  Since
   the base formula fixes exactly 112 edges, the 112-literal clause
   `OR[-e for e in E(G)]` blocks exactly that graph edge assignment.
5. Form `base CNF + verified symmetry clauses + catalogue blockers` and run
   an ordinary proof-producing solver:

```sh
smsg --no-SMS \
  --dimacs results/saturated.covered.cnf \
  --lrat-output results/saturated.covered.lrat \
  --cadical-config no-binary
```

6. Check the LRAT trace independently and in Lean.  The required coverage
   theorem is a small extension of LeanSMS's
   `trustModel_impossibility`: any hypothetical saturated Ramsey graph has
   a lex-minimal isomorphic copy; verified symmetry clauses preserve that
   copy; final UNSAT means it falsifies a catalogue blocker and hence equals
   a listed SMS-labelled graph.

LeanSMS currently provides verified clique-free and exact-cardinality
encodings and the symmetry/LRAT chain.  It does **not** yet provide a
turnkey catalogue-coverage theorem, an independent-set-free encoder, or the
saturation encoder.  Those three additions are required; claiming the raw
SMS run as formally certified without them would overstate the result.

## Isomorphism and certificate limitations

The LRAT/SMS chain certifies coverage, not pairwise non-isomorphism of a
postprocessed graph6 file.  For a credible computational paper:

- retain the exact SMS-labelled catalogue used by the blocking proof;
- provide an explicit permutation mapping every SMS output to its published
  canonical representative (easy for a small checker to verify);
- canonicalise independently with nauty and Traces, and preferably a second
  library such as bliss/dejavu;
- report hashes, sizes, tool commits, solver exit codes, and proof-checker
  results for every shard.

Complete pairwise non-isomorphism is still inside the trusted boundary of
the canonical-labelling implementations unless a proof-producing or
formally verified canonicaliser is added.  Two independent canonicalisers
plus the checked coverage chain is the realistic publication-grade target.

## Parallelisation warning

Do not naively fix a labelled degree sequence or an arbitrary edge-prefix
cube and then run full `S_22` symmetry breaking: the resulting CNF is no
longer invariant under all vertex permutations.  A sharded run must either

- be cubed by SMS's global canonical search and retain a checked cube cover,
  or
- restrict symmetry to the stabiliser of the fixed coloured partition and
  verify those restricted symmetry clauses.

The safest first benchmark is the monolithic saturated instance.  If it is
too large, construct a binary DPLL cube tree whose coverage can be checked
independently and carry the already verified global symmetry clauses into
every leaf.

## Feasibility

The nonsaturated side is already modest: 887,138 valid deletion records and
785,888 nauty classes.  The saturated side is the unknown dominant cost.  A
plain, symmetry-free 356,482-clause instance found one saturated witness in
about one minute with Kissat on the development machine, while CaDiCaL did
not finish the same first-model query within one minute.  This establishes
nonemptiness but says little about census size.  Run a bounded SMS pilot and
measure outputs, learned symmetry clauses, and models per hour before
allocating a cluster campaign.
