"""
Projection layer for KIRP Enterprise.

These modules implement the "projection" part of the event-sourced
architecture: they translate canonical events and domain-level changes into
relational views backed by PostgreSQL (the models under `src.models`).

Phase 4.3.b: the projection functions are defined here but are not yet wired
into the pipelines or workers. Phase 4.3.c will call these functions from
`EventPipeline` and background workers.
"""

