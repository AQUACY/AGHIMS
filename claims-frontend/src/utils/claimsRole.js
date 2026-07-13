/** True when the user has the Claims role (primary or additional). */
export function userHasClaimsRole(user) {
  if (!user) return false;
  const roles = [user.role, ...(user.additional_roles || [])]
    .filter(Boolean)
    .map((r) => String(r).trim().toLowerCase());
  return roles.includes('claims');
}
