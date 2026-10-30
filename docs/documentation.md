# ResearchLens — Project Documentation

*Version of 30 October 2026. Translated from the original Russian documentation.*

## Contents

1. [Background](#background)
2. [Plan, goal and hypothesis](#plan-goal-and-hypothesis)
3. [Step 1 — Baseline: how accurate is ordinary search?](#step-1--baseline-how-accurate-is-ordinary-search)
4. [Step 2 — Platform features](#step-2--platform-features)
5. [Step 3 — Choosing the AI model](#step-3--choosing-the-ai-model)
6. [Step 4 — Development and testing](#step-4--development-and-testing)
7. [Results](#results)
8. [Appendix A — Google Scholar baseline (20 articles)](#appendix-a--google-scholar-baseline-20-articles)
9. [Appendix B — Model comparison (9 tests)](#appendix-b--model-comparison-9-tests)
10. [Appendix C — Functional test of the platform](#appendix-c--functional-test-of-the-platform)

## Background

In June 2026 I started working on a research paper about AI: I wanted to find out how quickly an AI reaches a plateau during training. The idea came in May 2026, but because of my school exams and the SAT I postponed the research until June. Then I ran into a serious problem. While looking for relevant sources, I realised how many papers on AI there are: I found more than 2,000. I planned to go through the first 50 of them and found that each paper took me more than two hours. That time went not only into reading, but into understanding the terms, getting deep into the topic, and deciding whether the paper really fit my research.

After five papers I noticed that most of them were about AI and machine learning applied in other fields, such as chemistry, biology or sociology. They did not study machine learning itself, but because the text clearly talked about machine learning, every search service showed them to me even though they did not match my query. I realised I was not ready to spend months on this, so I started building my own website for finding relevant sources. The main audience of the platform is school and university students.

## Plan, goal and hypothesis

**Plan:**

- Study the reliable sources of academic papers and decide which one fits my tasks best.
- Find which AI model handles large amounts of text best while staying cheap.
- Plan the website and describe all its features.
- Build the website in Python with the help of the AI model Claude.
- Not copy the code blindly: review it, change the architecture, and run tests.
- After a working prototype, test the site with real people at my school and on online forums, and bring the project to a finished product.

**Goal:** give school and university students a free platform that helps them find sources for research papers. This could help them write papers and research much faster and more accurately.

**Hypothesis:** any student can collect relevant sources for their research with ResearchLens much faster than with ordinary article search. I expect finding the right papers to become more than 10 times faster, with strict accuracy of up to 80% and soft accuracy of up to 90%.

## Step 1 — Baseline: how accurate is ordinary search?

I tested an ordinary database search. Database: Google Scholar. Query: “Training a neural network on board games”. I analysed the first 20 results and recorded how well each one fits my query and goals (full table in [Appendix A](#appendix-a--google-scholar-baseline-20-articles)):

- **Fit (3):** match the topic exactly.
- **Partly fit (5):** not a perfect match, but touch on the topic and could be useful for narrower questions.
- **Do not fit (12):** do not cover the topic or are too general.

The topic may simply have few papers, but even so the strict accuracy of Google Scholar on the first 20 results is only 15%, and the soft accuracy (including partly fitting papers) is about 40%. I judged every article by its title and abstract, which took about 1.5 minutes per article on average.

## Step 2 — Platform features

I took OpenAlex, arXiv and Google Scholar as references. What they have in common: search, filters, topics, and the number of results for a query. OpenAlex shows statistics by publication year and has five filters: year, access, topic, institution and type. Google Scholar filters by year and type, sorts by date or relevance, and can show only review articles or articles with citations or patents; it has fewer filters than OpenAlex and gives a more general picture. arXiv only sorts by date and relevance and has a topic filter. I took the OpenAlex filters as the base and added a few more features.

**Main concept: a guide platform** that connects large databases with people without wasting their time and effort on finding sources. Every article in the results links to its page in the original database, where the user can open and download the paper.

- **Years:** a year filter and the number of articles per year.
- **Topics:** a list of topics; one article can belong to several.
- **Relevance score from 1 to 10**, based on the title and abstract. A vague or imprecise abstract gets a lower score. Roughly: 7.5–10 means the article fits the query, 4.0–7.4 means it is average and may be useful, and articles below 4.0 are not shown at all. The AI reads the abstract, writes one sentence explaining the score, and then gives the score. The highest-scoring articles are shown first.
- **Filters:** by year, by relevance (for example, only articles scored 7.5 or higher), by topic, and by access as a single checkbox: by default only free articles are shown, and the user decides whether to add paid ones.
- **Abstracts** are available for every article, so users can check the paper themselves.
- **No abstract:** the AI does not score the article. It is replaced by the next article in the results and shown in a separate “Articles without an abstract” list so the user can check it (in the first version such articles went to the “No” category).
- **Projects:** users can create projects and save the articles they like.
- **Nothing found:** if a query returns no suitable articles, the user sees an apology with an explanation and can write to support. I also see all queries that returned nothing, so I can study them.
- **Test mode** for myself, to check the whole system, updates and correct behaviour.

## Step 3 — Choosing the AI model

The model has to analyse articles by their abstracts, give relevance scores and filter out unsuitable articles. Different models differ in speed by fractions of a second, so accuracy is the priority. The model must process a large amount of text quickly: roughly up to 1,000 user searches a day, which is 4,000 to 20,000 requests to the model.

**Candidates via Groq (free).** All three have the same free-tier limits: 1,000 requests per day, 8,000 tokens per minute, 200,000 tokens per day, 30 requests per minute.

- gpt-oss-120b
- gpt-oss-20b
- Qwen3.8 27B

With 200,000 tokens per day, Groq can handle about 25–30 searches a day, which is not enough for public use. So the free tier is used only for testing and choosing the model; public use would go through OpenRouter. This estimate was made for the first version, where one search used about 8,000 tokens. After the instructions for the AI became more detailed, a search uses about 13,000 tokens, so the free limit covers about 15 searches a day.

**Candidates via OpenRouter (paid):**

| Model | Input price | Output price | Speed | Time to first answer | Cost per 1,000 user searches |
|---|---|---|---|---|---|
| gpt-oss-120b | $0.03 per million tokens | $0.15 per million tokens | 801 tokens/s (fastest) | 186 ms | $0.5–1.0 |
| gpt-oss-20b | $0.018 per million tokens | $0.09 per million tokens | 410 tokens/s | 227 ms | about $0.3 |
| Qwen3.8 27B | $0.02 per million tokens | $0.50 per million tokens | 609 tokens/s | 240 ms | about $0.7 |

Limits and prices checked on 24.10.2026: [Groq rate limits](https://console.groq.com/docs/rate-limits), [OpenRouter](https://openrouter.ai/discover).

**How the models are tested.** Each model scores the same 20 articles per query, and its answers are compared with my own table. Accuracy is the share of matches with my evaluation. During testing I found a fourth criterion, **stability**: whether the model gives the same answer to the same input. The order of comparison is: accuracy, then stability, then speed and price.

**Common evaluation criteria:**

- **Yes:** the abstract is clearly connected to the query. The main idea of the query is covered, even if smaller parts of the query are not.
- **Unclear:** the connection is indirect. The link to the main idea is unclear or more general; small details of the query would raise the relevance, but even without them the article goes to Unclear.
- **No:** no direct connection to the main idea of the query. There may be links to smaller parts of the query, but not to the main one. These articles are hidden from the user.

**Limitations of the testing:**

- **Subjectivity.** Model accuracy is measured against my own evaluation. I am a high-school student, not an expert in writing papers or in the topics I evaluate, so I cannot guarantee that my answers are fully objective.
- **AI rules.** The model split the query into parts and treated them as equal, although often they are not. For my query “Training a neural network on board games”, a paper about training neural networks (even not on board games) is more useful to me than any paper about board games. *Solution:* in the second version of the instructions for the AI (29.10.2026) the query is split into a main part, a secondary part and details. Without the main part an article gets 1–3.9; with the main part but not the secondary one, 4–7.4; with both, 7.5–10.
- **Missing abstracts.** The models do not always have the abstract, so some potentially useful articles are lost. This happens because OpenAlex itself has no abstract for them. In the first test, article #10 had no abstract, so the models put it in “No”, while I rated it “Yes”. *Solved in the second version of the platform* (see improvement 3 below).
- **One evaluator.** I could not involve a second evaluator, which affects objectivity, so I use a repeated evaluation of the same articles after some time.
- **Duplicates in OpenAlex.** One query can return several copies of the same article because it was uploaded to the database several times.

**How to reduce these limitations:**

1. Create common criteria for evaluating articles: clear requirements for each category, but flexible enough for the model to judge articles that do not fit any criterion exactly.
2. Re-evaluate the same 60 articles blindly a week later, without looking at my previous answers, to measure the stability of my own judgement. *Planned for early November 2026.*
3. If the model has no abstract, skip the article and replace it with the next one, so the number of analysed articles stays the same. This does not give the model access to missing abstracts, but it keeps the number of analysed articles and gives a chance that the new article is useful. *Implemented in version 2 (29.10.2026).*
4. Remove copies of the same article from the results and still analyse 20 articles, to maximise the chance of getting useful ones. *Implemented in version 2 (29.10.2026): only one copy of identical articles is kept.*

## Step 4 — Development and testing

- **Version 0 (June 2026):** the first prototype (Semantic Scholar + OpenAlex + Groq, Research Fit Score, Credibility Score, Deep Analysis, APA/BibTeX export). Its code is kept in [`legacy/prototype-june-2026`](../legacy/prototype-june-2026). The history is described in the [development diary](dev-diary.md#background-may--september-2026).
- **Version 1 (24–25.10.2026):** a working prototype without design: search in OpenAlex, AI scoring, filters, projects and test mode. The first bug found: OpenAlex returned error 400 for queries containing “?”; fixed by cleaning the query.
- **Model choice (26–29.10.2026):** three models were tested on 60 articles that I evaluated by hand. gpt-oss-20b was chosen: it has the best accuracy, the least junk and the highest speed (details in [Appendix B](#appendix-b--model-comparison-9-tests)).
- **Version 2 (29.10.2026):** one model left, gpt-oss-20b. New instructions for the AI split the query into main part, secondary part and details, and determine the type of work (review, study, method or theory). Added: removal of duplicate articles, replacement of articles without an abstract, Google-style typo correction with a “Search exactly…” link, a “Check 20 more articles” button (up to 100 articles per query), projects stored in the browser, a support form and an admin page.
- **Versions 3–4 (30.10.2026):** a new interface in the style of a library card catalogue: a stamp with the score on every article, a “Focus” slider to filter by score, a strip showing every article read, a dark theme and a mobile version.
- **Functional test (30.10.2026):** 34 checks of all features ([Appendix C](#appendix-c--functional-test-of-the-platform)). Two bugs were found and fixed. First, the “Save” menu closed right after a project was chosen. Second, Groq rejected a request with error 413 when a batch of articles with long abstracts exceeded the limit of 8,000 tokens per minute. Now long abstracts are shortened to 2,500 characters, the model's answer length is capped, batches are built by text size, and a request that is still too large is automatically split in half.

## Results

- **Speed: the hypothesis is confirmed.** Going through 20 articles by hand took me 40 to 70 minutes; the platform scores 20 articles in about 5.5 seconds (median for gpt-oss-20b).
- **Accuracy: the hypothesis is not confirmed yet.** The target was 80% strict and 90% soft accuracy; the chosen model reached 71.7% and 80%. For comparison, Google Scholar on my main query had 15% strict and 40% soft accuracy, but that was a different set of articles, so the comparison is approximate. Accuracy was measured with the first version of the instructions for the AI; the second version still needs to be tested on the same 60 articles.
- **Next steps:** the blind re-evaluation of the 60 articles, testing the accuracy of the second version of the instructions, publishing the platform online, and testing it with real users.

### Model comparison summary

| | gpt-oss-120b | gpt-oss-20b | qwen3.8-27b | Best |
|---|---|---|---|---|
| Strict accuracy (average) | 61.7% | **71.7%** | 68.3% | gpt-oss-20b |
| Soft accuracy (average) | 68.3% | **80%** | 75% | gpt-oss-20b |
| Junk shown (total) | 12 | **4** | 10 | gpt-oss-20b |
| Useful articles missed (total) | 7 | 8 | **5** | qwen3.8-27b |
| Stability (same category in 5 runs) | 52/60 (87%), 4 dangerous changes | 55/60 (92%), 4 dangerous changes | **59/60 (98%)**, 0 dangerous changes | qwen3.8-27b |
| Speed (median) | 7.1 s | **5.5 s** | 56.9 s | gpt-oss-20b |

*Dangerous change:* a change from Yes or Unclear to No between runs; such changes hide potentially useful articles.

gpt-oss-20b leads in accuracy, junk and speed. Since accuracy is the top priority, it is the logical choice, and its stability is good enough for the platform.

## Appendix A — Google Scholar baseline (20 articles)

Query: “Training a neural network on board games”. Source: Google Scholar. My answers are based only on the titles and abstracts. Result: 3 fit, 5 partly fit, 12 do not fit (strict accuracy 15%, soft accuracy 40%).

| # | Article | Fits the query? | Reason |
|---|---|---|---|
| 1 | PyTAG: Challenges and Opportunities for Reinforcement Learning in Tabletop Games | Yes | Described methods of learning of AI based on 20 different modern board games, exactly suits my query |
| 2 | Reinforcement Learning in Strategy-Based and Atari Games: A Review of Google DeepMinds Innovations | Yes | Described main AI’s such as AlphaGo, AlphaGo Zero, MuZero, based on strategic games. Not only on Atari games. |
| 3 | Reinforcement learning applied to games | Unclear | Because it is too generalized, types of games are not clear, just names “games”. But suits about learning of neural network. |
| 4 | A Survey of Planning and Learning in Games | Unclear | Not only about board games. Video games are included and too generalized about learning of AI |
| 5 | Deep Reinforcement Learning: An Overview | Unclear | Very good about deep learning and based on board games, but too generalized too and focuses on many other fields, such as text and video generation. |
| 6 | Applications of Artificial Neural Networks in Games | Yes | Talks not only about games in general: focuses on board games and on one field, how AI is used to create opponents in these games. |
| 7 | Neuroevolution in Games: State of the Art and Open Challenges | Unclear | Not training on board games exactly |
| 8 | EXAMPLES AS INTERACTION: ON HUMANS TEACHING A COMPUTER TO PLAY A GAME | Unclear | Focuses on 1 experiment, board strategic game and restrictions of training. Says only about computer, not neural networks. |
| 9 | Neuroevolution in Deep Neural Networks: Current Trends and Future Challenges | No | Not about training AI and neural systems. More about their evolution in many spheres. |
| 10 | Artificial Intelligence and Deep Learning in Video Games | No | Focuses on video games only, says about its future and about its application in other fields. |
| 11 | Embracing Change: Continual Learning in Deep Neural Networks | No | Not about board games, only continual learning based more about biological processes. |
| 12 | Fundamentals of Neural Networks | No | It’s too generalized. No words about board games. Less information about exactly learning. |
| 13 | Deep neural networks in psychiatry | No | Focuses on application of neural networks, no words about its learning only general information |
| 14 | A Brief History of AI: How to Prevent Another Winter | No | Not about theme |
| 15 | Chess and the human brain- Demystifying the therapeutic value of a board game | No | About psychology and neuropsychology and chess, no connection to neural networks and learning |
| 16 | Machine learning: applications of artificial intelligence to imaging and diagnosis | No | More about application of neural networks, not about training them |
| 17 | Special series on “effects of board games on health education and promotion” board games as a promising tool for health promotion: a review of recent literature | No | About health and medicine |
| 18 | Overview of Deep Learning in Gastrointestinal Endoscopy | No | Not about ML |
| 19 | Can Traditional Board Games Prevent or Slow Down Cognitive Impairment? A Systematic Review and Meta-Analysis | No | Not about neural networks in terms of ML |
| 20 | AI-DRIVEN OPTIMIZATION IN ROBOTIC PROCESS AUTOMATION: IMPLEMENTING NEURAL NETWORKS FOR REAL-TIME IMPERFECTION PREDICTION | No | Not about ML |
## Appendix B — Model comparison (9 tests)

All tests were run through Groq on the same three queries, using only free (open-access) articles:

1. “Training a neural network on board games” — my main query.
2. “The use of nanotechnology in medicine” — a query from another field.
3. “To what extent does the use of AI affect the quality of education for children under the age of 13?” — a narrow query.

**How the comparison works.** I evaluated all 60 articles myself (Yes / Unclear / No) and compared each model's answer with mine. *Strict accuracy* counts only exact matches. *Soft accuracy* also accepts Yes ↔ Unclear, because the platform shows both categories; Unclear ↔ No is not accepted, because an article scored No is hidden from the user and a potentially useful article is lost. *Junk shown* = articles I rated No that the model showed. *Useful articles missed* = articles I rated Yes or Unclear that the model hid. If accuracy is equal, models are compared by stability, then by speed and cost.

### How many articles each model approved

The model's own approval rate (not accuracy): the share of the first 20 articles it scored 7.5+ (strict) or 4.0+ (soft). The last column is my own evaluation.

| Query | gpt-oss-120b | gpt-oss-20b | qwen3.8-27b | My evaluation |
|---|---|---|---|---|
| Board games | 10 fit (10 scored 7.5+). 50% strict and soft. 5.9 s, 8,091 tokens | 10 fit (10 scored 7.5+). 50% strict and soft. 5.1 s, 8,052 tokens | 11 fit (10 scored 7.5+, 1 scored 4.0–7.4). 50% strict, 55% soft. 14.4 s, 8,062 tokens | 14 fit (11 Yes, 3 Unclear). About 2 minutes per article, about 40 minutes in total |
| Nanotechnology | 18 fit (17 + 1). 85% strict, 90% soft. 12.4 s, 7,911 tokens | 18 fit (17 + 1). 85% strict, 90% soft. 6.5 s, 8,001 tokens | 18 fit (16 + 2). 80% strict, 90% soft. 15.4 s, 8,082 tokens | 18 fit (17 Yes, 1 Unclear). About 2.5 minutes per article, about 50 minutes in total |
| AI in education | 11 fit (1 + 10). 5% strict, 55% soft. 6.6 s, 7,492 tokens | 4 fit (1 + 3). 5% strict, 20% soft. 44.2 s, 7,153 tokens | 13 fit (3 + 10). 15% strict, 65% soft. 21.5 s, 7,338 tokens | 4 fit (0 Yes, 4 Unclear). About 3.5 minutes per article, about 70 minutes in total |

### Accuracy against my evaluation

| Query | gpt-oss-120b | gpt-oss-20b | qwen3.8-27b |
|---|---|---|---|
| Board games | strict 70%, soft 80%, junk 0, missed 4 | strict 70%, soft 80%, junk 0, missed 4 | strict 75%, soft 85%, junk 0, missed 3 |
| Nanotechnology | strict 80%, soft 90%, junk 1, missed 1 | strict 75%, soft 90%, junk 1, missed 1 | strict 90%, soft 90%, junk 1, missed 1 |
| AI in education | strict 35%, soft 35%, junk 11, missed 2 | strict 70%, soft 70%, junk 3, missed 3 | strict 40%, soft 50%, junk 9, missed 1 |
| **Average** | **strict 61.7%, soft 68.3%, junk 12, missed 7** | **strict 71.7%, soft 80%, junk 4, missed 8** | **strict 68.3%, soft 75%, junk 10, missed 5** |

**Stability** was measured with a script: each model scored each query 5 times. A change is “dangerous” when an article moves from Yes or Unclear to No, because a potentially useful article becomes hidden.

### Detailed results of each test

### Test 1. Query: “Training a neural network on board games”, model: gpt-oss-120b

Run: 2026-10-27 14:56

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | A domain-specific supercomputer for training deep neural networks | No | No | 100% |
| 2 | AlphaViT: a flexible game-playing AI for multiple games and variable board sizes | Yes | Yes | 100% |
| 3 | AlphaZero Neural Scaling and Zipf's Law: a Tale of Board Games and Power Laws | Unclear | Yes | 50% |
| 4 | An fMRI Study of the Impact of Block Building and Board Games on Spatial Ability | No | No | 100% |
| 5 | Applications of neural networks in Computer Go | Yes | Yes | 100% |
| 6 | Biasing MCTS with Features for General Games | Yes | No | 0% |
| 7 | Cognitive training with modern board and card games in healthy older adults: two randomized controlled trials | No | No | 100% |
| 8 | Design and Training of Memristor-Based Neural Networks | Unclear | No | 0% |
| 9 | Designing an Artificial Neural Network for state evaluation in Arimaa : Using a Convolutional Neural Network | Yes | Yes | 100% |
| 10 | Efficiently Training Neural Networks for Imperfect Information Games by Sampling Information Sets | Yes | No | 0% |
| 11 | Evolving and training of Neural Network to Play DAMA Board Game Using NEAT Algorithm | Yes | Yes | 100% |
| 12 | Generation of Sokoban Stages using Recurrent Neural Networks | Yes | Unclear | 50% |
| 13 | Special series on “effects of board games on health education and promotion” board games as a promising tool for health promotion: a review of recent literature | No | No | 100% |
| 14 | Temporal Difference Learning for the Game Tic-Tac-Toe 3D: Applying Structure to Neural Networks | Yes | Yes | 100% |
| 15 | Train on Small, Play the Large: Scaling Up Board Games with AlphaZero and GNN | Yes | Yes | 100% |
| 16 | Training a Back-Propagation Network with Temporal Difference Learning and a database for the board game Pente | Yes | Yes | 100% |
| 17 | Training Artificial Neural Networks Using a Global Optimization Method That Utilizes Neural Networks | Unclear | No | 0% |
| 18 | Training Deep Convolutional Neural Networks to Play Go | Yes | Yes | 100% |
| 19 | Training Generative Adversarial Networks via Stochastic Nash Games | No | No | 100% |
| 20 | Training Spiking Neural Networks Using Lessons From Deep Learning | No | No | 100% |

Strict accuracy: 70% (14 matches). Soft accuracy: 80% (16 accepted). Junk shown: 0. Useful articles missed: 4 (#6, #8, #10, #17). Article #10 has no abstract in OpenAlex, so the model could not evaluate it; this is counted as a platform error with 0% match.

### Test 2. Query: “Training a neural network on board games”, model: gpt-oss-20b

Run: 2026-10-27 14:31

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | A domain-specific supercomputer for training deep neural networks | No | No | 100% |
| 2 | AlphaViT: a flexible game-playing AI for multiple games and variable board sizes | Yes | Yes | 100% |
| 3 | AlphaZero Neural Scaling and Zipf's Law: a Tale of Board Games and Power Laws | Unclear | Yes | 50% |
| 4 | An fMRI Study of the Impact of Block Building and Board Games on Spatial Ability | No | No | 100% |
| 5 | Applications of neural networks in Computer Go | Yes | Yes | 100% |
| 6 | Biasing MCTS with Features for General Games | Yes | No | 0% |
| 7 | Cognitive training with modern board and card games in healthy older adults: two randomized controlled trials | No | No | 100% |
| 8 | Design and Training of Memristor-Based Neural Networks | Unclear | No | 0% |
| 9 | Designing an Artificial Neural Network for state evaluation in Arimaa : Using a Convolutional Neural Network | Yes | Yes | 100% |
| 10 | Efficiently Training Neural Networks for Imperfect Information Games by Sampling Information Sets | Yes | No | 0% |
| 11 | Evolving and training of Neural Network to Play DAMA Board Game Using NEAT Algorithm | Yes | Yes | 100% |
| 12 | Generation of Sokoban Stages using Recurrent Neural Networks | Yes | Unclear | 50% |
| 13 | Special series on “effects of board games on health education and promotion” board games as a promising tool for health promotion: a review of recent literature | No | No | 100% |
| 14 | Temporal Difference Learning for the Game Tic-Tac-Toe 3D: Applying Structure to Neural Networks | Yes | Yes | 100% |
| 15 | Train on Small, Play the Large: Scaling Up Board Games with AlphaZero and GNN | Yes | Yes | 100% |
| 16 | Training a Back-Propagation Network with Temporal Difference Learning and a database for the board game Pente | Yes | Yes | 100% |
| 17 | Training Artificial Neural Networks Using a Global Optimization Method That Utilizes Neural Networks | Unclear | No | 0% |
| 18 | Training Deep Convolutional Neural Networks to Play Go | Yes | Yes | 100% |
| 19 | Training Generative Adversarial Networks via Stochastic Nash Games | No | No | 100% |
| 20 | Training Spiking Neural Networks Using Lessons From Deep Learning | No | No | 100% |

Strict accuracy: 70% (14 matches). Soft accuracy: 80% (16 accepted). Junk shown: 0. Useful articles missed: 4 (#6, #8, #10, #17). Article #10 has no abstract in OpenAlex (counted as 0% match). The answers of gpt-oss-20b and gpt-oss-120b on this query were identical.

### Test 3. Query: “Training a neural network on board games”, model: qwen3.8-27b

Run: 2026-10-26 14:14

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | A domain-specific supercomputer for training deep neural networks | No | No | 100% |
| 2 | AlphaViT: a flexible game-playing AI for multiple games and variable board sizes | Yes | Yes | 100% |
| 3 | AlphaZero Neural Scaling and Zipf's Law: a Tale of Board Games and Power Laws | Unclear | Yes | 50% |
| 4 | An fMRI Study of the Impact of Block Building and Board Games on Spatial Ability | No | No | 100% |
| 5 | Applications of neural networks in Computer Go | Yes | Yes | 100% |
| 6 | Biasing MCTS with Features for General Games | Yes | Unclear | 50% |
| 7 | Cognitive training with modern board and card games in healthy older adults: two randomized controlled trials | No | No | 100% |
| 8 | Design and Training of Memristor-Based Neural Networks | Unclear | No | 0% |
| 9 | Designing an Artificial Neural Network for state evaluation in Arimaa : Using a Convolutional Neural Network | Yes | Yes | 100% |
| 10 | Efficiently Training Neural Networks for Imperfect Information Games by Sampling Information Sets | Yes | No | 0% |
| 11 | Evolving and training of Neural Network to Play DAMA Board Game Using NEAT Algorithm | Yes | Yes | 100% |
| 12 | Generation of Sokoban Stages using Recurrent Neural Networks | Yes | Yes | 100% |
| 13 | Special series on “effects of board games on health education and promotion” board games as a promising tool for health promotion: a review of recent literature | No | No | 100% |
| 14 | Temporal Difference Learning for the Game Tic-Tac-Toe 3D: Applying Structure to Neural Networks | Yes | Yes | 100% |
| 15 | Train on Small, Play the Large: Scaling Up Board Games with AlphaZero and GNN | Yes | Yes | 100% |
| 16 | Training a Back-Propagation Network with Temporal Difference Learning and a database for the board game Pente | Yes | Yes | 100% |
| 17 | Training Artificial Neural Networks Using a Global Optimization Method That Utilizes Neural Networks | Unclear | No | 0% |
| 18 | Training Deep Convolutional Neural Networks to Play Go | Yes | Yes | 100% |
| 19 | Training Generative Adversarial Networks via Stochastic Nash Games | No | No | 100% |
| 20 | Training Spiking Neural Networks Using Lessons From Deep Learning | No | No | 100% |

Strict accuracy: 75% (15 matches). Soft accuracy: 85% (17 accepted). Junk shown: 0. Useful articles missed: 3 (#8, #10, #17). Article #10 has no abstract in OpenAlex (counted as 0% match).

### Test 4. Query: “The use of nanotechnology in medicine”, model: gpt-oss-120b

Run: 2026-10-27 15:23

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | Aspects of the use of nanotechnology and nanomedicine in medicine | Yes | Yes | 100% |
| 2 | Biotechnology, nanotechnology and medicine | Yes | Yes | 100% |
| 3 | Emerging Applications of Nanotechnology in Healthcare and Medicine | Yes | Yes | 100% |
| 4 | Food is Medicine: Next Steps Towards Feeding the World Using Nanotechnology Law | No | No | 100% |
| 5 | Integrating Artificial Intelligence and Nanotechnology for Precision Cancer Medicine | Yes | Yes | 100% |
| 6 | Nanomedicine, nanotechnology in medicine | Yes | Yes | 100% |
| 7 | Nanotechnology and its use in imaging and drug delivery (Review) | Yes | Yes | 100% |
| 8 | Nanotechnology in regenerative medicine: the materials side | Yes | No | 0% |
| 9 | NANOTECHNOLOGY USE IN MEDICINE | Yes | Yes | 100% |
| 10 | Nanotechnology- future prospect in recent medicine: a review | Yes | Yes | 100% |
| 11 | Nanotechnology: emerging tools for biology and medicine | Yes | Yes | 100% |
| 12 | New Zealander Reactions to the use of Biotechnology and Nanotechnology in Medicine, Farming and Food | No | Yes | 0% |
| 13 | Old Antibiotics Can Learn New Ways: A Systematic Review of Florfenicol Use in Veterinary Medicine and Future Perspectives Using Nanotechnology | Unclear | Yes | 50% |
| 14 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 15 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 16 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 17 | The Promise of Nanotechnology in Personalized Medicine | Yes | Yes | 100% |
| 18 | THE USE OF NANOTECHNOLOGY IN MEDICINE | Yes | Yes | 100% |
| 19 | Use Areas of Nanotechnology in Veterinary Medicine | Yes | Unclear | 50% |
| 20 | USE OF NANOTECHNOLOGIES AND NANOPARTICLES IN MEDICINE | Yes | Yes | 100% |

Strict accuracy: 80% (16 matches). Soft accuracy: 90% (18 accepted). Junk shown: 1 (#12). Useful articles missed: 1 (#8, no abstract in OpenAlex). Articles #14, #15 and #16 are the same paper uploaded to OpenAlex three times.

### Test 5. Query: “The use of nanotechnology in medicine”, model: gpt-oss-20b

Run: 2026-10-27 15:36

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | Aspects of the use of nanotechnology and nanomedicine in medicine | Yes | Yes | 100% |
| 2 | Biotechnology, nanotechnology and medicine | Yes | Yes | 100% |
| 3 | Emerging Applications of Nanotechnology in Healthcare and Medicine | Yes | Unclear | 50% |
| 4 | Food is Medicine: Next Steps Towards Feeding the World Using Nanotechnology Law | No | No | 100% |
| 5 | Integrating Artificial Intelligence and Nanotechnology for Precision Cancer Medicine | Yes | Yes | 100% |
| 6 | Nanomedicine, nanotechnology in medicine | Yes | Unclear | 50% |
| 7 | Nanotechnology and its use in imaging and drug delivery (Review) | Yes | Yes | 100% |
| 8 | Nanotechnology in regenerative medicine: the materials side | Yes | No | 0% |
| 9 | NANOTECHNOLOGY USE IN MEDICINE | Yes | Yes | 100% |
| 10 | Nanotechnology- future prospect in recent medicine: a review | Yes | Yes | 100% |
| 11 | Nanotechnology: emerging tools for biology and medicine | Yes | Yes | 100% |
| 12 | New Zealander Reactions to the use of Biotechnology and Nanotechnology in Medicine, Farming and Food | No | Yes | 0% |
| 13 | Old Antibiotics Can Learn New Ways: A Systematic Review of Florfenicol Use in Veterinary Medicine and Future Perspectives Using Nanotechnology | Unclear | Yes | 50% |
| 14 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 15 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 16 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 17 | The Promise of Nanotechnology in Personalized Medicine | Yes | Yes | 100% |
| 18 | THE USE OF NANOTECHNOLOGY IN MEDICINE | Yes | Yes | 100% |
| 19 | Use Areas of Nanotechnology in Veterinary Medicine | Yes | Yes | 100% |
| 20 | USE OF NANOTECHNOLOGIES AND NANOPARTICLES IN MEDICINE | Yes | Yes | 100% |

Strict accuracy: 75% (15 matches). Soft accuracy: 90% (18 accepted). Junk shown: 1 (#12). Useful articles missed: 1 (#8, no abstract in OpenAlex).

### Test 6. Query: “The use of nanotechnology in medicine”, model: qwen3.8-27b

Run: 2026-10-27 15:47

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | Aspects of the use of nanotechnology and nanomedicine in medicine | Yes | Yes | 100% |
| 2 | Biotechnology, nanotechnology and medicine | Yes | Yes | 100% |
| 3 | Emerging Applications of Nanotechnology in Healthcare and Medicine | Yes | Yes | 100% |
| 4 | Food is Medicine: Next Steps Towards Feeding the World Using Nanotechnology Law | No | No | 100% |
| 5 | Integrating Artificial Intelligence and Nanotechnology for Precision Cancer Medicine | Yes | Yes | 100% |
| 6 | Nanomedicine, nanotechnology in medicine | Yes | Yes | 100% |
| 7 | Nanotechnology and its use in imaging and drug delivery (Review) | Yes | Yes | 100% |
| 8 | Nanotechnology in regenerative medicine: the materials side | Yes | No | 0% |
| 9 | NANOTECHNOLOGY USE IN MEDICINE | Yes | Yes | 100% |
| 10 | Nanotechnology- future prospect in recent medicine: a review | Yes | Yes | 100% |
| 11 | Nanotechnology: emerging tools for biology and medicine | Yes | Yes | 100% |
| 12 | New Zealander Reactions to the use of Biotechnology and Nanotechnology in Medicine, Farming and Food | No | Unclear | 0% |
| 13 | Old Antibiotics Can Learn New Ways: A Systematic Review of Florfenicol Use in Veterinary Medicine and Future Perspectives Using Nanotechnology | Unclear | Unclear | 100% |
| 14 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 15 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 16 | Targeting miRNA-based medicines to cystic fibrosis airway epithelial cells using nanotechnology | Yes | Yes | 100% |
| 17 | The Promise of Nanotechnology in Personalized Medicine | Yes | Yes | 100% |
| 18 | THE USE OF NANOTECHNOLOGY IN MEDICINE | Yes | Yes | 100% |
| 19 | Use Areas of Nanotechnology in Veterinary Medicine | Yes | Yes | 100% |
| 20 | USE OF NANOTECHNOLOGIES AND NANOPARTICLES IN MEDICINE | Yes | Yes | 100% |

Strict accuracy: 90% (18 matches). Soft accuracy: 90% (18 accepted). Junk shown: 1 (#12). Useful articles missed: 1 (#8, no abstract in OpenAlex).

### Test 7. Query: “To what extent does the use of AI affect the quality of education for children under the age of 13?”, model: gpt-oss-120b

Run: 2026-10-28 20:47

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | A Review of Artificial Intelligence (AI) in Education from 2010 to 2020 | No | Unclear | 0% |
| 2 | AI in Education for Sustainable Development: A Comprehensive Framework for Equitable and Quality Learning | No | Unclear | 0% |
| 3 | AI in education: learner choice and fundamental rights | No | Unclear | 0% |
| 4 | Assessment and Evaluation in STEM Education in the Age of AI | No | Unclear | 0% |
| 5 | Could the Use of AI in Higher Education Hinder Students With Disabilities? A Scoping Review | No | No | 100% |
| 6 | Does Use of AI Affect the Creativity of Secondary School Children? | Unclear | No | 0% |
| 7 | Ethics of AI in Education: Towards a Community-Wide Framework | No | Unclear | 0% |
| 8 | Exploring the Impact of Generative AI ChatGPT on Critical Thinking in Higher Education: Passive AI-Directed Use or Human–AI Supported Collaboration? | Unclear | No | 0% |
| 9 | Fostering AI Literacy in Elementary Science, Technology, Engineering, Art, and Mathematics (STEAM) Education in the Age of Generative AI | No | Yes | 0% |
| 10 | Generative AI in Higher Education | No | No | 100% |
| 11 | Historical threads, missing links, and future directions in AI in education | No | Unclear | 0% |
| 12 | Navigating Education in the Age of Generative AI | No | Unclear | 0% |
| 13 | Revolutionizing education with AI: Exploring the transformative potential of ChatGPT | No | Unclear | 0% |
| 14 | The ethics of using AI in K-12 education: a systematic literature review | No | Unclear | 0% |
| 15 | The impacts of screen and AI use on children and young people | Unclear | Unclear | 100% |
| 16 | The role and challenges of education for responsible AI | No | Unclear | 0% |
| 17 | Using AI to Support Education for Collective Intelligence | No | No | 100% |
| 18 | What do I not know? How does AI affect critical thinking? | No | No | 100% |
| 19 | What if the devil is my guardian angel: ChatGPT as a case study of using chatbots in education | Unclear | Unclear | 100% |
| 20 | What Work Does Generative AI Do? | No | No | 100% |

Strict accuracy: 35% (7 matches). Soft accuracy: 35% (7 accepted). Junk shown: 11 (#1, 2, 3, 4, 7, 9, 11, 12, 13, 14, 16). Useful articles missed: 2 (#6, #8).

### Test 8. Query: “To what extent does the use of AI affect the quality of education for children under the age of 13?”, model: gpt-oss-20b

Run: 2026-10-28 20:57

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | A Review of Artificial Intelligence (AI) in Education from 2010 to 2020 | No | No | 100% |
| 2 | AI in Education for Sustainable Development: A Comprehensive Framework for Equitable and Quality Learning | No | Unclear | 0% |
| 3 | AI in education: learner choice and fundamental rights | No | No | 100% |
| 4 | Assessment and Evaluation in STEM Education in the Age of AI | No | Unclear | 0% |
| 5 | Could the Use of AI in Higher Education Hinder Students With Disabilities? A Scoping Review | No | No | 100% |
| 6 | Does Use of AI Affect the Creativity of Secondary School Children? | Unclear | No | 0% |
| 7 | Ethics of AI in Education: Towards a Community-Wide Framework | No | No | 100% |
| 8 | Exploring the Impact of Generative AI ChatGPT on Critical Thinking in Higher Education: Passive AI-Directed Use or Human–AI Supported Collaboration? | Unclear | No | 0% |
| 9 | Fostering AI Literacy in Elementary Science, Technology, Engineering, Art, and Mathematics (STEAM) Education in the Age of Generative AI | No | Unclear | 0% |
| 10 | Generative AI in Higher Education | No | No | 100% |
| 11 | Historical threads, missing links, and future directions in AI in education | No | No | 100% |
| 12 | Navigating Education in the Age of Generative AI | No | No | 100% |
| 13 | Revolutionizing education with AI: Exploring the transformative potential of ChatGPT | No | No | 100% |
| 14 | The ethics of using AI in K-12 education: a systematic literature review | No | No | 100% |
| 15 | The impacts of screen and AI use on children and young people | Unclear | Unclear | 100% |
| 16 | The role and challenges of education for responsible AI | No | No | 100% |
| 17 | Using AI to Support Education for Collective Intelligence | No | No | 100% |
| 18 | What do I not know? How does AI affect critical thinking? | No | No | 100% |
| 19 | What if the devil is my guardian angel: ChatGPT as a case study of using chatbots in education | Unclear | No | 0% |
| 20 | What Work Does Generative AI Do? | No | No | 100% |

Strict accuracy: 70% (14 matches). Soft accuracy: 70% (14 accepted). Junk shown: 3 (#2, 4, 9). Useful articles missed: 3 (#6, 8, 19).

### Test 9. Query: “To what extent does the use of AI affect the quality of education for children under the age of 13?”, model: qwen3.8-27b

Run: 2026-10-28 21:02

| # | Article | My answer | Model's answer | Match |
|---|---|---|---|---|
| 1 | A Review of Artificial Intelligence (AI) in Education from 2010 to 2020 | No | Unclear | 0% |
| 2 | AI in Education for Sustainable Development: A Comprehensive Framework for Equitable and Quality Learning | No | Unclear | 0% |
| 3 | AI in education: learner choice and fundamental rights | No | No | 100% |
| 4 | Assessment and Evaluation in STEM Education in the Age of AI | No | Unclear | 0% |
| 5 | Could the Use of AI in Higher Education Hinder Students With Disabilities? A Scoping Review | No | No | 100% |
| 6 | Does Use of AI Affect the Creativity of Secondary School Children? | Unclear | Yes | 50% |
| 7 | Ethics of AI in Education: Towards a Community-Wide Framework | No | Unclear | 0% |
| 8 | Exploring the Impact of Generative AI ChatGPT on Critical Thinking in Higher Education: Passive AI-Directed Use or Human–AI Supported Collaboration? | Unclear | No | 0% |
| 9 | Fostering AI Literacy in Elementary Science, Technology, Engineering, Art, and Mathematics (STEAM) Education in the Age of Generative AI | No | Yes | 0% |
| 10 | Generative AI in Higher Education | No | No | 100% |
| 11 | Historical threads, missing links, and future directions in AI in education | No | No | 100% |
| 12 | Navigating Education in the Age of Generative AI | No | Unclear | 0% |
| 13 | Revolutionizing education with AI: Exploring the transformative potential of ChatGPT | No | Unclear | 0% |
| 14 | The ethics of using AI in K-12 education: a systematic literature review | No | Unclear | 0% |
| 15 | The impacts of screen and AI use on children and young people | Unclear | Yes | 50% |
| 16 | The role and challenges of education for responsible AI | No | Unclear | 0% |
| 17 | Using AI to Support Education for Collective Intelligence | No | No | 100% |
| 18 | What do I not know? How does AI affect critical thinking? | No | No | 100% |
| 19 | What if the devil is my guardian angel: ChatGPT as a case study of using chatbots in education | Unclear | Unclear | 100% |
| 20 | What Work Does Generative AI Do? | No | No | 100% |

Strict accuracy: 40% (8 matches). Soft accuracy: 50% (10 accepted). Junk shown: 9 (#1, 2, 4, 7, 9, 12, 13, 14, 16). Useful articles missed: 1 (#8).

## Appendix C — Functional test of the platform

Date: 30.10.2026, version 4. Most checks were run as an automated click-through in a test environment where the responses of the AI and OpenAlex were replaced by real articles and scores saved from earlier searches. Checks 3, 6, 33 and 34 were confirmed with live searches.

### Search

| # | Action | Expected | Result | Status |
|---|---|---|---|---|
| 1 | Normal query in English | Articles with score marks and a “fit / partly / hidden” strip | 11 articles with score stamps (in version 4 stamps replaced the score rings); strip of 20 cards: 10 fit, 1 partly, 9 hidden | Works |
| 2 | The same query again | Opens instantly from the cache; no new row in the admin page | Opened in 0.2 s from the cache; no new row in the database (1 before, 1 after) | Works |
| 3 | Query with typos | “Showing results for…” and a “Search exactly…” link | “Showing results for brian's neural signals. Search exactly Brian's nerral signals”. In a live search on 29.10, “Brian's nerral signals” was corrected to “brian's neural signals” and 40 articles were found | Works |
| 4 | Click “Search exactly…” | Search for the original query without correction | Search for “Brian's nerral signals” without correction; no correction notice | Works |
| 5 | Random letters | “OpenAlex did not find any articles” | “OpenAlex did not find any articles for this query” | Works |
| 6 | Query in Russian | The site works; there may be few articles | The site works without errors; results, articles and scores are shown | Works |
| 7 | Query with ? : « » ( ) | No error | Results opened with the title “What is «AI»? (deep: learning)”; no error | Works |
| 8 | Empty query | The form is not submitted | The form was not submitted; the loading screen did not appear | Works |
| 9 | Search with “Show paid articles too” | Some articles are marked “Paid access” | 4 articles marked “Paid access”, 7 marked “Open access”; the summary says “including paid” | Works |

### Results

| # | Action | Expected | Result | Status |
|---|---|---|---|---|
| 10 | Open an abstract | The text expands | The abstract expanded on ruled paper (398 px high); the button switched to “open” | Works |
| 11 | Click an article title | The article page (DOI or OpenAlex) opens in a new tab | doi.org opens in a new tab | Works |
| 12 | “Only fitting” filter | Only green articles remain; the counter changes | Version 4 replaced this filter with the “Focus” slider. At 7.5, 10 of 11 articles remained, all scored 8.0 or higher | Works |
| 13 | Untick a type of work | Articles of this type disappear | All 11 articles were of type “Study”; after unticking, 0 of 11 were shown. Not checked with several types | Works |
| 14 | Years “from / to” and a click on a year bar | Only articles from those years remain; a second click removes the filter | 2015–2020: 4 articles from 2015–2017 remained. Click on 2025: only 2025; a second click brought back all 11 | Works |
| 15 | Topic filter | Only articles with the chosen topic | “Artificial Intelligence in Games”: 10 of 11, all with this topic | Works |
| 16 | “Reset filters” | All articles return | All 11 articles returned | Works |
| 17 | Very narrow query | “No fitting articles” message and support form | “No fitting articles among the first 20” and a “Report that the search did not work” button | Works |
| 18 | “Check 20 more articles” | Articles are added, “Checked 20 more…” message, no duplicates | 11 → 30 articles, 0 duplicates, message “Checked 20 more articles, fitting among them: 19” | Works |
| 19 | “Articles without an abstract” block | Expands; links work | Expanded; the link leads to doi.org | Works |

### Projects

| # | Action | Expected | Result | Status |
|---|---|---|---|---|
| 20 | “Save to project” → create a new one | “Saved to …”; a project counter appears in the menu | “Saved to «Test project»”, the button changed to “Saved”, project counter 1 | Works |
| 21 | Save to an existing project, then click again | First click saves, second click removes | 1st click: “Saved…”, 2nd: “Removed from…”. Bug found and fixed: the menu closed right after a project was chosen | Works |
| 22 | Open the “Projects” page | Articles with score marks; links work | 1 project, 2 articles with stamps; links lead to doi.org | Works |
| 23 | “Remove” an article and “Delete project” | Works; a project is deleted only on the second click | Article removed (2 → 1). The first click on “Delete project” showed “Delete for sure? Click again”; the project was deleted only after the second click | Works |
| 24 | Close and reopen the browser | Projects are still there | After reopening, the project “Closing check” with 1 article was still there | Works |

### Test mode and other

| # | Action | Expected | Result | Status |
|---|---|---|---|---|
| 25 | Wrong password at /test-login | “Wrong password” | “Wrong password” notice; the login page stayed | Works |
| 26 | Correct password, open a search | “Not fitting” articles and a statistics panel are visible | 40 articles visible, 10 of them “Not fitting”; the test-mode panel is shown | Works |
| 27 | “Score again” | New scores, new time in the panel | Time in the panel changed (16:49:46 → 16:50:13); a new search opened | Works |
| 28 | Send a support message | The message appears in the admin page | “Message sent…” notice; the message is visible in the admin page | Works |
| 29 | “Clear history” (2 clicks) | Searches deleted, messages kept | 1st click: “Clear for sure? Click again”, searches untouched (10). 2nd: 0 searches; the support message stayed (1) | Works |
| 30 | Dark theme, reload the page | The theme is remembered | After reloading the theme stayed dark | Works |
| 31 | Open the site on a phone or in a narrow window | Nothing goes past the screen edge; filters collapse | Width 390 px with no sideways scrolling on the home, results, projects and “How it works” pages; filters collapse into a “Filters” button | Works |
| 32 | Non-existent address, e.g. /abc | “No such page” page | Status 404, “No such page” | Works |

### Quality of scoring

| # | Action | Expected | Result | Status |
|---|---|---|---|---|
| 33 | Check 2–3 “Fits” articles by eye | They really fit the query | They really fit the query | Works |
| 34 | Find the “AI could not score” label | No such articles, or very few | Works correctly. Over 32 searches (640 scored articles) the label appeared on 4 articles, all in one search on 29.10 (“brian's neural signals”). One of them had the text “version:NA” in OpenAlex instead of an abstract; the AI did not return the other three in its answer | Works |
