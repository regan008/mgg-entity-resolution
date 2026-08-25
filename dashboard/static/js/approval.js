/**
 * Shared "unapproved edits" warning for the venue review screens.
 *
 * Approve writes a point-in-time snapshot (venue_assignments_approved.csv).
 * Any edit afterwards changes only the draft, so the snapshot goes stale — and
 * assign_ids.py --commit reads the snapshot. Committing then would silently
 * discard the newer edits (the script now refuses outright), so both venue
 * views surface this state and point at the Approve button.
 *
 * Usage: renderApprovalWarning(approval, "stale-warning", "stale-detail")
 * where `approval` is the object returned under `approval` by the venue
 * summary / records endpoints.
 */
function renderApprovalWarning(approval, warningElId, detailElId) {
    const box = document.getElementById(warningElId);
    if (!box) return;
    const detail = detailElId ? document.getElementById(detailElId) : null;

    if (!approval || !approval.stale) {
        box.classList.add("hidden");
        return;
    }

    let msg = "You've edited groups since your last approval. "
            + "Commit reads the approved snapshot, so these edits won't reach the "
            + "database until you approve again.";
    if (approval.approved_venues != null && approval.draft_venues != null) {
        msg += ` (Approved snapshot: ${approval.approved_venues} venues · `
             + `current: ${approval.draft_venues} venues.)`;
    }
    if (detail) {
        detail.textContent = msg;
    } else {
        box.textContent = msg;
    }
    box.classList.remove("hidden");
}
