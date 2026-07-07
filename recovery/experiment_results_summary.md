# Recovery Experiment Results

## Main Table

| Experiment | N | L1 | L2 | L3 | Sem Full | Sem Partial | Sem Unsup. | Sem Unc. | L2 Repaired | L2 Failed | Ret Full | Ret Partial | Ret Unver. | Ret Failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Exp1 | 20 | 20 | 0 | 0 | 20 | 0 | 0 | 0 | -- | -- | 0 | 0 | 0 | 0 |
| Exp2 | 20 | 0 | 10 | 10 | 0 | 6 | 14 | 0 | 6 | 4 | 6 | 3 | 1 | 4 |
| Exp3 | 20 | 10 | 0 | 10 | 0 | 0 | 11 | 9 | -- | -- | 5 | 2 | 4 | 9 |
| Exp4 | 20 | 10 | 10 | 0 | 3 | 3 | 10 | 4 | 7 | 3 | 8 | 0 | 0 | 6 |
| Exp5 | 20 | 0 | 0 | 20 | 0 | 0 | 20 | 0 | -- | -- | 5 | 4 | 0 | 11 |
| **Total** | **100** | **40** | **20** | **40** | **23** | **9** | **55** | **13** | **13** | **7** | **24** | **9** | **5** | **30** |

Notes:

- Semantic Full = `SUPPORTED`; Semantic Partial = `PARTIALLY_SUPPORTED`.
- Semantic Unc. = `UNCERTAIN`, mostly missing abstracts or temporary API/model failures.
- Retrieval Full = `retrieved`; Retrieval Partial = `partial`; Ret Unver. = `unverified`.
- Alternative retrieval is evaluated only for citations not already supported at Layer 3.

## Rates For Text

| Experiment | Semantic verified support | Semantic unsupported | Semantic uncertain | L2 repair rate | Verified retrieval | Candidate retrieval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exp1 | 20/20 (100%) | 0/20 (0%) | 0/20 (0%) | -- | -- | -- |
| Exp2 | 6/20 (30%) | 14/20 (70%) | 0/20 (0%) | 6/10 (60%) | 9/14 (64%) | 10/14 (71%) |
| Exp3 | 0/20 (0%) | 11/20 (55%) | 9/20 (45%) | -- | 7/20 (35%) | 11/20 (55%) |
| Exp4 | 6/20 (30%) | 10/20 (50%) | 4/20 (20%) | 7/10 (70%) | 8/14 (57%) | 8/14 (57%) |
| Exp5 | 0/20 (0%) | 20/20 (100%) | 0/20 (0%) | -- | 9/20 (45%) | 9/20 (45%) |
