"""UUIDv7 generation infrastructure.

Provides a single canonical UUIDv7 generator for the entire project.

Implementation:
    Uses the `uuid_extensions` package (pip: uuid_extensions>=1.0) which
    implements RFC 9562-compliant UUIDv7 generation in pure Python.
    Compatible with Python 3.10+.

    Package: https://github.com/chadoe/uuid-extensions
    License: Apache-2.0

Architecture alignment:
    Per 08_Implementation_Architecture.md §4.1 and 09_Database_Physical_Design.md:
    All primary keys and foreign keys use UUIDv7. This module is the single
    source of truth for UUID generation in the application layer.

Usage:
    from backend.shared.infrastructure.uuid import generate_uuid
    entity_id = generate_uuid()
"""

from __future__ import annotations

from uuid import UUID

from uuid_extensions import uuid7


def generate_uuid() -> UUID:
    """Generate a new UUIDv7.

    Returns:
        A UUIDv7 instance (time-sorted, version 7).
    """
    return uuid7()
