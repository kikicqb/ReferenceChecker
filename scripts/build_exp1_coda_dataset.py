import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "source_papers" / "CoDa_2024_findings_naacl.pdf"


EXP1_ITEMS = [
    {
        "id": 1,
        "title": "Graph Propagation based Data Augmentation for Named Entity Recognition",
        "author": "Jiong Cai, Shen Huang, Yong Jiang, Zeqi Tan, Pengjun Xie, Kewei Tu",
        "year": "2023",
        "link": "https://doi.org/10.18653/v1/2023.acl-short.11",
    },
    {
        "id": 2,
        "title": "LeXFiles and LegalLAMA: Facilitating English Multinational Legal Language Model Development",
        "author": "Ilias Chalkidis, Nicolas Garneau, Catalina Goanta, Daniel Katz, Anders Søgaard",
        "year": "2023",
        "link": "https://doi.org/10.18653/v1/2023.acl-long.865",
    },
    {
        "id": 3,
        "title": "An Empirical Survey of Data Augmentation for Limited Data Learning in NLP",
        "author": "Jiaao Chen, Derek Tam, Colin Raffel, Mohit Bansal, Diyi Yang",
        "year": "2023",
        "link": "https://doi.org/10.1162/tacl_a_00542",
    },
    {
        "id": 4,
        "title": "Style Transfer as Data Augmentation: A Case Study on Named Entity Recognition",
        "author": "Shuguang Chen, Leonardo Neves, Thamar Solorio",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.emnlp-main.120",
    },
    {
        "id": 5,
        "title": "An Analysis of Simple Data Augmentation for Named Entity Recognition",
        "author": "Xiang Dai, Heike Adel",
        "year": "2020",
        "link": "https://doi.org/10.18653/v1/2020.coling-main.343",
    },
    {
        "id": 6,
        "title": "DAGA: Data Augmentation with a Generation Approach for Low-resource Tagging Tasks",
        "author": "Bosheng Ding, Linlin Liu, Lidong Bing, Canasai Kruengkrai, Thien Hai Nguyen, Shafiq Joty, Luo Si, Chunyan Miao",
        "year": "2020",
        "link": "https://doi.org/10.18653/v1/2020.emnlp-main.488",
    },
    {
        "id": 7,
        "title": "Finding Dataset Shortcuts with Grammar Induction",
        "author": "Dan Friedman, Alexander Wettig, Danqi Chen",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.emnlp-main.293",
    },
    {
        "id": 8,
        "title": "BioAug: Conditional Generation based Data Augmentation for Low-Resource Biomedical NER",
        "author": "Sreyan Ghosh, Utkarsh Tyagi, Sonal Kumar, Dinesh Manocha",
        "year": "2023",
        "link": "https://doi.org/10.1145/3539618.3591957",
    },
    {
        "id": 9,
        "title": "ACLM: A Selective-Denoising based Generative Data Augmentation Approach for Low-Resource Complex NER",
        "author": "Sreyan Ghosh, Utkarsh Tyagi, Manan Suri, Sonal Kumar, Ramaneswaran S, Dinesh Manocha",
        "year": "2023",
        "link": "https://doi.org/10.18653/v1/2023.acl-long.8",
    },
    {
        "id": 10,
        "title": "AEDA: An Easier Data Augmentation Technique for Text Classification",
        "author": "Akbar Karimi, Leonardo Rossi, Andrea Prati",
        "year": "2021",
        "link": "https://doi.org/10.18653/v1/2021.findings-emnlp.234",
    },
    {
        "id": 11,
        "title": "SSMBA: Self-Supervised Manifold Based Data Augmentation for Improving Out-of-Domain Robustness",
        "author": "Nathan Ng, Kyunghyun Cho, Marzyeh Ghassemi",
        "year": "2020",
        "link": "https://doi.org/10.18653/v1/2020.emnlp-main.97",
    },
    {
        "id": 12,
        "title": "AMR-DA: Data Augmentation by Abstract Meaning Representation",
        "author": "Ziyi Shou, Yuxin Jiang, Fangzhen Lin",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.findings-acl.244",
    },
    {
        "id": 13,
        "title": "NewsQA: A Machine Comprehension Dataset",
        "author": "Adam Trischler, Tong Wang, Xingdi Yuan, Justin Harris, Alessandro Sordoni, Philip Bachman, Kaheer Suleman",
        "year": "2017",
        "link": "https://doi.org/10.18653/v1/w17-2623",
    },
    {
        "id": 14,
        "title": "PromDA: Prompt-based Data Augmentation for Low-Resource NLU Tasks",
        "author": "Yufei Wang, Can Xu, Qingfeng Sun, Huang Hu, Chongyang Tao, Xiubo Geng, Daxin Jiang",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.acl-long.292",
    },
    {
        "id": 15,
        "title": "ZeroGen: Efficient Zero-shot Learning via Dataset Generation",
        "author": "Jiacheng Ye, Jiahui Gao, Qintong Li, Hang Xu, Jiangtao Feng, Zhiyong Wu, Tao Yu, Lingpeng Kong",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.emnlp-main.801",
    },
    {
        "id": 16,
        "title": "GPT3Mix: Leveraging Large-scale Language Models for Text Augmentation",
        "author": "Kang Min Yoo, Dongju Park, Jaewook Kang, Sang-Woo Lee, Woomyoung Park",
        "year": "2021",
        "link": "https://doi.org/10.18653/v1/2021.findings-emnlp.192",
    },
    {
        "id": 17,
        "title": "FlipDA: Effective and Robust Data Augmentation for Few-Shot Learning",
        "author": "Jing Zhou, Yanan Zheng, Jie Tang, Li Jian, Zhilin Yang",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.acl-long.592",
    },
    {
        "id": 18,
        "title": "MELM: Data Augmentation with Masked Entity Language Modeling for Low-Resource NER",
        "author": "Ran Zhou, Xin Li, Ruidan He, Lidong Bing, Erik Cambria, Luo Si, Chunyan Miao",
        "year": "2022",
        "link": "https://doi.org/10.18653/v1/2022.acl-long.160",
    },
    {
        "id": 19,
        "title": "A Primer in BERTology: What We Know About How BERT Works",
        "author": "Anna Rogers, Olga Kovaleva, Anna Rumshisky",
        "year": "2020",
        "link": "https://doi.org/10.1162/tacl_a_00349",
    },
    {
        "id": 20,
        "title": "EDA: Easy Data Augmentation Techniques for Boosting Performance on Text Classification Tasks",
        "author": "Jason Wei, Kai Zou",
        "year": "2019",
        "link": "https://doi.org/10.18653/v1/d19-1670",
    },
]


def main() -> None:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"Missing source PDF: {SOURCE_PDF}")

    dataset = [
        {
            **item,
            "is_real": True,
            "group": "Exp1_CoDa_Clean_Level1",
        }
        for item in EXP1_ITEMS
    ]

    (ROOT / "json_datasets" / "exp1.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    cleaned_results = {
        "summary": {
            "total_papers": len(dataset),
            "labeled_papers": len(dataset),
            "correct_predictions": len(dataset),
            "accuracy": "100.00%",
            "source": "Oracle clean Level 1 labels for CoDa Exp1 recovery.",
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
    print("Updated recovery/exp1_cleaned_results.json")
    print("Updated grobid_datasets/exp1.pdf")
    print("Updated recovery/exp1.pdf")


if __name__ == "__main__":
    main()
