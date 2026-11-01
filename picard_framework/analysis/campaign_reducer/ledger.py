"""Reservation/budget ledger for the campaign reducer (ticket D2).

One ledger owns every admitted ceiling in
``CANONICAL_INTERFACE.json["budgets_required"]``. The rules it enforces
come straight from ``budget_rules``:

- ``None`` is never unlimited: ``parse_ceilings`` rejects missing, null,
  non-numeric or non-finite values, and non-positive ceilings (except
  ``max_retries``, which may be zero) before any work is admitted.
- Reserve before request: shard/phase reservations are disjoint slices of
  the parent's remaining capacity; a reservation that cannot fit fails
  atomically (all-or-none).
- Retries, resumes, query jobs and concurrency charge the *same* ledger —
  spent counters are cumulative, are checkpointed, and are never reset on
  resume (a resumed phase constructs a ledger seeded with the checkpoint's
  spent counters).
- ``checkpoint_reserve_bytes``/``checkpoint_reserve_seconds`` are held back:
  work charges cannot consume them; only the checkpoint path may.
- ``safety_factor`` is retained verbatim for quote arithmetic; it is not a
  chargeable counter.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping

# The 23 chargeable ceilings, verbatim from CANONICAL_INTERFACE.json
# ``budgets_required``. ``safety_factor`` is a quote multiplier, not a
# charge counter; the two ``checkpoint_reserve_*`` fields are held-back
# reserves rather than spendable ceilings.
BUDGET_FIELDS: tuple[str, ...] = (
    "max_list_pages",
    "max_api_calls_total",
    "max_head_requests",
    "max_get_requests",
    "max_source_objects",
    "max_source_object_bytes_referenced",
    "max_compressed_bytes_read",
    "max_uncompressed_bytes",
    "max_member_bytes",
    "max_central_directory_bytes",
    "max_output_bytes",
    "max_spool_bytes",
    "max_wall_seconds",
    "max_queue_wait_seconds",
    "max_vcpu_seconds",
    "max_memory_mib_seconds",
    "max_jobs",
    "max_inflight_jobs",
    "max_retries",
    "max_cost_usd",
    "safety_factor",
    "checkpoint_reserve_bytes",
    "checkpoint_reserve_seconds",
)

# Fields a normal charge may never touch; the checkpoint path charges
# them through ``charge_checkpoint`` only.
_RESERVE_FIELDS = frozenset(
    {"checkpoint_reserve_bytes", "checkpoint_reserve_seconds"}
)
_UNSPENDABLE = _RESERVE_FIELDS | {"safety_factor"}
# Per-occurrence caps (a single member/range/job may not exceed these);
# they bound each event, they do not accumulate spend.
_PER_EVENT_CAPS = frozenset({"max_member_bytes", "max_central_directory_bytes"})


class BudgetBlocked(Exception):
    """Admission failure: a ceiling is unset, non-finite or non-positive."""


class BudgetExceeded(Exception):
    """A charge would exceed a ceiling (stop-and-checkpoint signature)."""

    def __init__(self, field: str, attempted: float, remaining: float):
        super().__init__(
            f"{field}: charge {attempted} exceeds remaining {remaining}"
        )
        self.field = field
        self.attempted = attempted
        self.remaining = remaining


class UnknownPrice(BudgetBlocked):
    """A cost was charged against a price the cost model does not know."""


def parse_ceilings(
    budgets: Mapping[str, object] | None,
    *,
    required: tuple[str, ...] = BUDGET_FIELDS,
) -> dict[str, float]:
    """Validate a ``budgets`` block into finite float ceilings.

    Every required field must be present, numeric, finite and positive;
    ``max_retries`` may be zero; ``safety_factor`` must be positive. Any
    unset/invalid value raises :class:`BudgetBlocked` — admission stops,
    it does not silently continue unbounded.
    """
    doc = dict(budgets or {})
    return {field: _ceiling(field, doc.get(field)) for field in required}


def _ceiling(field: str, value: object) -> float:
    """One ceiling: present, numeric, finite, positive (retries >= 0)."""
    if value is None or isinstance(value, bool) or not isinstance(
        value, (int, float)
    ):
        raise BudgetBlocked(f"{field}: unset or non-numeric ceiling")
    fval = float(value)
    if not math.isfinite(fval):
        raise BudgetBlocked(f"{field}: non-finite ceiling")
    if field == "max_retries":
        if fval < 0:
            raise BudgetBlocked("max_retries: negative ceiling")
    elif fval <= 0:
        raise BudgetBlocked(f"{field}: non-positive ceiling")
    return fval


class Reservation:
    """An atomic slice of a ledger's remaining capacity.

    Charges a :class:`ShardBudget` makes first consume this reservation;
    ``release`` frees what is left, ``commit`` converts the consumed
    amount into parent spend. Releasing twice is a no-op.
    """

    def __init__(self, ledger: "BudgetLedger", amounts: dict[str, float]):
        self._ledger = ledger
        self.amounts = dict(amounts)
        self._consumed: dict[str, float] = dict.fromkeys(amounts, 0.0)
        self._closed = False

    def consume(self, field: str, amount: float, detail: str = "") -> None:
        if field in self.amounts:
            available = self.amounts[field] - self._consumed[field]
            if amount > available:
                raise BudgetExceeded(field, amount, available)
            self._consumed[field] += amount
        self._ledger._consume(self, field, amount, detail)

    def commit(self) -> None:
        if self._closed:
            return
        for field, used in self._consumed.items():
            self._ledger.reserved[field] -= self.amounts[field]
            self._ledger.spent[field] = (
                self._ledger.spent.get(field, 0.0) + used
            )
        self._closed = True

    def release(self) -> None:
        """Return the reservation. Same ledger effect as :meth:`commit`."""
        self.commit()


class ShardBudget:
    """A disjoint child reservation charged through the shared ledger."""

    def __init__(self, ledger: "BudgetLedger", reservation: Reservation):
        self.ledger = ledger
        self.reservation = reservation

    def charge(self, field: str, amount: float, detail: str = "") -> None:
        self.reservation.consume(field, amount, detail)

    def cap(self, field: str, amount: float, detail: str = "") -> None:
        self.ledger.cap(field, amount, detail)

    def commit(self) -> None:
        self.reservation.commit()

    def release(self) -> None:
        self.reservation.release()


class BudgetLedger:
    """The shared, cumulative, checkpointable reservation ledger.

    ``spent`` accumulates every charged unit (requests, bytes, rows,
    wall/vCPU/memory seconds, jobs, cost); ``reserved`` holds the
    not-yet-consumed slices handed to shard children. A charge fits when
    ``spent + reserved + amount <= ceiling`` — so concurrent shard
    reservations can never oversubscribe the parent.
    """

    def __init__(
        self,
        ceilings: Mapping[str, float],
        *,
        clock: Callable[[], float] | None = None,
        prices: Mapping[str, float] | None = None,
        require_prices: bool = False,
        spent: Mapping[str, float] | None = None,
    ) -> None:
        self.ceilings = dict(ceilings)
        self.spent: dict[str, float] = {
            f: float(v) for f, v in (spent or {}).items()
        }
        self.reserved: dict[str, float] = {}
        self.inflight = 0
        self.jobs = 0
        self.retries = 0
        self.clock = clock if clock is not None else time.monotonic
        self.prices = dict(prices or {})
        self.require_prices = require_prices

    def _ceiling(self, field: str) -> float:
        ceiling = self.ceilings.get(field)
        if ceiling is None:
            raise BudgetBlocked(f"{field}: no ceiling declared; not unlimited")
        return ceiling

    def headroom(self, field: str) -> float:
        return (
            self._ceiling(field)
            - self.spent.get(field, 0.0)
            - self.reserved.get(field, 0.0)
        )

    def _consume(
        self, reservation: Reservation | None, field: str, amount: float, _detail: str
    ) -> None:
        if field in _UNSPENDABLE:
            raise BudgetBlocked(f"{field}: not a spendable ceiling")
        if amount < 0:
            raise BudgetBlocked(f"{field}: negative charge {amount}")
        if field not in _PER_EVENT_CAPS:
            # A reservation charge converts reserve into spend; the
            # global invariant spent+reserved <= ceiling was established
            # at reserve() time and is unchanged by the move. Only the
            # reservation's own remaining capacity binds (checked in
            # consume()); verify the invariant for safety.
            if (
                self.spent.get(field, 0.0) + self.reserved.get(field, 0.0)
                > self._ceiling(field)
            ):
                raise BudgetExceeded(
                    field, amount, self.headroom(field)
                )

    def charge(self, field: str, amount: float, detail: str = "") -> None:
        """Cumulative charge against the shared ledger."""
        if field in _RESERVE_FIELDS:
            raise BudgetBlocked(f"{field}: reserve-only ceiling")
        if field == "safety_factor":
            raise BudgetBlocked("safety_factor: not a spendable ceiling")
        if amount < 0:
            raise BudgetBlocked(f"{field}: negative charge {amount}")
        if field in _PER_EVENT_CAPS:
            self.cap(field, amount, detail)
            return
        remaining = self.headroom(field)
        if amount > remaining:
            raise BudgetExceeded(field, amount, remaining)
        self.spent[field] = self.spent.get(field, 0.0) + amount

    def cap(self, field: str, amount: float, _detail: str = "") -> None:
        """Per-occurrence ceiling: one event may not exceed the cap."""
        ceiling = self._ceiling(field)
        if amount > ceiling:
            raise BudgetExceeded(field, amount, ceiling)

    def charge_checkpoint(self, field: str, amount: float) -> None:
        """Checkpoint writes consume their own held-back reserve."""
        if field not in _RESERVE_FIELDS:
            raise BudgetBlocked(f"{field}: not a checkpoint reserve")
        remaining = self._ceiling(field) - self.spent.get(field, 0.0)
        if amount > remaining:
            raise BudgetExceeded(field, amount, remaining)
        self.spent[field] = self.spent.get(field, 0.0) + amount

    def reserve(self, amounts: Mapping[str, float]) -> Reservation:
        """Atomic disjoint reservation; all fields must fit or none."""
        for field, amount in amounts.items():
            if field in _UNSPENDABLE:
                raise BudgetBlocked(f"{field}: cannot be reserved")
            if amount < 0:
                raise BudgetBlocked(f"{field}: negative reservation")
            if amount > self.headroom(field):
                raise BudgetExceeded(
                    field, amount, self.headroom(field)
                )
        for field, amount in amounts.items():
            self.reserved[field] = self.reserved.get(field, 0.0) + amount
        return Reservation(self, dict(amounts))

    def shard(self, amounts: Mapping[str, float]) -> ShardBudget:
        return ShardBudget(self, self.reserve(amounts))

    def acquire_job(self, _detail: str = "") -> None:
        """One inflight slot + one cumulative job, charged atomically."""
        if self.inflight + 1 > self._ceiling("max_inflight_jobs"):
            raise BudgetExceeded(
                "max_inflight_jobs", self.inflight + 1, self._ceiling("max_inflight_jobs")
            )
        if self.jobs + 1 > self._ceiling("max_jobs"):
            raise BudgetExceeded("max_jobs", self.jobs + 1, self._ceiling("max_jobs"))
        self.inflight += 1
        self.jobs += 1

    def release_job(self) -> None:
        if self.inflight > 0:
            self.inflight -= 1

    def charge_retry(self, detail: str = "") -> None:
        """One retry: counts toward max_retries and api calls."""
        self.retries += 1
        if self.retries > self._ceiling("max_retries"):
            raise BudgetExceeded(
                "max_retries", self.retries, self._ceiling("max_retries")
            )
        self.charge("max_api_calls_total", 1, detail or "retry")

    def charge_wall(self, seconds: float, detail: str = "") -> None:
        if seconds < 0:
            raise BudgetBlocked(f"max_wall_seconds: negative charge {seconds}")
        self.charge("max_wall_seconds", seconds, detail)

    def charge_cost(self, kind: str, units: float) -> float:
        """Charge ``units`` of a priced operation to ``max_cost_usd``.

        ``prices`` maps operation kind -> USD per unit. When
        ``require_prices`` is set an unknown price kind blocks the charge
        outright — unknown price means blocked, never free.
        """
        price = self.prices.get(kind)
        if price is None:
            if self.require_prices:
                raise UnknownPrice(f"{kind}: no unit price declared")
            return 0.0
        cost = price * units
        self.charge("max_cost_usd", cost, kind)
        return cost

    def snapshot(self) -> dict:
        """Checkpoint-safe spend state (reservations die with a process)."""
        return {
            "spent": dict(self.spent),
            "jobs": self.jobs,
            "retries": self.retries,
        }

    @classmethod
    def resume(
        cls,
        ceilings: Mapping[str, float],
        snapshot: Mapping[str, object] | None,
        **kwargs,
    ) -> "BudgetLedger":
        """A ledger for a resumed phase: spent counters carry forward."""
        snap = dict(snapshot or {})
        ledger = cls(ceilings, spent=snap.get("spent") or {}, **kwargs)
        ledger.jobs = int(snap.get("jobs") or 0)
        ledger.retries = int(snap.get("retries") or 0)
        return ledger
