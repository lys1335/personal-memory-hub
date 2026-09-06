"""Cross-package shared exception base classes.

MemoryHubError is the architecture root for all MemoryHub exceptions.
Located in shared/domain/ because:
- It is a cross-package shared type (referenced by service/ and ingest/)
- It has no technical infrastructure dependencies (config/db/di/logging)
- It is a domain-level contract consumed by Entry Layer for error translation

DomainError and its subclasses remain in service/exceptions.py to
preserve the service-level implementation contract and avoid breaking
existing imports.
"""
from __future__ import annotations


class MemoryHubError(Exception):
    """Base exception for all MemoryHub errors.

    All service-level exceptions inherit from this class.
    Entry Layer translates MemoryHubError subclasses into protocol-specific
    error responses.
    """