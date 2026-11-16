"""T197 local skill proposal and admin-review workflow.

The workflow stores the exact T196 inputs for review.  It intentionally does
not install, load, execute, or grant permissions to a skill.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .skill_manifest import SkillManifestError, parse_skill_package
from .models import SkillProposal


class SkillApprovalError(ValueError):
    """Raised when a proposal or review cannot proceed safely."""


def _proposal_digest(*, skill_md: str, manifest_json: str, content_diff: str) -> str:
    """Bind the exact review inputs without normalizing or executing them."""
    payload = b""
    for value in (skill_md, manifest_json, content_diff):
        encoded = value.encode("utf-8")
        payload += len(encoded).to_bytes(8, "big") + encoded
    return hashlib.sha256(b"skill-proposal-v1\n" + payload).hexdigest()


def propose_skill(*, skill_md: str, manifest_json: str, proposer_kind: str, proposer_id: str, content_diff: str = "") -> SkillProposal:
    if proposer_kind not in SkillProposal.ProposerKind.values:
        raise SkillApprovalError("Unknown proposal actor kind.")
    if not isinstance(proposer_id, str) or not proposer_id.strip() or len(proposer_id) > 128:
        raise SkillApprovalError("Proposal actor identity is invalid.")
    if not isinstance(content_diff, str) or len(content_diff) > 200_000:
        raise SkillApprovalError("Proposal diff is invalid or too large.")
    try:
        parsed = parse_skill_package(skill_md, manifest_json)
    except (SkillManifestError, TypeError) as exc:
        raise SkillApprovalError("Skill package is not a valid T196 package.") from exc
    return SkillProposal.objects.create(
        name=parsed.name,
        version=parsed.version,
        skill_md=skill_md,
        manifest_json=manifest_json,
        content_diff=content_diff,
        proposer_kind=proposer_kind,
        proposer_id=proposer_id.strip(),
        proposal_digest=_proposal_digest(
            skill_md=skill_md, manifest_json=manifest_json, content_diff=content_diff
        ),
    )


def review_skill_proposal(proposal_id: UUID | str, *, actor, decision: str, note: str = "") -> SkillProposal:
    """Approve or reject a proposal using a fresh persisted admin identity.

    A runtime agent, service principal, anonymous object, normal user, stale
    user, or unsaved user is denied before the proposal is locked.
    """
    if decision not in (SkillProposal.State.APPROVED, SkillProposal.State.REJECTED):
        raise SkillApprovalError("Review decision is invalid.")
    if not isinstance(note, str) or len(note) > 512:
        raise SkillApprovalError("Review note is invalid or too large.")
    user_model = get_user_model()
    if not isinstance(actor, user_model) or not getattr(actor, "pk", None):
        raise PermissionDenied("Only a persisted admin user may review skills.")
    try:
        reviewer = user_model.objects.get(pk=actor.pk)
    except user_model.DoesNotExist as exc:
        raise PermissionDenied("Only a persisted admin user may review skills.") from exc
    if not reviewer.is_active or not reviewer.is_staff:
        raise PermissionDenied("Only an active staff user may review skills.")

    with transaction.atomic():
        proposal = SkillProposal.objects.select_for_update().get(pk=proposal_id)
        if proposal.state != SkillProposal.State.PROPOSED:
            raise SkillApprovalError("Only proposed skills may be reviewed.")
        # Re-parse the exact stored bytes immediately before review.  A
        # malformed package can never become approved through this path.
        try:
            parsed = parse_skill_package(proposal.skill_md, proposal.manifest_json)
        except (SkillManifestError, TypeError) as exc:
            raise SkillApprovalError("Stored skill package is no longer valid.") from exc
        if (parsed.name, parsed.version) != (proposal.name, proposal.version):
            raise SkillApprovalError("Stored proposal metadata is inconsistent.")
        expected_digest = _proposal_digest(
            skill_md=proposal.skill_md,
            manifest_json=proposal.manifest_json,
            content_diff=proposal.content_diff,
        )
        if proposal.proposal_digest != expected_digest:
            raise SkillApprovalError("Stored skill content or diff was altered after proposal.")
        proposal.state = decision
        proposal.reviewed_by = reviewer
        proposal.reviewed_at = timezone.now()
        proposal.review_note = note.strip()
        # The model's immutable save guard is bypassed only for this explicit,
        # locked state transition; no package content is ever changed.
        type(proposal).objects.filter(pk=proposal.pk, state=SkillProposal.State.PROPOSED).update(
            state=proposal.state,
            reviewed_by=reviewer,
            reviewed_at=proposal.reviewed_at,
            review_note=proposal.review_note,
        )
        return SkillProposal.objects.get(pk=proposal.pk)
