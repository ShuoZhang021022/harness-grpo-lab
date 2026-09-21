# Verification Record

Run from the project root in PowerShell:

~~~powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -q
~~~

Recorded result: 33 tests passed.

## Test coverage

- Exactly 50 initial tools, all 50 interface examples, and boundary checks for arithmetic identities, linear-system residuals, paths, and mutation protection.
- The main-agent input builder exposes only the description and tool catalog, excluding code files, answers, and hidden tests.
- Immediate checking of each new tool; similarity rejection prevents further actions and solver calls, sets final reward to exactly -1, and cleans up temporary execution copies.
- Growth of the reference set after tool acceptance, tool costs, single-file and multi-file tools, and diagnostic tool-call coverage.
- An update only after 100 questions with eight trajectories each; the next batch uses the new policy version. Infrastructure errors are recorded without contributing to an update.
- GRPO group advantages, gradient direction, token masks, detached old probabilities and rewards, clipping, and teacher forcing for all main-agent output tokens.
- One LoRA update after accumulating 800 numerical fixture trajectories, with frozen parameters unchanged. This test uses a tiny tensor policy and is not an LLM training result.
- Dataset counts of 1,000 training and 100 test tasks per domain, totaling 3,300, and a corresponding private verifier record for every public task.
- Per-question statistics, rejection of missing, duplicate, or mixed-policy groups, and rendering of four-system comparison plots. Plotting fixtures are tests, not model scores.

## Dataset checks

- Reference programs for all 1,100 synthetic code-repair tasks agree with the declarative oracle. Every buggy program fails at least one hidden test.
- Routes for all 1,100 synthetic map scenarios pass deterministic replay.
- Math labels remain source-provided references without completed independent verification. The dataset contains 983 AIME questions (883 train and 100 test) and 117 MATH supplements.
- Source revisions, file hashes, filtering rules, and split rules are recorded in dataset_audit/audit.json.
- A prior audit found that 11 of 100 code test tasks match a training program's outputs for all integers from -500 to 500. This finite-range overlap remains unresolved; it is not proof of equivalence over all integer inputs.

## English conversion

The conversion covers project documentation, model prompts, command-line help, generated task text, and the tool-catalog introduction. Core source code, tool descriptions, mathematical questions, test code, answers, and hidden tests were already in English. Conversion checks and hashes are recorded in english_conversion.json.

## Not completed or validated

- Real main-agent autoregressive sampling, external solver and similarity-judge LLM adapters, and an isolated execution backend have not been integrated.
- No actual A100 training, distributed throughput or memory validation, or real end-to-end LLM trajectory collection has occurred.
- The 48,000 training trajectories across both trained systems and the 9,600 four-system test trajectories have not been collected. No real success rates or experimental comparison charts are available.
- Independent math-answer verification, model and resource configuration, solver permissions, and execution budgets remain incomplete.

Successful dataset construction and numerical gradient tests do not establish support for the research hypothesis.
