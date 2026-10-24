# Reversible Branch Lab

A small executable comparison laboratory for the divstep branch-decoding rule in [Gu, Kemeny, Yelin and Lukin, arXiv:2610.22367v1](https://arxiv.org/html/2610.22367v1), Appendix A. The underlying arithmetic rule is **prior work**. This repository supplies an original reference implementation and finite controls, not a new inversion algorithm or a claim of better published resources.

## Run

Use Python3.12 or later, with no third-party dependencies:

```text
python verify.py
```

The verifier checks the source manifest, runs the four programs in a temporary directory, compares their scientific outputs with the recorded results and checks the generated gate list byte for byte. Observation timestamps and interpreter versions are preserved as provenance, rather than required to remain equal on a new execution.

## What is checked

- Integer recurrence and backward recovery for all4095 inputs across odd moduli3..127, including composites:47168 active steps and12918 ambiguous decisions.
- Exact truth tables and algebraic normal forms for depths2..10. Published term counts at depths2..8 are reproduced. Additional small depths are finite diagnostics, not a circuit lower bound.
- An original compute-copy-uncompute oracle built from X, CNOT and Toffoli gates. Truth tables are checked at depths2..8. At depth6, all4096 combinations of the ten input bits, control flag and target bit are simulated through the complete gate list; inputs and flag are preserved and workspace returns to zero.

The current depth6 reference uses101 Toffolis,2056 CNOTs,2 X gates and52 workspace qubits, or64 qubits including inputs, target and flag. These counts include the controlled output and reverse cleanup. They do **not** include the complete divstep walk, depth-flag computation, data routing, physical error correction or hardware timing. The supplied flag is an input to this oracle, not a free complete depth selector.

Every primitive in that unitary reference is a basis permutation with positive amplitudes, so that model introduces no relative phase. This structural observation and finite basis simulation are not a formal proof-assistant verification or a noisy-device test.

## Compare the same cleanup model

The published evaluator also permits measurement-based uncomputation (MBU). Comparing that model with a purely unitary reverse pass would mix cost conventions. `src/compare_models.py` now compares both versions of the arithmetic DAG with an original reconstruction of the described prefix-traversal strategy, under the same **supplied-flag oracle** interface. The source strategy is attributed to [andigu/uncompute, pinned commit64b5a13](https://github.com/andigu/uncompute/blob/64b5a13aa249f1360846657392e6c66817b26d0f/tasks/modinv-point-add/circuits/divsteps/engine.py); its complete engine has not been run or reproduced here.

| Depth | Arithmetic MBU: Toffolis / total qubits / TQ | Prefix reconstruction MBU: Toffolis / total qubits / TQ |
| --- | ---: | ---: |
|5|24 /35 /840|38 /12 /456|
|6|51 /64 /3264|124 /15 /1860|
|7|84 /99 /8316|430 /18 /7740|
|8|124 /141 /17484|1707 /22 /37554|

Fewer Toffolis therefore do **not** imply a smaller space-time product. At depth6 the arithmetic reference uses fewer Toffolis but has a larger oracle TQ. At depth8 its local TQ is smaller while its qubit demand is much larger. These finite results do not establish a point-adder Pareto improvement.

The checker evaluates complete basis truth tables, including flag and target, for depths5..8:1024,4096,16384 and65536 inputs per circuit respectively. All16 constructed streams pass. It represents the phase as an exact linear form in independent measurement-record bits, so each finite input check covers every measurement record rather than a random sample. A second serial checker covers4096 cases per depth6 circuit. Omitting one phase correction produces detected counterexamples in both MBU families. The prefix traversal also reproduces the source's stated12 interior nodes at depth5.

For MBU, each discarded AND bit contributes its measurement-dependent phase and the conditional CZ correction cancels it. Measurement bits do not control basis-changing gates here. Counts include those measurements and corrections, but neither is counted as a Toffoli, following the stated model. They are not physically free. This is finite model verification, not a formal proof assistant, realistic noise model or universal benchmark. Complete flag generation, routing, packing and the later destruction of a predicate remain outside the oracle contract.

## Research boundary

No advantage over the paper's actual optimized circuits has been established. Comparing a dense algebraic normal form with an arithmetic circuit is not a fair optimal-circuit comparison. This simple design retains nonlinear intermediate nodes, which is costly in workspace. A useful improvement must survive a comparison with the published factored implementation and include selection, routing, workspace reuse and cleanup under the same cost model.

The prototype preserves two elementary compiler choices: dead-node removal and copying a computed linear output through one controlled operation. Neither is presented as a new algorithmic discovery. Earlier unpruned results remain archived locally; this repository freezes the specified reference version. There is no AIRR manuscript score or new theorem here.

## Provenance and connection

Lluis Eriksson's research workflow,24October2026, with OpenAI Codex assistance for reading, implementation and finite verification. No human peer review, external circuit reproduction or formal verification is claimed. The code is original; no third-party implementation or full paper text is redistributed. Source ideas and formulas are attributed above. The MIT license applies to this repository's original code, not to the cited paper.

This laboratory is indexed by the [PhysMath Knowledge Tree](https://github.com/lluiseriksson/physmath-knowledge-tree). Its role is a bounded experimental artifact. It is not a general computational campaign or a ready Research Capsule; it cannot promote a speculative graph claim to a theorem.
