# ClaimVerifier

A GenLayer Intelligent Contract for independently verifying real-world claims using multi-source web evidence and substantive validator consensus.

## Overview

**ClaimVerifier** allows users to submit a factual claim together with verification criteria and multiple independent web sources.

The contract fetches evidence from the supplied sources and asks GenLayer validators to determine whether the evidence substantively satisfies the claim and criteria.

The key design principle is:

> Validators must independently evaluate the same claim, criteria, and fetched evidence and agree on the substantive `APPROVED` or `REJECTED` outcome.

Validators do not simply check whether another validator returned an allowed label.

---

## How It Works

The verification flow is:

```text
User
 │
 ├── Claim
 ├── Verification Criteria
 └── Multiple Source URLs
          │
          ▼
    ClaimVerifier
          │
          ▼
   Fetch Web Evidence
          │
          ▼
     Leader Evaluation
          │
          ▼
   GenLayer Consensus
          │
     ┌────┴────┐
     ▼         ▼
 Validator   Validator
     │         │
     └────┬────┘
          ▼
 Independent Evaluation
          │
          ▼
 APPROVED / REJECTED
          │
          ▼
   On-chain Report
```

---

## Example

A user can submit:

### Claim

```text
Tesla released Model X in 2015.
```

### Criteria

```text
1. Evidence must come from reliable sources.
2. The sources must support the release year.
3. The evidence must directly support the claim.
```

### Sources

```text
https://example-source-1.com
https://example-source-2.com
```

The contract fetches the evidence and evaluates it.

A validator may determine:

```json
{
  "decision": "APPROVED",
  "criteria_satisfied": true,
  "reason": "The supplied sources directly support the claimed release year.",
  "evidence_quality": "STRONG"
}
```

Another validator independently performs the same evaluation.

---

## Substantive Validator Consensus

The most important part of ClaimVerifier is the validator function.

A validator does **not** simply check whether the Leader returned:

```text
APPROVED
```

or:

```text
REJECTED
```

Instead, the validator independently:

1. Receives the same claim.
2. Receives the same verification criteria.
3. Fetches the same source URLs.
4. Evaluates the fetched evidence.
5. Determines whether the criteria are actually satisfied.
6. Produces its own `APPROVED` or `REJECTED` decision.
7. Compares its substantive result with the Leader's result.

Consensus is accepted only when the independent evaluation agrees with the Leader.

Conceptually:

```python
independent = evaluate(
    claim,
    criteria,
    source_urls
)

if independent["decision"] != leader["decision"]:
    return False

if (
    independent["criteria_satisfied"]
    != leader["criteria_satisfied"]
):
    return False
```

This prevents opposite decisions from both being accepted merely because both use an allowed label.

---

## Why This Design Matters

A naive validator could perform a check such as:

```text
Does the response start with APPROVED or REJECTED?
```

That does not prove that the underlying claim was actually evaluated.

For example, both of these responses would pass such a superficial check:

```text
APPROVED
```

and:

```text
REJECTED
```

ClaimVerifier instead requires validators to independently assess the actual claim and evidence.

Therefore:

```text
Leader       → APPROVED
Validator    → REJECTED
                    ↓
             Consensus fails
```

Whereas:

```text
Leader       → APPROVED
Validator    → APPROVED
                    ↓
             Consensus succeeds
```

---

## Evidence

Each verification can contain multiple source URLs.

The contract requires at least two sources and supports up to five sources.

The fetched evidence is stored with the resulting report.

Each evidence item contains:

```json
{
  "url": "https://example.com",
  "content": "Fetched source content..."
}
```

This provides provenance for the final verification result.

---

## Verification Criteria

Criteria are supplied by the user and become part of the verification input.

For example:

```text
The claim is approved only if:

1. The source is authoritative.
2. The source directly confirms the claim.
3. The evidence is consistent with the stated date.
```

Validators evaluate these criteria rather than merely checking whether evidence exists.

A claim can therefore be rejected even when sources are available if those sources do not substantively satisfy the criteria.

---

## Verification Result

A successful report contains:

