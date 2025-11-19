# 🍲 Vietnamese Recipe Search Engine

> A centralized culinary search engine leveraging **TF-IDF Algorithm** and **Generative AI** to aggregate, index, and rank recipes from multiple Vietnamese food platforms.

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![Flask](https://img.shields.io/badge/Web%20Framework-Flask-green?logo=flask)
![Gemini AI](https://img.shields.io/badge/AI-Gemini%20API-red?logo=google-gemini)
![BeautifulSoup](https://img.shields.io/badge/Crawler-BS4-yellow)
![Algorithm](https://img.shields.io/badge/Ranking-TF%E2%80%93IDF-orange)

## 📖 Introduction

The **Vietnamese Recipe Search Engine** addresses the fragmentation of culinary data by providing a unified interface to search across diverse recipe websites. Unlike basic keyword matching, this system implements a **Vector Space Model** with **Field-Weighted TF-IDF** to rank results based on relevance (prioritizing titles and ingredients).

Crucially, the project demonstrates **three distinct data collection strategies**, ranging from standard pagination to AJAX handling and AI-assisted extraction.

## 🏗️ System Architecture & File Descriptions

This project is structured into three core modules. Below is the technical breakdown of key files:

### 1. Data Collection Layer (`crawler/`)
This module demonstrates versatility in handling different web architectures.

| File | Method / Technique | Description |
| :--- | :--- | :--- |
| **`monngonmoingay_crawler.py`** | **Standard Pagination** | Handles traditional server-side rendered pages. Iterates through numbered pages via URL modification and uses CSS selectors for extraction. Implements basic politeness delays. |
| **`dienmayxanh_crawler.py`** | **AJAX & ID Tracking** | Solves the challenge of **Dynamic Content Loading**. Instead of URL pagination, it reverse-engineers the **AJAX POST requests**, manages payload parameters (`pageindex`, `listdishid`), and tracks unique IDs to ensure no data duplication. |
| **`disneycooking_crawler.py`** | **AI-Assisted Extraction** | The most advanced crawler. It integrates **Google Gemini API** to parse unstructured recipe text into standardized JSON objects (Title, Ingredients, Instructions). It also implements **Exponential Backoff** logic to robustly handle network instability or API rate limits. |

### 2. Indexing & Search Core (`src/`)
The search engine logic is built from scratch without relying on heavy search libraries like ElasticSearch.

| File | Key Algorithm | Description |
| :--- | :--- | :--- |
| **`build_index.py`** | **Inverted Indexing** | Processes raw JSON data, cleans text (tokenization, stopword removal), and builds a **Field-Based Inverted Index**. It includes a **Token Expansion** logic (e.g., treating `cà_rốt` and `cà rốt` as synonyms) to improve recall. |
| **`search_engine.py`** | **Field-Weighted TF-IDF** | Implements the ranking algorithm. It assigns different weights to fields: **Title (3.0)** > **Ingredients (2.0)** > **Instructions (1.0)**. This ensures that a query matching the title appears higher than a query matching only the instructions. |
| **`evaluate_ranking.py`** | **System Evaluation** | A testing script that calculates **Precision@K** and **MAP (Mean Average Precision)** against a manually curated "Ground Truth" dataset to quantitatively measure search quality. |

### 3. Web Application Layer
* **`webapp.py`**: A lightweight Flask server that loads the Inverted Index into memory upon startup and serves search requests via RESTful routes.
* **`run.py`**: The application entry point.

## 📂 Project Structure

```text
root/
├── crawler/                 # Scraping scripts (BS4, Requests, Gemini API)
│   ├── dienmayxanh_crawler.py
│   ├── disneycooking_crawler.py
│   └── monngonmoingay_crawler.py
├── data/                    # Data storage
│   ├── raw/                 # Raw JSON data collected from crawlers
│   └── index/               # Processed Inverted Index (optimized for speed)
├── src/                     # Core Search Logic
│   ├── build_index.py       # Indexer
│   ├── search_engine.py     # Ranking Algorithm
│   └── evaluate_ranking.py  # Performance Metrics
├── templates/               # HTML Frontend
├── requirements.txt         # Dependencies
└── run.py                   # App Entry Point
