<template>
  <q-page class="hms-page">
    <HmsPageHeader title="Billing" subtitle="Search patients, build bills, and issue receipts.">
      <template #actions>
        <div class="module-seg" role="tablist" aria-label="Billing module">
          <button
            type="button"
            role="tab"
            class="seg-btn"
            :class="{ active: billingModule === 'opd' }"
            :aria-selected="billingModule === 'opd'"
            @click="billingModule = 'opd'"
          >
            OPD
          </button>
          <button
            type="button"
            role="tab"
            class="seg-btn"
            :class="{ active: billingModule === 'ipd' }"
            :aria-selected="billingModule === 'ipd'"
            @click="billingModule = 'ipd'"
          >
            IPD
          </button>
        </div>
      </template>
    </HmsPageHeader>

    <!-- Patient Search -->
    <section v-if="!patient" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Search patient</div>
          <div class="panel-sub">Enter a card number to load encounters and bills.</div>
        </div>
      </div>
      <div class="panel-body search-body">
        <input
          v-model="cardNumber"
          type="search"
          class="tool-input tool-input--search tool-input--grow"
          placeholder="Patient card number"
          :disabled="loadingPatient"
          @keyup.enter="searchPatient"
        />
        <HmsButton
          variant="primary"
          size="sm"
          :loading="loadingPatient"
          @click="searchPatient"
        >
          Search
        </HmsButton>
      </div>
    </section>

    <!-- Patient Info & Encounter Selection -->
    <div v-if="patient" class="patient-hero">
      <div class="hero-main">
        <div class="hero-avatar">{{ patientInitials }}</div>
        <div class="hero-text">
          <div class="hero-name-row">
            <h1 class="hero-name">{{ patientDisplayName }}</h1>
            <HmsBadge :tone="patient.insured ? 'success' : 'warning'">
              {{ patient.insured ? 'Insured' : 'Cash' }}
            </HmsBadge>
            <HmsBadge tone="info">{{ billingModule === 'opd' ? 'OPD' : 'IPD' }}</HmsBadge>
          </div>
          <div class="hero-meta">
            <span class="mono">{{ patient.card_number }}</span>
            <template v-if="selectedEncounter && selectedEncounter.ccc_number">
              <span class="sep">·</span>
              <span>CCC {{ selectedEncounter.ccc_number }}</span>
            </template>
            <template v-else-if="selectedEncounter && !selectedEncounter.ccc_number">
              <span class="sep">·</span>
              <span>Cash &amp; carry</span>
            </template>
            <template v-if="selectedWardAdmission && billingModule === 'ipd'">
              <span class="sep">·</span>
              <span>Ward {{ selectedWardAdmission.ward }} · Bed {{ selectedWardAdmission.bed_number || 'N/A' }}</span>
            </template>
          </div>
        </div>
      </div>
      <div class="hero-actions">
        <HmsButton variant="ghost" size="sm" @click="clearSearch">Clear</HmsButton>
        <HmsButton
          v-if="showRecalculateButton"
          variant="healthcare"
          size="sm"
          @click="openRecalculateDialog"
        >
          Update to insured
        </HmsButton>
      </div>
    </div>

    <section v-if="patient" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">
            {{ billingModule === 'opd' ? 'OPD encounter' : 'IPD admission' }}
          </div>
          <div class="panel-sub">
            {{ filteredEncounters.length }} option{{ filteredEncounters.length === 1 ? '' : 's' }} available
          </div>
        </div>
      </div>
      <div class="panel-body">
        <div v-if="filteredEncounters.length > 0" class="encounter-row">
          <q-select
            v-model="selectedEncounterId"
            :options="filteredEncounters"
            option-value="id"
            option-label="label"
            outlined
            dense
            :label="billingModule === 'opd' ? 'OPD Encounter' : 'IPD Admission'"
            emit-value
            map-options
            class="encounter-select"
            @update:model-value="loadEncounterData"
          />
          <div class="badge-row">
            <HmsBadge v-if="selectedEncounter && selectedEncounter.ccc_number" tone="success">
              Insured · CCC {{ selectedEncounter.ccc_number }}
            </HmsBadge>
            <HmsBadge v-else-if="selectedEncounter && !selectedEncounter.ccc_number" tone="warning">
              Cash &amp; carry
            </HmsBadge>
            <HmsBadge v-if="selectedWardAdmission && billingModule === 'ipd'" tone="info">
              {{ selectedWardAdmission.ward }} · Bed {{ selectedWardAdmission.bed_number || 'N/A' }}
            </HmsBadge>
          </div>
        </div>
        <div v-else class="empty-hint">
          {{ billingModule === 'opd' ? 'No active OPD encounters found for this patient.' : 'No active IPD admissions found for this patient.' }}
        </div>
      </div>
    </section>

    <!-- Billing Section -->
    <div v-if="selectedEncounterId" class="billing-workspace">
      <!-- Auto-calculated Bill Items -->
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Diagnoses</div>
            <div class="panel-sub">Auto-calculated GDRG items ready to bill</div>
          </div>
          <div class="panel-actions">
            <HmsButton
              variant="secondary"
              size="sm"
              :loading="calculatingItems"
              @click="loadAutoCalculatedItems"
            >
              Recalculate
            </HmsButton>
          </div>
        </div>
        <div v-if="autoCalculatedItems.length > 0">
          <q-table
            class="diag-table"
            :rows="autoCalculatedItems"
            :columns="billItemColumns"
            row-key="item_code"
            flat
            dense
          >
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <HmsButton
                  variant="primary"
                  size="sm"
                  :loading="addingDiagnosisId === props.row.item_code"
                  :disabled="addingDiagnosisId !== null"
                  @click="addDiagnosisToBill(props.row)"
                >
                  Add to bill
                </HmsButton>
              </q-td>
            </template>
          </q-table>
          <div class="panel-footer">
            <span class="total-label">Total</span>
            <span class="total-value">₵{{ autoCalculatedTotal.toFixed(2) }}</span>
          </div>
        </div>
        <div v-else-if="!calculatingItems" class="empty-hint">
          No unbilled diagnoses with GDRG codes found.
          <br />
          <span class="empty-note">Prescriptions and investigations are billed when confirmed by their respective staff.</span>
        </div>
      </section>

      <!-- Manual Bill Items -->
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Bill items</div>
            <div class="panel-sub">{{ billItems.length }} item{{ billItems.length === 1 ? '' : 's' }} staged</div>
          </div>
          <div class="panel-actions">
            <HmsButton variant="secondary" size="sm" @click="showAddItemDialog = true">
              Add item
            </HmsButton>
          </div>
        </div>
        <q-table
          v-if="billItems.length > 0"
          class="diag-table"
          :rows="billItems"
          :columns="billItemColumns"
          row-key="id"
          flat
          dense
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <HmsButton variant="ghost" size="sm" @click="removeBillItem(props.rowIndex)">
                Remove
              </HmsButton>
            </q-td>
          </template>
        </q-table>
        <div v-else class="empty-hint">
          No items added. Use Add item or Add to bill from diagnoses.
        </div>

        <div class="panel-body">
          <q-input
            v-model="miscellaneous"
            outlined
            dense
            label="Miscellaneous notes"
            type="textarea"
            rows="2"
            class="full-width"
            hint="Additional items or notes not in the price list"
          />
          <div class="create-row">
            <div class="total-block">
              <span class="total-label">Total</span>
              <span class="total-value">GHC {{ totalAmount.toFixed(2) }}</span>
            </div>
            <HmsButton
              variant="primary"
              size="sm"
              :loading="creating"
              :disabled="billItems.length === 0"
              @click="createBill"
            >
              Create bill
            </HmsButton>
          </div>
        </div>
      </section>

      <!-- Existing Bills -->
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">
              {{ billingModule === 'ipd' ? 'IPD bills' : 'Existing bills' }}
            </div>
            <div class="panel-sub">View, pay, or manage receipts</div>
          </div>
          <div class="panel-actions">
            <HmsButton
              variant="secondary"
              size="sm"
              :loading="loadingBills"
              @click="loadExistingBills"
            >
              Refresh
            </HmsButton>
          </div>
        </div>

        <!-- IPD Bills Grouped by Ward Admission -->
        <div v-if="billingModule === 'ipd' && groupedIPDBills.length > 0" class="ipd-groups">
          <div v-for="group in groupedIPDBills" :key="group.wardAdmissionId" class="ipd-group">
            <div class="ipd-group-head">
              <div>
                <div class="ipd-group-title">Ward {{ group.ward }} · Bed {{ group.bedNumber || 'N/A' }}</div>
                <div class="ipd-group-sub">
                  Admission {{ group.wardAdmissionId }} · Encounter #{{ group.encounterId }}
                </div>
              </div>
              <div class="ipd-group-totals">
                Total ₵{{ group.total.toFixed(2) }}
                <span class="sep">·</span>
                Paid ₵{{ group.paid.toFixed(2) }}
                <span class="sep">·</span>
                Balance ₵{{ group.balance.toFixed(2) }}
              </div>
            </div>
            <q-table
              class="diag-table"
              :rows="group.bills"
              :columns="existingBillColumns"
              row-key="id"
              flat
              dense
            >
              <template v-slot:body-cell-encounter_id="props">
                <q-td :props="props">
                  <span class="mono">#{{ props.value }}</span>
                </q-td>
              </template>
              <template v-slot:body-cell-services="props">
                <q-td :props="props">
                  <div class="services-cell" :title="props.value">{{ props.value }}</div>
                </q-td>
              </template>
              <template v-slot:body-cell-remaining_balance="props">
                <q-td :props="props">
                  <span :class="(props.row.total_amount - props.row.paid_amount) > 0 ? 'amt-due' : 'amt-ok'">
                    {{ (props.row.total_amount - props.row.paid_amount) > 0 ? `₵${(props.row.total_amount - props.row.paid_amount).toFixed(2)}` : '₵0.00' }}
                  </span>
                </q-td>
              </template>
              <template v-slot:body-cell-is_paid="props">
                <q-td :props="props">
                  <HmsBadge :tone="props.value ? 'success' : 'warning'">
                    {{ props.value ? 'Paid' : 'Unpaid' }}
                  </HmsBadge>
                </q-td>
              </template>
              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <div class="row-actions">
                    <HmsButton variant="ghost" size="sm" @click="viewBillDetails(props.row.id)">View</HmsButton>
                    <HmsButton
                      v-if="!props.row.is_paid"
                      variant="primary"
                      size="sm"
                      @click="openReceiptDialog(props.row)"
                    >
                      Pay
                    </HmsButton>
                    <HmsButton
                      v-if="authStore.userRole === 'Admin'"
                      variant="secondary"
                      size="sm"
                      :loading="updatingBillId === props.row.id"
                      @click="editBill(props.row)"
                    >
                      Edit
                    </HmsButton>
                    <HmsButton
                      v-if="props.row.is_paid && authStore.userRole === 'Admin'"
                      variant="healthcare"
                      size="sm"
                      @click="refundReceipt(props.row)"
                    >
                      Refund
                    </HmsButton>
                    <HmsButton
                      v-if="authStore.userRole === 'Admin'"
                      variant="ghost"
                      size="sm"
                      @click="confirmDeleteBill(props.row)"
                    >
                      Delete
                    </HmsButton>
                  </div>
                </q-td>
              </template>
            </q-table>
          </div>
        </div>

        <!-- OPD Bills (Regular Table) -->
        <q-table
          v-if="billingModule === 'opd' && existingBills.length > 0"
          class="diag-table"
          :rows="existingBills"
          :columns="existingBillColumns"
          row-key="id"
          flat
          dense
          :loading="loadingBills"
        >
          <template v-slot:body-cell-encounter_id="props">
            <q-td :props="props">
              <span class="mono">#{{ props.value }}</span>
            </q-td>
          </template>
          <template v-slot:body-cell-services="props">
            <q-td :props="props">
              <div class="services-cell" :title="props.value">{{ props.value }}</div>
            </q-td>
          </template>
          <template v-slot:body-cell-remaining_balance="props">
            <q-td :props="props">
              <span :class="(props.row.total_amount - props.row.paid_amount) > 0 ? 'amt-due' : 'amt-ok'">
                {{ (props.row.total_amount - props.row.paid_amount) > 0 ? `₵${(props.row.total_amount - props.row.paid_amount).toFixed(2)}` : '₵0.00' }}
              </span>
            </q-td>
          </template>
          <template v-slot:body-cell-is_paid="props">
            <q-td :props="props">
              <HmsBadge :tone="props.value ? 'success' : 'warning'">
                {{ props.value ? 'Paid' : 'Unpaid' }}
              </HmsBadge>
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row-actions">
                <HmsButton variant="ghost" size="sm" @click="viewBillDetails(props.row.id)">View</HmsButton>
                <HmsButton
                  v-if="!props.row.is_paid"
                  variant="primary"
                  size="sm"
                  @click="openReceiptDialog(props.row)"
                >
                  Pay
                </HmsButton>
                <HmsButton
                  v-if="authStore.userRole === 'Admin'"
                  variant="secondary"
                  size="sm"
                  :loading="updatingBillId === props.row.id"
                  @click="editBill(props.row)"
                >
                  Edit
                </HmsButton>
                <HmsButton
                  v-if="props.row.is_paid && authStore.userRole === 'Admin'"
                  variant="healthcare"
                  size="sm"
                  @click="refundReceipt(props.row)"
                >
                  Refund
                </HmsButton>
                <HmsButton
                  v-if="authStore.userRole === 'Admin'"
                  variant="ghost"
                  size="sm"
                  @click="confirmDeleteBill(props.row)"
                >
                  Delete
                </HmsButton>
              </div>
            </q-td>
          </template>
        </q-table>
        <div v-if="billingModule === 'opd' && existingBills.length === 0 && !loadingBills" class="empty-hint">
          No bills found for this encounter
        </div>
        <div v-if="billingModule === 'ipd' && groupedIPDBills.length === 0 && !loadingBills" class="empty-hint">
          No IPD bills found for this patient
        </div>
      </section>
    </div>

    <!-- Bill Details Dialog -->
    <q-dialog v-model="showBillDetailsDialog">
      <q-card class="billing-dialog-card" style="min-width: min(700px, 96vw); max-width: 900px">
        <q-card-section class="billing-dialog-head">
          <div class="dialog-head-row">
            <div>
              <div class="dialog-title">Bill details</div>
              <div class="dialog-sub" v-if="currentBillDetails">{{ currentBillDetails.bill_number }}</div>
            </div>
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
        </q-card-section>
        <q-card-section v-if="currentBillDetails">
          <div class="row q-mb-md">
            <div class="col-6">
              <div class="text-caption text-grey-7">Bill Number</div>
              <div class="text-body1">{{ currentBillDetails.bill_number }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Created At</div>
              <div class="text-body1">{{ new Date(currentBillDetails.created_at).toLocaleString() }}</div>
            </div>
          </div>
          <div class="row q-mb-md">
            <div class="col-6">
              <div class="text-caption text-grey-7">Total Amount</div>
              <div class="text-h6">₵{{ currentBillDetails.total_amount.toFixed(2) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Paid Amount</div>
              <div class="text-h6">₵{{ currentBillDetails.paid_amount.toFixed(2) }}</div>
            </div>
          </div>
          <div class="q-mb-md">
            <HmsBadge :tone="currentBillDetails.is_paid ? 'success' : 'warning'">
              {{ currentBillDetails.is_paid ? 'Paid' : 'Unpaid' }}
            </HmsBadge>
          </div>
          <div v-if="currentBillDetails.miscellaneous" class="q-mb-md">
            <div class="text-caption text-grey-7">Miscellaneous Notes</div>
            <div class="text-body2">{{ currentBillDetails.miscellaneous }}</div>
          </div>
          <div class="text-subtitle1 q-mt-md q-mb-sm">Bill Items</div>
          
          <!-- Grouped Bill Items -->
          <div v-for="(group, groupName) in groupedBillItems" :key="groupName" class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm" style="color: #1976d2; font-weight: bold;">
              {{ groupName }}
            </div>
            <q-table
              :rows="group"
              :columns="billDetailColumns"
              row-key="id"
              flat
              dense
              class="q-mb-md"
            >
            <template v-slot:body-cell-receipt_numbers="props">
              <q-td :props="props">
                <div v-if="props.row.payment_info && props.row.payment_info.length > 0">
                  <div
                    v-for="(payment, index) in props.row.payment_info"
                    :key="index"
                    class="row items-center q-gutter-xs q-mb-xs"
                  >
                    <q-chip
                      size="sm"
                      :color="payment.refunded ? 'grey' : 'primary'"
                      text-color="white"
                      :label="payment.receipt_number"
                    >
                      <q-tooltip>
                        Paid: ₵{{ payment.amount_paid.toFixed(2) }}<br />
                        Method: {{ payment.payment_method }}<br />
                        Date: {{ new Date(payment.issued_at).toLocaleString() }}<br />
                        Status: {{ payment.refunded ? 'Refunded' : 'Active' }}
                      </q-tooltip>
                    </q-chip>
                    <q-btn
                      v-if="!payment.refunded"
                      size="xs"
                      icon="delete"
                      color="negative"
                      flat
                      round
                      dense
                      @click="confirmDeleteReceipt(payment.receipt_id, props.row.id)"
                    >
                      <q-tooltip>Delete Receipt</q-tooltip>
                    </q-btn>
                    <q-btn
                      v-if="!payment.refunded && authStore.userRole === 'Admin'"
                      size="xs"
                      icon="undo"
                      color="orange"
                      flat
                      round
                      dense
                      @click="confirmRefundReceipt(payment.receipt_id)"
                    >
                      <q-tooltip>Refund Receipt</q-tooltip>
                    </q-btn>
                  </div>
                  <q-btn
                    v-if="props.row.remaining_balance > 0"
                    size="xs"
                    icon="add"
                    color="primary"
                    label="Add Receipt"
                    flat
                    dense
                    @click="openAddReceiptDialog(props.row)"
                    class="q-mt-xs"
                  />
                </div>
                <div v-else>
                  <span class="text-grey-7 q-mr-sm">No receipts</span>
                  <q-btn
                    size="xs"
                    icon="add"
                    color="primary"
                    label="Add Receipt"
                    flat
                    dense
                    @click="openAddReceiptDialog(props.row)"
                  />
                </div>
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="authStore.userRole === 'Admin'"
                  size="sm"
                  color="secondary"
                  icon="edit"
                  flat
                  round
                  dense
                  @click="editBillItem(props.row)"
                  :loading="updatingBillItemId === props.row.id"
                >
                  <q-tooltip>Edit bill item (Admin only)</q-tooltip>
                </q-btn>
              </q-td>
            </template>
            </q-table>
            <div class="text-caption text-grey-7 q-mt-xs">
              Subtotal: ₵{{ groupSubtotal(group).toFixed(2) }}
            </div>
          </div>
          
          <div v-if="Object.keys(groupedBillItems).length === 0" class="text-grey-7 q-pa-md text-center">
            No bill items found
          </div>
          
          <div class="q-mt-md" style="border-top: 2px solid #1976d2; padding-top: 8px;">
            <div class="text-subtitle1 text-weight-bold">
              Grand Total: ₵{{ currentBillDetails?.total_amount.toFixed(2) || '0.00' }}
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Bill Item Dialog -->
    <q-dialog v-model="showEditBillItemDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="row items-center">
            <div class="text-h6">Edit Bill Item</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
          <div class="text-caption text-warning q-mt-sm">
            Admin: Edit individual bill item. Changes will update the bill total automatically.
          </div>
        </q-card-section>
        <q-card-section v-if="editingBillItem">
          <q-form @submit="updateBillItemSubmit" class="q-gutter-md">
            <q-input
              v-model="editBillItemForm.item_code"
              filled
              label="Item Code"
              readonly
              hint="Cannot be changed"
            />
            <q-input
              v-model="editBillItemForm.item_name"
              filled
              label="Item Name"
              readonly
              hint="Cannot be changed"
            />
            <q-input
              v-model="editBillItemForm.category"
              filled
              label="Category"
              readonly
              hint="Cannot be changed"
            />
            <q-input
              v-model.number="editBillItemForm.quantity"
              filled
              type="number"
              label="Quantity *"
              :min="1"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <q-input
              v-model.number="editBillItemForm.unit_price"
              filled
              type="number"
              step="0.01"
              label="Unit Price *"
              :min="0"
              :rules="[
                (val) => val !== null && val !== undefined || 'Unit price is required',
                (val) => val >= 0 || 'Unit price must be greater than or equal to 0'
              ]"
            />
            <div class="q-mt-md" style="border-top: 1px solid #ccc; padding-top: 8px;">
              <div class="text-subtitle2">
                Total: ₵{{ ((editBillItemForm.quantity || 0) * (editBillItemForm.unit_price || 0)).toFixed(2) }}
              </div>
            </div>
            <div class="row q-gutter-md q-mt-md">
              <q-btn
                label="Cancel"
                flat
                v-close-popup
                class="col"
              />
              <q-btn
                label="Update Item"
                type="submit"
                color="primary"
                class="col"
                :loading="updatingBillItemId !== null"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Bill Dialog -->
    <q-dialog v-model="showEditBillDialog">
      <q-card style="min-width: 800px; max-width: 1000px">
        <q-card-section>
          <div class="row items-center">
            <div class="text-h6">Edit Bill - {{ editingBill?.bill_number }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
          <div class="text-caption text-warning q-mt-sm">
            Admin: You can edit bill items. Changes will update the bill total and may affect payments.
          </div>
        </q-card-section>
        <q-card-section v-if="editingBill">
          <div class="row q-mb-md">
            <div class="col-6">
              <div class="text-caption text-grey-7">Bill Number</div>
              <div class="text-body1">{{ editingBill.bill_number }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Encounter ID</div>
              <div class="text-body1">{{ editingBill.encounter_id }}</div>
            </div>
          </div>
          <div class="text-subtitle1 q-mt-md q-mb-sm">Bill Items</div>
          
          <q-table
            :rows="editingBillItems"
            :columns="editBillItemColumns"
            row-key="id"
            flat
            dense
            class="q-mb-md"
          >
            <template v-slot:body-cell-quantity="props">
              <q-td :props="props">
                <q-input
                  v-model.number="props.row.editableQuantity"
                  type="number"
                  dense
                  filled
                  :min="1"
                  @update:model-value="updateBillItemTotal(props.row)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-unit_price="props">
              <q-td :props="props">
                <q-input
                  v-model.number="props.row.editableUnitPrice"
                  type="number"
                  dense
                  filled
                  step="0.01"
                  :min="0"
                  @update:model-value="updateBillItemTotal(props.row)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  @click="removeBillItemFromEdit(props.row)"
                  :loading="updatingBillItemId === props.row.id"
                >
                  <q-tooltip>Remove item</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
          
          <div class="q-mt-md" style="border-top: 2px solid #1976d2; padding-top: 8px;">
            <div class="text-subtitle1 text-weight-bold">
              Grand Total: ₵{{ editBillTotal.toFixed(2) }}
            </div>
          </div>
          
          <div class="row q-gutter-md q-mt-md">
            <q-btn
              label="Cancel"
              flat
              v-close-popup
              class="col"
            />
            <q-btn
              label="Update Bill"
              color="primary"
              class="col"
              @click="updateBillSubmit"
              :loading="updatingBillId !== null"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Receipt Dialog with Itemized Payment -->
    <q-dialog v-model="showReceiptDialog">
      <q-card class="billing-dialog-card" style="min-width: min(700px, 96vw); max-width: 900px">
        <q-card-section class="billing-dialog-head">
          <div class="dialog-head-row">
            <div>
              <div class="dialog-title">Issue receipt</div>
              <div class="dialog-sub">Bill {{ currentBillForReceipt?.bill_number }}</div>
            </div>
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
        </q-card-section>
        <q-card-section v-if="currentBillForReceipt">
          <div class="text-subtitle2 q-mb-md">
            Total Bill: ₵{{ currentBillForReceipt.total_amount.toFixed(2) }} | 
            Paid: ₵{{ currentBillForReceipt.paid_amount.toFixed(2) }} | 
            Balance: ₵{{ (currentBillForReceipt.total_amount - currentBillForReceipt.paid_amount).toFixed(2) }}
          </div>
          
          <div class="q-mb-md">
            <q-select
              v-model="receiptPaymentMethod"
              :options="['cash', 'card', 'mobile_money']"
              label="Payment Method"
              filled
            />
          </div>

          <div class="text-subtitle2 q-mb-sm">Select Items to Pay:</div>
          
          <!-- Grouped Receipt Items -->
          <div v-for="(group, groupName) in groupedReceiptItems" :key="groupName" class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm" style="color: #1976d2; font-weight: bold;">
              {{ groupName }}
            </div>
            <q-table
              :rows="group"
              :columns="receiptItemColumnsWithInputs"
              row-key="id"
              flat
              dense
              v-model:selected="selectedBillItems"
              selection="multiple"
            >
            <template v-slot:body-cell-receipt_number="props">
              <q-td :props="props">
                <q-input
                  v-if="receiptItemData && receiptItemData[props.row.id]"
                  v-model="receiptItemData[props.row.id].receipt_number"
                  dense
                  filled
                  placeholder="Enter receipt number"
                  :disable="!selectedBillItems.some(sel => sel.id === props.row.id)"
                />
                <span v-else>-</span>
              </q-td>
            </template>
            <template v-slot:body-cell-amount_paid="props">
              <q-td :props="props">
                <q-input
                  v-if="receiptItemData && receiptItemData[props.row.id]"
                  v-model.number="receiptItemData[props.row.id].amount_paid"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  :disable="!selectedBillItems.some(sel => sel.id === props.row.id)"
                />
                <span v-else>-</span>
              </q-td>
            </template>
            </q-table>
            <div class="text-caption text-grey-7 q-mt-xs">
              Subtotal: ₵{{ getGroupSubtotal(group) }}
            </div>
          </div>
          
          <div v-if="Object.keys(groupedReceiptItems).length === 0" class="text-grey-7 q-pa-md text-center">
            No bill items available
          </div>
          
          <div class="q-mt-md" style="border-top: 2px solid #1976d2; padding-top: 8px;">
            <div class="text-subtitle2 text-weight-bold">
              Selected Total: ₵{{ selectedTotal.toFixed(2) }}
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn
            color="primary"
            label="Issue Receipt"
            @click="createReceiptWithItems"
            :disable="selectedBillItems.length === 0 || selectedTotal <= 0"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add Manual Receipt Dialog -->
    <q-dialog v-model="showAddReceiptDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="row items-center">
            <div class="text-h6">Add Manual Receipt</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
        </q-card-section>
        <q-card-section v-if="currentBillItemForReceipt">
          <div class="q-mb-md">
            <div class="text-caption text-grey-7">Item: {{ currentBillItemForReceipt.item_name }}</div>
            <div class="text-caption text-grey-7">Total: ₵{{ currentBillItemForReceipt.total_price.toFixed(2) }}</div>
            <div class="text-caption text-grey-7">Remaining Balance: ₵{{ currentBillItemForReceipt.remaining_balance.toFixed(2) }}</div>
          </div>
          <q-form @submit="saveManualReceipt" class="q-gutter-md">
            <q-input
              v-model="manualReceiptForm.receipt_number"
              filled
              label="Receipt Number *"
              hint="Enter the manually written receipt number"
              :rules="[val => !!val || 'Receipt number is required']"
            />
            <q-input
              v-model.number="manualReceiptForm.amount_paid"
              filled
              type="number"
              label="Amount Paid *"
              step="0.01"
              :rules="[
                val => val !== null && val !== undefined && val > 0 || 'Amount must be greater than 0',
                val => {
                  const maxAmount = currentBillItemForReceipt?.remaining_balance || currentBillItemForReceipt?.total_price || 0;
                  return val <= maxAmount || `Amount cannot exceed remaining balance (₵${maxAmount.toFixed(2)})`;
                }
              ]"
            />
            <q-select
              v-model="manualReceiptForm.payment_method"
              :options="['cash', 'card', 'mobile_money']"
              label="Payment Method"
              filled
            />
            <q-card-actions align="right">
              <q-btn flat label="Cancel" v-close-popup />
              <q-btn color="primary" label="Add Receipt" type="submit" />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Recalculate Billing Dialog -->
    <q-dialog v-model="showRecalculateDialog" persistent>
      <q-card class="billing-dialog-card" style="min-width: min(500px, 96vw); max-width: 700px">
        <q-card-section class="billing-dialog-head">
          <div class="dialog-head-row">
            <div>
              <div class="dialog-title">Recalculate with insurance</div>
              <div class="dialog-sub">Update CCC and co-payment rates for all bill items</div>
            </div>
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
          <div class="text-caption text-warning q-mt-sm">
            This will update the encounter CCC number and recalculate all bill items (paid and unpaid) with insurance co-payment rates.
          </div>
        </q-card-section>
        <q-card-section>
          <div v-if="loadingOpdCcc" class="text-center q-pa-md">
            <q-spinner color="primary" size="3em" />
            <div class="q-mt-md">Loading OPD CCC information...</div>
          </div>
          <div v-else>
            <div v-if="opdCccNumber" class="q-mb-md">
              <q-banner class="bg-positive text-white q-mb-md">
                <template v-slot:avatar>
                  <q-icon name="check_circle" />
                </template>
                <div class="text-weight-bold">CCC Number Auto-Detected</div>
                <div class="text-caption">
                  Found CCC number from OPD consultation
                  <span v-if="opdEncounterInfo">
                    (Encounter #{{ opdEncounterInfo.id }} - {{ opdEncounterInfo.department }})
                  </span>
                </div>
                <div class="text-h6 q-mt-sm">{{ opdCccNumber }}</div>
              </q-banner>
            </div>
            <div v-else class="q-mb-md">
              <q-banner class="bg-warning text-dark q-mb-md">
                <template v-slot:avatar>
                  <q-icon name="warning" />
                </template>
                <div class="text-weight-bold">No OPD CCC Found</div>
                <div class="text-caption">
                  Could not auto-detect CCC number. Please enter manually.
                </div>
              </q-banner>
            </div>
            
            <q-input
              v-model="manualCccNumber"
              filled
              label="CCC Number *"
              hint="Enter or confirm the CCC number for this encounter"
              :rules="[(val) => !!val || 'CCC number is required']"
              class="q-mb-md"
            />
            
            <div class="text-caption text-grey-7 q-mt-md">
              <strong>Note:</strong> After recalculation, if bills were overpaid (paid more than the new insured amount), you will be prompted to process refunds.
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            label="Cancel"
            flat
            v-close-popup
            :disable="recalculating"
          />
          <q-btn
            label="Recalculate"
            color="primary"
            @click="recalculateBilling"
            :loading="recalculating"
            :disable="!manualCccNumber.trim() || loadingOpdCcc"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Refund Prompt Dialog -->
    <q-dialog v-model="showRefundPrompt" persistent>
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="row items-center">
            <div class="text-h6 text-warning">
              <q-icon name="warning" color="warning" class="q-mr-sm" />
              Excess Payment Detected
            </div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
        </q-card-section>
        <q-card-section v-if="recalculationResult">
          <div class="text-body1 q-mb-md">
            Billing has been recalculated successfully. However, the patient was overcharged and there is an excess payment that needs to be refunded.
          </div>
          
          <div class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm">Summary:</div>
            <div class="text-body2">
              <strong>Total Excess Payment:</strong> 
              <span class="text-negative text-weight-bold">₵{{ recalculationResult.total_excess_payment.toFixed(2) }}</span>
            </div>
            <div class="text-body2 q-mt-xs">
              <strong>Bills Updated:</strong> {{ recalculationResult.bills_updated }}
            </div>
          </div>
          
          <div v-if="recalculationResult.bills_with_excess && recalculationResult.bills_with_excess.length > 0" class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm">Bills with Excess Payments:</div>
            <q-table
              :rows="recalculationResult.bills_with_excess"
              :columns="[
                { name: 'bill_number', label: 'Bill #', field: 'bill_number', align: 'left' },
                { name: 'old_total', label: 'Old Total', field: 'old_total', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
                { name: 'new_total', label: 'New Total', field: 'new_total', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
                { name: 'paid_amount', label: 'Paid', field: 'paid_amount', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
                { name: 'excess_payment', label: 'Excess', field: 'excess_payment', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
              ]"
              row-key="bill_id"
              flat
              dense
              class="q-mb-md"
            />
          </div>
          
          <q-banner class="bg-info text-white">
            <template v-slot:avatar>
              <q-icon name="info" />
            </template>
            <div class="text-weight-bold">Next Steps:</div>
            <div class="text-caption q-mt-xs">
              Please process refunds for the excess payments. You can view each bill and refund the appropriate receipts.
            </div>
          </q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            label="Close"
            color="primary"
            @click="closeRefundPrompt"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add Item Dialog -->
    <q-dialog v-model="showAddItemDialog">
      <q-card class="billing-dialog-card" style="min-width: min(700px, 96vw); max-width: 900px">
        <q-card-section class="billing-dialog-head">
          <div class="dialog-title">Add bill item</div>
          <div class="dialog-sub">Search price list or enter a custom item</div>
        </q-card-section>
        <q-tabs v-model="addItemTab" class="text-primary">
          <q-tab name="search" label="Search from Price List" />
          <q-tab name="custom" label="Add Custom Item" />
        </q-tabs>
        <q-tab-panels v-model="addItemTab" animated>
          <!-- Search from Price List Tab -->
          <q-tab-panel name="search">
            <q-form @submit="searchAndAddItem" class="q-gutter-md">
              <q-input
                v-model="searchTerm"
                filled
                label="Search Item"
                @keyup.enter="searchItems"
                hint="Search by item code or name"
              />
              <q-select
                v-model="searchCategory"
                filled
                :options="['surgery', 'procedure', 'product', 'consumable', 'drg']"
                label="Category (Optional)"
                clearable
              />
              <q-btn
                color="primary"
                label="Search"
                @click="searchItems"
                :loading="searching"
                class="full-width"
              />
              
              <q-table
                v-if="searchResults.length > 0"
                :rows="searchResults"
                :columns="searchResultColumns"
                row-key="id"
                flat
                class="q-mt-md"
              >
                <template v-slot:body-cell-actions="props">
                  <q-td :props="props">
                    <q-btn
                      size="sm"
                      color="primary"
                      label="Add"
                      @click="addSearchResult(props.row)"
                    />
                  </q-td>
                </template>
              </q-table>
            </q-form>
          </q-tab-panel>
          
          <!-- Add Custom Item Tab -->
          <q-tab-panel name="custom">
            <q-form @submit="addCustomItem" class="q-gutter-md">
              <q-input
                v-model="customItemForm.item_code"
                filled
                label="Item Code (Optional)"
                hint="Leave blank for miscellaneous items without codes (e.g., inpatient bill, undertaking)"
                clearable
              />
              <q-input
                v-model="customItemForm.item_name"
                filled
                label="Item Name / Service Description"
                hint="Name of the service or item (required)"
                :rules="[val => !!val || 'Item name is required']"
              />
              <q-select
                v-model="customItemForm.category"
                filled
                :options="['surgery', 'procedure', 'product', 'consumable', 'drg', 'other', 'miscellaneous']"
                label="Category (Optional)"
                hint="Leave blank for miscellaneous items"
                clearable
              />
              <div class="row q-gutter-md">
                <q-input
                  v-model.number="customItemForm.quantity"
                  filled
                  type="number"
                  label="Quantity"
                  class="col"
                  :rules="[val => val > 0 || 'Quantity must be greater than 0']"
                  min="1"
                />
                <q-input
                  v-model.number="customItemForm.unit_price"
                  filled
                  type="number"
                  label="Unit Price (₵)"
                  class="col"
                  :rules="[val => val >= 0 || 'Price must be 0 or greater']"
                  min="0"
                  step="0.01"
                />
              </div>
              <div class="row q-gutter-md q-mt-md">
                <div class="col-12 text-right">
                  <strong>Total: ₵{{ ((customItemForm.quantity || 0) * (customItemForm.unit_price || 0)).toFixed(2) }}</strong>
                </div>
              </div>
              <div class="row q-gutter-md q-mt-md">
                <q-btn label="Cancel" flat v-close-popup class="col" />
                <q-btn 
                  label="Add to Bill" 
                  type="submit"
                  color="primary" 
                  class="col"
                  :disable="!customItemForm.item_name || customItemForm.unit_price < 0"
                />
              </div>
            </q-form>
          </q-tab-panel>
        </q-tab-panels>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { billingAPI, patientsAPI, encountersAPI, priceListAPI, consultationAPI } from '../services/api';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../stores/auth';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const billingModule = ref('opd'); // 'opd' or 'ipd'
const cardNumber = ref('');
const loadingPatient = ref(false);
const patient = ref(null);

const patientDisplayName = computed(() => {
  if (!patient.value) return '';
  const parts = [patient.value.name, patient.value.surname, patient.value.other_names].filter(Boolean);
  return parts.join(' ');
});

const patientInitials = computed(() => {
  if (!patient.value) return '?';
  const first = (patient.value.name || '').trim().charAt(0);
  const last = (patient.value.surname || patient.value.other_names || '').trim().charAt(0);
  const letters = `${first}${last}`.toUpperCase();
  return letters || '?';
});
const activeEncounters = ref([]);
const wardAdmissions = ref([]); // Store ward admissions for IPD filtering

const selectedEncounterId = ref(null);
const selectedEncounter = ref(null);
const selectedWardAdmission = ref(null);
const calculatingItems = ref(false);
const autoCalculatedItems = ref([]);
const addingDiagnosisId = ref(null);
const billItems = reactive([]);
const miscellaneous = ref('');
const creating = ref(false);
const existingBills = ref([]);
const loadingBills = ref(false);
const showAddItemDialog = ref(false);
const addItemTab = ref('search');
const searchTerm = ref('');
const searchCategory = ref(null);
const searching = ref(false);
const searchResults = ref([]);
const customItemForm = ref({
  item_code: '',
  item_name: '',
  category: null,
  quantity: 1,
  unit_price: 0,
});
const showBillDetailsDialog = ref(false);
const currentBillDetails = ref(null);
const showReceiptDialog = ref(false);
const currentBillForReceipt = ref(null);
const selectedBillItems = ref([]);
const receiptPaymentMethod = ref('cash');
const showAddReceiptDialog = ref(false);
// For receipt dialog - store receipt number and amount per item

// Recalculate billing with insurance
const showRecalculateDialog = ref(false);
const loadingOpdCcc = ref(false);
const opdCccNumber = ref(null);
const opdEncounterInfo = ref(null);
const manualCccNumber = ref('');
const recalculating = ref(false);
const recalculationResult = ref(null);
const showRefundPrompt = ref(false);

const closeRefundPrompt = () => {
  showRefundPrompt.value = false;
  recalculationResult.value = null;
  // Reload encounter data and bills
  loadEncounterData();
  loadExistingBills();
};
const receiptItemData = ref({}); // { bill_item_id: { receipt_number: '', amount_paid: 0 } }
const currentBillItemForReceipt = ref(null);
const manualReceiptForm = ref({
  receipt_number: '',
  amount_paid: 0,
  payment_method: 'cash',
});
const showEditBillDialog = ref(false);
const editingBill = ref(null);
const editingBillItems = ref([]);
const updatingBillId = ref(null);
const updatingBillItemId = ref(null);
const showEditBillItemDialog = ref(false);
const editingBillItem = ref(null);
const editBillItemForm = ref({
  id: null,
  item_code: '',
  item_name: '',
  category: '',
  quantity: 1,
  unit_price: 0,
});

const billItemColumns = [
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit Price', field: 'unit_price', align: 'right', format: (val) => val.toFixed(2) },
  { name: 'total_price', label: 'Total', field: 'total_price', align: 'right', format: (val) => val.toFixed(2) },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const existingBillColumns = [
  { name: 'bill_number', label: 'Bill Number', field: 'bill_number', align: 'left' },
  { name: 'encounter_id', label: 'Encounter', field: 'encounter_id', align: 'center' },
  { name: 'services', label: 'Services', field: 'services', align: 'left' },
  { name: 'total_amount', label: 'Total Amount', field: 'total_amount', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'paid_amount', label: 'Paid', field: 'paid_amount', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'remaining_balance', label: 'Balance', field: 'remaining_balance', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'is_paid', label: 'Status', field: 'is_paid', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Filter encounters based on billing module (OPD vs IPD)
const filteredEncounters = computed(() => {
  if (billingModule.value === 'opd') {
    // OPD: Show encounters that don't have ward admissions
    if (!activeEncounters.value || activeEncounters.value.length === 0) return [];
    const ipdEncounterIds = new Set(wardAdmissions.value.map(wa => wa.encounter_id));
    return activeEncounters.value.filter(enc => !ipdEncounterIds.has(enc.id));
  } else {
    // IPD: Show encounters that have ward admissions
    const ipdEncounterIds = new Set(wardAdmissions.value.map(wa => wa.encounter_id));
    
    if (ipdEncounterIds.size === 0) return [];
    
    // First, try to find encounters from activeEncounters
    let ipdEncounters = [];
    if (activeEncounters.value && activeEncounters.value.length > 0) {
      ipdEncounters = activeEncounters.value.filter(enc => ipdEncounterIds.has(enc.id));
    }
    
    // If no encounters found in activeEncounters, create entries from ward admissions
    // This handles cases where the encounter might be archived or not in activeEncounters
    if (ipdEncounters.length === 0) {
      console.log('No encounters found in activeEncounters, creating from ward admissions');
      ipdEncounters = wardAdmissions.value.map(wa => {
        const wardAdmission = wa;
        const isPartiallyDischarged = wardAdmission?.partially_discharged_at && !wardAdmission?.discharged_at;
        return {
          id: wa.encounter_id,
          label: `Encounter #${wa.encounter_id} - ${wa.encounter_department || 'IPD'} (${new Date(wa.encounter_created_at || wa.admitted_at).toLocaleDateString()})`,
          value: wa.encounter_id,
          department: wa.encounter_department || 'IPD',
          created_at: wa.encounter_created_at || wa.admitted_at,
          wardAdmission: wardAdmission
        };
      });
    }
    
    // Enrich with ward admission info
    return ipdEncounters.map(enc => {
      const wardAdmission = wardAdmissions.value.find(wa => wa.encounter_id === enc.id) || enc.wardAdmission;
      const isPartiallyDischarged = wardAdmission?.partially_discharged_at && !wardAdmission?.discharged_at;
      return {
        ...enc,
        label: `${enc.label} | Ward: ${wardAdmission?.ward || 'N/A'} | Bed: ${wardAdmission?.bed_number || 'N/A'}${isPartiallyDischarged ? ' (Partially Discharged)' : ''}`,
        wardAdmission: wardAdmission
      };
    });
  }
});

// Group IPD bills by ward admission
const groupedIPDBills = computed(() => {
  if (billingModule.value !== 'ipd' || !existingBills.value || existingBills.value.length === 0) {
    return [];
  }
  
  // Group bills by ward admission
  const groups = {};
  
  existingBills.value.forEach(bill => {
    const wardAdmission = wardAdmissions.value.find(wa => wa.encounter_id === bill.encounter_id);
    if (wardAdmission) {
      const key = wardAdmission.id;
      if (!groups[key]) {
        groups[key] = {
          wardAdmissionId: wardAdmission.id,
          encounterId: wardAdmission.encounter_id,
          ward: wardAdmission.ward,
          bedNumber: wardAdmission.bed_number,
          bills: [],
          total: 0,
          paid: 0,
          balance: 0
        };
      }
      groups[key].bills.push(bill);
      groups[key].total += bill.total_amount || 0;
      groups[key].paid += bill.paid_amount || 0;
      groups[key].balance += (bill.total_amount || 0) - (bill.paid_amount || 0);
    }
  });
  
  // Convert to array and sort by ward admission ID (most recent first)
  return Object.values(groups).sort((a, b) => b.wardAdmissionId - a.wardAdmissionId);
});

const billDetailColumns = [
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit Price', field: 'unit_price', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'total_price', label: 'Total', field: 'total_price', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'amount_paid', label: 'Amount Paid', field: 'amount_paid', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'remaining_balance', label: 'Balance', field: 'remaining_balance', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'receipt_numbers', label: 'Receipt Number(s)', field: 'receipt_numbers', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const editBillItemColumns = [
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit Price', field: 'unit_price', align: 'right' },
  { name: 'total_price', label: 'Total', field: 'total_price', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const searchResultColumns = [
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'cash_price', label: 'Cash Price', field: 'cash_price', align: 'right', format: (val) => val.toFixed(2) },
  { name: 'insured_price', label: 'Insured Price', field: 'insured_price', align: 'right', format: (val) => val.toFixed(2) },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const autoCalculatedTotal = computed(() => {
  return autoCalculatedItems.value.reduce((sum, item) => sum + (item.total_price || 0), 0);
});

// Group auto-calculated items by service group
const groupedAutoCalculatedItems = computed(() => {
  if (!autoCalculatedItems.value || autoCalculatedItems.value.length === 0) return {};
  
  const groups = {};
  const order = ['Lab', 'Scan', 'X-ray', 'Diagnose', 'Surgery', 'Pharmacy', 'Other'];
  
  // Initialize groups
  order.forEach(group => {
    groups[group] = [];
  });
  
  // Group items
  autoCalculatedItems.value.forEach(item => {
    const serviceGroup = item.service_group || 'Other';
    if (!groups[serviceGroup]) {
      groups[serviceGroup] = [];
    }
    groups[serviceGroup].push(item);
  });
  
  // Remove empty groups and sort by order
  const sortedGroups = {};
  order.forEach(group => {
    if (groups[group] && groups[group].length > 0) {
      sortedGroups[group] = groups[group];
    }
  });
  
  // Add any other groups not in the order
  Object.keys(groups).forEach(group => {
    if (!order.includes(group) && groups[group].length > 0) {
      sortedGroups[group] = groups[group];
    }
  });
  
  return sortedGroups;
});

const totalAmount = computed(() => {
  return billItems.reduce((sum, item) => sum + (item.total_price || 0), 0);
});

const searchPatient = async () => {
  if (!cardNumber.value || !cardNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  loadingPatient.value = true;
  try {
    const response = await patientsAPI.getByCard(cardNumber.value.trim());
    console.log('Billing card search response:', response);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      patients = response.data.data;
    } else if (response.data?.results && Array.isArray(response.data.results)) {
      patients = response.data.results;
    }
    
    if (patients.length === 0) {
      patient.value = null;
      activeEncounters.value = [];
      wardAdmissions.value = [];
      selectedEncounterId.value = null;
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
      return;
    }
    
    if (patients.length === 1) {
      // Single result - use it directly
      patient.value = patients[0];
      
      // Load encounters
      const encountersResponse = await encountersAPI.getPatientEncounters(patient.value.id);
      const allEncounters = encountersResponse.data.filter(e => !e.archived);
      activeEncounters.value = allEncounters.map(e => ({
        id: e.id,
        label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})${e.ccc_number ? ' [Insured]' : ' [Cash]'}`,
        value: e.id,
        ...e, // Store full encounter data
      }));
      
      // Load ward admissions for IPD filtering (include partially discharged)
      try {
        const wardAdmissionsResponse = await consultationAPI.getWardAdmissionsByPatientCard(patient.value.card_number, false);
        wardAdmissions.value = wardAdmissionsResponse.data || [];
        console.log('Loaded ward admissions for billing:', wardAdmissions.value);
        console.log('Active encounters:', activeEncounters.value.map(e => ({ id: e.id, department: e.department })));
        console.log('Ward admission encounter IDs:', wardAdmissions.value.map(wa => wa.encounter_id));
        
        // Auto-switch to IPD mode if ward admissions exist
        if (wardAdmissions.value.length > 0 && billingModule.value === 'opd') {
          billingModule.value = 'ipd';
        }
        
        console.log('Filtered encounters (IPD):', filteredEncounters.value);
        console.log('Filtered encounters count:', filteredEncounters.value.length);
      } catch (error) {
        console.error('Failed to load ward admissions:', error);
        wardAdmissions.value = [];
      }
      
      if (activeEncounters.value.length === 0) {
        $q.notify({
          type: 'info',
          message: 'No active encounters found for this patient',
        });
      } else if (filteredEncounters.value.length === 1) {
        selectedEncounterId.value = filteredEncounters.value[0].id;
        selectedEncounter.value = filteredEncounters.value[0];
        if (billingModule.value === 'ipd' && filteredEncounters.value[0].wardAdmission) {
          selectedWardAdmission.value = filteredEncounters.value[0].wardAdmission;
        }
        await loadEncounterData();
      } else if (filteredEncounters.value.length > 0 && billingModule.value === 'ipd') {
        // If multiple IPD encounters, still try to load bills for all of them
        await loadExistingBills();
      }
    } else {
      // Multiple results - navigate to search results page
      router.push({
        name: 'PatientSearchResults',
        query: { 
          searchType: 'card',
          searchTerm: cardNumber.value.trim(),
          patients: JSON.stringify(patients) 
        }
      });
    }
  } catch (error) {
    patient.value = null;
    activeEncounters.value = [];
    wardAdmissions.value = [];
    selectedEncounterId.value = null;
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to search patients',
    });
  } finally {
    loadingPatient.value = false;
  }
};

const loadEncounterData = async () => {
  if (!selectedEncounterId.value) return;
  
  // Find and store the selected encounter for insurance status display
  selectedEncounter.value = filteredEncounters.value.find(e => e.id === selectedEncounterId.value);
  
  // For IPD, also store the ward admission
  if (billingModule.value === 'ipd' && selectedEncounter.value?.wardAdmission) {
    selectedWardAdmission.value = selectedEncounter.value.wardAdmission;
  } else {
    selectedWardAdmission.value = null;
  }
  
  await loadAutoCalculatedItems();
  await loadExistingBills();
};

const loadAutoCalculatedItems = async () => {
  if (!selectedEncounterId.value) return;

  calculatingItems.value = true;
  try {
    const response = await billingAPI.autoCalculateBillItems(selectedEncounterId.value);
    // Only show diagnoses (category "drg"), filter out investigations, prescriptions, etc.
    const allItems = response.data.items || [];
    autoCalculatedItems.value = allItems.filter(item => 
      item.category === 'drg' && 
      item.item_name && 
      item.item_name.toLowerCase().startsWith('diagnosis:')
    );
  } catch (error) {
    console.error('Failed to auto-calculate bill items:', error);
    autoCalculatedItems.value = [];
    $q.notify({
      type: 'warning',
      message: error.response?.data?.detail || 'Failed to calculate bill items',
    });
  } finally {
    calculatingItems.value = false;
  }
};

const addDiagnosisToBill = async (diagnosisItem) => {
  if (!selectedEncounterId.value) return;
  
  addingDiagnosisId.value = diagnosisItem.item_code;
  
  try {
    const billData = {
      encounter_id: selectedEncounterId.value,
      items: [{
        item_code: diagnosisItem.item_code,
        item_name: diagnosisItem.item_name,
        category: diagnosisItem.category,
        quantity: diagnosisItem.quantity,
      }],
      miscellaneous: null,
    };
    
    await billingAPI.createBill(billData);
    
    $q.notify({
      type: 'positive',
      message: 'Diagnosis added to bill successfully',
    });
    
    // Reload auto-calculated items from backend to ensure accuracy
    // This will exclude the diagnosis we just added since it now has a bill
    await loadAutoCalculatedItems();
    
    // Reload existing bills to show the new bill
    await loadExistingBills();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add diagnosis to bill',
    });
  } finally {
    addingDiagnosisId.value = null;
  }
};

const loadExistingBills = async () => {
  if (billingModule.value === 'ipd') {
    // For IPD: Load all bills for all IPD encounters (ward admissions) of the patient
    if (!patient.value) return;
    
    loadingBills.value = true;
    try {
      // Get all IPD encounter IDs from ward admissions
      let ipdEncounterIds = wardAdmissions.value.map(wa => wa.encounter_id);
      
      // If no ward admissions loaded yet, try to load them first
      if (ipdEncounterIds.length === 0 && patient.value.card_number) {
        console.log('No ward admissions found, attempting to load...');
        try {
          const wardAdmissionsResponse = await consultationAPI.getWardAdmissionsByPatientCard(patient.value.card_number, false);
          wardAdmissions.value = wardAdmissionsResponse.data || [];
          ipdEncounterIds = wardAdmissions.value.map(wa => wa.encounter_id);
          console.log('Loaded ward admissions:', wardAdmissions.value);
        } catch (error) {
          console.error('Failed to load ward admissions in loadExistingBills:', error);
        }
      }
      
      // Also include the selected encounter if it's set and not already in the list
      if (selectedEncounterId.value && !ipdEncounterIds.includes(selectedEncounterId.value)) {
        console.log('Adding selected encounter to IPD encounter IDs:', selectedEncounterId.value);
        ipdEncounterIds.push(selectedEncounterId.value);
      }
      
      // Fallback: If still no encounter IDs, try to get all encounters for the patient
      // This handles cases where ward admissions might not be properly linked
      if (ipdEncounterIds.length === 0 && activeEncounters.value.length > 0) {
        console.warn('No IPD encounter IDs from ward admissions, trying all active encounters as fallback');
        // Filter encounters that might be IPD (have department that suggests IPD)
        const possibleIPDEncounters = activeEncounters.value.filter(enc => {
          const dept = enc.department?.toLowerCase() || '';
          return dept.includes('ward') || dept.includes('ipd') || dept.includes('inpatient') || 
                 dept.includes('maternity') || dept.includes('surgical');
        });
        if (possibleIPDEncounters.length > 0) {
          ipdEncounterIds = possibleIPDEncounters.map(enc => enc.id);
          console.log('Using fallback IPD encounter IDs:', ipdEncounterIds);
        } else {
          // Last resort: use all active encounters
          ipdEncounterIds = activeEncounters.value.map(enc => enc.id);
          console.log('Using all active encounters as last resort:', ipdEncounterIds);
        }
      }
      
      if (ipdEncounterIds.length === 0) {
        console.warn('No IPD encounter IDs found for loading bills');
        existingBills.value = [];
        return;
      }
      
      console.log('Loading bills for IPD encounter IDs:', ipdEncounterIds);
      
      // Load bills for all IPD encounters
      const allBillsPromises = ipdEncounterIds.map(encounterId => 
        billingAPI.getEncounterBills(encounterId).catch(err => {
          console.warn(`Failed to load bills for encounter ${encounterId}:`, err);
          return { data: [] };
        })
      );
      
      const allBillsResponses = await Promise.all(allBillsPromises);
      const allBills = allBillsResponses.flatMap(response => response.data || []);
      console.log('Loaded bills from API:', allBills);
      
      // Enrich bills with detailed information
      const enrichedBills = await Promise.all(allBills.map(async (bill) => {
        try {
          // Get bill details to get service information
          const billDetailsResponse = await billingAPI.getBillDetails(bill.id);
          const billDetails = billDetailsResponse.data?.data || billDetailsResponse.data;
          
          // Calculate remaining balance
          const remainingBalance = (bill.total_amount || 0) - (bill.paid_amount || 0);
          
          // Group services by category/service group
          const services = [];
          if (billDetails?.bill_items) {
            const serviceGroups = {};
            billDetails.bill_items.forEach(item => {
              const serviceGroup = item.service_group || item.category || 'Other';
              if (!serviceGroups[serviceGroup]) {
                serviceGroups[serviceGroup] = [];
              }
              serviceGroups[serviceGroup].push(item.item_name || item.item_code);
            });
            
            Object.keys(serviceGroups).forEach(group => {
              services.push(`${group}: ${serviceGroups[group].join(', ')}`);
            });
          }
          
          return {
            ...bill,
            remaining_balance: remainingBalance,
            services: services.join('; ') || 'No services',
            service_count: billDetails?.bill_items?.length || 0,
          };
        } catch (error) {
          console.error(`Failed to load details for bill ${bill.id}:`, error);
          const remainingBalance = (bill.total_amount || 0) - (bill.paid_amount || 0);
          return {
            ...bill,
            remaining_balance: remainingBalance,
            services: 'Details unavailable',
            service_count: 0,
          };
        }
      }));
      
      existingBills.value = enrichedBills;
      console.log('Final enriched bills:', enrichedBills.length, 'bills loaded');
      if (enrichedBills.length === 0) {
        console.warn('No bills found for IPD encounters. Encounter IDs searched:', ipdEncounterIds);
      }
    } catch (error) {
      console.error('Failed to load IPD bills:', error);
      existingBills.value = [];
    } finally {
      loadingBills.value = false;
    }
  } else {
    // For OPD: Load bills for the selected encounter only
    if (!selectedEncounterId.value) return;

    loadingBills.value = true;
    try {
      const response = await billingAPI.getEncounterBills(selectedEncounterId.value);
      const bills = response.data || [];
      
      // Enrich bills with detailed information
      const enrichedBills = await Promise.all(bills.map(async (bill) => {
        try {
          // Get bill details to get service information
          const billDetailsResponse = await billingAPI.getBillDetails(bill.id);
          const billDetails = billDetailsResponse.data?.data || billDetailsResponse.data;
          
          // Calculate remaining balance
          const remainingBalance = (bill.total_amount || 0) - (bill.paid_amount || 0);
          
          // Group services by category/service group
          const services = [];
          if (billDetails?.bill_items) {
            const serviceGroups = {};
            billDetails.bill_items.forEach(item => {
              const serviceGroup = item.service_group || item.category || 'Other';
              if (!serviceGroups[serviceGroup]) {
                serviceGroups[serviceGroup] = [];
              }
              serviceGroups[serviceGroup].push(item.item_name || item.item_code);
            });
            
            Object.keys(serviceGroups).forEach(group => {
              services.push(`${group}: ${serviceGroups[group].join(', ')}`);
            });
          }
          
          return {
            ...bill,
            remaining_balance: remainingBalance,
            services: services.join('; ') || 'No services',
            service_count: billDetails?.bill_items?.length || 0,
          };
        } catch (error) {
          console.error(`Failed to load details for bill ${bill.id}:`, error);
          const remainingBalance = (bill.total_amount || 0) - (bill.paid_amount || 0);
          return {
            ...bill,
            remaining_balance: remainingBalance,
            services: 'Details unavailable',
            service_count: 0,
          };
        }
      }));
      
      existingBills.value = enrichedBills;
    } catch (error) {
      console.error('Failed to load bills:', error);
      existingBills.value = [];
    } finally {
      loadingBills.value = false;
    }
  }
};

const searchItems = async () => {
  if (!searchTerm.value) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a search term',
    });
    return;
  }

  searching.value = true;
  try {
    const response = await priceListAPI.search(
      searchTerm.value,
      null, // service_type
      searchCategory.value || null // file_type
    );
    searchResults.value = response.data || [];
  } catch (error) {
    console.error('Failed to search items:', error);
    searchResults.value = [];
    $q.notify({
      type: 'negative',
      message: 'Failed to search items',
    });
  } finally {
    searching.value = false;
  }
};

const searchAndAddItem = () => {
  searchItems();
};

const addSearchResult = (priceItem) => {
  const isInsured = selectedEncounter.value?.ccc_number ? true : false;
  const unitPrice = isInsured ? (priceItem.insured_price || priceItem.cash_price) : priceItem.cash_price;
  
  const billItem = {
    id: Date.now() + Math.random(),
    item_code: priceItem.item_code || priceItem.g_drg_code || priceItem.medication_code,
    item_name: priceItem.item_name || priceItem.service_name || priceItem.product_name,
    category: priceItem.category || priceItem.file_type || 'other',
    quantity: 1,
    unit_price: unitPrice,
    total_price: unitPrice,
  };

  billItems.push(billItem);
  $q.notify({
    type: 'positive',
    message: 'Item added to bill',
  });
  
  // Clear search and close dialog
  searchTerm.value = '';
  searchResults.value = [];
  searchCategory.value = null;
  showAddItemDialog.value = false;
};

const addCustomItem = () => {
  // Validate that price is provided
  if (!customItemForm.value.item_name || (customItemForm.value.unit_price || 0) < 0) {
    $q.notify({
      type: 'warning',
      message: 'Item name and price are required',
    });
    return;
  }
  
  // Explicitly handle empty strings and null values
  const itemCode = customItemForm.value.item_code && customItemForm.value.item_code.trim() !== '' 
    ? customItemForm.value.item_code 
    : null;
  const itemCategory = customItemForm.value.category && customItemForm.value.category.trim() !== '' 
    ? customItemForm.value.category 
    : null;
  
  const billItem = {
    id: Date.now() + Math.random(),
    item_code: itemCode, // null for items without codes
    item_name: customItemForm.value.item_name,
    category: itemCategory, // null for items without categories
    quantity: customItemForm.value.quantity || 1,
    unit_price: customItemForm.value.unit_price || 0,
    total_price: (customItemForm.value.quantity || 1) * (customItemForm.value.unit_price || 0),
    is_custom: true, // Flag to indicate this is a custom item
  };
  
  billItems.push(billItem);
  
  // Reset form
  customItemForm.value = {
    item_code: '',
    item_name: '',
    category: null,
    quantity: 1,
    unit_price: 0,
  };
  
  showAddItemDialog.value = false;
  
  $q.notify({
    type: 'positive',
    message: 'Custom item added to bill',
  });
};

const removeBillItem = (index) => {
  billItems.splice(index, 1);
};

const createBill = async () => {
  if (billItems.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please add at least one item to the bill',
    });
    return;
  }

  creating.value = true;
  try {
    const billData = {
      encounter_id: selectedEncounterId.value,
      items: billItems.map(item => {
        const itemData = {
          item_name: item.item_name,
          quantity: item.quantity,
        };
        
        // Only include item_code if it exists (not null/undefined)
        if (item.item_code) {
          itemData.item_code = item.item_code;
        } else {
          itemData.item_code = null; // Explicitly set to null for items without codes
        }
        
        // Only include category if it exists (not null/undefined)
        if (item.category) {
          itemData.category = item.category;
        } else {
          itemData.category = null; // Explicitly set to null for items without categories
        }
        
        // Include custom price if this is a custom item
        if (item.is_custom) {
          itemData.unit_price = item.unit_price;
        }
        
        return itemData;
      }),
      miscellaneous: miscellaneous.value || null,
    };

    await billingAPI.createBill(billData);
    
    $q.notify({
      type: 'positive',
      message: 'Bill created successfully',
    });
    
    // Reset form
    billItems.splice(0);
    miscellaneous.value = '';
    autoCalculatedItems.value = [];
    
    // Reload bills and recalculate
    await loadExistingBills();
    await loadAutoCalculatedItems();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to create bill',
    });
  } finally {
    creating.value = false;
  }
};

const receiptItemColumns = [
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit Price', field: 'unit_price', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'total_price', label: 'Total', field: 'total_price', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
];

const receiptItemColumnsWithInputs = [
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'total_price', label: 'Item Total', field: 'total_price', align: 'right', format: (val) => `₵${val.toFixed(2)}` },
  { name: 'receipt_number', label: 'Receipt Number', field: 'receipt_number', align: 'left' },
  { name: 'amount_paid', label: 'Amount Paid', field: 'amount_paid', align: 'right' },
];

const receiptItemsWithFields = computed(() => {
  if (!currentBillForReceipt.value || !currentBillForReceipt.value.bill_items) return [];
  
  // Ensure receiptItemData is initialized
  if (!receiptItemData.value || typeof receiptItemData.value !== 'object') {
    receiptItemData.value = {};
  }
  
  const billItems = currentBillForReceipt.value.bill_items;
  if (!Array.isArray(billItems)) return [];
  
  return billItems.map(item => {
    if (!item || !item.id) return null;
    
    // Ensure receiptItemData exists for this item
    if (!receiptItemData.value[item.id]) {
      receiptItemData.value[item.id] = {
        receipt_number: '',
        amount_paid: item.total_price || 0,
      };
    }
    
    const itemData = receiptItemData.value[item.id];
    
    return {
      ...item,
      receipt_number: itemData?.receipt_number || '',
      amount_paid: itemData?.amount_paid || item.total_price || 0,
    };
  }).filter(item => item !== null); // Remove null items
});

// Group receipt items by service group
const groupedReceiptItems = computed(() => {
  if (!receiptItemsWithFields.value || !Array.isArray(receiptItemsWithFields.value) || receiptItemsWithFields.value.length === 0) {
    return {};
  }
  
  const groups = {};
  const order = ['Lab', 'Scan', 'X-ray', 'Diagnose', 'Surgery', 'Pharmacy', 'Other'];
  
  // Initialize groups
  order.forEach(group => {
    groups[group] = [];
  });
  
  // Group items - filter out invalid items
  receiptItemsWithFields.value.forEach(item => {
    if (!item || !item.id) return; // Skip invalid items
    const serviceGroup = item.service_group || 'Other';
    if (!groups[serviceGroup]) {
      groups[serviceGroup] = [];
    }
    groups[serviceGroup].push(item);
  });
  
  // Remove empty groups and sort by order
  const sortedGroups = {};
  order.forEach(group => {
    if (groups[group] && Array.isArray(groups[group]) && groups[group].length > 0) {
      sortedGroups[group] = groups[group];
    }
  });
  
  // Add any other groups not in the order
  Object.keys(groups).forEach(group => {
    if (!order.includes(group) && Array.isArray(groups[group]) && groups[group].length > 0) {
      sortedGroups[group] = groups[group];
    }
  });
  
  return sortedGroups;
});

const selectedTotal = computed(() => {
  if (!selectedBillItems.value.length) return 0;
  return selectedBillItems.value.reduce((sum, item) => {
    const itemData = receiptItemData.value[item.id];
    return sum + (itemData?.amount_paid || item.total_price || 0);
  }, 0);
});

const billItemsWithReceipts = computed(() => {
  if (!currentBillDetails.value || !currentBillDetails.value.bill_items) return [];
  
  return currentBillDetails.value.bill_items.map(item => ({
    ...item,
    receipt_numbers: item.payment_info
      ? item.payment_info.map(p => p.receipt_number).join(', ')
      : ''
  }));
});

// Group bill items by service group
const groupedBillItems = computed(() => {
  if (!currentBillDetails.value || !currentBillDetails.value.bill_items) return {};
  
  const groups = {};
  const order = ['Lab', 'Scan', 'X-ray', 'Diagnose', 'Surgery', 'Pharmacy', 'Other'];
  
  // Initialize groups
  order.forEach(group => {
    groups[group] = [];
  });
  
  // Add 'Other' for any unmapped groups
  groups['Other'] = groups['Other'] || [];
  
  // Group items
  currentBillDetails.value.bill_items.forEach(item => {
    const serviceGroup = item.service_group || 'Other';
    if (!groups[serviceGroup]) {
      groups[serviceGroup] = [];
    }
    groups[serviceGroup].push({
      ...item,
      receipt_numbers: item.payment_info
        ? item.payment_info.map(p => p.receipt_number).join(', ')
        : ''
    });
  });
  
  // Remove empty groups and sort by order
  const sortedGroups = {};
  order.forEach(group => {
    if (groups[group] && groups[group].length > 0) {
      sortedGroups[group] = groups[group];
    }
  });
  
  // Add any other groups not in the order
  Object.keys(groups).forEach(group => {
    if (!order.includes(group) && groups[group].length > 0) {
      sortedGroups[group] = groups[group];
    }
  });
  
  return sortedGroups;
});

const groupSubtotal = (items) => {
  return items.reduce((sum, item) => sum + (item.total_price || 0), 0);
};

const getGroupSubtotal = (group) => {
  try {
    if (!group || !Array.isArray(group) || group.length === 0) {
      return '0.00';
    }
    
    const total = group.reduce((sum, item) => {
      if (!item || !item.id) return sum;
      
      // Safely access receiptItemData
      let itemData = null;
      try {
        if (receiptItemData.value && typeof receiptItemData.value === 'object') {
          itemData = receiptItemData.value[item.id];
        }
      } catch (e) {
        console.warn('Error accessing receiptItemData:', e);
      }
      
      const amount = itemData?.amount_paid || item.total_price || 0;
      return sum + (typeof amount === 'number' ? amount : parseFloat(amount) || 0);
    }, 0);
    
    return typeof total === 'number' ? total.toFixed(2) : '0.00';
  } catch (error) {
    console.error('Error calculating group subtotal:', error);
    return '0.00';
  }
};

const viewBillDetails = async (billId) => {
  try {
    const response = await billingAPI.getBillDetails(billId);
    currentBillDetails.value = response.data;
    showBillDetailsDialog.value = true;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load bill details',
    });
  }
};

const editBill = async (bill) => {
  try {
    const response = await billingAPI.getBillDetails(bill.id);
    const billData = response.data?.data || response.data;
    editingBill.value = billData;
    
    // Create editable copy of bill items
    // Ensure each item has an id
    const items = billData.bill_items || [];
    console.log('Bill items from API:', items);
    editingBillItems.value = items.map(item => {
      if (!item.id) {
        console.error('Bill item missing id:', item);
        $q.notify({
          type: 'warning',
          message: `Bill item "${item.item_name}" is missing an ID and cannot be edited`,
        });
      }
      const editableItem = {
        ...item,
        editableQuantity: item.quantity || 1,
        editableUnitPrice: item.unit_price || 0,
        total_price: (item.quantity || 1) * (item.unit_price || 0),
      };
      console.log('Created editable item:', editableItem);
      return editableItem;
    }).filter(item => item.id); // Only include items with IDs
    
    console.log('Final editable bill items:', editingBillItems.value);
    
    if (editingBillItems.value.length === 0) {
      $q.notify({
        type: 'warning',
        message: 'No editable bill items found',
      });
      return;
    }
    
    showEditBillDialog.value = true;
  } catch (error) {
    console.error('Error loading bill details:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load bill details',
    });
  }
};

const updateBillItemTotal = (item) => {
  item.total_price = (item.editableQuantity || 1) * (item.editableUnitPrice || 0);
};

const editBillItem = (item) => {
  if (!item || !item.id) {
    $q.notify({
      type: 'warning',
      message: 'Bill item is missing an ID and cannot be edited',
    });
    return;
  }
  
  editingBillItem.value = item;
  editBillItemForm.value = {
    id: item.id,
    item_code: item.item_code || '',
    item_name: item.item_name || '',
    category: item.category || '',
    quantity: item.quantity || 1,
    unit_price: item.unit_price || 0,
  };
  
  console.log('Editing bill item:', item);
  console.log('Edit form:', editBillItemForm.value);
  
  showEditBillItemDialog.value = true;
};

const updateBillItemSubmit = async () => {
  if (!editBillItemForm.value.id) {
    $q.notify({
      type: 'warning',
      message: 'Bill item ID is missing',
    });
    return;
  }
  
  updatingBillItemId.value = editBillItemForm.value.id;
  
  try {
    const updateData = {
      quantity: editBillItemForm.value.quantity,
      unit_price: editBillItemForm.value.unit_price,
    };
    
    console.log(`Updating bill item ${editBillItemForm.value.id} with data:`, updateData);
    
    await billingAPI.updateBillItem(editBillItemForm.value.id, updateData);
    
    $q.notify({
      type: 'positive',
      message: 'Bill item updated successfully',
    });
    
    showEditBillItemDialog.value = false;
    
    // Reload bill details to show updated values
    if (currentBillDetails.value) {
      await viewBillDetails(currentBillDetails.value.id);
    }
    
    // Reload bills list if we have an encounter selected
    if (selectedEncounterId.value) {
      await loadExistingBills();
    }
  } catch (error) {
    console.error('Failed to update bill item:', error);
    $q.notify({
      type: 'negative',
      message: `Failed to update bill item: ${error.response?.data?.detail || error.message}`,
    });
  } finally {
    updatingBillItemId.value = null;
  }
};

const removeBillItemFromEdit = async (item) => {
  $q.dialog({
    title: 'Remove Item',
    message: `Are you sure you want to remove ${item.item_name} from this bill?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    updatingBillItemId.value = item.id;
    try {
      // Remove item from editing list
      editingBillItems.value = editingBillItems.value.filter(i => i.id !== item.id);
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to remove item',
      });
    } finally {
      updatingBillItemId.value = null;
    }
  });
};

const editBillTotal = computed(() => {
  return editingBillItems.value.reduce((sum, item) => {
    return sum + (item.total_price || 0);
  }, 0);
});

const updateBillSubmit = async () => {
  if (!editingBill.value) return;
  
  updatingBillId.value = editingBill.value.id;
  try {
    // Update each bill item individually
    // The backend will automatically recalculate the bill total
    for (const item of editingBillItems.value) {
      if (!item.id) {
        console.warn('Bill item missing id:', item);
        $q.notify({
          type: 'warning',
          message: `Bill item "${item.item_name}" is missing an ID and cannot be updated`,
        });
        continue;
      }
      
      const updateData = {
        quantity: item.editableQuantity,
        unit_price: item.editableUnitPrice,
      };
      
      console.log(`Updating bill item ${item.id} (${item.item_name}) with data:`, updateData);
      
      try {
        await billingAPI.updateBillItem(item.id, updateData);
        console.log(`Successfully updated bill item ${item.id}`);
      } catch (itemError) {
        console.error(`Failed to update bill item ${item.id}:`, itemError);
        console.error('Item data:', item);
        console.error('Update data:', updateData);
        $q.notify({
          type: 'negative',
          message: `Failed to update ${item.item_name} (ID: ${item.id}): ${itemError.response?.data?.detail || itemError.message}`,
        });
        throw itemError; // Stop processing if one item fails
      }
    }
    
    // No need to update bill total separately - backend recalculates it automatically
    // from all bill items when we update each item
    
    $q.notify({
      type: 'positive',
      message: 'Bill updated successfully',
    });
    
    showEditBillDialog.value = false;
    // Reload bills
    if (selectedEncounterId.value) {
      await loadExistingBills();
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update bill',
    });
  } finally {
    updatingBillId.value = null;
  }
};

const updateReceiptItemData = (itemId, field, value) => {
  if (!receiptItemData.value[itemId]) {
    receiptItemData.value[itemId] = {
      receipt_number: '',
      amount_paid: 0,
    };
  }
  receiptItemData.value[itemId][field] = value;
};

const openReceiptDialog = async (bill) => {
  try {
    const response = await billingAPI.getBillDetails(bill.id);
    // Handle both response.data and response.data.data structures
    const billData = response.data?.data || response.data;
    currentBillForReceipt.value = billData;
    
    // Initialize receipt item data for all items
    receiptItemData.value = {};
    const billItems = billData?.bill_items || [];
    billItems.forEach(item => {
      if (!item || !item.id) return;
      // Use remaining balance if available, otherwise use total price
      const defaultAmount = (item.remaining_balance && item.remaining_balance > 0) ? item.remaining_balance : (item.total_price || 0);
      receiptItemData.value[item.id] = {
        receipt_number: '',
        amount_paid: defaultAmount,
      };
    });
    
    // Select unpaid items by default
    const billDetails = billData;
    const totalAmount = billDetails?.total_amount || 0;
    const paidAmount = billDetails?.paid_amount || 0;
    const remainingBalance = totalAmount - paidAmount;
    
    // If there's remaining balance, select items that have remaining balance
    if (remainingBalance > 0 && billItems.length > 0) {
      selectedBillItems.value = billItems.filter(
        item => item && item.remaining_balance && item.remaining_balance > 0
      );
    } else {
      selectedBillItems.value = [];
    }
    
    receiptPaymentMethod.value = 'cash';
    showReceiptDialog.value = true;
  } catch (error) {
    console.error('Error opening receipt dialog:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || error.message || 'Failed to load bill details',
    });
  }
};

const createReceiptWithItems = async () => {
  if (selectedBillItems.value.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please select at least one item to pay',
    });
    return;
  }

  // Validate all selected items have receipt numbers and amounts
  const missingFields = [];
  const invalidAmounts = [];
  
  for (const item of selectedBillItems.value) {
    const itemData = receiptItemData.value[item.id];
    
    if (!itemData || !itemData.receipt_number || !itemData.receipt_number.trim()) {
      missingFields.push(item.item_name);
    }
    
    if (!itemData || !itemData.amount_paid || itemData.amount_paid <= 0) {
      invalidAmounts.push(item.item_name);
    }
    
    if (itemData && itemData.amount_paid > item.total_price) {
      invalidAmounts.push(`${item.item_name} (exceeds total: ₵${item.total_price.toFixed(2)})`);
    }
  }
  
  if (missingFields.length > 0) {
    $q.notify({
      type: 'warning',
      message: `Please enter receipt numbers for: ${missingFields.join(', ')}`,
    });
    return;
  }
  
  if (invalidAmounts.length > 0) {
    $q.notify({
      type: 'warning',
      message: `Invalid amounts for: ${invalidAmounts.join(', ')}`,
    });
    return;
  }

  try {
    const receiptData = {
      bill_id: currentBillForReceipt.value.id,
      payment_method: receiptPaymentMethod.value,
      receipt_items: selectedBillItems.value.map(item => {
        const itemData = receiptItemData.value[item.id];
        return {
          bill_item_id: item.id,
          amount_paid: parseFloat(itemData.amount_paid),
          receipt_number: itemData.receipt_number.trim(),
        };
      }),
    };

    const response = await billingAPI.createReceipt(receiptData);
    
    const receiptCount = response.data.receipts?.length || 1;
    $q.notify({
      type: 'positive',
      message: `${receiptCount} receipt(s) issued successfully`,
    });
    
    showReceiptDialog.value = false;
    receiptItemData.value = {};
    await loadExistingBills();
    
    // Reload bill details if dialog was opened from view
    if (currentBillDetails.value) {
      await viewBillDetails(currentBillForReceipt.value.id);
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to issue receipt',
    });
  }
};

const openAddReceiptDialog = (billItem) => {
  currentBillItemForReceipt.value = billItem;
  const remainingBalance = billItem.remaining_balance > 0 ? billItem.remaining_balance : billItem.total_price;
  manualReceiptForm.value = {
    receipt_number: '',
    amount_paid: remainingBalance,
    payment_method: 'cash',
  };
  showAddReceiptDialog.value = true;
};

const saveManualReceipt = async () => {
  if (!manualReceiptForm.value.receipt_number || !manualReceiptForm.value.receipt_number.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a receipt number',
    });
    return;
  }

  if (!manualReceiptForm.value.amount_paid || manualReceiptForm.value.amount_paid <= 0) {
    $q.notify({
      type: 'warning',
      message: 'Amount paid must be greater than 0',
    });
    return;
  }

  // Validate against remaining balance
  const maxAmount = currentBillItemForReceipt.value?.remaining_balance || currentBillItemForReceipt.value?.total_price || 0;
  if (manualReceiptForm.value.amount_paid > maxAmount) {
    $q.notify({
      type: 'warning',
      message: `Amount cannot exceed remaining balance (₵${maxAmount.toFixed(2)})`,
    });
    return;
  }

  try {
    await billingAPI.addManualReceiptToBillItem(
      currentBillItemForReceipt.value.id,
      {
        receipt_number: manualReceiptForm.value.receipt_number.trim(),
        amount_paid: parseFloat(manualReceiptForm.value.amount_paid),
        payment_method: manualReceiptForm.value.payment_method,
      }
    );

    $q.notify({
      type: 'positive',
      message: 'Receipt added successfully',
    });

    showAddReceiptDialog.value = false;
    
    // Reload bill details
    if (currentBillDetails.value) {
      await viewBillDetails(currentBillDetails.value.id);
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add receipt',
    });
  }
};

const confirmDeleteReceipt = (receiptId, billItemId) => {
  // Find the receipt_item_id from payment_info
  const billItem = billItemsWithReceipts.value.find(item => item.id === billItemId);
  if (!billItem || !billItem.payment_info) return;

  const payment = billItem.payment_info.find(p => p.receipt_id === receiptId);
  if (!payment || !payment.receipt_item_id) return;

  $q.dialog({
    title: 'Delete Receipt',
    message: `Are you sure you want to delete receipt ${payment.receipt_number}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await billingAPI.deleteReceiptItem(payment.receipt_item_id);

      $q.notify({
        type: 'positive',
        message: 'Receipt deleted successfully',
      });

      // Reload bill details
      if (currentBillDetails.value) {
        await viewBillDetails(currentBillDetails.value.id);
      }
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete receipt',
      });
    }
  });
};

const confirmRefundReceipt = (receiptId) => {
  $q.dialog({
    title: 'Refund Receipt',
    message: `Are you sure you want to refund this receipt? This action cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await billingAPI.refundReceipt(receiptId);

      $q.notify({
        type: 'positive',
        message: 'Receipt refunded successfully',
      });

      // Reload bill details
      if (currentBillDetails.value) {
        await viewBillDetails(currentBillDetails.value.id);
      }
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to refund receipt',
      });
    }
  });
};

