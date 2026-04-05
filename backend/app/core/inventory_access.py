"""
Who may use Inventory mode and inventory analytics — assignments + key roles (not Nurse/Doctor/PA by default).
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.models.ward import Ward
from app.models.department_staff_assignment import DepartmentStaffAssignment, DepartmentRole
from app.models.store_staff_assignment import StoreStaffAssignment, StoreRole

INVENTORY_MODE_ROLES = frozenset(
    {
        "Admin",
        "Management",
        "Store Manager",
        "Department Head",
        "Pharmacy Head",
        "Pharmacy",
    }
)

DASHBOARD_UNRESTRICTED_FILTER_ROLES = frozenset(
    {"Admin", "Management", "Pharmacy Head", "Pharmacy"}
)


@dataclass
class PharmacyRequisitionAccessScope:
    """Who may list/read pharmacy requisitions: oversight roles, store staff (by assignment), or IC/deputy (department only)."""

    unrestricted: bool
    store_ids: List[int]
    ic_department_ids: List[int]
    ic_ward_names: List[str]


def get_ic_managed_department_scope(db: Session, user_id: int) -> Tuple[List[int], List[str]]:
    """Department IDs and ward names for IC/deputy assignments (same Ward join as dashboard)."""
    rows = (
        db.query(Ward.id, Ward.name)
        .join(DepartmentStaffAssignment, DepartmentStaffAssignment.department_id == Ward.id)
        .filter(
            and_(
                DepartmentStaffAssignment.user_id == user_id,
                DepartmentStaffAssignment.is_active == True,
                DepartmentStaffAssignment.role.in_([DepartmentRole.IC, DepartmentRole.DEPUTY]),
            )
        )
        .all()
    )
    ids = sorted({r[0] for r in rows if r[0] is not None})
    names = sorted({r[1] for r in rows if r[1]})
    return ids, names


def get_pharmacy_requisition_access_scope(db: Session, user: User) -> PharmacyRequisitionAccessScope:
    """
    Resolves list/detail access for pharmacy requisitions.
    Order: super admin / Pharmacy oversight → all; store assignment → that store(s); IC/deputy → department(s); else none.
    """
    u = (
        db.query(User)
        .options(joinedload(User.additional_roles))
        .filter(User.id == user.id)
        .first()
    )
    additional_roles = [ur.role for ur in (u.additional_roles if u else [])]
    all_names = {user.role, *additional_roles}
    is_super = bool(getattr(user, "is_super_admin", False))
    if is_super or bool(all_names & DASHBOARD_UNRESTRICTED_FILTER_ROLES):
        return PharmacyRequisitionAccessScope(True, [], [], [])

    store_ids = get_assigned_store_ids(db, user.id)
    if store_ids:
        return PharmacyRequisitionAccessScope(False, store_ids, [], [])

    ic_ids, ic_names = get_ic_managed_department_scope(db, user.id)
    if ic_ids or ic_names:
        return PharmacyRequisitionAccessScope(False, [], ic_ids, ic_names)

    return PharmacyRequisitionAccessScope(False, [], [], [])


def pharmacy_requisition_record_allowed(
    scope: PharmacyRequisitionAccessScope,
    department_id: Optional[int],
    ward: Optional[str],
    store_id: Optional[int],
    *,
    user_id: int,
    requested_by: Optional[int],
) -> bool:
    if scope.unrestricted:
        return True
    if scope.store_ids:
        if store_id is not None and store_id in scope.store_ids:
            return True
    elif scope.ic_department_ids or scope.ic_ward_names:
        if department_id is not None and department_id in scope.ic_department_ids:
            return True
        if ward is not None and ward in set(scope.ic_ward_names):
            return True
    if requested_by is not None and requested_by == user_id:
        return True
    return False


@dataclass
class InventoryAccessFlags:
    is_department_ic_or_deputy: bool
    has_store_manager_assignment: bool
    has_store_department_head_assignment: bool
    can_access_inventory_mode: bool


@dataclass
class InventoryDashboardScope:
    """How dashboard filters behave; enforced server-side on /inventory-analytics/dashboard."""

    unrestricted_filters: bool  # may choose any store / department
    assigned_store_ids: List[int]  # store staff: analytics limited to these stores
    ic_managed_ward_names: List[str]  # IC/deputy: analytics limited to these ward names


def get_ic_managed_ward_names(db: Session, user_id: int) -> List[str]:
    rows = (
        db.query(Ward.name)
        .join(DepartmentStaffAssignment, DepartmentStaffAssignment.department_id == Ward.id)
        .filter(
            and_(
                DepartmentStaffAssignment.user_id == user_id,
                DepartmentStaffAssignment.is_active == True,
                DepartmentStaffAssignment.role.in_([DepartmentRole.IC, DepartmentRole.DEPUTY]),
            )
        )
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


def get_assigned_store_ids(db: Session, user_id: int) -> List[int]:
    rows = (
        db.query(StoreStaffAssignment.store_id)
        .filter(
            and_(
                StoreStaffAssignment.user_id == user_id,
                StoreStaffAssignment.is_active == True,
            )
        )
        .all()
    )
    return sorted({r[0] for r in rows if r[0] is not None})


def get_inventory_dashboard_scope(db: Session, user: User, additional_roles: list[str]) -> InventoryDashboardScope:
    all_names = {user.role, *additional_roles}
    is_super = bool(getattr(user, "is_super_admin", False))
    if is_super or bool(all_names & DASHBOARD_UNRESTRICTED_FILTER_ROLES):
        return InventoryDashboardScope(True, [], [])

    store_ids = get_assigned_store_ids(db, user.id)
    if store_ids:
        return InventoryDashboardScope(False, store_ids, [])

    wards = get_ic_managed_ward_names(db, user.id)
    if wards:
        return InventoryDashboardScope(False, [], wards)

    return InventoryDashboardScope(False, [], [])


def resolve_inventory_dashboard_filters(
    scope: InventoryDashboardScope,
    requested_store_id: Optional[int],
    requested_department: Optional[str],
) -> Tuple[Optional[List[int]], Optional[List[str]]]:
    """
    Returns (store_ids_filter, department_names_filter) for queries.
    None means no filter on that axis.
    Raises HTTPException if the user requests out-of-scope values.
    """
    if (
        not scope.unrestricted_filters
        and not scope.assigned_store_ids
        and not scope.ic_managed_ward_names
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No analytics scope for your account (needs store or department assignment).",
        )

    dept_in = (requested_department or "").strip() or None

    if scope.unrestricted_filters:
        sids = [requested_store_id] if requested_store_id is not None else None
        dnames = [dept_in] if dept_in else None
        return sids, dnames

    if scope.assigned_store_ids:
        allowed = set(scope.assigned_store_ids)
        if requested_store_id is not None and requested_store_id not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may only view analytics for your assigned store(s).",
            )
        return list(allowed), None

    if scope.ic_managed_ward_names:
        allowed_w = set(scope.ic_managed_ward_names)
        if dept_in is not None and dept_in not in allowed_w:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may only view analytics for department(s) you are assigned to lead.",
            )
        return None, list(allowed_w)

    return None, None


def user_may_print_fulfilled_requisition(db: Session, user: User, requisition_store_id: Optional[int]) -> bool:
    """Only store manager / store department-head assignments for that store may print slips (plus super admin)."""
    from app.core.audit import is_super_admin

    if is_super_admin(user):
        return True
    if requisition_store_id is None:
        return False
    row = (
        db.query(StoreStaffAssignment)
        .filter(
            and_(
                StoreStaffAssignment.user_id == user.id,
                StoreStaffAssignment.store_id == requisition_store_id,
                StoreStaffAssignment.is_active == True,
                StoreStaffAssignment.role.in_([StoreRole.STORE_MANAGER, StoreRole.DEPARTMENT_HEAD]),
            )
        )
        .first()
    )
    return row is not None


def user_may_view_ward_stock(
    db: Session,
    user: User,
    additional_roles: list[str],
    ward_name: str,
) -> bool:
    """IC/deputy: only own ward(s). Store staff: any ward (rows filtered by store). Unrestricted: any."""
    from app.core.audit import is_super_admin

    if is_super_admin(user):
        return True
    all_names = {user.role, *additional_roles}
    if bool(all_names & DASHBOARD_UNRESTRICTED_FILTER_ROLES):
        return True

    scope = get_inventory_dashboard_scope(db, user, additional_roles)
    if scope.assigned_store_ids:
        return True
    if scope.ic_managed_ward_names:
        return ward_name in scope.ic_managed_ward_names
    return False


def get_inventory_access_flags(db: Session, user: User, additional_roles: list[str]) -> InventoryAccessFlags:
    uid = user.id
    ic_or_deputy = (
        db.query(DepartmentStaffAssignment)
        .filter(
            and_(
                DepartmentStaffAssignment.user_id == uid,
                DepartmentStaffAssignment.is_active == True,
                DepartmentStaffAssignment.role.in_([DepartmentRole.IC, DepartmentRole.DEPUTY]),
            )
        )
        .first()
        is not None
    )
    has_sm = (
        db.query(StoreStaffAssignment)
        .filter(
            and_(
                StoreStaffAssignment.user_id == uid,
                StoreStaffAssignment.is_active == True,
                StoreStaffAssignment.role == StoreRole.STORE_MANAGER,
            )
        )
        .first()
        is not None
    )
    has_sdh = (
        db.query(StoreStaffAssignment)
        .filter(
            and_(
                StoreStaffAssignment.user_id == uid,
                StoreStaffAssignment.is_active == True,
                StoreStaffAssignment.role == StoreRole.DEPARTMENT_HEAD,
            )
        )
        .first()
        is not None
    )
    all_names = {user.role, *additional_roles}
    role_ok = bool(all_names & INVENTORY_MODE_ROLES)
    is_super = bool(getattr(user, "is_super_admin", False))
    can = is_super or role_ok or ic_or_deputy or has_sm or has_sdh
    return InventoryAccessFlags(
        is_department_ic_or_deputy=ic_or_deputy,
        has_store_manager_assignment=has_sm,
        has_store_department_head_assignment=has_sdh,
        can_access_inventory_mode=can,
    )
