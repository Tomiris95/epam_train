## Selected Metrics

The following two metrics were selected as the most valuable for the RAG subsystem:

### Answer Found Rate (AFR)

\[
AFR = \frac{\text{Number of questions with valid answers}}{\text{Total number of questions}}
\]

An answer is considered valid if the model does not return the fallback phrase:  
**"The provided context does not contain the answer to this question."**

**Rationale:**
- Directly reflects retrieval quality  
- Measures whether the system can locate relevant information  
- Important for user satisfaction and perceived usefulness  

---

### LLM-based Answer Quality Score (0–100)

Each answer is evaluated using an **LLM-as-a-Judge** approach based on three criteria:
- Factual correctness  
- Completeness  
- Faithfulness to the source documents  

The judge compares the RAG-generated answer with the expected answer derived strictly from source documents (generated with Gemini).

**Rationale:**
- Captures qualitative aspects that AFR alone cannot  
- Penalizes hallucinations and missing details  
- Aligns well with real user perception of answer quality  

---

## Automated Evaluation Environment

To ensure reproducibility and scalability, an automated evaluation pipeline was implemented.

### Test Dataset
- 20 manually prepared questions  
- Expected answers generated from source documents  
- Stored in JSON format  

### Automated Testing Workflow

For each system version:
1. Run RAG inference for all test questions  
2. Save results to CSV  
3. Automatically evaluate answers using LLM Judge  
4. Aggregate metrics (AFR and Average LLM Score)  
5. Store evaluation results as JSON  

This setup enables consistent comparison across multiple system iterations.

---

## Data Sources

In the earlier version (Module 3), the knowledge base partially relied on GPT-generated content.  
In the current version, only reliable and authoritative sources were used:

- *Caring for Your Baby and Young Child* by the American Academy of Pediatrics (AAP), Chapter 10  
- *The Ultimate List of Montessori Activities for Babies, Toddlers and Preschoolers* by The Montessori Notebook  

The total volume of processed data is **155 pages**.

---

## Baseline System (Iteration 1)  
*(ingestion/database_creation.ipynb, test_rag.ipynb)*

### Baseline Chunking Strategy
- Chunk size: **2000 tokens**  
- Overlap: **300 tokens**

---

## Iteration 2: Improved Chunking (Paragraph + Tables)  
*(ingestion/database_creation_v2.ipynb, data_extraction/parse_tables, test_rag.ipynb)*

### Enhancement Rationale

To better preserve semantic structure and factual data, chunking was changed to:
- Paragraph-based text chunks  
- Tables extracted and stored as separate chunks  

---

## Iteration 3: Paragraph-only Chunking  
*(ingestion/database_creation_v3.ipynb, test_rag.ipynb)*

### Enhancement Rationale

Tables introduced noise for natural language queries.  
This iteration uses:
- Semantic paragraph chunking only  

---

## Intermediate Results (to choose chunking method)

| Metric                         | Version 1 | Version 2 | Version 3 |
|--------------------------------|-----------|-----------|-----------|
| Answer Found Rate (AFR)        | 0.60      | 0.40      | 0.70      |
| LLM-based Answer Quality Score | 40.00     | 32.25     | 42.75     |

---

## Intermediate Conclusion

The paragraph-only chunking approach (Version 3) provides the best balance between retrieval precision and answer quality.  
Although Version 1 achieved a reasonable Answer Found Rate, the use of large chunks with significant overlap introduced semantic noise, negatively affecting answer completeness and factual precision. Version 2 showed the weakest performance across both metrics, indicating that structured tabular data added irrelevant or distracting context for natural language queries in this domain.

---

## Iteration 4: Re-ranking with Cross-Encoder  
*(test_rag.ipynb)*

### Enhancement Rationale

Dense retrieval alone may rank documents imperfectly.  
A cross-encoder re-ranking stage was added to improve top-K relevance.

---

## Iteration 5: HyDE  
*(test_rag.ipynb)*

### Enhancement Rationale

Some user questions are underspecified.  
HyDE (Hypothetical Document Embeddings) helps retrieve relevant documents by embedding a generated hypothetical answer.

---

## Results (Comparative Analysis)

| Metric                         | Version 1 | Version 2 | Version 3 | Version 4 | Version 5 |
|--------------------------------|-----------|-----------|-----------|-----------|-----------|
| Answer Found Rate (AFR)        | 0.60      | 0.40      | 0.70      | 0.70      | 0.75      |
| LLM-based Answer Quality Score | 40.00     | 32.25     | 42.75     | 54.00     | 49.50     |

---

## Conclusion

The experimental results show that iterative enhancements significantly improved the RAG subsystem performance. Compared to the baseline (Version 1), **Version 5** achieved the highest Answer Found Rate (0.75), representing a **25% improvement**, while **Version 4** achieved the highest LLM-based Answer Quality Score (54.00), corresponding to a **35% improvement**. Re-ranking proved most effective for improving answer quality, whereas HyDE improved robustness and answer coverage. Overall, the applied enhancements successfully increased both retrieval effectiveness and answer quality.

---

**GitHub link:**  
*https://github.com/Tomiris95/epam_train/tree/main/Module4*
