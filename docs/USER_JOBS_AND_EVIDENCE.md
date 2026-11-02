# Who would use codbeing, and what supports it?

Research checked 2026-11-02. This is a design brief, not a product validation study.

## First useful job

A person is about to choose a study plan, a work priority, or another reversible
choice they expect to revisit. They want to remember what they knew and why they
chose, rather than reconstruct a flattering explanation afterward.

1. Record the context, options, choice, rejected options, and reasoning with
   `cb capture`. Avoid names or sensitive third-party information.
2. Read the local report. Treat repeated patterns as hypotheses and correct
   interpretations that do not fit. The tool does not establish a diagnosis.
3. For a prospective hypothesis, issue the card before making the later choice,
   then record the actual choice in the separate prospective command.
4. Compare the original record with the later choice. A match is not evidence
   that the choice was good. A mismatch is not evidence that the person failed.

The capture/report path and the prospective-card path are distinct interfaces.
The present predictor copies fields from the single past decision with the most
overlapping condition tags, breaking ties by ID. Its `low`/`moderate` confidence
is a hand-written rule, not a calibrated probability or a learned personality
model. Synthetic `decisions.json` fixtures use a different schema from DecisionTrace;
do not pass one to the other. The prospective flow still requires JSON editing.
It is therefore developer-oriented, not a finished consumer onboarding flow.

## Other plausible jobs, not validated demand

- An individual developer keeps the rationale for an architectural choice and
  revisits it after implementation. A plain architecture decision record may
  be simpler for team use; codbeing is not a collaboration platform.
- A researcher reproduces the public synthetic pipeline and inspects evidence
  provenance. It is suitable as an auditable prototype, not an accuracy claim.
- A frequent journaler wants a structured review of one important decision.
  Someone who prefers free-form writing may get less value from a rigid schema.

No customer interviews, usage analytics, willingness-to-pay study, or observed
retention data were available for this assessment. These are candidate jobs.

## Evidence map

| Source | What it supports | What it does not establish |
|---|---|---|
| Becker et al., 2023, systematic metacognitive reflection experiment [1] | Guided questions about the decision process can improve planning strategies in the studied five-step task. | Transfer to everyday personal decisions, codbeing effectiveness, or personality prediction. |
| Yeung & Summerfield, 2012, metacognition review [2] | Confidence and error monitoring are useful research constructs. | That reported confidence is calibrated, or laboratory results automatically generalize to life. |
| Hacker News decision-journal discussion, 2020 [3] | Some practitioners describe wanting alternatives and rationale preserved; documentation burden also appears. | Representative demand, causal benefit, or a market-size estimate. |
| Reddit decision-journal discussion, 2020 [4] | At least one participant reports difficulty making a rigid template a habit and prefers reflective essays. | A population estimate of adoption or retention. |

The citations motivate a testable design. They do not confer a scientific
endorsement on this product. The synthetic cycle demonstrates implementation
reproducibility only. Local hashes detect changes against a saved head; they do
not independently prove when a human decision happened.

## Smallest evaluation worth doing next

Recruit consenting adults who already revisit a recurring, low-stakes choice.
First test whether they can install, record one decision, find the report, and
explain what the report cannot claim. Time and observe the tasks, rather than
asking only whether they like the concept. A small usability test can uncover
friction; it cannot establish efficacy.

For an outcomes study, define the outcome and baseline before collecting data:
for example, later ability to recover original reasons versus a plain text
journal. Keep the prediction frozen before the later observation, include
misses and abandoned records, and distinguish choice prediction from decision
quality. Any probability calibration score needs a defined event, numerical
probability, resolution rule, and suitable baseline. The current confidence
labels and synthetic matches do not supply that study.

Never infer a person's stable character from a handful of records. Never use
this prototype for clinical triage or high-stakes automated decisions.

## Sources

1. Becker et al. (2023), *Systematic metacognitive reflection helps people discover far-sighted decision strategies: A process-tracing experiment*, Judgment and Decision Making. Primary experiment. https://www.cambridge.org/core/journals/judgment-and-decision-making/article/systematic-metacognitive-reflection-helps-people-discover-farsighted-decision-strategies-a-processtracing-experiment/BA25E058C30249E1A22D464A6145165E
2. Yeung & Summerfield (2012), *Metacognition in human decision-making: confidence and error monitoring*. Review. https://pmc.ncbi.nlm.nih.gov/articles/PMC3318764/
3. *Use a Decision Journal*, Hacker News (2020). Anecdotal community discussion. https://news.ycombinator.com/item?id=22694014
4. *Do you use a Decision Journal?*, Reddit (2020). Anecdotal community discussion. https://www.reddit.com/r/slatestarcodex/comments/ge3yht/do_you_use_a_decision_journal/
5. Python Packaging User Guide, *Creating and packaging command-line tools*. Installation implementation guidance, not behavior-change evidence. https://packaging.python.org/en/latest/guides/creating-command-line-tools/
6. Setuptools, *Package Discovery and Namespace Packages*. https://setuptools.pypa.io/en/latest/userguide/package%5Fdiscovery.html
