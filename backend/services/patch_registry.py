from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATABASE_PATH = (
    PROJECT_ROOT / "data" / "patch_registry.sqlite3"
)


# ============================================================
# PATCH PROPOSAL MODEL
# ============================================================

@dataclass
class PatchProposal:
    proposal_id: str
    repository_path: str
    file_path: str

    original_hash: str
    proposed_hash: str

    proposed_source: str

    verification_status: str = "pending"
    approved: bool = False
    applied: bool = False

    created_at: str = ""


# ============================================================
# PATCH REGISTRY
# ============================================================

class PatchRegistry:
    """
    Persistent patch registry for Code Guardian AI.

    Responsibilities:
    - Register patch proposals.
    - Persist proposals in SQLite.
    - Track verification status.
    - Approve verified proposals.
    - Track applied patches.
    - Preserve state across backend restarts.
    """

    ALLOWED_VERIFICATION_STATUSES = {
        "pending",
        "verified",
        "rejected",
        "syntax_passed",
    }

    def __init__(
        self,
        database_path: str | Path | None = None,
    ) -> None:

        configured_path = (
            database_path
            or os.getenv("PATCH_REGISTRY_DB")
            or DEFAULT_DATABASE_PATH
        )

        self.database_path = (
            Path(configured_path)
            .expanduser()
            .resolve()
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self._initialize_database()

    # ========================================================
    # SOURCE HASHING
    # ========================================================

    @staticmethod
    def hash_source(source: str) -> str:
        """Calculate a SHA-256 hash of source code."""

        return hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """
        Create a database connection.

        Commit on success and roll back on exceptions.
        """

        connection = sqlite3.connect(
            str(self.database_path),
            timeout=15,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA busy_timeout = 15000"
        )

        try:
            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    # ========================================================
    # DATABASE INITIALIZATION
    # ========================================================

    def _initialize_database(self) -> None:
        """Create the patch proposals table if it doesn't exist."""

        with self._lock, self._connection() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS patch_proposals (

                    proposal_id TEXT PRIMARY KEY,

                    repository_path TEXT NOT NULL,

                    file_path TEXT NOT NULL,

                    original_hash TEXT NOT NULL,

                    proposed_hash TEXT NOT NULL,

                    proposed_source TEXT NOT NULL,

                    verification_status TEXT NOT NULL
                        DEFAULT 'pending',

                    approved INTEGER NOT NULL DEFAULT 0,

                    applied INTEGER NOT NULL DEFAULT 0,

                    created_at TEXT NOT NULL

                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_patch_proposals_created_at
                ON patch_proposals(created_at)
                """
            )

    # ========================================================
    # DATABASE ROW CONVERSION
    # ========================================================

    @staticmethod
    def _to_proposal(
        row: sqlite3.Row | None,
    ) -> PatchProposal | None:
        """Convert a SQLite row into a PatchProposal."""

        if row is None:
            return None

        return PatchProposal(
            proposal_id=row["proposal_id"],
            repository_path=row["repository_path"],
            file_path=row["file_path"],
            original_hash=row["original_hash"],
            proposed_hash=row["proposed_hash"],
            proposed_source=row["proposed_source"],
            verification_status=row["verification_status"],
            approved=bool(row["approved"]),
            applied=bool(row["applied"]),
            created_at=row["created_at"],
        )

    # ========================================================
    # REGISTER PROPOSAL
    # ========================================================

    def register(
        self,
        *,
        repository_path: str,
        file_path: str,
        original_source: str,
        proposed_source: str,
    ) -> PatchProposal:
        """
        Register a new patch proposal in SQLite.
        """

        proposal = PatchProposal(
            proposal_id=secrets.token_urlsafe(24),

            repository_path=repository_path,

            file_path=file_path,

            original_hash=self.hash_source(
                original_source
            ),

            proposed_hash=self.hash_source(
                proposed_source
            ),

            proposed_source=proposed_source,

            verification_status="pending",

            approved=False,

            applied=False,

            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        with self._lock, self._connection() as connection:

            connection.execute(
                """
                INSERT INTO patch_proposals (

                    proposal_id,
                    repository_path,
                    file_path,
                    original_hash,
                    proposed_hash,
                    proposed_source,
                    verification_status,
                    approved,
                    applied,
                    created_at

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.repository_path,
                    proposal.file_path,
                    proposal.original_hash,
                    proposal.proposed_hash,
                    proposal.proposed_source,
                    proposal.verification_status,
                    int(proposal.approved),
                    int(proposal.applied),
                    proposal.created_at,
                ),
            )

        return proposal

    # ========================================================
    # GET PROPOSAL
    # ========================================================

    def get(
        self,
        proposal_id: str,
    ) -> PatchProposal | None:
        """Retrieve a proposal by its ID."""

        with self._lock, self._connection() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM patch_proposals
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()

        return self._to_proposal(row)

    # ========================================================
    # LIST PROPOSALS
    # ========================================================

    def list_proposals(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        approved: bool | None = None,
        applied: bool | None = None,
    ) -> list[PatchProposal]:
        """Return recent proposals with optional filters."""

        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        allowed_statuses = {
            "pending",
            "verified",
            "rejected",
            "syntax_passed",
        }

        if status is not None and status not in allowed_statuses:
            raise ValueError(
                f"Invalid status. Allowed values: {sorted(allowed_statuses)}"
            )

        conditions = []
        parameters = []

        if status is not None:
            conditions.append("verification_status = ?")
            parameters.append(status)

        if approved is not None:
            conditions.append("approved = ?")
            parameters.append(int(approved))

        if applied is not None:
            conditions.append("applied = ?")
            parameters.append(int(applied))

        where_clause = (
            " WHERE " + " AND ".join(conditions)
            if conditions
            else ""
        )

        query = (
            "SELECT * FROM patch_proposals"
            + where_clause
            + " ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?"
        )

        parameters.extend([limit, offset])

        with self._lock, self._connection() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            proposal
            for row in rows
            if (
                proposal := self._to_proposal(row)
            ) is not None
        ]

    def count_proposals(
        self,
        status: str | None = None,
        approved: bool | None = None,
        applied: bool | None = None,
    ) -> int:
        """Count proposals matching the supplied filters."""

        allowed_statuses = {
            "pending",
            "verified",
            "rejected",
            "syntax_passed",
        }

        if status is not None and status not in allowed_statuses:
            raise ValueError(
                f"Invalid status. Allowed values: {sorted(allowed_statuses)}"
            )

        conditions = []
        parameters = []

        if status is not None:
            conditions.append("verification_status = ?")
            parameters.append(status)

        if approved is not None:
            conditions.append("approved = ?")
            parameters.append(int(approved))

        if applied is not None:
            conditions.append("applied = ?")
            parameters.append(int(applied))

        where_clause = (
            " WHERE " + " AND ".join(conditions)
            if conditions
            else ""
        )

        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM patch_proposals" + where_clause,
                parameters,
            ).fetchone()

        return int(row[0])

    # ========================================================
    # UPDATE VERIFICATION STATUS
    # ========================================================

    def mark_verified(
        self,
        proposal_id: str,
        status: str,
    ) -> PatchProposal:
        """
        Update verification status.

        Allowed statuses:
        pending, verified, rejected, syntax_passed
        """

        if status not in self.ALLOWED_VERIFICATION_STATUSES:
            raise ValueError(
                f"Invalid verification status: {status}"
            )

        with self._lock, self._connection() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM patch_proposals
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()

            proposal = self._to_proposal(row)

            if proposal is None:
                raise KeyError(
                    "Proposal not found."
                )

            if proposal.applied:
                raise ValueError(
                    "An applied proposal cannot be re-verified."
                )

            if proposal.approved:
                raise ValueError(
                    "An approved proposal cannot be re-verified."
                )

            connection.execute(
                """
                UPDATE patch_proposals
                SET verification_status = ?
                WHERE proposal_id = ?
                """,
                (status, proposal_id),
            )

            proposal.verification_status = status

        return proposal

    # ========================================================
    # APPROVE PROPOSAL
    # ========================================================

    def approve(
        self,
        proposal_id: str,
    ) -> PatchProposal:
        """
        Approve a successfully verified proposal.
        """

        with self._lock, self._connection() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM patch_proposals
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()

            proposal = self._to_proposal(row)

            if proposal is None:
                raise KeyError(
                    "Proposal not found."
                )

            if proposal.verification_status != "verified":
                raise ValueError(
                    "Only successfully verified proposals can be approved."
                )

            if proposal.applied:
                raise ValueError(
                    "This proposal has already been applied."
                )

            connection.execute(
                """
                UPDATE patch_proposals
                SET approved = 1
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            )

            proposal.approved = True

        return proposal

    # ========================================================
    # MARK PROPOSAL AS APPLIED
    # ========================================================

    def mark_applied(
        self,
        proposal_id: str,
    ) -> PatchProposal:
        """
        Mark a verified and approved proposal as applied.
        """

        with self._lock, self._connection() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM patch_proposals
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()

            proposal = self._to_proposal(row)

            if proposal is None:
                raise KeyError(
                    "Proposal not found."
                )

            if proposal.verification_status != "verified":
                raise ValueError(
                    "Only verified proposals can be applied."
                )

            if not proposal.approved:
                raise ValueError(
                    "Proposal requires approval."
                )

            if proposal.applied:
                raise ValueError(
                    "Proposal has already been applied."
                )

            connection.execute(
                """
                UPDATE patch_proposals
                SET applied = 1
                WHERE proposal_id = ?
                """,
                (proposal_id,),
            )

            proposal.applied = True

        return proposal


# ============================================================
# SHARED REGISTRY INSTANCE
# ============================================================

patch_registry = PatchRegistry()