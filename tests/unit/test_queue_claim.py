"""T070: Queue claim logic — auto-block at N=3, release returns to open."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid

# ---------------------------------------------------------------------------
# In-process stub: simulates WorkQueue without a real DB
# ---------------------------------------------------------------------------

MAX_CLAIM_COUNT = 3

@dataclass
class FakeWorkItem:
    item_id: str
    status: str = "open"
    claimed_by: Optional[str] = None
    claim_count: int = 0


class FakeQueue:
    """In-process WorkQueue with dict-backed storage for testing."""

    def __init__(self):
        self._items: dict[str, FakeWorkItem] = {}

    def add(self, item_id: Optional[str] = None) -> str:
        item_id = item_id or str(uuid.uuid4())
        self._items[item_id] = FakeWorkItem(item_id=item_id)
        return item_id

    def claim(self, agent_id: str) -> Optional[FakeWorkItem]:
        for item in self._items.values():
            if item.status == "open" and item.claimed_by is None:
                item.status = "claimed"
                item.claimed_by = agent_id
                item.claim_count += 1
                return item
        return None

    def release(self, item_id: str) -> str:
        item = self._items[item_id]
        new_status = "blocked" if item.claim_count >= MAX_CLAIM_COUNT else "open"
        item.status = new_status
        item.claimed_by = None
        return new_status

    def close(self, item_id: str) -> None:
        self._items[item_id].status = "closed"

    def get(self, item_id: str) -> FakeWorkItem:
        return self._items[item_id]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_claim_returns_item():
    q = FakeQueue()
    item_id = q.add()
    result = q.claim("agent-1")
    assert result is not None
    assert result.item_id == item_id
    assert result.status == "claimed"


def test_claim_increments_count():
    q = FakeQueue()
    item_id = q.add()
    q.claim("agent-1")
    q.release(item_id)
    q.claim("agent-2")
    assert q.get(item_id).claim_count == 2


def test_two_agents_get_different_items():
    q = FakeQueue()
    id1 = q.add()
    id2 = q.add()
    r1 = q.claim("agent-1")
    r2 = q.claim("agent-2")
    assert r1 is not None
    assert r2 is not None
    assert r1.item_id != r2.item_id


def test_claimed_item_not_returned_to_another_agent():
    q = FakeQueue()
    q.add()
    q.claim("agent-1")
    result = q.claim("agent-2")
    assert result is None


def test_release_returns_to_open_before_limit():
    q = FakeQueue()
    item_id = q.add()
    q.claim("agent-1")
    q.claim("agent-1")  # simulate re-claim after release for claim_count
    new_status = q.release(item_id)
    # claim_count is 2 here (< 3), should return to open
    # Adjust: claim increments on claim(), so after two claims, count=2 after second release
    # Let's do it properly:

    q2 = FakeQueue()
    item_id2 = q2.add()
    q2.claim("agent-1")       # count=1
    q2.release(item_id2)       # count=1, open
    q2.claim("agent-1")       # count=2
    status = q2.release(item_id2)  # count=2, open
    assert status == "open"


def test_auto_block_at_claim_count_3():
    q = FakeQueue()
    item_id = q.add()

    for i in range(MAX_CLAIM_COUNT):
        q.claim(f"agent-{i}")
        q.release(item_id)

    item = q.get(item_id)
    assert item.status == "blocked"


def test_no_claim_after_blocked():
    q = FakeQueue()
    item_id = q.add()

    for i in range(MAX_CLAIM_COUNT):
        q.claim(f"agent-{i}")
        q.release(item_id)

    result = q.claim("agent-new")
    assert result is None


def test_close_removes_from_available():
    q = FakeQueue()
    item_id = q.add()
    q.claim("agent-1")
    q.close(item_id)
    result = q.claim("agent-2")
    assert result is None
    assert q.get(item_id).status == "closed"
