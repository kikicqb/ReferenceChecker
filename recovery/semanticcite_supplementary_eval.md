# SemanticCite Supplementary Evaluation

This is a component-level evaluation of the abstract-based semantic verifier.
It uses SemanticCite claim-source labels as external labels, but evaluates only
the abstract contained in the dataset metadata, not the full reference PDF.

Sample: 20 items (5 per label when available)
Exact four-class accuracy: 75.0%
Binary supported-vs-unsupported accuracy: 100.0%

## Label Counts

Gold: {'UNCERTAIN': 5, 'PARTIALLY_SUPPORTED': 5, 'UNSUPPORTED': 5, 'SUPPORTED': 5}
Predicted: {'UNSUPPORTED': 8, 'PARTIALLY_SUPPORTED': 5, 'SUPPORTED': 5, 'UNCERTAIN': 2}

## Confusion Matrix

| Gold \ Pred | SUPPORTED | PARTIAL | UNSUPPORTED | UNCERTAIN |
|---|---:|---:|---:|---:|
| SUPPORTED | 4 | 1 | 0 | 0 |
| PARTIALLY_SUPPORTED | 1 | 4 | 0 | 0 |
| UNSUPPORTED | 0 | 0 | 5 | 0 |
| UNCERTAIN | 0 | 0 | 3 | 2 |

## Mismatches

- `UNCERTAIN` -> `UNSUPPORTED`: A gridded global data set of soil, intact regolith, and sedimentary deposit thicknesses for regional and global land surface modeling
  Claim: General trends in the residual ùúÄ‡Øå of the slope-based amplification model are displayed using the 2016 sedimentary basin thickness data set, but no coherent trend of the sort seen in Figure 15 is demonstrated.
  Reason: The abstract describes the creation of a global thickness data set for soil and regolith and makes no mention of a 'slope-based amplification model' or residual analysis related to the specific figure mentioned in the claim.
- `UNCERTAIN` -> `UNSUPPORTED`: Coherent elastic neutrino-nucleus scattering: EFT analysis and nuclear responses
  Claim: The hadronic structure parameters for scalar interactions are fpu = 0.0208, fnu = 0.0189, fpd = 0.0411, and fnd = 0.0451, while for tensor interactions, Œ¥pu = Œ¥nd = 0.54 and Œ¥pd = Œ¥nu = –0.23.
  Reason: The abstract discusses the general formalism and calculation of nuclear form factors for CEvNS experiments but does not provide or list the specific numerical hadronic structure parameter values mentioned in the claim.
- `SUPPORTED` -> `PARTIALLY_SUPPORTED`: Exceptionally low shear modulus in a prototypical imidazole-based metal-organic framework.
  Claim: It has been experimentally determined that ZIF-8 [Zn(C4H5N2)2] possesses a shear modulus slightly below 1 GPa, which is one order of magnitude lower than its bulk modulus of 8 GPa; this significant difference is now understood to be a common feature in metal-organic frameworks (MOFs).
  Reason: The abstract confirms the experimental determination of ZIF-8's shear modulus (< 1 GPa) and its relationship to the bulk modulus, but it does not provide evidence that this behavior is a 'common feature in metal-organic frameworks (MOFs)'.
- `PARTIALLY_SUPPORTED` -> `SUPPORTED`: Extrusion 3D Printing of Paracetamol Tablets from a Single Formulation with Tunable Release Profiles Through Control of Tablet Geometry
  Claim: Immediate release was achieved with the mesh tablets, whereas ring and solid tablets demonstrated sustained release.
  Reason: The abstract explicitly states that the tablets demonstrated well-defined release profiles ranging from immediate to sustained release based on their geometries (mesh, ring, and solid), aligning directly with the claim.
- `UNCERTAIN` -> `UNSUPPORTED`: Cornering the Two Higgs Doublet Model Type II
  Claim: In figure 8, more b → s`+`− observables are considered (as listed in table 7), and some of these observables also exhibit tension with experimental results within the Standard Model.
  Reason: The abstract does not mention Figure 8, Table 7, or the specific b -> s+ - observables mentioned in the claim, nor does it discuss tensions within the Standard Model regarding these specific observables.
