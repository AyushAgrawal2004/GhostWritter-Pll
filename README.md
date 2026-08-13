# Local PII Detection & Anonymization Engine for Financial Documents

![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local%20%2F%20Zero%20API%20Calls-success)
![Model](https://img.shields.io/badge/Model-GLiNER%20%2B%20Regex%20Engine-orange)

---

## 2. OVERVIEW & MOTIVATION

This project automatically detects, redacts, and replaces Personally Identifiable Information (PII) in unstructured `.docx` files with realistic synthetic surrogates. 

**Privacy-First Engineering:** The entire pipeline runs 100% locally on CPU or GPU hardware without sending a single byte of sensitive financial data to external cloud APIs. 

**Target Use Case:** It is purpose-built for redacting highly sensitive legal and financial documents—such as IPO Red Herring Prospectuses (RHPs)—while strictly preserving the underlying `DOCX` layout, including nested tables, fonts, and inline XML formatting.

---

## 3. ARCHITECTURE & SYSTEM DESIGN

The system follows a strict 5-stage sequential processing pipeline:

```text
[ Input: .docx ]
       │
       ▼
 1. Pre-Processing & Legal Whitelist Filter
    (Strips out known regulatory jargon like SEBI, BSE)
       │
       ▼
 2. Deterministic Regex Engine
    (Extracts Emails, Indian Phone Numbers, URLs, PIN Codes)
       │
       ▼
 3. Local Zero-Shot NLP Engine
    (urchade/gliner_multi_pii-v1 analyzes surrounding context)
       │
       ▼
 4. Stateful Entity Mapping
    (Alphanumeric normalization ensures 1-to-1 consistent synthetic replacements)
       │
       ▼
 5. DOCX Paragraph & Table XML Injection Engine
    (Preserves inline run styles and table heights)
       │
       ▼
[ Output: Redacted .docx ]
```

---

## 4. KEY FEATURES

- **Hybrid Detection Strategy:** Combines deterministic Regular Expressions for highly structured data with a state-of-the-art Transformer NER (GLiNER) for fuzzy context-based entity recognition.
- **Zero Layout Distortion:** Directly modifies the underlying XML text runs without ruining table heights, borders, or text styles.
- **Stateful Anonymization:** A stateful mapping engine guarantees that the same real person or company gets assigned the exact same synthetic replacement throughout the entire length of the document.
- **Indian Financial Context Awareness:** Specifically tuned to detect complex Indian multi-word names, multi-line corporate office addresses, and regional landline formats.

---

## 5. TECHNICAL TRADEOFFS & KNOWN LIMITATIONS

- **Security Mandate (Recall over Precision):** The model confidence threshold is explicitly set to `0.65` to ensure maximum data privacy protection. Over-redacting safe legal terms is considered acceptable; leaving real human PII exposed is a critical failure.
- **Over-Redaction of Legal Terms (False Positives):** Highly specific capitalized terms like *"Qualified Institutional Buyers"* or *"Bidders"* can occasionally be incorrectly flagged as corporate entities or names by the NLP model if they bypass the whitelist.
- **Stateful Name Variations (False Negatives):** While heavily normalized, extreme variations between all-caps comma-separated banner names vs. title-case standalone names can occasionally create separate dictionary keys.

---

## 6. EVALUATION STRATEGY & METRICS

The engine was evaluated against a full-document benchmark of an unredacted Red Herring Prospectus.

### Overall Performance Summary
- **Overall Precision:** 84.65%
- **Overall Recall:** 92.93%
- **Overall F1-Score:** 88.60%

### Category Breakdown Table

| Entity Category | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision (%) | Recall (%) | F1-Score (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Emails** | 17 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| **Phone / Tel** | 12 | 0 | 0 | 100.00% | 100.00% | 100.00% |
| **Websites / URLs** | 5 | 0 | 1 | 100.00% | 83.33% | 90.91% |
| **Addresses** | 18 | 1 | 0 | 94.74% | 100.00% | 97.30% |
| **Person Names** | 88 | 18 | 8 | 83.02% | 91.67% | 87.13% |
| **Organizations** | 31 | 12 | 4 | 72.09% | 88.57% | 79.49% |
| **Total** | **171** | **31** | **13** | **84.65%** | **92.93%** | **88.60%** |

---

## 7. PROJECT STRUCTURE

```text
GhostWriter PII/
├── README.md
├── requirements.txt
├── main.py                     # CLI Entry Point
├── src/
│   ├── detectors/
│   │   └── hybrid_detector.py  # Regex + GLiNER Engine
│   └── redactors/
│       ├── docx_handler.py     # XML Run Parser & Injector
│       └── mapper.py           # Stateful Faker Dictionary
├── Red Herring Prospectus.docx # Input File
└── redacted_output.docx        # Output File
```

---

## 8. INSTALLATION & SETUP

> **Warning:** Python 3.14 is currently incompatible with certain dependencies due to the removal of `pkgutil`. Ensure you are running **Python 3.11, 3.12, or 3.13**.

Run the following commands in your terminal to set up the local environment:

```bash
# Create a virtual environment
python3.12 -m venv venv

# Activate the virtual environment (Mac/Linux)
source venv/bin/activate

# Install the required local dependencies
pip install -r requirements.txt
```

---

## 9. USAGE & CLI COMMANDS

To execute the redaction pipeline on a document, run the following command:

```bash
python main.py --mode redact --input "Red Herring Prospectus.docx" --output "redacted_output.docx"
```

*(Note: The GLiNER model weights will automatically download to your local machine on the first execution.)*