const confirmDeleteBill = (bill) => {
  $q.dialog({
    title: 'Delete Bill',
    message: `Are you sure you want to delete Bill ${bill.bill_number}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    ok: {
      color: 'negative',
      label: 'Delete'
    }
  }).onOk(async () => {
    try {
      console.log('Deleting bill:', bill.id);
      const response = await billingAPI.deleteBill(bill.id);
      console.log('Delete response:', response);
      
      $q.notify({
        type: 'positive',
        message: 'Bill deleted successfully',
      });
      
      await loadExistingBills();
    } catch (error) {
      console.error('Error deleting bill:', error);
      console.error('Error response:', error.response);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || error.message || 'Failed to delete bill',
      });
    }
  });
};

const refundReceipt = (bill) => {
  $q.dialog({
    title: 'Refund Receipt',
    message: `Are you sure you want to refund the payment for Bill ${bill.bill_number}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      // Get bill details to find receipt ID
      const billResponse = await billingAPI.getBillDetails(bill.id);
      
      if (!billResponse.data.receipt) {
        $q.notify({
          type: 'warning',
          message: 'No receipt found for this bill',
        });
        return;
      }

      if (billResponse.data.receipt.refunded) {
        $q.notify({
          type: 'warning',
          message: 'This receipt has already been refunded',
        });
        return;
      }

      await billingAPI.refundReceipt(billResponse.data.receipt.id);
      
      $q.notify({
        type: 'positive',
        message: 'Receipt refunded successfully',
      });
      
      await loadExistingBills();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to refund receipt',
      });
    }
  });
};

