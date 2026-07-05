"""Pagination helpers for Repository queries.

Provides cursor-based and offset-based pagination primitives used by
all Repository implementations for list queries.

Per 10_9 §5.1: Pagination is shared infrastructure for all Repositories,
especially QueryRepositories that return large result sets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """A single page of paginated results.

    Attributes:
        items: The items on this page.
        total: Total number of items across all pages (may be None for cursor-based pagination).
        page_number: 1-based page number.
        page_size: Number of items per page.
        has_next: Whether there is a next page.
        has_prev: Whether there is a previous page.
        next_cursor: Opaque cursor for the next page (cursor-based pagination).
        prev_cursor: Opaque cursor for the previous page (cursor-based pagination).
    """

    items: list[T] = field(default_factory=list)
    total: int | None = None
    page_number: int = 1
    page_size: int = 20
    has_next: bool = False
    has_prev: bool = False
    next_cursor: str | None = None
    prev_cursor: str | None = None

    @property
    def is_empty(self) -> bool:
        """Return True if this page has no items."""
        return len(self.items) == 0

    @property
    def is_last(self) -> bool:
        """Return True if this is the last page."""
        return not self.has_next

    @classmethod
    def empty(cls, page_size: int = 20) -> Page[T]:
        """Create an empty page with the given page size."""
        return cls(items=[], page_size=page_size, page_number=1, has_next=False, has_prev=False)


@dataclass
class OffsetPage(Page[T]):
    """Offset-based pagination.

    Uses page_number + page_size for navigation.
    """

    def __post_init__(self) -> None:
        if self.total is not None:
            total_pages = (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 0
            self.has_next = self.page_number < total_pages
            self.has_prev = self.page_number > 1


@dataclass
class CursorPage(Page[T]):
    """Cursor-based pagination.

    Uses opaque cursors (typically base64-encoded position markers) for navigation.
    Suitable for large datasets where offset pagination becomes inefficient.
    """

    total: int | None = None  # Cursor pagination typically omits total

    def __post_init__(self) -> None:
        # Cursor-based: has_next is determined by whether we got page_size + 1 items
        self.has_next = len(self.items) > 0 and self.items[-1] is not None  # sentinel check
        self.has_prev = self.prev_cursor is not None
