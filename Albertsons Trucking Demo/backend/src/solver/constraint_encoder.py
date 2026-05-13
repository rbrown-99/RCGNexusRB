"""Encode constraints into solver-friendly forms.

Currently provides:
  * effective_weight_capacity(trailer, state) -> applies state-level weight limits
  * is_trailer_allowed_in_state(...) -> for filtering combos out of restricted states
  * forbidden_state_pairs(...) -> not used (we restrict by destination state instead)
"""
from __future__ import annotations

from ..models import ConstraintBundle, TrailerConfig


def effective_weight_capacity(
    bundle: ConstraintBundle, trailer: TrailerConfig, states: list[str]
) -> float:
    """Lowest weight cap considering state restrictions traversed."""
    cap = trailer.max_weight_lbs
    for state in states:
        for r in bundle.road_restrictions:
            if not r.applies_to(trailer.trailer_config):
                continue
            if r.state != state:
                continue
            if r.restriction_type == "WEIGHT_LIMIT":
                # parse "Max NNNNN lbs..." pattern
                detail = r.restriction_detail.lower()
                tokens = [t for t in detail.replace(",", "").split() if t.isdigit()]
                if tokens:
                    cap = min(cap, float(tokens[0]))
    return cap


def is_trailer_allowed_to_visit(
    bundle: ConstraintBundle, trailer: TrailerConfig, dest_state: str
) -> bool:
    """Returns False if a hard rule blocks this trailer from visiting that state.

    Interpretation for POC:
      - INTERSTATE_ONLY / HIGHWAY_RESTRICTION: still allowed (not hard-blocked),
        but recorded as a consideration / warning at validation time.
      - WEIGHT_LIMIT: handled via effective_weight_capacity.
      - UNRESTRICTED: allowed.
    """
    return True  # POC: nothing is hard-blocked, all warnings raised by validator


def relevant_restrictions(
    bundle: ConstraintBundle, trailer: TrailerConfig, states: list[str]
) -> list[str]:
    """Human-readable list of restrictions that apply to this trailer + states."""
    out: list[str] = []
    for state in states:
        for r in bundle.road_restrictions:
            if not r.applies_to(trailer.trailer_config):
                continue
            if r.state != state:
                continue
            if r.restriction_type == "UNRESTRICTED":
                continue
            out.append(f"{state}/{trailer.trailer_config}: {r.restriction_detail}")
    return out


def encode_constraints(bundle: ConstraintBundle) -> ConstraintBundle:
    """Currently a passthrough; future: build OR-Tools constraint objects."""
    return bundle
