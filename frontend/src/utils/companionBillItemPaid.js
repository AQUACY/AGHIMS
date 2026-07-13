/** Shared paid-state for companion visit line items (deposit-only, mixed, cash). */

export function companionItemRowAmount(row) {
  return (Number(row.unit_price) || 0) * (Number(row.quantity) || 1);
}

export function isCompanionBillItemPaid(row) {
  if (companionItemRowAmount(row) === 0) return true;
  const T = companionItemRowAmount(row);
  const ln = String(row.admission_deposit_line_receipt || '').trim();
  const rn = String(row.receipt_number || '').trim();
  const rawApplied = row.admission_deposit_applied;
  const pm = (row.payment_method || '').trim();

  if (rawApplied == null && pm === 'admission_deposit') {
    return Boolean(rn || ln);
  }
  if (rawApplied != null) {
    const rem = Math.round((T - Number(rawApplied)) * 100) / 100;
    if (rem <= 0.01) return Boolean(ln);
    return Boolean(ln && rn);
  }
  return Boolean(rn);
}

export function companionBillPaidLabel(row) {
  if (companionItemRowAmount(row) === 0) return 'Paid (0.00)';
  const ln = String(row.admission_deposit_line_receipt || '').trim();
  const rn = String(row.receipt_number || '').trim();
  if ((row.payment_method || '') === 'mixed' && ln && rn) {
    return `Deposit ${ln} + top-up ${rn}`;
  }
  if ((row.payment_method || '') === 'admission_deposit') {
    const show = ln || rn;
    return show ? `Admission deposit · ${show}` : 'Paid';
  }
  if (rn) return `Receipt ${rn}`;
  if (ln) return `Admission deposit · ${ln}`;
  return 'Paid';
}
