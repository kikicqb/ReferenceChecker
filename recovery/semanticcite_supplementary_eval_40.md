# SemanticCite Supplementary Evaluation

This is a component-level evaluation of the abstract-based semantic verifier.
It uses SemanticCite claim-source labels as external labels, but evaluates only
the abstract contained in the dataset metadata, not the full reference PDF.

Sample: 40 items (10 per label when available)
Exact four-class accuracy: 70.0%
Binary supported-vs-unsupported accuracy: 92.5%

## Label Counts

Gold: {'UNSUPPORTED': 10, 'UNCERTAIN': 10, 'SUPPORTED': 10, 'PARTIALLY_SUPPORTED': 10}
Predicted: {'UNSUPPORTED': 18, 'UNCERTAIN': 5, 'SUPPORTED': 9, 'PARTIALLY_SUPPORTED': 8}

## Confusion Matrix

| Gold \ Pred | SUPPORTED | PARTIAL | UNSUPPORTED | UNCERTAIN |
|---|---:|---:|---:|---:|
| SUPPORTED | 7 | 2 | 1 | 0 |
| PARTIALLY_SUPPORTED | 2 | 6 | 2 | 0 |
| UNSUPPORTED | 0 | 0 | 10 | 0 |
| UNCERTAIN | 0 | 0 | 5 | 5 |

## Mismatches

- `SUPPORTED` -> `PARTIALLY_SUPPORTED`: Exceptionally low shear modulus in a prototypical imidazole-based metal-organic framework.
  Claim: It has been experimentally determined that ZIF-8 [Zn(C4H5N2)2] possesses a shear modulus slightly below 1 GPa, which is one order of magnitude lower than its bulk modulus of 8 GPa; this significant difference is now understood to be a common feature in metal-organic frameworks (MOFs).
  Reason: The abstract confirms the shear modulus and bulk modulus values for ZIF-8, but it does not provide evidence that this significant difference is a 'common feature in metal-organic frameworks (MOFs)' as stated in the claim.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Comparison of Joblib and Pymp for Parallel Fingerprint Recognition
  Claim: To maximize simulator performance, vectorization is leveraged where available and simulations are optionally parallelized using joblib.
  Reason: The claim refers to a general-purpose simulator utilizing vectorization and joblib, while the paper is a comparative study specifically focused on parallelizing fingerprint recognition algorithms.
- `UNCERTAIN` -> `UNSUPPORTED`: Coherent elastic neutrino-nucleus scattering: EFT analysis and nuclear responses
  Claim: The hadronic structure parameters for scalar interactions are fpu = 0.0208, fnu = 0.0189, fpd = 0.0411, and fnd = 0.0451, while for tensor interactions, Œ¥pu = Œ¥nd = 0.54 and Œ¥pd = Œ¥nu = –0.23.
  Reason: The abstract discusses the general formalism for nuclear form factors and effective field theory operators for CEνNS, but it does not provide the specific numerical values for hadronic structure parameters listed in the claim.
- `SUPPORTED` -> `UNSUPPORTED`: Failed rifting and fast drifting: Midcontinent Rift development, Laurentia’s rapid motion and the driver of Grenvillian orogenesis
  Claim: This pole can be compared to a synthesized apparent polar wander path (APWP) developed using an Euler pole inversion of chronostratigraphically-controlled volcanic poles.
  Reason: While the abstract discusses the development of an APWP for Laurentia using chronostratigraphically-controlled volcanic poles, it does not mention or utilize an 'Euler pole inversion' to synthesize that path.
- `SUPPORTED` -> `PARTIALLY_SUPPORTED`: Reaction of Perfluorooctanoic Acid with Criegee Intermediates and Implications for the Atmospheric Fate of Perfluorocarboxylic Acids.
  Claim: The reaction of the resultant hydroperoxyl-fluoroester products with HO radicals probably reforms the perfluoro-carboxylic acids on a timescale of 1-2 days.
  Reason: The abstract confirms that gas-phase reactions with OH regenerate the perfluorocarboxylic acid but does not provide or verify the specific '1-2 days' timescale mentioned in the claim.
- `PARTIALLY_SUPPORTED` -> `SUPPORTED`: Synthetic glycolate metabolism pathways stimulate crop growth and productivity in the field
  Claim: A variant of this bypass can increase the productivity of tobacco plants in the field by more than 40%.
  Reason: The abstract explicitly states that transgenic tobacco plants with engineered glycolate metabolic pathways showed as much as 40% greater productivity than wild-type plants in field trials.
- `UNCERTAIN` -> `UNSUPPORTED`: Measurement of the Coherent Elastic Neutrino-Nucleus Scattering Cross Section on CsI by COHERENT.
  Claim: Quenched recoils are characterized by a light yield given as LY = 13.35 PE/keVee, where PE = LY × Eer, and the electron-equivalent energy is defined in terms of Enr as Eer = x1E0nr + x2E0^2nr + x3E0^3nr + x4E0^4nr, with coefficients x1 = 0.0554628, x2 = 4.30681, x3 = –111.707, and x4 = 840.384.
  Reason: The abstract discusses the measurement of CEvNS cross-sections and improvements in quenching models in a general sense, but it does not provide the specific numerical coefficients or the mathematical formula for the light yield quenching model mentioned in the claim.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: An international multi-center investigation on the accuracy of radionuclide calibrators in nuclear medicine theragnostics
  Claim: Activity measurements traceable to primary standards are not commonly used in all countries, despite the observation of larger variabilities in international comparison exercises.
  Reason: The provided abstract focuses on assessing measurement accuracy in specific hospitals in three countries and does not contain data or statements regarding the global prevalence of the use of primary standards.
- `PARTIALLY_SUPPORTED` -> `SUPPORTED`: Extrusion 3D Printing of Paracetamol Tablets from a Single Formulation with Tunable Release Profiles Through Control of Tablet Geometry
  Claim: Immediate release was achieved with the mesh tablets, whereas ring and solid tablets demonstrated sustained release.
  Reason: The abstract explicitly states that the different geometries (mesh, ring, and solid) resulted in release profiles ranging from immediate to sustained, which directly supports the claim that mesh tablets achieved immediate release while ring and solid ones demonstrated sustained release.
- `UNCERTAIN` -> `UNSUPPORTED`: A gridded global data set of soil, intact regolith, and sedimentary deposit thicknesses for regional and global land surface modeling
  Claim: General trends in the residual ùúÄ‡Øå of the slope-based amplification model are displayed using the 2016 sedimentary basin thickness data set, but no coherent trend of the sort seen in Figure 15 is demonstrated.
  Reason: The abstract describes the development of a global thickness data set and does not mention slope-based amplification models or residual analysis, indicating the paper is not the source of the claim.
- `UNCERTAIN` -> `UNSUPPORTED`: Cornering the Two Higgs Doublet Model Type II
  Claim: In figure 8, more b → s`+`− observables are considered (as listed in table 7), and some of these observables also exhibit tension with experimental results within the Standard Model.
  Reason: The abstract does not mention Figure 8, Table 7, or the specific b -> s+ - observables mentioned in the claim, focusing instead on global parameter space constraints for the 2HDM-II model.
- `UNCERTAIN` -> `UNSUPPORTED`: Observation of coherent elastic neutrino-nucleus scattering
  Claim: The Klein Nystrand parametrization is used for the form factor, in agreement with the official COHERENT analysis.
  Reason: The abstract discusses the first observation of CEνNS but does not mention the Klein-Nystrand parametrization or specific details regarding form factor modeling.
