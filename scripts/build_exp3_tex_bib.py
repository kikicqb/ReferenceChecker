import json

import build_exp5_tex_bib as builder


def main() -> None:
    builder.PDF_PATH = builder.Path(
        "source_papers/"
        "Duplicate_Record_Detection_A_Survey.pdf"
    )
    builder.JSON_PATH = builder.ROOT / "json_datasets" / "exp3.json"
    builder.OUT_DIR = builder.ROOT / "exp3_constructed"
    builder.TEI_PATH = (
        builder.ROOT
        / ".grobid_cache"
        / "Duplicate_Record_Detection_A_Survey_48164e11330b.tei.xml"
    )
    builder.KEY_PREFIX = "exp3"

    # First 10 entries are real Level-1 papers that should be semantically
    # unsupported; place them in specific phonetic/numeric-metric contexts.
    # Last 10 entries are Level-3 fake citations placed in later model contexts.
    builder.SELECTED_REF_ORDINALS = list(range(55, 65)) + list(range(69, 79))

    builder.OUT_DIR.mkdir(exist_ok=True)
    items = json.loads(builder.JSON_PATH.read_text(encoding="utf-8"))
    root = builder.etree.fromstring(builder.TEI_PATH.read_bytes())

    bib_stem = "exp3_mixed"
    tex_text, mapping = builder.build_tex(root, items, bib_stem)
    bib_text = "\n\n".join(
        builder.make_bib_entry(item, index=i)
        for i, item in enumerate(items, 1)
    ) + "\n"

    (builder.OUT_DIR / "exp3_duplicate_survey_mixed.tex").write_text(
        tex_text, encoding="utf-8"
    )
    (builder.OUT_DIR / "exp3_mixed.bib").write_text(
        bib_text, encoding="utf-8"
    )
    (builder.OUT_DIR / "exp3_citation_mapping.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {builder.OUT_DIR / 'exp3_duplicate_survey_mixed.tex'}")
    print(f"Wrote {builder.OUT_DIR / 'exp3_mixed.bib'}")
    print(f"Wrote {builder.OUT_DIR / 'exp3_citation_mapping.json'}")
    print(f"Inserted citations: {len(mapping)}")


if __name__ == "__main__":
    main()