// Computed property to check if recalculate button should be shown
const showRecalculateButton = computed(() => {
  // Only show for Admin
  if (authStore.userRole !== 'Admin') {
    return false;
  }
  
  // Must have a selected encounter
  if (!selectedEncounter.value || !patient.value) {
    return false;
  }
  
  // Patient must be insured
  if (!patient.value.insured) {
    return false;
  }
  
  // Encounter must not have CCC number
  if (selectedEncounter.value.ccc_number) {
    return false;
  }
  
  // For OPD: only show if encounter is from today
  if (billingModule.value === 'opd') {
    const encounterDate = new Date(selectedEncounter.value.created_at);
    const today = new Date();
    const isToday = encounterDate.toDateString() === today.toDateString();
    if (!isToday) {
      return false;
    }
  }
  
  // For IPD: always show if conditions above are met
  return true;
});

// Load OPD CCC for auto-detection
const loadOpdCcc = async () => {
  if (!selectedEncounterId.value) return;
  
  loadingOpdCcc.value = true;
  opdCccNumber.value = null;
  opdEncounterInfo.value = null;
  manualCccNumber.value = '';
  
  try {
    const response = await billingAPI.getOpdCccForEncounter(selectedEncounterId.value);
    if (response.data.found) {
      opdCccNumber.value = response.data.ccc_number;
      opdEncounterInfo.value = response.data.opd_encounter;
      manualCccNumber.value = response.data.ccc_number; // Pre-fill with auto-detected
    }
  } catch (error) {
    console.error('Failed to load OPD CCC:', error);
    $q.notify({
      type: 'warning',
      message: error.response?.data?.detail || 'Failed to load OPD CCC information',
    });
  } finally {
    loadingOpdCcc.value = false;
  }
};

