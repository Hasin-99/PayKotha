from __future__ import annotations

"""Payment rail adapters — sandbox stands in for NPSB / MFS switches."""

from dataclasses import dataclass
from uuid import uuid4

from backend.app.core.config import get_settings


@dataclass
class RailResult:
    success: bool
    rail_ref: str
    message: str


class PaymentRail:
    def transfer(self, *, from_account: str, to_account: str, amount: float, narrative: str) -> RailResult:
        raise NotImplementedError


class SandboxRail(PaymentRail):
    """Deterministic local rail used for bank-grade workflow testing."""

    def transfer(self, *, from_account: str, to_account: str, amount: float, narrative: str) -> RailResult:
        if amount <= 0:
            return RailResult(False, "", "Invalid amount")
        ref = f"NPSB-SBX-{uuid4().hex[:12].upper()}"
        return RailResult(True, ref, f"Sandbox cleared {amount:.2f} {from_account}->{to_account}: {narrative}")


class MockNpsbRail(PaymentRail):
    """Slightly stricter mock of an interbank switch."""

    def transfer(self, *, from_account: str, to_account: str, amount: float, narrative: str) -> RailResult:
        if len(to_account) < 8:
            return RailResult(False, "", "Beneficiary rejected by switch")
        if amount > 500000:
            return RailResult(False, "", "Switch limit exceeded")
        ref = f"NPSB-{uuid4().hex[:12].upper()}"
        return RailResult(True, ref, "Accepted by mock NPSB")


def get_rail() -> PaymentRail:
    mode = get_settings().rail_mode
    if mode == "mock_npsb":
        return MockNpsbRail()
    return SandboxRail()
