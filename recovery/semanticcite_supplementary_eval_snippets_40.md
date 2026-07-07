# SemanticCite Supplementary Evaluation

This is a component-level evaluation of the semantic verifier using SemanticCite reference snippets.
It uses SemanticCite claim-source labels as external labels, but evaluates only
the selected evidence field, not the full reference PDF.

Sample: 40 items (10 per label when available)
Exact four-class accuracy: 52.5%
Binary supported-vs-unsupported accuracy: 80.0%

## Label Counts

Gold: {'UNSUPPORTED': 10, 'UNCERTAIN': 10, 'SUPPORTED': 10, 'PARTIALLY_SUPPORTED': 10}
Predicted: {'UNSUPPORTED': 27, 'PARTIALLY_SUPPORTED': 5, 'SUPPORTED': 7, 'UNCERTAIN': 1}

## Confusion Matrix

| Gold \ Pred | SUPPORTED | PARTIAL | UNSUPPORTED | UNCERTAIN |
|---|---:|---:|---:|---:|
| SUPPORTED | 7 | 2 | 1 | 0 |
| PARTIALLY_SUPPORTED | 0 | 3 | 7 | 0 |
| UNSUPPORTED | 0 | 0 | 10 | 0 |
| UNCERTAIN | 0 | 0 | 9 | 1 |

## Mismatches

- `UNCERTAIN` -> `UNSUPPORTED`: Circuits of the mind
  Claim: Earlier experiments with rodents and monkeys found neurons that responded only to a specific combination of stimulus features, but not to any of these features in isolation, supporting Valiant's version.
  Reason: The provided snippets discuss hippocampal neurons in humans, eye movement learning, and V1/vM1 neural responses in rats, none of which describe neurons responding to specific stimulus combinations as described in the claim.
- `SUPPORTED` -> `UNSUPPORTED`: Thermal conductivity spectroscopy technique to measure phonon mean free paths.
  Claim: The onset of the size effect is observed when the mean free path of heat-carrying phonons becomes comparable to the heat transport distance.
  Reason: While the snippets discuss phonon mean free paths and transport regimes, they do not explicitly define the 'onset of the size effect' as occurring when the mean free path is comparable to the heat transport distance.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Dark Matter Search in Missing Energy Events with NA64.
  Claim: The ability of SND@LHC to probe currently unexplored parameter space depends on the coupling of the mediator to electrons and photons, and if such a coupling exists, the model may already be constrained by experiments that search for missing energy or momentum, such as NA64, BaBar, and Belle.
  Reason: The provided snippets discuss NA64 and dark photon theory, but they contain no information regarding SND@LHC or how its ability to probe parameter space is constrained by other experiments.
- `SUPPORTED` -> `PARTIALLY_SUPPORTED`: Exceptionally low shear modulus in a prototypical imidazole-based metal-organic framework.
  Claim: It has been experimentally determined that ZIF-8 [Zn(C4H5N2)2] possesses a shear modulus slightly below 1 GPa, which is one order of magnitude lower than its bulk modulus of 8 GPa; this significant difference is now understood to be a common feature in metal-organic frameworks (MOFs).
  Reason: The snippets confirm that ZIF-8 has a shear modulus (Gmax and Gmin) around 1 GPa, but they do not provide the experimental bulk modulus of 8 GPa nor confirm that this discrepancy is a common feature in MOFs.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Comparison of Joblib and Pymp for Parallel Fingerprint Recognition
  Claim: To maximize simulator performance, vectorization is leveraged where available and simulations are optionally parallelized using joblib.
  Reason: The provided snippets discuss the parallelization of fingerprint recognition algorithms using Joblib and Pymp, but contain no information regarding the use of vectorization to maximize simulator performance.
