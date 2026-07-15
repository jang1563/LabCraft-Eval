# Purify-01 Sources

## Evidence Boundary

`purification_lysate_his6_mbp_gfp_001` is a causal seeded benchmark fixture: a
clarified, chelator-free native lysate produced from the benign synthetic
His6-MBP-GFP expression construct. Its fixed 18.4 mg available target mass and
50 mM sodium phosphate, 300 mM NaCl, pH 8.0 buffer provenance are task
configuration. The fixed 4 mL bed is also benchmark configuration, chosen so
18.4 mg remains below the handbook's conservative 5 mg target per mL resin
capacity bound. No source is represented as documenting or measuring this exact
lysate.

The accepted workflow is deliberately product-specific: QIAGEN Ni-NTA
Superflow, 10-20 mM load/binding imidazole, exactly 20 mM wash imidazole,
exactly 250 mM elution imidazole, and a 0.5-1.0 mL/min starting lysate-loading
flow rate. Resin identity, bed volume, and input mass are fixed context; only
the four buffer/flow values are agent decisions.

The accepted-run recovery fraction (`0.85`), eluate volume (`2.5` column
volumes), purity (`95%`), and expected apparent band (`72 kDa`) are synthetic
deterministic simulator calibrations, not empirical performance claims or
universal Ni-NTA outcomes. The 72 kDa value is an expected apparent band for
the synthetic fixture, not an externally measured molecular mass. A
well-formed out-of-contract attempt consumes the seeded input and returns zero
recovery with no prepared eluate strictly as a simulator state transition; it
does not claim that the corresponding physical experiment must yield zero
protein.

## Tier Summary

- Gold: 0
- Silver: 1
- Bronze: 1
- Copper: 0

## Included Sources

### Silver

1. Bornhorst JA, Falke JJ. *Purification of proteins using polyhistidine affinity tags.* Methods in Enzymology. 2000. DOI: https://doi.org/10.1016/S0076-6879(00)26058-8
   - Used for: peer-reviewed background on immobilized-metal affinity capture and elution of polyhistidine-tagged proteins.
   - Not used for: the exact fixture mass, fixed bed volume, deterministic recovery, eluate volume, purity, or apparent band.

### Bronze

1. QIAGEN. *The QIAexpressionist, Fifth Edition.* June 2003. https://www.qiagen.com/en-us/resources/download/kithandbook/en-the-qiaexpressionist
   - Used for: native Ni-NTA Superflow workflow identity; 50 mM sodium phosphate, 300 mM NaCl, pH 8.0 native buffer; 10-20 mM imidazole during load/binding; the standard 20 mM wash recipe; the standard 250 mM elution recipe; 5-10 mg/mL resin capacity; and a 0.5-1.0 mL/min starting lysate-loading flow rate.
   - Boundary: broader optimization ranges in the handbook are not substituted for the exact standard wash and elution recipes selected by this benchmark.

## Rejected Sources

1. Cytiva HisTrap HP conditions as values for this workflow.
   - Rejected because HisTrap HP uses Ni Sepharose High Performance, a different product and column format. Its product-specific profile must not be mixed into the fixed QIAGEN Ni-NTA Superflow contract.

2. Thermo Scientific HisPur Ni-NTA conditions as values for this workflow.
   - Rejected because HisPur is a separate product workflow. Similar-looking load, wash, or elution concentrations do not establish the selected QIAGEN product contract.

3. The NEB pMAL product page as evidence for an exact 72 kDa band.
   - Rejected because it does not document or measure the synthetic His6-MBP-GFP benchmark fixture. The expected apparent band is labeled as task configuration.

4. Community protein-purification tutorials.
   - Rejected because unattributed community tutorials do not meet the Bronze-tier bar and cannot resolve product-specific conditions.

5. Internal LabCraft design notes as scientific evidence.
   - Rejected because simulator configuration is documented directly as configuration, not presented as an external protocol claim.
