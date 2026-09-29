"""Synthetic schema lab: canonical contract, validation, migration, projections.

This package implements the M1 data contract agreed at review checkpoint 1.
See `docs/schema-lab-checkpoint-1-decisions.md` for the semantics it encodes.

Nothing here reads the network or the clock. Every entry point is deterministic
so repeated runs over identical inputs produce identical bytes.
"""

CONTRACT_VERSION = "0.1.0"

__all__ = ["CONTRACT_VERSION"]