- `UNCERTAIN` -> `UNSUPPORTED`: Coherent elastic neutrino-nucleus scattering: EFT analysis and nuclear responses
  Claim: The hadronic structure parameters for scalar interactions are fpu = 0.0208, fnu = 0.0189, fpd = 0.0411, and fnd = 0.0451, while for tensor interactions, Œ¥pu = Œ¥nd = 0.54 and Œ¥pd = Œ¥nu = –0.23.
  Reason: The provided snippets discuss nuclear shell model configurations and scalar/tensor operators in the context of CEvNS, but they contain no numerical values or tables defining the hadronic structure parameters fpu, fnu, fpd, fnd, or the tensor couplings.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Nanoengineered on-demand drug delivery system improves efficacy of pharmacotherapy for epilepsy
  Claim: An electro-responsive dopamine-pyrrole hybrid system has been developed that improves the delivery efficiency of anti-epileptic drugs by enhancing blood-brain barrier crossing through the combination of receptor-mediated transcytosis and photothermal conversion of near-infrared light. This system demonstrates enhanced conductivity and sensitivity in various seizure models, including acute seizure, continuous seizure, and spontaneous seizure, making it effective for epilepsy pharmacotherapy.
  Reason: The provided evidence snippets describe a gold nanoparticle (AuNP) system utilizing picosecond laser stimulation for BBB permeability, which contradicts the claim's description of an electro-responsive dopamine-pyrrole hybrid system using near-infrared light.
- `UNCERTAIN` -> `UNSUPPORTED`: Clinical outcomes in patients with baseline renal dysfunction in the NETTER-1 study: 177Lu-Dotatate vs. high dose octreotide in progressive midgut neuroendocrine tumors.
  Claim: No evidence of clinically significant worsening of renal dysfunction was demonstrated among 11 patients with baseline mild renal dysfunction (GFR 50-59) and 13 patients with moderate renal dysfunction (GFR < 50) treated on the 177Lu-DOTATATE arm of the NETTER-1 study.
  Reason: The provided snippets discuss the NETTER-1 trial design, quality of life, and symptom improvement, but contain no information or data regarding renal function, GFR levels, or the safety profile of patients with baseline renal dysfunction.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Depth-dependent redox behavior of LiNi0.6Mn0.2Co0.2O2
  Claim: A valence state change distinctly contributes to the spectroscopic fingerprint in soft X-ray absorption spectroscopy (XAS) data over the Ni L3-edge. Without lateral spatial resolution, chemical reactions at different depths can be explored using conventional XAS signals in two different detection modalities: total electron yield (TEY) with approximately 5 nm probing depth and fluorescence yield (FY) with approximately 100 nm probing depth.
  Reason: The provided snippets discuss iron and carbon K-edge spectromicroscopy and do not contain any information regarding Ni L3-edge spectroscopy, valence states, or the use of TEY and FY detection modalities.
- `UNCERTAIN` -> `UNSUPPORTED`: Measurement of the Coherent Elastic Neutrino-Nucleus Scattering Cross Section on CsI by COHERENT.
  Claim: Quenched recoils are characterized by a light yield given as LY = 13.35 PE/keVee, where PE = LY × Eer, and the electron-equivalent energy is defined in terms of Enr as Eer = x1E0nr + x2E0^2nr + x3E0^3nr + x4E0^4nr, with coefficients x1 = 0.0554628, x2 = 4.30681, x3 = –111.707, and x4 = 840.384.
  Reason: The provided evidence snippets contain no numerical data regarding light yield (LY), the specific coefficients for the electron-equivalent energy equation, or the mathematical relationship between nuclear recoil energy and electron-equivalent energy described in the claim.
