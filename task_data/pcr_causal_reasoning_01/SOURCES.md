# PCR Causal Reasoning-01 Sources

## Scope

This development task reuses the cited PCR-01 simulator contract. It adds no
new physical-performance claim: the paired failure records, causal labels, and
counterfactual outcomes are deterministic benchmark states built from the
existing `run_pcr` and `run_gel` operations.

## Tier Summary

- Gold: 0
- Silver: 1
- Bronze: 5
- Copper: 0

## Included Sources

### Silver

1. Cline J, Braman JC, Hogrefe HH. *PCR fidelity of pfu DNA polymerase and other
   thermostable DNA polymerases.* Nucleic Acids Research. 1996.
   DOI: https://doi.org/10.1093/nar/24.18.3546
   - Reused for: the high-fidelity-versus-Taq distinction in `case_a`.

### Bronze

1. NEB. *Q5 High-Fidelity DNA Polymerase.*
   https://www.neb.com/en-us/products/m0491-q5-high-fidelity-dna-polymerase
   - Reused for: Q5 as an accepted difficult-PCR correction.

2. Thermo Fisher. *Phusion High-Fidelity DNA Polymerase.*
   https://www.thermofisher.com/order/catalog/product/F530S
   - Reused for: Phusion as an alternative-valid correction.

3. NEB. *PCR Using Q5 High-Fidelity DNA Polymerase.*
   https://www.neb.com/en-us/protocols/2013/12/13/pcr-using-q5-high-fidelity-dna-polymerase-m0491
   - Reused for: the accepted 2 kb extension-time range held fixed or varied in
     the one-variable intervention and counterfactual checks.

4. Thermo Fisher. *Phusion PCR Protocol.*
   https://www.thermofisher.com/us/en/home/references/protocols/nucleic-acid-amplification-and-expression-profiling/pcr-protocol/phusion-pcr-protocol.html
   - Reused for: bounded cycle-count and extension-time settings.

5. NEB. *Protocol for Q5 High-Fidelity 2X Master Mix.*
   https://www.neb.com/en-us/protocols/2012/12/07/protocol-for-q5-high-fidelity-2x-master-mix-m0492
   - Reused for: the accepted genomic-PCR cycle-count range in `case_b`.

## Rejected Sources

1. New web searches or uncited troubleshooting pages
   - Rejected because this local slice intentionally introduces no new
     scientific threshold beyond the already reviewed PCR-01 source stack.

2. Simulator `notes` emitted by the prior failed reaction
   - Rejected from the agent-facing record because those notes state the causal
     failure directly and would collapse the reasoning task into copying.

3. Internal project design notes
   - Rejected as public scientific support because they document benchmark
     intent rather than external PCR evidence.
