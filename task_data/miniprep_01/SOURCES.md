# Miniprep-01 Sources

## Tier Summary

- Gold: 0
- Silver: 1
- Bronze: 2
- Copper: 0

## Included Sources

### Silver

1. Birnboim HC, Doly J. *A rapid alkaline extraction procedure for screening recombinant plasmid DNA.* Nucleic Acids Research. 1979. DOI: https://doi.org/10.1093/nar/7.6.1513
   - Used for: the foundational alkaline-lysis plasmid-extraction principle.
   - Not used for: QIAprep proprietary buffer labels or benchmark-specific numeric calibrations.

### Bronze

1. QIAGEN. *QIAprep Miniprep Handbook.* December 2020. https://www.qiagen.com/en-US/resources/download/KitHandbook/hb-1206-006-hb-qiaprep-miniprep-0320-ww
   - Used for: the high-copy-plasmid scenario (1-5 mL overnight *E. coli* culture in LB), P1/P2/N3 order, P2 lysis no longer than 5 min, QIAprep 2.0 silica-membrane spin-column purification, supported 50-100 uL elution with 50 uL as the standard recommendation, and column capacity up to 20 ug.
   - Causal distinction: long alkaline exposure can irreversibly denature plasmid DNA; vigorous mixing or vortexing, rather than elapsed lysis time alone, can shear genomic DNA into the eluate.

2. Thermo Fisher. *260/280 and 260/230 Ratios Reference.* https://assets.thermofisher.com/TFS-Assets/CAD/Product-Bulletins/TN52646-E-0215M-NucleicAcid.pdf
   - Used for: the general observation that A260/A280 of approximately 1.8 is commonly accepted for DNA, while approximately 2.0 is commonly accepted for RNA.
   - Not used for: a universal 1.8-2.0 pure-DNA interval or a rule that a high ratio alone proves RNA contamination; the note explicitly recommends considering spectra, pH, measurement conditions, and downstream functionality.

## Benchmark Calibrations

- The lysis-duration action is an integer, so 1 min is the benchmark's positive lower bound. The literature-backed protocol threshold is the 5 min maximum.
- A260/A280 is deterministically calibrated to 1.8 for a successful run. This is a simulator configuration anchored to the Thermo Fisher nominal DNA value, not a universal acceptance interval or a direct plasmid-integrity assay.
- Total yield is deterministically calibrated to 10 ug at the 5 mL reference culture volume. This conservative task value is below the QIAprep 2.0 column's stated capacity of up to 20 ug and is not presented as a universal fixed yield.
- Successful preparations support the handbook's 50-100 uL elution range. The decision rubric awards its optimum to the standard recommended 50 uL condition; 100 uL remains a valid, source-backed preparation with lower concentration at the same calibrated yield.
- The finite accepted method aliases all denote the same QIAprep-compatible silica-membrane spin-column workflow. Generic "QIAGEN column" and anion-exchange terms are excluded because QIAGEN-tip anion exchange is a distinct product and procedure.

## Rejected Sources

1. Community miniprep tutorials.
   - Rejected because unattributed community tutorials do not meet the Bronze-tier bar.

2. Internal LabCraft design notes.
   - Rejected because project context is not a public citable source.
