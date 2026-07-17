"""Entry Layer — Protocol Adapters for Personal Memory Hub.

This package implements Entry Layer adapters that translate external
protocols to Service Layer commands and back.

Per D5_Entry_Layer_Architecture:
- Entry is a Service Adapter, not a business logic layer
- Protocol-agnostic: same Service Layer accessed through multiple adapters
- Single Source of Truth: GitHub HEAD is authoritative
- Two-Layer Validation: Entry = contract validation, Service = domain validation
- DTO Strategy: External DTOs (Entry) ↔ Internal DTOs (Service) ↔ Domain Models (Engine)
- Error Translation: Domain errors → protocol-specific error responses
- One Operation → One Capability mapping

Architecture:
    External Systems → Entry Layer (D5) → Service Layer (D3) → Engine (D4) → Repository (D2) → DB
"""

from __future__ import annotations

__all__ = [
    "rest_adapter",
    "dto",
    "validation",
]