```json
{
  "id": "0",
  "claim": "Example claim",
  "criteria": "Example verification criteria",
  "sources": [
    "https://source-one.example",
    "https://source-two.example"
  ],
  "decision": "APPROVED",
  "criteria_satisfied": true,
  "reason": "The evidence directly supports the claim.",
  "evidence_quality": "STRONG"
}
```

The report also includes verification metadata:

```json
{
  "verification": {
    "method": "GenLayer Independent Consensus",
    "validator_rule": "Validators independently fetch the same sources and evaluate the same claim and criteria.",
    "decision_agreement": "Required",
    "criteria_agreement": "Required",
    "consensus": "accepted"
  }
}
```

---

## Smart Contract Interface

### `submit_claim`

Creates a new verification request.

Parameters:

```text
claim
criteria
source_urls_json
```

Returns:

```text
claim_id
```

Example source list:

```json
[
  "https://example.com/source1",
  "https://example.com/source2"
]
```

---

### `get_claim`

Reads a previously verified claim.

```text
get_claim(claim_id)
```

Returns the stored verification report as JSON.

---

### `get_counter`

Returns the number of submitted claims.

```text
get_counter()
```

---

## Verification States

A claim can reach one of two substantive outcomes:

### APPROVED

The validators independently determine that the evidence satisfies the supplied criteria and supports the claim.

### REJECTED

The validators independently determine that the evidence does not sufficiently support the claim or that one or more required criteria are not satisfied.

The contract does not treat the existence of evidence as automatic approval.

---

## Security and Trust Model

ClaimVerifier is designed around independent evaluation rather than trusting a single result.

The Leader produces an initial evaluation.

Validators independently repeat the evaluation using:

```text
Same Claim
+
Same Criteria
+
Same Source URLs
+
Fresh Evidence Retrieval
```

The validator then checks whether its independently derived substantive result agrees with the Leader.

This makes the consensus decision meaningful rather than merely validating the format of a response.

---

## Data Provenance

The verification pipeline is:

```text
User Claim
     ↓
Verification Criteria
     ↓
Source URLs
     ↓
Web Evidence
     ↓
Leader Evaluation
     ↓
Independent Validator Evaluation
     ↓
Consensus
     ↓
On-chain Verification Report
```

The stored report preserves the claim, criteria, sources, evidence, decision, reasoning, and verification metadata.

---

## Technology

* GenLayer Intelligent Contracts
* Python
* GenLayer `gl.vm.run_nondet_unsafe`
* GenLayer nondeterministic web access
* GenLayer validator consensus
* JSON-based verification reports

---

## Running the Contract

Deploy the contract through GenLayer Studio or the appropriate GenLayer development environment.

Before deployment, validate the contract with the GenLayer linter:

```bash
genvm-lint check contract.py
```

Then deploy the contract and test it with multiple claims.

---

## Recommended Test Cases

### Test 1 — Clearly Supported Claim

Provide multiple authoritative sources that directly support the claim.

Expected:

```text
APPROVED
```

### Test 2 — Clearly False Claim

Provide sources that contradict the claim.

Expected:

```text
REJECTED
```

### Test 3 — Insufficient Evidence

Provide sources that mention the subject but do not establish the claim.

Expected:

```text
REJECTED
```

### Test 4 — Conflicting Sources

Provide sources with conflicting information.

Expected:

```text
REJECTED
```

or another consensus outcome supported by the actual evaluation, depending on the supplied criteria.

### Test 5 — Validator Disagreement

Use ambiguous evidence that may cause independent validators to reach different substantive conclusions.

Expected:

```text
Consensus failure
```

This test is particularly important because it demonstrates that the validator is actually evaluating the claim rather than simply accepting an allowed label.

---

## Design Principle

ClaimVerifier follows one central principle:

> **Consensus should be based on independent agreement about the substance of the claim, not agreement about the format of a response.**

The validators must independently evaluate:

```text
CLAIM
   +
CRITERIA
   +
EVIDENCE
```

before accepting the Leader's result.

This makes the verification process substantially stronger than a label-only validation scheme.
