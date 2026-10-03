# Text model report

Model: hashed word + char 2-4 gram features (D=16384) -> softmax, int8 weights. File: models/model.json (279 KB).

Data: 258 hand-written + 480 Gemini-generated synthetic intent examples (Kiswahili, English, mixed / Sheng / typos) + typo augmentation; 443 real out-of-scope utterances from MASSIVE sw-KE + en-US + 43 hand-written farm near misses (other crops, livestock, antestia) as 'none'.

## Held-out check (the honest number)

Trained on the Gemini examples only, tested on the 258 hand-written ones (different authors, never seen) + 89 unseen MASSIVE messages: answered accuracy 97.7%, coverage 67.8% (right 171, wrong 4, not sure 83), off-topic not answered 100.0%.

## 5-fold cross-validation (threshold 0.86)

- In-scope questions: 738; answered right 388, answered wrong 8, sent to 'not sure' 342
- Accuracy when it answers: 98.0%; coverage: 53.7%
- Out-of-scope messages: 443; correctly not answered 435 (98.2%)

Threshold rule: the lowest confidence that keeps wrong answers <= 3% and answers to off-topic messages <= 5%; below it the farmer gets 'not sure, saved for the extension officer'.

## Per intent (out-of-fold)

| intent | n | right | not sure | wrong |
|---|---|---|---|---|
| leaf_rust | 63 | 46 | 15 | 2 |
| cbd | 62 | 40 | 22 | 0 |
| berry_borer | 61 | 32 | 28 | 1 |
| spray_timing | 61 | 47 | 14 | 0 |
| yield_drop | 62 | 17 | 45 | 0 |
| fertilizer_weeds | 61 | 26 | 35 | 0 |
| pruning | 60 | 24 | 35 | 1 |
| harvest | 60 | 34 | 25 | 1 |
| quality | 60 | 30 | 29 | 1 |
| price | 62 | 32 | 30 | 0 |
| varieties | 59 | 28 | 31 | 0 |
| ask_person | 67 | 32 | 33 | 2 |
| none | 443 | 408 | 27 | 8 |

## Wrong answers above the threshold (out-of-fold)

- "kutoa majani na vijiti" (quality) -> leaf_rust @ 0.99
- "hospitali iko wapi" (none) -> ask_person @ 0.94
- "where can i buy fertilizer" (ask_person) -> fertilizer_weeds @ 0.91
- "Found a tiny black bug on my berries" (berry_borer) -> cbd @ 1.0
- "tea price per kilo" (none) -> price @ 0.96
- "Best spray for leaf rust" (leaf_rust) -> spray_timing @ 0.96
- "where to get copper spray" (ask_person) -> spray_timing @ 1.0
- "How to spray hii kutu?" (leaf_rust) -> spray_timing @ 0.99
- "Kahawa yangu ya zamani haitoi mavuno mazuri" (pruning) -> yield_drop @ 0.98
- "mavuno ya kahawa yanaanza lini" (harvest) -> yield_drop @ 0.93
- "bei ya chai" (none) -> price @ 0.94
- "nyanya zinaoza" (none) -> cbd @ 0.88
- "majani ya chai yana ugonjwa" (none) -> leaf_rust @ 0.97
- "beans have insects" (none) -> berry_borer @ 0.92
- "tea leaves turning yellow" (none) -> leaf_rust @ 0.95
- "get me a person a. s. a. p." (none) -> ask_person @ 0.98

## Limits

- Training questions are synthetic: written by the team, not collected from farmers. Real messages will be messier; the 'not sure' route is the safety net.
- Kiswahili and English only in training. Kikuyu is tested separately (see below) and is expected to do worse.
- Cross-validation on synthetic data overstates real-world accuracy.

## Kikuyu (less-supported language)

- In-scope: 72 Kikuyu messages (Gemini translations of our Kiswahili examples, unverified): right 7, wrong 0, not sure 65 -> answered accuracy 100%, coverage 10%.
- Off-topic: 300 real Kikuyu sentences (FLORES-200): answered by mistake 0 (0.0%).
- The model never saw Kikuyu in training; it only catches words shared with Kiswahili / English (e.g. kahawa / kahũa, loanwords). The safe failure is 'not sure', which sends the question to a person.
- Export check: the int8 model reproduces 4/4 stored predictions.