// Open recalculate dialog
const openRecalculateDialog = async () => {
  if (!showRecalculateButton.value) return;
  
  showRecalculateDialog.value = true;
  await loadOpdCcc();
};

// Recalculate billing with insurance
const recalculateBilling = async () => {
  if (!selectedEncounterId.value) return;
  
  const cccToUse = manualCccNumber.value.trim();
  if (!cccToUse) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a CCC number',
    });
    return;
  }
  
  recalculating.value = true;
  try {
    const response = await billingAPI.recalculateBillingWithInsurance(selectedEncounterId.value, {
      ccc_number: cccToUse
    });
    
    recalculationResult.value = response.data;
    
    // Check if there's excess payment
    if (response.data.total_excess_payment > 0) {
      showRecalculateDialog.value = false;
      showRefundPrompt.value = true;
    } else {
      $q.notify({
        type: 'positive',
        message: response.data.message,
        timeout: 5000,
      });
      showRecalculateDialog.value = false;
      
      // Reload encounter data and bills
      await loadEncounterData();
      await loadExistingBills();
    }
  } catch (error) {
    console.error('Failed to recalculate billing:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to recalculate billing',
    });
  } finally {
    recalculating.value = false;
  }
};

const clearSearch = () => {
  cardNumber.value = '';
  patient.value = null;
  activeEncounters.value = [];
  wardAdmissions.value = [];
  selectedEncounterId.value = null;
  selectedEncounter.value = null;
  selectedWardAdmission.value = null;
  billItems.splice(0);
  miscellaneous.value = '';
  autoCalculatedItems.value = [];
  existingBills.value = [];
};