- `UNCERTAIN` -> `UNSUPPORTED`: Organic aerosol formation in urban and industrial plumes near Houston and Dallas, Texas
  Claim: The uncertainty quantification of chemical species was conducted as described in Sect. S1 in the Supplement.
  Reason: The provided snippets discuss a general definition of uncertainty quantification and the results of the TexAQS-2006 study, but they contain no reference to the specific methodologies used for chemical species or any mention of a Supplement section S1.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: An international multi-center investigation on the accuracy of radionuclide calibrators in nuclear medicine theragnostics
  Claim: Activity measurements traceable to primary standards are not commonly used in all countries, despite the observation of larger variabilities in international comparison exercises.
  Reason: The provided snippets discuss measurement accuracy, variability, and the impact of sample geometry, but they contain no information regarding the adoption rates or traceability of activity measurements to primary standards across different countries.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Highly Active, Nonprecious Electrocatalyst Comprising Borophene Subunits for the Hydrogen Evolution Reaction.
  Claim: The current densities widely used in alkaline electrolyzers range from 200 to 500 mA cm-2, and can reach 1000 mA cm-2 in some cases.
  Reason: The provided snippets discuss a specific electrocatalyst (α-MoB2) and quantum information density scaling, neither of which provides information or data regarding the standard operating current density ranges for alkaline electrolyzers.
- `PARTIALLY_SUPPORTED` -> `UNSUPPORTED`: Extrusion 3D Printing of Paracetamol Tablets from a Single Formulation with Tunable Release Profiles Through Control of Tablet Geometry
  Claim: Immediate release was achieved with the mesh tablets, whereas ring and solid tablets demonstrated sustained release.
  Reason: The provided snippets discuss drug release profiles generally, but they do not contain specific data or statements confirming that mesh tablets achieved immediate release while ring and solid tablets achieved sustained release.
- `UNCERTAIN` -> `UNSUPPORTED`: Temperature and Loading-Dependent Diffusion of Light Hydrocarbons in ZIF-8 as Predicted Through Fully Flexible Molecular Simulations.
  Claim: A weakening of C2H4-framework interactions with increasing amounts of adsorbed C2H4 has been observed.
  Reason: The provided snippets discuss CO2 detection in lattice structures, adsorption models for other systems, and general stability criteria, but contain no information regarding C2H4-framework interactions or the effect of C2H4 loading on these interactions.
- `UNCERTAIN` -> `UNSUPPORTED`: A gridded global data set of soil, intact regolith, and sedimentary deposit thicknesses for regional and global land surface modeling
  Claim: General trends in the residual ùúÄ‡Øå of the slope-based amplification model are displayed using the 2016 sedimentary basin thickness data set, but no coherent trend of the sort seen in Figure 15 is demonstrated.
  Reason: The provided snippets discuss soil thickness and Vs,30 correlations in Europe, but they contain no mention of residual analysis for a slope-based amplification model, sedimentary basin thickness data sets, or any comparison to a 'Figure 15'.
- `SUPPORTED` -> `PARTIALLY_SUPPORTED`: Strategies and limitations in app usage and human mobility
  Claim: It has been studied whether human cognition imposes constraints in the digital space similar to those that exist in the physical space, such as maintaining a stable number of friends and favorite places over time.
  Reason: The snippets explicitly raise the question of whether digital behavior exhibits constraints similar to the physical world, but they do not provide the specific examples of maintaining a stable number of friends or favorite places.
- `UNCERTAIN` -> `UNSUPPORTED`: Cornering the Two Higgs Doublet Model Type II
  Claim: In figure 8, more b → s`+`− observables are considered (as listed in table 7), and some of these observables also exhibit tension with experimental results within the Standard Model.
  Reason: The provided snippets do not mention figure 8, table 7, or the specific b -> s transitions required to verify the claim; they discuss R(D) and R(D*) instead.
- `UNCERTAIN` -> `UNSUPPORTED`: Observation of coherent elastic neutrino-nucleus scattering
  Claim: The Klein Nystrand parametrization is used for the form factor, in agreement with the official COHERENT analysis.
  Reason: The provided snippets discuss systematic uncertainties and form factors in the context of pion-exchange calculations, but they contain no mention of the Klein-Nystrand parametrization or its use in the COHERENT analysis.
