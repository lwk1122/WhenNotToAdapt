from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts" / "theory_support"
sys.path.insert(0, str(SCRIPT_DIR))

import online_runtime_simulator as sim  # noqa: E402


class ParetoCamcGateTests(unittest.TestCase):
    def test_rejects_candidate_when_success_noninferiority_fails(self) -> None:
        decision = sim.pareto_camc_gate(
            anchor_loss=1.00,
            candidate_loss=0.70,
            anchor_benefit=0.82,
            candidate_benefit=0.68,
            anchor_violation=0.04,
            candidate_violation=0.04,
            rho_loss_anchor=0.01,
            rho_loss_candidate=0.01,
            rho_benefit_anchor=0.01,
            rho_benefit_candidate=0.01,
            rho_violation_anchor=0.005,
            rho_violation_candidate=0.005,
            reference_shift=0.10,
            state_uncertainty=0.05,
            action_kind="neutral",
        )

        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reject_reason"], "benefit")

    def test_high_shift_contracts_same_candidate_that_low_shift_accepts(self) -> None:
        low_shift = sim.pareto_camc_gate(
            anchor_loss=1.00,
            candidate_loss=0.86,
            anchor_benefit=0.80,
            candidate_benefit=0.80,
            anchor_violation=0.05,
            candidate_violation=0.045,
            rho_loss_anchor=0.01,
            rho_loss_candidate=0.01,
            rho_benefit_anchor=0.005,
            rho_benefit_candidate=0.005,
            rho_violation_anchor=0.005,
            rho_violation_candidate=0.005,
            reference_shift=0.10,
            state_uncertainty=0.04,
            action_kind="neutral",
        )
        high_shift = sim.pareto_camc_gate(
            anchor_loss=1.00,
            candidate_loss=0.86,
            anchor_benefit=0.80,
            candidate_benefit=0.80,
            anchor_violation=0.05,
            candidate_violation=0.045,
            rho_loss_anchor=0.01,
            rho_loss_candidate=0.01,
            rho_benefit_anchor=0.005,
            rho_benefit_candidate=0.005,
            rho_violation_anchor=0.005,
            rho_violation_candidate=0.005,
            reference_shift=0.95,
            state_uncertainty=0.04,
            action_kind="neutral",
        )

        self.assertTrue(low_shift["accepted"])
        self.assertFalse(high_shift["accepted"])
        self.assertEqual(high_shift["reject_reason"], "loss")

    def test_verify_down_requires_no_certified_risk_increase(self) -> None:
        decision = sim.pareto_camc_gate(
            anchor_loss=1.00,
            candidate_loss=0.75,
            anchor_benefit=0.82,
            candidate_benefit=0.83,
            anchor_violation=0.040,
            candidate_violation=0.041,
            rho_loss_anchor=0.01,
            rho_loss_candidate=0.01,
            rho_benefit_anchor=0.005,
            rho_benefit_candidate=0.005,
            rho_violation_anchor=0.001,
            rho_violation_candidate=0.001,
            reference_shift=0.10,
            state_uncertainty=0.05,
            action_kind="verify_down",
        )

        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reject_reason"], "violation")

    def test_hysteresis_extra_threshold_closes_marginal_switch(self) -> None:
        base = dict(
            anchor_loss=1.00,
            candidate_loss=0.86,
            anchor_benefit=0.80,
            candidate_benefit=0.80,
            anchor_violation=0.05,
            candidate_violation=0.045,
            rho_loss_anchor=0.01,
            rho_loss_candidate=0.01,
            rho_benefit_anchor=0.005,
            rho_benefit_candidate=0.005,
            rho_violation_anchor=0.005,
            rho_violation_candidate=0.005,
            reference_shift=0.10,
            state_uncertainty=0.04,
            action_kind="neutral",
        )

        self.assertTrue(sim.pareto_camc_gate(**base)["accepted"])
        cooled = sim.pareto_camc_gate(**base, extra_tau=0.08)
        self.assertFalse(cooled["accepted"])
        self.assertEqual(cooled["reject_reason"], "loss")


if __name__ == "__main__":
    unittest.main()
