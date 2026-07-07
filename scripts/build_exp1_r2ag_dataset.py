import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "source_papers" / "R2AG_2024_findings_emnlp.pdf"


EXP1_ITEMS = [
    {
        "id": 1,
        "title": "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection",
        "author": "Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi",
        "year": "2023",
        "link": "https://doi.org/10.48550/arXiv.2310.11511",
    },
    {
        "id": 2,
        "title": "When Not to Trust Language Models: Investigating Effectiveness of Parametric and Non-Parametric Memories",
        "author": "Alex Mallen, Akari Asai, Victor Zhong, Rajarshi Das",
        "year": "2023",
        "link": "https://doi.org/10.18653/v1/2023.acl-long.546",
    },
    {
        "id": 3,
        "title": "REPLUG: Retrieval-Augmented Black-Box Language Models",
        "author": "Weijia Shi, Sewon Min, Michihiro Yasunaga, Minjoon Seo",
        "year": "2023",
        "link": "https://doi.org/10.48550/arXiv.2301.12652",
    },
    {
        "id": 4,
        "title": "Seven Failure Points When Engineering a Retrieval Augmented Generation System",
        "author": "Scott Barnett, Stefanus Kurniawan, Srikanth Thudumu, Zach Brannelly",
        "year": "2024",
        "link": "https://doi.org/10.48550/arXiv.2401.05856",
    },
    {
        "id": 5,
        "title": "Can Retriever-Augmented Language Models Reason? The Blame Game Between the Retriever and the Language Model",
        "author": "Parishad BehnamGhader, Santiago Miret, Siva Reddy",
        "year": "2022",
        "link": "https://doi.org/10.48550/arXiv.2212.09146",
    },
    {
        "id": 6,
        "title": "InternLM2 Technical Report",
        "author": "Zheng Cai, Maosong Cao, Haojiong Chen, Kai Chen",
        "year": "2024",
        "link": "https://doi.org/10.48550/arXiv.2403.17297",
    },
    {
        "id": 7,
        "title": "RegaVAE: A Retrieval-Augmented Gaussian Mixture Variational Auto-Encoder for Language Modeling",
        "author": "Jingcheng Deng, Liang Pang, Huawei Shen, Xueqi Cheng",
        "year": "2023",
        "link": "https://doi.org/10.18653/v1/2023.findings-emnlp.164",
    },
    {
        "id": 8,
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "author": "Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova",
        "year": "2019",
        "link": "https://doi.org/10.18653/v1/N19-1423",
    },
    {
        "id": 9,
        "title": "Retrieval-Augmented Generation for Large Language Models: A Survey",
        "author": "Yunfan Gao, Yun Xiong, Xinyu Gao, Kangxiang Jia",
        "year": "2023",
        "link": "https://doi.org/10.48550/arXiv.2312.10997",
    },
    {
        "id": 10,
        "title": "Re2G: Retrieve, Rerank, Generate",
        "author": "Michael Glass, Gaetano Rossiello, Md Faisal Mahbub Chowdhury",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.naacl-main.194",
    },
    {
        "id": 11,
        "title": "G-Retriever: Retrieval-Augmented Generation for Textual Graph Understanding and Question Answering",
        "author": "Xiaoxin He, Yijun Tian, Yifei Sun, Nitesh V. Chawla",
        "year": "2024",
        "link": "https://doi.org/10.48550/arXiv.2402.07630",
    },
    {
        "id": 12,
        "title": "Constructing a Multi-hop QA Dataset for Comprehensive Evaluation of Reasoning Steps",
        "author": "Xanh Ho, Anh-Khoa Duong Nguyen, Saku Sugawara, Akiko Aizawa",
        "year": "2020",
        "link": "https://doi.org/10.18653/v1/2020.coling-main.580",
    },
    {
        "id": 13,
        "title": "RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation",
        "author": "Fangyuan Xu, Weijia Shi, Eunsol Choi",
        "year": "2023",
        "link": "https://doi.org/10.48550/arXiv.2310.04408",
    },
    {
        "id": 14,
        "title": "Atlas: Few-shot Learning with Retrieval Augmented Language Models",
        "author": "Gautier Izacard, Patrick Lewis, Maria Lomeli, Lucas Hosseini",
        "year": "2022",
        "link": "https://doi.org/10.48550/arXiv.2208.03299",
    },
    {
        "id": 15,
        "title": "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression",
        "author": "Huiqiang Jiang, Qianhui Wu, Xufang Luo, Dongsheng Li",
        "year": "2023",
        "link": "https://doi.org/10.48550/arXiv.2310.06839",
    },
    {
        "id": 16,
        "title": "Large Language Models Struggle to Learn Long-Tail Knowledge",
        "author": "Nikhil Kandpal, Adam Deng, Eric Roberts, Colin Raffel",
        "year": "2022",
        "link": "https://doi.org/10.48550/arXiv.2211.08411",
    },
    {
        "id": 17,
        "title": "Bridging the Preference Gap between Retrievers and LLMs",
        "author": "Zixuan Ke, Weize Kong, Cheng Li, Mingyang Zhang",
        "year": "2024",
        "link": "https://doi.org/10.48550/arXiv.2401.06954",
    },
    {
        "id": 18,
        "title": "Natural Questions: A Benchmark for Question Answering Research",
        "author": "Tom Kwiatkowski, Jennimaria Palomaki, Olivia Redfield, Michael Collins",
        "year": "2019",
        "link": "https://doi.org/10.1162/tacl_a_00276",
    },
    {
        "id": 19,
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "author": "Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni",
        "year": "2020",
        "link": "https://doi.org/10.48550/arXiv.2005.11401",
    },
    {
        "id": 20,
        "title": "Lost in the Middle: How Language Models Use Long Contexts",
        "author": "Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape",
        "year": "2023",
        "link": "https://doi.org/10.1162/tacl_a_00638",
    },
]