// Watch billing module changes and reload data
watch(billingModule, async () => {
  // Reset selection when switching modules
  selectedEncounterId.value = null;
  selectedEncounter.value = null;
  selectedWardAdmission.value = null;
  billItems.splice(0);
  miscellaneous.value = '';
  autoCalculatedItems.value = [];
  existingBills.value = [];
  
  // Reload ward admissions if patient is already loaded
  if (patient.value) {
    try {
      const wardAdmissionsResponse = await consultationAPI.getWardAdmissionsByPatientCard(patient.value.card_number);
      wardAdmissions.value = wardAdmissionsResponse.data || [];
      
      // Reload bills for the new module
      if (billingModule.value === 'ipd') {
        await loadExistingBills();
      }
    } catch (error) {
      console.warn('Failed to reload ward admissions:', error);
      wardAdmissions.value = [];
    }
  }
});

// Auto-load if encounterId is in route
const autoLoadFromRoute = async () => {
  if (route.params.encounterId) {
    const encounterId = parseInt(route.params.encounterId);
    selectedEncounterId.value = encounterId;
    
    try {
      // Get encounter details to get patient info
      const encounterResponse = await encountersAPI.get(encounterId);
      const encounter = encounterResponse.data;
      
      if (encounter && encounter.patient_id) {
        // Get patient info
        const patientResponse = await patientsAPI.get(encounter.patient_id);
        patient.value = patientResponse.data;
        
        // Load all encounters for this patient
        const encountersResponse = await encountersAPI.getPatientEncounters(encounter.patient_id);
        const allEncounters = encountersResponse.data.filter(e => !e.archived);
        activeEncounters.value = allEncounters.map(e => ({
          id: e.id,
          label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})${e.ccc_number ? ' [Insured]' : ' [Cash]'}`,
          value: e.id,
          ...e,
        }));
        
        // Load ward admissions for IPD filtering (include partially discharged)
        try {
          const wardAdmissionsResponse = await consultationAPI.getWardAdmissionsByPatientCard(patient.value.card_number, false);
          wardAdmissions.value = wardAdmissionsResponse.data || [];
          console.log('Auto-load: Loaded ward admissions:', wardAdmissions.value);
          
          // Determine if this is an IPD encounter
          const isIPD = wardAdmissions.value.some(wa => wa.encounter_id === encounterId);
          if (isIPD) {
            billingModule.value = 'ipd';
            const wardAdmission = wardAdmissions.value.find(wa => wa.encounter_id === encounterId);
            if (wardAdmission) {
              selectedWardAdmission.value = wardAdmission;
            }
          }
        } catch (error) {
          console.error('Failed to load ward admissions:', error);
          wardAdmissions.value = [];
        }
        
        // Set selected encounter
        selectedEncounter.value = filteredEncounters.value.find(e => e.id === encounterId);
        
        // Load encounter data
        await loadEncounterData();
      }
    } catch (error) {
      console.error('Failed to auto-load from route:', error);
      $q.notify({
        type: 'warning',
        message: 'Failed to load encounter details',
      });
    }
  }
};

// Watch for route changes
watch(() => route.params.encounterId, (newEncounterId) => {
  if (newEncounterId) {
    autoLoadFromRoute();
  }
});

// Auto-load on mount
onMounted(() => {
  autoLoadFromRoute();
});
</script>

<style scoped>
.module-seg {
  display: inline-flex;
  padding: 0.2rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  gap: 0.15rem;
}
.seg-btn {
  border: 0;
  background: transparent;
  color: var(--hms-text-secondary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 650;
  padding: 0.35rem 0.85rem;
  border-radius: calc(var(--hms-radius-lg) - 2px);
  cursor: pointer;
}
.seg-btn.active {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}
.patient-hero {
  position: sticky;
  top: 0.55rem;
  z-index: 6;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  margin-bottom: 0.95rem;
  padding: 0.95rem 1.1rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-glass-bg-strong);
  border: 1px solid var(--hms-border-strong);
  box-shadow: var(--hms-shadow-lg), var(--hms-shadow-inner);
  backdrop-filter: blur(16px);
}
.hero-main { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.hero-avatar {
  width: 3.1rem; height: 3.1rem; border-radius: 9999px;
  background: linear-gradient(145deg, var(--hms-accent-muted), rgba(6, 182, 212, 0.18));
  color: var(--hms-accent); display: inline-flex; align-items: center; justify-content: center;
  font-weight: 750; flex-shrink: 0;
}
.hero-name-row { display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem; }
.hero-name {
  margin: 0; font-size: var(--hms-text-2xl); font-weight: 750;
  letter-spacing: var(--hms-tracking-tight); color: var(--hms-text-primary);
}
.hero-meta {
  margin-top: 0.35rem; display: flex; flex-wrap: wrap; gap: 0.15rem 0.2rem;
  color: var(--hms-text-secondary); font-size: var(--hms-text-sm);
}
.sep { color: var(--hms-text-muted); margin: 0 0.2rem; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
.mono { font-family: var(--hms-font-mono); font-size: 0.75rem; }
.diag-panel {
  margin-bottom: 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  overflow: hidden;
}
.panel-head {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 0.75rem; padding: 0.85rem 1rem; border-bottom: 1px solid var(--hms-border);
}
.panel-title { font-size: var(--hms-text-base); font-weight: 750; color: var(--hms-text-primary); }
.panel-sub { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.panel-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
.panel-body { padding: 0.95rem 1rem; }
.panel-footer {
  display: flex; justify-content: flex-end; align-items: baseline; gap: 0.55rem;
  padding: 0.75rem 1rem; border-top: 1px solid var(--hms-border);
}
.search-body { display: flex; flex-wrap: wrap; gap: 0.55rem; align-items: center; }
.tool-input {
  height: 2.15rem; border-radius: var(--hms-radius-lg); border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg); color: var(--hms-text-primary); font-family: inherit;
  font-size: var(--hms-text-sm); padding: 0 0.7rem;
}
.tool-input:disabled { opacity: 0.55; cursor: not-allowed; }
.tool-input--search { min-width: 14rem; }
.tool-input--grow { flex: 1; min-width: 12rem; }
.encounter-row { display: flex; flex-direction: column; gap: 0.65rem; }
.encounter-select { width: 100%; max-width: 36rem; }
.badge-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.diag-table { background: transparent; }
.diag-table :deep(thead tr),
.diag-table :deep(.q-table__top) { background: transparent; }
.diag-table :deep(th) {
  font-size: 0.68rem; letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--hms-text-muted); font-weight: 700;
}
.empty-hint {
  text-align: center; color: var(--hms-text-muted); padding: 1.25rem 1rem;
  font-size: var(--hms-text-sm);
}
.empty-note { display: inline-block; margin-top: 0.35rem; font-size: var(--hms-text-xs); }
.full-width { width: 100%; }
.create-row {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 0.75rem; margin-top: 0.85rem;
}
.total-block { display: inline-flex; align-items: baseline; gap: 0.45rem; }
.total-label {
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--hms-text-muted);
}
.total-value { font-size: var(--hms-text-lg); font-weight: 750; color: var(--hms-text-primary); font-variant-numeric: tabular-nums; }
.row-actions { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
.services-cell {
  max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--hms-text-secondary); font-size: var(--hms-text-sm);
}
.amt-due { color: var(--hms-critical); font-weight: 700; font-variant-numeric: tabular-nums; }
.amt-ok { color: var(--hms-success); font-weight: 650; font-variant-numeric: tabular-nums; }
.ipd-groups { display: flex; flex-direction: column; gap: 0.85rem; padding: 0.75rem 0.85rem 1rem; }
.ipd-group {
  border: 1px solid var(--hms-border); border-radius: var(--hms-radius-lg);
  overflow: hidden; background: var(--hms-surface);
}
.ipd-group-head {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 0.55rem; padding: 0.7rem 0.85rem; border-bottom: 1px solid var(--hms-border);
}
.ipd-group-title { font-weight: 700; color: var(--hms-text-primary); font-size: var(--hms-text-sm); }
.ipd-group-sub { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.ipd-group-totals { font-size: var(--hms-text-xs); color: var(--hms-text-secondary); font-weight: 650; }
.billing-dialog-card {
  border-radius: var(--hms-radius-xl) !important;
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
}
.billing-dialog-head { border-bottom: 1px solid var(--hms-border); }
.dialog-head-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; }
.dialog-title { font-size: var(--hms-text-xl); font-weight: 750; color: var(--hms-text-primary); }
.dialog-sub { margin-top: 0.2rem; font-size: var(--hms-text-sm); color: var(--hms-text-muted); }
@media (max-width: 720px) {
  .patient-hero { position: static; }
  .tool-input--search { width: 100%; }
}
</style>
