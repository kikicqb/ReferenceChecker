# Reference Checker

Reference Checker is a research prototype for extracting references from academic PDFs and checking whether cited papers are real, flawed, or likely fabricated.

The project combines:

- GROBID reference extraction from PDFs
- rule-based verification against CrossRef, Semantic Scholar, OpenAlex, and DBLP
- an optional Gemini-powered agent verifier
- an optional recovery pipeline for checking whether citations semantically support nearby claims

## Project Structure

```text
.
├── main.py                  # Basic PDF extraction + verification entry point
├── extraction.py            # GROBID reference extraction
├── verification.py          # Rule-based multi-database citation verifier
├── agent.py                 # LLM-assisted citation verification
├── run_test.py              # Benchmark runner for JSON datasets
├── data_pool/               # Source pools for benchmark construction
├── grobid_datasets/         # Extracted benchmark datasets and source PDFs
├── json_datasets/           # JSON benchmark datasets
├── recovery/                # Semantic support recovery pipeline
└── scripts/                 # Dataset and evaluation utilities
```

## Setup

Create a Python environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file and add your own keys:

```bash
cp .env.example .env
```

Required for agent and recovery workflows:

- `GEMINI_API_KEY`

Optional for higher Semantic Scholar rate limits:

- `S2_API_KEY`

## GROBID

Reference extraction expects a local GROBID service at:

```text
http://localhost:8070
```

One common way to start it is with Docker:

```bash
docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

## Usage

Extract references from a PDF and verify the first few citations:

```bash
python main.py grobid_datasets/exp1.pdf --limit 10
```

Run the rule-based benchmark:

```bash
python run_test.py
```

Run the LLM-assisted verifier:

```bash
python agent.py
```

Run the recovery pipeline:

```bash
python recovery/run_recovery.py --pdf recovery/exp1.pdf --results recovery/exp1_cleaned_results.json
```

## Verification Labels

- `LEVEL_1_PERFECT`: metadata matches an existing paper
- `LEVEL_2_FLAWED`: the paper exists, but the citation metadata has a flaw
- `LEVEL_3_FAKE`: no convincing paper match was found

## Notes for GitHub

Generated outputs, local caches, virtual environments, and private environment files are ignored by Git. Do not commit `.env` or API keys.