def main() -> None:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"Missing source PDF: {SOURCE_PDF}")

    dataset = [
        {
            **item,
            "is_real": True,
            "group": "Exp1_R2AG_Clean_Level1",
        }
        for item in EXP1_ITEMS
    ]

    for dataset_path in [
        ROOT / "json_datasets" / "exp1.json",
        ROOT / "grobid_datasets" / "exp1.json",
    ]:
        dataset_path.write_text(
            json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    cleaned_results = {
        "summary": {
            "total_papers": len(dataset),
            "labeled_papers": len(dataset),
            "correct_predictions": len(dataset),
            "accuracy": "100.00%",
            "source": "Oracle clean Level 1 labels for R2AG Exp1 recovery.",
        },
        "detailed_results": [
            {
                "id": item["id"],
                "title": item["title"],
                "author": item["author"],
                "year": item["year"],
                "link": item["link"],
                "group": item["group"],
                "has_label": True,
                "expected_real": True,
                "clean_verdict": "LEVEL_1_PERFECT",
                "system_result": [
                    "LEVEL_1_PERFECT",
                    "Oracle clean input for recovery evaluation.",
                ],
                "is_correct": True,
            }
            for item in dataset
        ],
    }
    (ROOT / "recovery" / "exp1_cleaned_results.json").write_text(
        json.dumps(cleaned_results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for target in [
        ROOT / "grobid_datasets" / "exp1.pdf",
        ROOT / "recovery" / "exp1.pdf",
    ]:
        shutil.copyfile(SOURCE_PDF, target)

    print("Updated json_datasets/exp1.json")
    print("Updated grobid_datasets/exp1.json")
    print("Updated recovery/exp1_cleaned_results.json")
    print("Updated grobid_datasets/exp1.pdf")
    print("Updated recovery/exp1.pdf")


if __name__ == "__main__":
    main()
