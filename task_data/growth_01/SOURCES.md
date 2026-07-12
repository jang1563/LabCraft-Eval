# Growth-01 Sources

## Tier Breakdown

- Gold: 2
- Bronze: 0
- Silver: 8
- Copper: 0

## Included Sources

### Gold

1. Monod J. *The Growth of Bacterial Cultures*. Annual Review of Microbiology (1949). DOI: 10.1146/annurev.mi.03.100149.002103
   - Used as the canonical conceptual reference for nutrient-dependent bacterial growth.

2. Zwietering MH, Jongenburger I, Rombouts FM, van 't Riet K. *Modeling of the bacterial growth curve*. Applied and Environmental Microbiology (1990). DOI: 10.1128/aem.56.6.1875-1881.1990
   - Used as the canonical bacterial growth-curve modeling reference for windowed fit design.

### Silver

1. Growth and Maintenance of *Escherichia coli* Laboratory Strains
   - URL: https://pubmed.ncbi.nlm.nih.gov/33484484/
   - Used for the representative ~20 minute doubling time in rich LB medium.

2. Cell size and growth rate are major determinants of *E. coli* mRNA abundance
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC103779/
   - Used for the representative ~57 minute doubling time in glucose minimal medium.

3. Chloramphenicol affects *Escherichia coli* growth rates and bacterial membrane composition
   - URL: https://pubmed.ncbi.nlm.nih.gov/6992672/
   - Used for the roughly 50% growth-rate reduction at 1.8 uM chloramphenicol.

4. RqcH supports survival in the absence of non-stop ribosome rescue factors
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC8006063/
   - Used to provide an OD600 0.05 reference point within the defensible starting range and to anchor the defensible cadence range at 15 minutes.

5. The *E. coli* molecular phenotype under different growth conditions
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC5394689/
   - Used for the cited 0.05-0.75 fraction-of-maximum OD600 fitting window.

6. The *E. coli* molecular phenotype under different growth conditions
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC5394689/
   - Reused for the growth-fit troubleshooting rationale when a trajectory does not yield enough usable points.

7. Invariance of initiation mass and predictability of cell size in *Escherichia coli*
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC5474944/
   - Used to support the early-exponential OD600 range; the cited experiment maintained cultures between OD600 0.05 and 0.20, while this benchmark conservatively caps the starting range at 0.10.

8. Single-cell mass distributions reveal simple rules for achieving steady-state growth
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10653891/
   - Used to support the inclusive OD600 0.01 lower bound; the study identifies approximately 0.01 as the lower accuracy boundary and describes longitudinal measurements beginning at that value.

The approximately 20-minute LB doubling-time source above also defines the
maximum accepted measurement interval. This makes cadence credit reflect the
task instruction to choose a defensible cadence instead of requiring one hidden
exact value.

## Rejected Sources

- General educational blog posts describing bacterial growth curves
  - Rejected because they do not meet the minimum Silver requirement for growth-rate thresholds or fitting-window decisions.

- Textbook-style summaries without a canonical URL or DOI
  - Rejected because the handoff requires each parameter and ground-truth threshold to point to a canonical public source record.
