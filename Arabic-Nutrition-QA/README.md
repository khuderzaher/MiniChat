---
license: apache-2.0
dataset_info:
  features:
  - name: Question
    dtype: string
  - name: Answer
    dtype: string
  splits:
  - name: train
    num_bytes: 10111271
    num_examples: 11861
  - name: test
    num_bytes: 590627
    num_examples: 625
  download_size: 4955388
  dataset_size: 10701898
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
  - split: test
    path: data/test-*
language:
- ar
tags:
- QA
size_categories:
- 10K<n<100K
---

# Dataset Card for Arabic-Nutrition-QA

## Dataset Description

The **Arabic-Nutrition-QA** dataset is a specialized corpus of approximately 12,486 question-and-answer pairs focused on the domain of nutrition and health. It is designed to facilitate the development and fine-tuning of Large Language Models (LLMs) to handle medical and dietary inquiries in Arabic with high linguistic and domain accuracy.

### Link to Dataset
**Source:** `moazeldegwy/Arabic-Nutrition-QA`

---

## Dataset Summary

| Aspect | Details |
| :--- | :--- |
| **Total Rows** | 12,486 |
| **Language** | Arabic (UTF-8) |
| **Primary Tasks** | Question Answering, Fine-tuning LLMs, Text Classification |
| **Average Question Length** | ~20 words (Specific health/dietary concerns) |
| **Average Answer Length** | ~70 words (Detailed recommendations and guidance) |

---

## Data Structure

### Data Fields
*   `Question`: (String) A free-text query in Arabic regarding a specific nutrition or health concern.
*   `Answer`: (String) A comprehensive Arabic response providing dietary advice, lifestyle changes, and/or medical recommendations.

### Data Splits
The dataset is pre-split into training and testing sets to ensure standardized evaluation:

| Split | Number of Rows | Size (Approx) |
| :--- | :--- | :--- |
| **Train** | 11,861 | 10.11 MB |
| **Test** | 625 | 0.59 MB |

---

## Content & Coverage

The dataset covers a wide array of health-related themes, including but not limited to:
*   **Weight Management:** Fat loss, obesity, and safe weight-loss supplements.
*   **Metabolic Health:** Diabetes (Type 2, Pre-diabetes), blood sugar control, and HbA1c management.
*   **Cardiovascular Health:** Cholesterol (LDL/HDL) and lipid profile improvements.
*   **Specialized Nutrition:** Pregnancy diets, pediatric nutrition, and skin health (acne).
*   **Hormonal Health:** Dietary considerations for PCOS and thyroid issues.

---

## Intended Use Cases

1.  **Model Fine-tuning:** Training Arabic LLMs to adopt a professional, health-oriented persona.
2.  **RAG (Retrieval-Augmented Generation):** Serving as a grounded knowledge base for Arabic nutrition chatbots.
3.  **Topic Modeling:** Categorizing user health concerns into sub-domains (e.g., "Endocrinology" vs. "General Fitness").
4.  **Summarization:** Training models to condense long medical advice into concise, actionable bullet points.

---

## Key Features

*   **Domain Specificity:** Unlike general-purpose Arabic datasets, this focuses purely on nutrition and health.
*   **Cultural Relevance:** The advice often reflects dietary habits and food items common in Arabic-speaking regions.
*   **High-Quality Responses:** Answers are typically multi-sentence, providing step-by-step guidance rather than simple "Yes/No" answers.

## Licensing & Disclaimer

*   **License:** Apache-2.0
*   **Disclaimer:** This dataset is intended for research and development purposes. The information provided within the dataset should not be treated as a substitute for professional medical advice, diagnosis, or treatment.

---

## How to Load

```python
from datasets import load_dataset

dataset = load_dataset("moazeldegwy/Arabic-Nutrition-QA")