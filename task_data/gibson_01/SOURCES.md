# Gibson-01 Sources

## Tier Summary

- Gold: 0
- Silver: 1
- Bronze: 4
- Copper: 0

## Included Sources

### Silver

1. Gibson DG, Young L, Chuang RY, Venter JC, Hutchison CA, Smith HO. *Enzymatic assembly of DNA molecules up to several hundred kilobases.* Nature Methods. 2009. DOI: https://doi.org/10.1038/nmeth.1318
   - Used for: the original one-step isothermal system at 50 C and its exact ISO-buffer formulation with T5 exonuclease, Phusion polymerase, and Taq DNA ligase.
   - Scope note: the supplementary experiments include 40 bp overlaps and high correct-clone rates in other assembly settings. They are not used here to claim a universal 20 bp minimum or a published 80% correctness rate for this two-fragment task.

### Bronze

1. New England Biolabs. *Gibson Assembly Protocol (E5510).* https://www.neb.com/en/protocols/gibson-assembly-protocol-e5510?pdf=true
   - Used for: the Gibson Assembly Master Mix product name, 50 C incubation, 15 minutes for 2-3 fragments, and the documented option to extend incubation to 60 minutes.

2. New England Biolabs. *NEBuilder HiFi DNA Assembly Reaction Protocol.* https://www.neb.com/en-us/protocols/nebuilder-hifi-dna-assembly-reaction-protocol
   - Used for: the distinct NEBuilder HiFi DNA Assembly Master Mix product name and its 50 C, 15-minute workflow for 2-3 fragments.

3. New England Biolabs. *NEBuilder HiFi DNA Assembly Cloning Kit Manual (E2621/E5520).* https://www.neb.com/en/-/media/nebus/files/manuals/manuale2621_e5520.pdf
   - Used for: the 15-20 bp overlap guidance for 2-3-fragment NEBuilder assemblies and to establish that the task's fixed, observed 20 bp overlap is within a supported range.

4. New England Biolabs. *NEB 5-alpha Competent E. coli (High Efficiency) (C2987).* https://www.neb.com/en-us/products/c2987-neb-5-alpha-competent-e-coli-high-efficiency
   - Used for: 100 ug/mL ampicillin selection.

## Source-Boundary Notes

- Gibson Assembly E5510 and NEBuilder HiFi E2621/E5520 are documented as separate vendor product/protocol families; their titles and URLs are not conflated.
- The benchmark's two supplied fragments, 20 bp overlap, 1,200 bp insert, 15-60 minute validity window, and 0.80 simulator efficiency are task-contract choices where explicitly labeled, not universal biological thresholds.
- Fragment count and the already-observed overlap remain report-fidelity fields but are not independent decision-quality rewards.

## Rejected Sources

1. The former citation titled “NEBuilder HiFi DNA Assembly Master Mix Protocol (E2621 / E5510)” at the legacy Gibson E5510 URL.
   - Rejected because it conflated two distinct NEB products and attached the wrong title/product code to the URL.

2. Community Gibson assembly tutorials.
   - Rejected because unattributed community tutorials do not meet the Bronze-tier bar.

3. Internal LabCraft design notes as scientific evidence.
   - Rejected because benchmark configuration is not a public scientific source; task-defined values are labeled as configuration instead.
