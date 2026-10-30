# ResearchLens — Development Diary

*Translated from the original Russian diary. Detailed result tables are in the [project documentation](documentation.md).*

## Background (May – September 2026)

*This section was written in October 2026, from memory and from the files that survive from that time. I did not keep a diary in the summer, so the dates below come from the dates of those files.*

- **May 2026.** I came up with the idea of an AI research paper: how quickly an AI reaches a plateau during training. Because of school exams and the SAT, I postponed it until June.
- **June 2026.** I started the research and ran into the problem that led to ResearchLens. I found more than 2,000 papers, and each one took me more than two hours to read and judge. Most of them only applied machine learning in other fields, but search engines still showed them for my query.
- **23 June 2026.** First experiment: a short script (`test.py`) that searches the Semantic Scholar API and prints titles, years, citation counts and abstracts.
- **25 June 2026.** First prototype of the website: Flask, Semantic Scholar + OpenAlex search, removal of duplicates by DOI, a Research Fit Score and a Credibility Score, a short AI summary and a Deep Analysis mode through Groq (llama-3.3-70b-versatile), and export of citations in APA and BibTeX. The same day a document called “ResearchLens 2.0” was prepared with recommendations for rebuilding the project: modular architecture, keys in `.env`, error handling, a cleaner interface. The prototype code is kept in [`legacy/prototype-june-2026`](../legacy/prototype-june-2026).
- **July – September 2026.** The project was on pause while I prepared for the SAT and IELTS.
- **October 2026.** Looking at the prototype again, I decided to treat it as a draft and rebuild the platform from scratch around one idea: a guide that connects large databases with students. The new version dropped citation export, Deep Analysis and the Credibility Score; I decided the Credibility Score was not a reliable measure of a paper's quality. The diary below starts with this restart.

## 20.10.2026

I tested Google Scholar: how accurate are the first 20 results for a query? I judged every article myself with three answers: fits the query, partly fits, does not fit. Of the first 20 articles, only 3 fit, 5 partly fit and 12 did not fit at all. That is about 15% accuracy with a strict check and 40% with a softer one. ([Appendix A](documentation.md#appendix-a--google-scholar-baseline-20-articles))

## 21.10.2026

I started the documentation: the goals, the hypothesis, where the idea came from and the history of the project. I also made a step-by-step plan.

## 22.10.2026

I wrote the first two steps of the plan in the documentation: the results of the preliminary test, the comparison of different databases, and the list of features of the future platform.

## 23.10.2026

I wrote the third step of the plan: choosing the AI model for the final platform. I selected 3 candidates and 2 ways of using them: free through Groq and paid through OpenRouter.

## 24.10.2026

Work on the code of the platform started. The main source of the code is Claude. I review the code, write the list of features, the documentation and the project plan, design the measurements and test all of the code. The first check found the first bug: OpenAlex returned error 400 for queries with a “?”; fixed by cleaning the query.

## 25.10.2026

The first version of the platform was made.

A check on the same query as in Google Scholar: of the first 20 articles, 11 fit, meaning they scored 4.0 or higher. To be fair, these included paid articles; among the free ones only the first 10 fit. So the first version approved 45% of articles as fitting perfectly and 50% with a softer check. Compared with my manual search in Google Scholar, that is 30 points higher in strict accuracy and 10 points higher in soft accuracy. The default model at that time was gpt-oss-120b. Later it turned out that this comparison was incorrect: see 26.10.

Then I analysed three models: gpt-oss-120b, gpt-oss-20b and qwen3.8-27b. The test was run in test mode through Groq on three different queries, using only free articles for all models and queries:

1. “Training a neural network on board games” — my main query.
2. “The use of nanotechnology in medicine” — a query from another field.
3. “To what extent does the use of AI affect the quality of education for children under the age of 13?” — a narrower query.

The results are in [Appendix B](documentation.md#appendix-b--model-comparison-9-tests). Observations:

- Some articles have no abstract in OpenAlex, so the models could not evaluate them and put them in the “No” category. In query 1 this was article #10, which I rated “Yes” after visiting its page and reading the abstract. In query 2 the same happened with article #8.
- In query 2, articles #14, #15 and #16 were the same paper, because it was uploaded to OpenAlex several times. I added this limitation to the documentation and planned to fix it in the next version.
- I found a new evaluation criterion, stability: the same model could change its score for the same query.
- The long time for query 3 and its low match with the query were caused by how narrow the query is.

## 26.10.2026

I did a full manual analysis of the first 20 articles returned by the platform and compared all three models with my analysis. I also wrote down the limitations of the analysis method and of the model choice, and possible solutions.

It also became clear that the comparison from 25.10 was incorrect. The 45% and 50% there are the share of articles the AI approved itself, not the match with my evaluation. Besides, Google Scholar and OpenAlex returned different sets of articles, so they cannot be compared directly. Accuracy has to be measured by comparing the AI's answers with my manual evaluation of the same articles.

## 27.10.2026

Based on my analysis, I compared all three models on the first query. I also analysed the next 20 articles for the second query and found a flaw in OpenAlex itself (duplicate articles).

## 28.10.2026

I found one more limitation during testing and added it to the documentation. I also finished the manual analysis of all 60 articles, compared them with the answers of the three models and filled in the table. As a result, I got the average values of all models across all three queries.

## 29.10.2026

| | gpt-oss-120b | gpt-oss-20b | qwen3.8-27b | Best |
|---|---|---|---|---|
| Strict accuracy (average) | 61.7% | 71.7% | 68.3% | gpt-oss-20b |
| Soft accuracy (average) | 68.3% | 80% | 75% | gpt-oss-20b |
| Junk shown (total) | 12 | 4 | 10 | gpt-oss-20b |
| Useful articles missed (total) | 7 | 8 | 5 | qwen3.8-27b |
| Stability (category changes between runs) | 52/60 (87%), 4 dangerous changes | 55/60 (92%), 4 dangerous changes | 59/60 (98%), 0 dangerous changes | qwen3.8-27b |
| Speed (median) | 7.1 s | 5.5 s | 56.9 s | gpt-oss-20b |

gpt-oss-20b leads in accuracy, the amount of junk and speed. Since accuracy is our top priority, it is the most logical choice, and its stability is good enough for us.

The second version of the platform was also made, and I tested it. After several queries the platform worked normally, without errors. When I entered a query with a typo, “Brian's nerral signals”, an error banner appeared with the message “No fitting articles among the first 0”. This message was wrong, as if the platform had checked nothing, so the code was changed: for queries with typos the platform now shows the corrected query and all articles for it.

## 30.10.2026

A functional test of the platform was carried out: 34 checks ([Appendix C](documentation.md#appendix-c--functional-test-of-the-platform)). A new design of the platform in the style of a library card catalogue was also made (versions 3 and 4). During a live search, error 413 appeared: Groq rejected the request because a batch of articles with long abstracts exceeded the limit of 8,000 tokens per minute. The bug was fixed: long abstracts are shortened to 2,500 characters, the length of the AI's answer is capped, batches are built by text size, and a request that is still too large is split in half. Another bug was also found and fixed: the “Save” menu closed right after a project was chosen. Step 4 and the results were added to the documentation.
