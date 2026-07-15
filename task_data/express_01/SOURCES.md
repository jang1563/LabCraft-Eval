# Express-01 Sources

## Evidence Boundary

`expression_construct_his6_mbp_gfp_001` is an explicit benign benchmark fixture:
a synthetic pET-style T7lac construct encoding His6-MBP-GFP at approximately
72 kDa. No source is represented as documenting this exact plasmid or a universal
yield for it. The supported parameter windows are the declared task contract;
external sources motivate their scientific plausibility but do not establish a
universal optimum. The deterministic 40 mg/L pre-solubility value and the profile
fractions `0.08`, `0.12`, `0.18`, and `0.25` are synthetic simulator calibrations,
not empirical performance claims. An out-of-contract attempt is assigned zero
observed yield and no lysate strictly as a simulator state transition; it does not
claim that a corresponding physical experiment would produce zero protein.

## Tier Summary

- Gold: 0
- Silver: 1
- Bronze: 3
- Copper: 0

## Included Sources

### Silver

1. Rosano GL, Ceccarelli EA. *Recombinant protein expression in Escherichia coli: advances and challenges.* Frontiers in Microbiology. 2014. DOI: https://doi.org/10.3389/fmicb.2014.00172
   - Used for: DE3 expression-host context, specialized host variants, and the evidence-supported 15-25 °C low-temperature range for reducing aggregation.
   - Not used for: a 0.5-1.0 mM IPTG threshold, an OD600 threshold, exact induction durations, or a 40 mg/L MBP-GFP yield.

### Bronze

1. Thermo Fisher Scientific. *Champion pET Gateway Expression Kits with Lumio Technology User Manual.* 2010. https://documents.thermofisher.com/TFS-Assets/LSG/manuals/petlumiodest_man.pdf
   - Used for: T7lac/pET mechanism, DE3-host requirement, 0.5-1.0 mM IPTG, OD600 0.5-0.8 pilot induction, 37 °C time-course sampling over 4-6 h, 500 mL scale-up, His-tag/Ni-NTA context, and a representative native lysis buffer at pH 7.8.

2. QIAGEN. *The QIAexpressionist, Fifth Edition.* June 2003. https://www.qiagen.com/en-us/resources/download/kithandbook/en-the-qiaexpressionist
   - Used for: native Ni-NTA lysis buffer at pH 8.0, the statement that pH 7.5 is essential for efficient 6xHis binding, and the broad 10-50 mg/L high-expression scale used only to sanity-check the simulator calibration.

3. New England Biolabs. *NEBExpress MBP Fusion and Purification System Quick Start Protocol.* https://www.neb.com/en-us/protocols/nebexpress-mbp-fusion-and-purification-system-quick-start-protocol-neb-e8201
   - Used for: the shape of MBP-fusion temperature-duration alternatives (short warm induction, intermediate room-temperature induction, and extended cold induction).
   - Boundary: this is a Ptac/MBP workflow, not evidence that the seeded benchmark fixture is the NEB plasmid or that Ptac and T7lac are interchangeable.

## Rejected Sources

1. The legacy NEB pMAL product page as evidence for a T7/pET construct.
   - Rejected because pMAL/MBP expression uses a different promoter and purification workflow; it cannot establish the seeded T7lac fixture.

2. A universal 40 mg/L His6-MBP-GFP yield attributed to Rosano 2014.
   - Rejected because the review does not report that construct-specific value. The simulator calibration is labeled directly instead.

3. Community protein-expression tutorials.
   - Rejected because unattributed tutorials do not meet the Bronze-tier bar.

4. Internal LabCraft design notes as scientific evidence.
   - Rejected because task configuration is documented as configuration, not presented as an external protocol claim.
