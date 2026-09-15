# {
#   "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"
# }

import json
import genlayer.gl as gl


class ClaimVerifier(gl.Contract):

    counter: gl.u256
    claims: gl.TreeMap[str, str]

    def __init__(self):
        self.counter = 0
        self.claims = gl.TreeMap()

    def _build_prompt(
        self,
        claim: str,
        criteria: str,
        evidence: list,
    ) -> str:

        evidence_text = ""

        for item in evidence:
            evidence_text += (
                "\nSOURCE URL: "
                + str(item["url"])
                + "\nSOURCE CONTENT:\n"
                + str(item["content"])
                + "\n---\n"
            )

        return f"""
You are an independent fact verifier.

Your job is to determine whether a CLAIM is substantively
supported by the supplied EVIDENCE according to the CRITERIA.

CLAIM:
{claim}

CRITERIA:
{criteria}

EVIDENCE:
{evidence_text}

Important rules:

1. Evaluate the actual meaning of the claim.
2. Evaluate every criterion.
3. Do not trust a previous APPROVED or REJECTED label.
4. Do not approve merely because evidence exists.
5. The evidence must actually support the claim.
6. If an important criterion is not satisfied, reject the claim.
7. Conflicting evidence must be considered.
8. Do not invent facts that are not present in the evidence.

Return JSON with exactly these fields:

{{
  "decision": "APPROVED" or "REJECTED",
  "criteria_satisfied": true or false,
  "reason": "short explanation",
  "evidence_quality": "STRONG", "MEDIUM", or "WEAK"
}}
"""

    def _fetch_evidence(self, urls: list):
        evidence = []

        for url in urls:
            response = gl.nondet.web.render(
                url,
                mode="html"
            )

            body = response.body

            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="ignore")

            evidence.append(
                {
                    "url": url,
                    "content": body[:12000],
                }
            )

        return evidence

    def _evaluate(
        self,
        claim: str,
        criteria: str,
        urls: list,
    ):

        evidence = self._fetch_evidence(urls)

        prompt = self._build_prompt(
            claim,
            criteria,
            evidence,
        )

        result = gl.nondet.exec_prompt(
            prompt,
            response_format="json",
        )

        if not isinstance(result, dict):
            raise gl.UserError(
                "Validator returned invalid structured data"
            )

        decision = str(
            result.get("decision", "")
        ).upper()

        criteria_satisfied = result.get(
            "criteria_satisfied"
        )

        reason = str(
            result.get("reason", "")
        )

        evidence_quality = str(
            result.get("evidence_quality", "")
        ).upper()

        if decision not in (
            "APPROVED",
            "REJECTED",
        ):
            raise gl.UserError(
                "Invalid verification decision"
            )

        if not isinstance(
            criteria_satisfied,
            bool
        ):
            raise gl.UserError(
                "Invalid criteria_satisfied value"
            )

        if evidence_quality not in (
            "STRONG",
            "MEDIUM",
            "WEAK",
        ):
            raise gl.UserError(
                "Invalid evidence quality"
            )

        if not reason.strip():
            raise gl.UserError(
                "Verification reason is empty"
            )

        return {
            "decision": decision,
            "criteria_satisfied": criteria_satisfied,
            "reason": reason,
            "evidence_quality": evidence_quality,
            "evidence": evidence,
        }

    @gl.public.write
    def submit_claim(
        self,
        claim: str,
        criteria: str,
        source_urls_json: str,
    ) -> str:

        urls = json.loads(source_urls_json)

        if not isinstance(urls, list):
            raise gl.UserError(
                "source_urls_json must contain a list"
            )

        if len(urls) < 2:
            raise gl.UserError(
                "At least two independent sources are required"
            )

        if len(urls) > 5:
            raise gl.UserError(
                "Maximum five sources allowed"
            )

        for url in urls:
            if not isinstance(url, str):
                raise gl.UserError(
                    "Every source URL must be a string"
                )

        claim_id = str(self.counter)

        def leader_fn():

            return self._evaluate(
                claim,
                criteria,
                urls,
            )

        def validator_fn(
            leader_result
        ) -> bool:

            if not isinstance(
                leader_result,
                gl.vm.Return,
            ):
                return False

            leader = leader_result.calldata

            try:

                independent = self._evaluate(
                    claim,
                    criteria,
                    urls,
                )

            except Exception:
                return False

            # The validator must independently reach
            # the SAME substantive decision.

            if (
                independent["decision"]
                != leader["decision"]
            ):
                return False

            # The validator must also independently
            # agree that the criteria were satisfied.

            if (
                independent["criteria_satisfied"]
                != leader["criteria_satisfied"]
            ):
                return False

            # A claim cannot be approved if the criteria
            # are not satisfied.

            if leader["decision"] == "APPROVED":
                if not leader["criteria_satisfied"]:
                    return False

                if not independent[
                    "criteria_satisfied"
                ]:
                    return False

            # Rejection must also be substantive:
            # validators independently reached REJECTED.

            if leader["decision"] == "REJECTED":
                if independent["decision"] != "REJECTED":
                    return False

            return True

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn,
        )

        if not isinstance(result, dict):
            raise gl.UserError(
                "Consensus returned invalid result"
            )

        decision = result["decision"]

        if decision not in (
            "APPROVED",
            "REJECTED",
        ):
            raise gl.UserError(
                "Consensus produced invalid decision"
            )

        report = {
            "id": claim_id,
            "claim": claim,
            "criteria": criteria,
            "sources": urls,
            "decision": decision,
            "criteria_satisfied":
                result["criteria_satisfied"],
            "reason": result["reason"],
            "evidence_quality":
                result["evidence_quality"],
            "evidence":
                result["evidence"],
            "verification": {
                "method":
                    "GenLayer Independent Consensus",
                "validator_rule":
                    "Validators independently fetch the same sources and evaluate the same claim and criteria.",
                "decision_agreement":
                    "Required",
                "criteria_agreement":
                    "Required",
                "consensus":
                    "accepted",
            },
        }

        self.claims[claim_id] = json.dumps(
            report
        )

        self.counter += 1

        return claim_id

    @gl.public.view
    def get_claim(
        self,
        claim_id: str,
    ) -> str:

        if claim_id not in self.claims:
            return ""

        return self.claims[claim_id]

    @gl.public.view
    def get_counter(self) -> int:
        return int(self.counter)
