# Would a keyword SMS menu do the same job?

Same unseen messages for both. Off-topic rows: every answer is a wrong answer.

| test set | tool | messages | right | WRONG | not answered | of which 'did you mean' offers the right topic |
|---|---|---|---|---|---|---|
| clean | keyword menu | 258 | 192 (74%) | 13 (5%) | 53 (21%) | n/a |
| clean | small model | 258 | 171 (66%) | 4 (2%) | 83 (32%) | 63 (24%) |
| typos | keyword menu | 258 | 106 (41%) | 11 (4%) | 141 (55%) | n/a |
| typos | small model | 258 | 109 (42%) | 1 (0%) | 148 (57%) | 96 (37%) |
| off-topic | keyword menu | 389 | 0 (0%) | 10 (3%) | 379 (97%) | n/a |
| off-topic | small model | 389 | 0 (0%) | 0 (0%) | 389 (100%) | 0 (0%) |

**clean:** right answer directly or in one tap: small model 91% vs keyword menu 74%; wrong answers: 2% vs 5%.

**typos:** right answer directly or in one tap: small model 79% vs keyword menu 41%; wrong answers: 0% vs 4%.

The keyword lists were written with sight of the examples, which favours the keyword menu. The model never
saw the hand-written messages. 'Not answered' is the safe outcome (the question goes to a person);
'wrong' is the costly one (a confident answer about the wrong problem).
