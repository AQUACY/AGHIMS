<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Billing</div>
    <div class="text-body2 glass-text-muted q-mb-lg">Search by card or visit number, select a service (visit), then view the bill and record payment.</div>

    <!-- Search visits -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Search service (visit)</div>
        <div class="row q-col-gutter-md items-end">
          <q-input
            v-model="filters.card_number"
            filled
            dense
            label="Card number"
            clearable
            class="col-12 col-sm-3"
            @keyup.enter="loadVisits"
          />
          <q-input
            v-model="filters.visit_number"
            filled
            dense
            label="Visit number"
            clearable
            class="col-12 col-sm-3"
            @keyup.enter="loadVisits"
          />
          <q-select
            v-model="filters.status"
            :options="statusOptions"
            filled
            dense
            label="Status"
            emit-value
            map-options
            clearable
            class="col-12 col-sm-2"
          />
          <q-btn
            unelevated
            label="Search"
            class="glass-button"
            icon="search"
            :loading="loadingVisits"
            @click="loadVisits"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Visit selection -->
    <q-card v-if="visits.length > 0" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Select a visit to view and bill</div>
        <q-table
          :rows="visits"
          :columns="visitColumns"
          row-key="id"
          flat
          dense
          :rows-per-page-options="[5, 10, 25]"
          class="glass-table"
        >
          <template v-slot:body-cell-created_at="props">
            <q-td :props="props">{{ formatDate(props.row.created_at) }}</q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                size="sm"
                color="primary"
                icon="receipt_long"
                label="View bill"
                @click="selectVisit(props.row)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
    <div v-else-if="searched && !loadingVisits" class="text-grey-7 q-mb-md">No visits found. Try different filters or create a service first.</div>

    <!-- Selected visit & bill -->
    <template v-if="selectedVisit">
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div>
              <div class="text-h6 glass-text">Client / Visit</div>
              <div class="text-body2">
                Card: {{ selectedVisit.external_card_number }} · Visit: {{ selectedVisit.external_visit_number }}
                <span v-if="selectedVisit.client_name"> · {{ selectedVisit.client_name }}</span>
              </div>
              <div class="q-mt-xs">
                <q-badge :color="selectedVisit.status === 'closed' ? 'grey' : 'primary'">
                  {{ selectedVisit.status }}
                </q-badge>
                <q-badge v-if="selectedVisit.undertaking_status === 'pending'" color="orange" class="q-ml-sm">
                  Undertaking pending
                </q-badge>
                <q-badge v-if="selectedVisit.undertaking_status === 'approved'" color="teal" class="q-ml-sm">
                  Undertaking approved
                </q-badge>
                <span v-if="(selectedVisit.undertaking_status === 'pending' || selectedVisit.undertaking_status === 'approved') && selectedVisit.undertaking_deposit_amount != null" class="q-ml-sm text-body2">
                  Deposit: GH¢ {{ formatPrice(selectedVisit.undertaking_deposit_amount) }}
                </span>
                <div v-if="selectedVisit.undertaking_status === 'approved' && selectedVisit.undertaking_approved_by_name" class="q-mt-xs text-body2 text-grey-8">
                  Approved by <strong>{{ selectedVisit.undertaking_approved_by_name }}</strong> on {{ formatDate(selectedVisit.undertaking_approved_at) }}
                </div>
                <div v-if="selectedVisit.undertaking_unapproved_by_name" class="q-mt-xs text-body2 text-grey-8">
                  Unapproved by <strong>{{ selectedVisit.undertaking_unapproved_by_name }}</strong> on {{ formatDate(selectedVisit.undertaking_unapproved_at) }}
                </div>
              </div>
            </div>
            <q-space />
            <div class="row q-gutter-sm no-wrap">
              <q-btn
                v-if="canCloseVisit"
                unelevated
                color="primary"
                icon="lock"
                label="Close visit"
                :loading="closingVisit"
                @click="confirmCloseVisit"
              />
              <q-btn
                v-if="canReopenVisit"
                unelevated
                color="secondary"
                icon="lock_open"
                label="Reopen visit"
                :loading="reopeningVisit"
                @click="showReopenDialog = true"
              />
              <q-btn
                v-if="canRequestUndertaking"
                flat
                color="orange"
                icon="description"
                label="Request undertaking"
                :loading="undertakingRequesting"
                @click="showRequestUndertakingDialog = true"
              />
              <q-btn
                v-if="canEditUndertaking"
                flat
                color="orange"
                icon="edit"
                label="Edit undertaking"
                :loading="undertakingUpdating"
                @click="openEditUndertakingDialog"
              />
              <q-btn
                v-if="canCancelUndertaking"
                flat
                color="negative"
                icon="cancel"
                label="Cancel undertaking"
                :loading="undertakingCancelling"
                @click="confirmCancelUndertakingFromCard"
              >
                <q-tooltip>Cancel undertaking (e.g. client paid in full). Requester or Admin only.</q-tooltip>
              </q-btn>
              <q-btn
                v-if="canApproveUndertaking"
                unelevated
                color="teal"
                icon="check_circle"
                label="Approve undertaking"
                :loading="undertakingApproving"
                @click="showApproveUndertakingDialog = true"
              />
              <q-btn
                v-if="canUnapproveUndertaking"
                unelevated
                color="secondary"
                icon="undo"
                label="Unapprove undertaking"
                :loading="undertakingUnapproving"
                @click="showUnapproveUndertakingDialog = true"
              />
            </div>
            <q-btn flat dense icon="close" label="Clear" @click="clearSelection" />
          </div>
        </q-card-section>
      </q-card>

      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div>
              <div class="text-h6 glass-text">Bill items</div>
              <div class="text-caption text-grey-7">Sections: Drugs, Investigations, Scans, X-rays, Surgeries (day &amp; major), Dressing / Treatment room, Oxygen, Inpatient.</div>
            </div>
            <q-space />
            <q-btn
              v-if="selectedVisit"
              flat
              color="primary"
              icon="fact_check"
              label="Check vs Government OPD Excel"
              class="q-mr-sm"
              @click="showReconcileDialog = true"
            />
            <q-btn
              v-if="selectedVisit"
              flat
              color="primary"
              icon="description"
              label="Check vs Government IPD invoice"
              class="q-mr-sm"
              @click="showIpdReconcileDialog = true"
            />
            <q-btn
              v-if="canMarkPaid && selectedVisit && selectedVisit.status === 'open'"
              unelevated
              color="primary"
              icon="add"
              label="Add inpatient fee"
              class="glass-button q-mr-md"
              @click="openAddInpatientFeeDialog"
            />
            <div v-if="canMarkPaid && selectedVisit && selectedVisit.status === 'open'" class="text-caption text-grey-7">
              Payments are grouped by category (one receipt per category by default). You can still override receipts per item.
            </div>
            <div v-if="selectedVisit && selectedVisit.status === 'closed' && !canAdmin" class="text-caption text-grey-7">
              This visit is closed. Only Admin can reopen or edit.
            </div>
          </div>
          <q-linear-progress v-if="loadingItems" indeterminate class="q-mb-md" />
          <div v-else-if="billItems.length > 0">
            <q-card
              v-for="group in groupedBillItems"
              :key="group.key"
              class="q-mb-md glass-card"
              flat
            >
              <q-card-section class="q-pb-sm">
                <div class="row items-center">
                  <div>
                    <div class="text-subtitle1 text-weight-bold">{{ group.title }}</div>
                    <div class="text-caption text-grey-7">
                      Total: GH¢ {{ formatPrice(group.total) }} · Unpaid: GH¢ {{ formatPrice(group.unpaidTotal) }}
                    </div>
                  </div>
                  <q-space />
                  <q-btn
                    v-if="canMarkPaid && selectedVisit && selectedVisit.status === 'open'"
                    unelevated
                    color="primary"
                    icon="receipt"
                    class="glass-button"
                    label="Pay selected"
                    :disable="selectedIdsByCategory[group.key].length === 0"
                    @click="openPayDialogForCategory(group.key)"
                  />
                </div>
              </q-card-section>
              <q-card-section class="q-pt-none">
                <q-table
                  :rows="group.items"
                  :columns="billColumns"
                  row-key="id"
                  flat
                  dense
                  class="glass-table"
                  selection="multiple"
                  v-model:selected="selectedRowsByCategory[group.key]"
                  :rows-per-page-options="[0]"
                  hide-pagination
                >
                  <template v-slot:body-cell-item_name="props">
                    <q-td :props="props">
                      <div class="text-body2" :style="props.row.cancelled ? 'text-decoration: line-through; opacity: 0.75;' : ''">
                        {{ props.row.item_name }}
                      </div>
                      <div v-if="props.row.category === 'oxygen' && props.row.start_time && props.row.end_time" class="text-caption text-grey-7">
                        {{ formatOxygenPeriod(props.row) }}
                      </div>
                      <div v-if="props.row.created_by_name" class="text-caption text-grey-7">Added by: {{ props.row.created_by_name }}</div>
                      <div v-if="props.row.cancelled" class="text-caption text-negative q-mt-xs">
                        Cancelled {{ formatDate(props.row.cancelled_at) }} by {{ props.row.cancelled_by_name || '—' }} — {{ props.row.cancel_reason || '—' }}
                      </div>
                    </q-td>
                  </template>
                  <template v-slot:body-cell-created_at="props">
                    <q-td :props="props">{{ formatDate(props.row.created_at) }}</q-td>
                  </template>
                  <template v-slot:body-cell-unit_price="props">
                    <q-td :props="props">GH¢ {{ formatPrice(props.row.unit_price) }}</q-td>
                  </template>
                  <template v-slot:body-cell-amount="props">
                    <q-td :props="props">GH¢ {{ formatPrice((props.row.unit_price || 0) * (props.row.quantity || 1)) }}</q-td>
                  </template>
                  <template v-slot:body-cell-paid="props">
                    <q-td :props="props">
                      <q-badge v-if="props.row.cancelled" color="negative">Cancelled</q-badge>
                      <template v-if="isPaidRow(props.row)">
                        <q-badge color="positive">{{ paidLabel(props.row) }}</q-badge>
                        <div v-if="props.row.paid_at" class="text-caption text-grey-7">{{ formatDate(props.row.paid_at) }}</div>
                      </template>
                      <q-badge v-else-if="!props.row.cancelled" color="warning">Unpaid</q-badge>
                    </q-td>
                  </template>
                  <template v-slot:body-cell-actions="props">
                    <q-td :props="props">
                      <template v-if="canMarkPaid && selectedVisit && selectedVisit.status === 'open' && !isPaidRow(props.row) && !props.row.cancelled">
                        <q-btn
                          flat
                          dense
                          size="sm"
                          icon="receipt"
                          label="Pay"
                          color="primary"
                          @click="paySingle(props.row)"
                        />
                      </template>
                      <template v-else-if="canMarkPaid && selectedVisit && selectedVisit.status === 'open' && isPaidRow(props.row) && props.row.receipt_number && !props.row.cancelled">
                        <q-btn
                          flat
                          dense
                          size="sm"
                          icon="undo"
                          label="Refund"
                          color="warning"
                          :loading="refundingItemId === props.row.id"
                          @click="refundItem(props.row)"
                        >
                          <q-tooltip>Reverse payment for this item</q-tooltip>
                        </q-btn>
                      </template>
                      <template v-if="canAddItems && selectedVisit && selectedVisit.status === 'open' && !props.row.receipt_number && !props.row.cancelled">
                        <q-btn
                          flat
                          dense
                          size="sm"
                          icon="cancel"
                          label="Cancel"
                          color="negative"
                          :loading="cancellingItemId === props.row.id"
                          @click="cancelBillItem(props.row)"
                        >
                          <q-tooltip>Cancel this item (reason required)</q-tooltip>
                        </q-btn>
                      </template>
                      <template v-if="isSuperAdmin && selectedVisit && selectedVisit.status === 'open' && !props.row.receipt_number">
                        <q-btn
                          flat
                          dense
                          size="sm"
                          icon="delete_forever"
                          label="Delete"
                          color="negative"
                          :loading="deletingItemId === props.row.id"
                          @click="deleteBillItem(props.row)"
                        >
                          <q-tooltip>Superadmin: hard delete (no record)</q-tooltip>
                        </q-btn>
                      </template>
                      <template v-if="canEditDeleteInpatient && isInpatientItem(props.row) && !isPaidRow(props.row) && selectedVisit && selectedVisit.status === 'open'">
                        <q-btn
                          flat
                          dense
                          size="sm"
                          icon="edit"
                          label="Edit"
                          color="grey"
                          :loading="editingItemId === props.row.id"
                          @click="openEditInpatientFee(props.row)"
                        >
                          <q-tooltip>Edit amount or description</q-tooltip>
                        </q-btn>
                      </template>
                    </q-td>
                  </template>
                </q-table>
              </q-card-section>
            </q-card>
          </div>
          <div v-else class="text-grey-7 text-center q-pa-lg">No items on this visit. Add lab, scan, X-ray, drugs, surgeries, or dressing room services from the visit detail page.</div>

          <!-- Pending from Government (not yet added) -->
          <q-card
            v-if="pendingGovItems.length > 0"
            class="q-mt-md glass-card"
            flat
          >
            <q-card-section>
              <div class="row items-center">
                <div>
                  <div class="text-h6 glass-text">Pending from Government</div>
                  <div class="text-caption text-grey-7">
                    These services are in the imported GHIMS export but not yet in the bill. Click Confirm to add automatically (price list match + export qty).
                  </div>
                </div>
                <q-space />
              </div>
              <q-table
                class="glass-table q-mt-md"
                :rows="pendingGovItems"
                :columns="pendingGovCols"
                row-key="key"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
              >
                <template v-slot:body="props">
                  <q-tr :props="props" style="opacity: 0.6">
                    <q-td key="description" :props="props">{{ props.row.description }}</q-td>
                    <q-td key="quantity" :props="props" class="text-right">{{ props.row.quantity }}</q-td>
                    <q-td key="actions" :props="props" class="text-right">
                      <q-btn
                        unelevated
                        color="primary"
                        size="sm"
                        icon="check"
                        label="Confirm"
                        :loading="confirmingGovKey === props.row.key"
                        @click="confirmGovItem(props.row)"
                      />
                    </q-td>
                  </q-tr>
                </template>
              </q-table>
            </q-card-section>
          </q-card>

          <div v-if="billItems.length > 0" class="row q-mt-lg justify-end column items-end">
            <div class="text-h6 text-weight-bold">Total: GH¢ {{ formatPrice(billTotal) }}</div>
            <div class="text-body2 text-grey-7">Paid so far: GH¢ {{ formatPrice(paidAmount) }}</div>
            <div v-if="undertakingDepositAmount != null && undertakingDepositAmount > 0" class="text-body2 text-grey-7">
              Deposit: GH¢ {{ formatPrice(undertakingDepositAmount) }}
            </div>
            <div class="row items-center q-gutter-sm no-wrap">
              <div class="text-subtitle1 text-weight-medium">Pending balance: GH¢ {{ formatPrice(pendingBalance) }}</div>
              <q-btn
                v-if="showCloseVisitByBalance"
                unelevated
                color="primary"
                icon="lock"
                label="Close visit"
                size="sm"
                :loading="closingVisit"
                @click="confirmCloseVisit"
              >
                <q-tooltip>Pending balance is zero. Close this visit for the client.</q-tooltip>
              </q-btn>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </template>

    <!-- Reconcile with government OPD Excel export -->
    <q-dialog v-model="showReconcileDialog" persistent>
      <q-card style="min-width: 720px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">Check billing vs government OPD export</div>
          <div v-if="selectedVisit" class="text-caption text-grey-7 q-mt-sm">
            This will only work if the file matches this visit:
            claim_no = {{ selectedVisit.external_visit_number }} and patient_no = {{ selectedVisit.external_card_number }}.
          </div>
          <div class="text-caption text-grey-7 q-mt-sm">
            {{ reconcileStatusText }}
          </div>
          <div class="text-caption text-grey-7 q-mt-sm">
            If new services were added in GHIMS after the last import, re-download the export from GHIMS and upload again here.
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-file
            v-model="reconcileFile"
            filled
            dense
            clearable
            accept=".xls,.xlsx"
            label="Upload OPD export (.xls/.xlsx)"
          />
          <div class="row q-mt-md items-center q-gutter-sm">
            <q-btn
              unelevated
              color="primary"
              icon="upload_file"
              :label="reconcileFile ? 'Upload & run check' : 'Run check (saved)'"
              :disable="!selectedVisit"
              :loading="reconciling"
              @click="runReconcile"
            />
            <q-btn
              v-if="canAdmin && selectedVisit && reconcileResult && reconcileResult.imported_at"
              flat
              color="negative"
              icon="delete_forever"
              label="Clear saved import"
              :loading="clearingSavedImport"
              @click="confirmClearSavedImport"
            />
            <q-btn flat color="grey" label="Close" v-close-popup />
          </div>

          <q-separator class="q-my-md" />

          <q-linear-progress v-if="reconciling" indeterminate />

          <div v-else-if="reconcileResult">
            <div class="row items-center q-col-gutter-md q-mb-sm">
              <div class="col-12 col-sm-6">
                <q-card flat bordered class="q-pa-sm">
                  <div class="text-body2"><strong>Claim No:</strong> {{ reconcileResult.claim_no || '—' }}</div>
                  <div class="text-body2"><strong>Patient No (Card):</strong> {{ reconcileResult.patient_no || '—' }}</div>
                  <div class="text-body2"><strong>Status:</strong> {{ reconcileResult.claim_status || '—' }}</div>
                  <div class="text-body2"><strong>Date:</strong> {{ reconcileResult.service_date || '—' }}</div>
                </q-card>
              </div>
              <div class="col-12 col-sm-6">
                <q-card flat bordered class="q-pa-sm">
                  <div class="text-body2"><strong>Missing in Companion bill:</strong> {{ (reconcileResult.missing_in_billing || []).length }}</div>
                  <div class="text-body2"><strong>Extra in Companion bill:</strong> {{ (reconcileResult.extra_in_billing || []).length }}</div>
                  <div class="text-body2"><strong>Qty mismatches:</strong> {{ (reconcileResult.quantity_mismatches || []).length }}</div>
                </q-card>
              </div>
            </div>

            <q-expansion-item
              v-if="(reconcileResult.missing_in_billing || []).length"
              label="Missing in Companion bill (present in government export)"
              icon="playlist_add"
              class="q-mb-sm"
              default-opened
            >
              <div class="row items-center q-gutter-sm q-pa-sm">
                <q-select
                  v-model="bulkAddCategory"
                  :options="addMissingCategoryOptions"
                  dense
                  outlined
                  emit-value
                  map-options
                  label="Category for selected"
                  style="min-width: 220px"
                />
                <q-btn
                  unelevated
                  color="primary"
                  icon="playlist_add"
                  label="Add selected (price list)"
                  :disable="!missingSelectedRows.length"
                  :loading="bulkAddingMissing"
                  @click="addSelectedMissingFromPriceList"
                />
                <div class="text-caption text-grey-7">
                  Selected: {{ missingSelectedRows.length }}
                </div>
              </div>
              <q-table
                :rows="reconcileResult.missing_in_billing"
                :columns="reconcileGovCols"
                row-key="normalized"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
                selection="multiple"
                v-model:selected="missingSelectedRows"
              >
                <template v-slot:body-cell-actions="props">
                  <q-td :props="props">
                    <q-btn
                      flat
                      dense
                      size="sm"
                      icon="add"
                      color="primary"
                      label="Add"
                      @click="openAddMissing(props.row)"
                    />
                    <q-btn
                      flat
                      dense
                      size="sm"
                      icon="search"
                      color="secondary"
                      label="Find price"
                      class="q-ml-sm"
                      @click="openPriceSuggest(props.row)"
                    />
                  </q-td>
                </template>
              </q-table>
            </q-expansion-item>

            <q-expansion-item
              v-if="(reconcileResult.extra_in_billing || []).length"
              label="Extra in Companion bill (not found in government export)"
              icon="remove_circle"
              class="q-mb-sm"
            >
              <q-table
                :rows="reconcileResult.extra_in_billing"
                :columns="reconcileBillCols"
                row-key="id"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
              />
            </q-expansion-item>

            <q-expansion-item
              v-if="(reconcileResult.quantity_mismatches || []).length"
              label="Quantity mismatches"
              icon="difference"
            >
              <q-table
                :rows="reconcileResult.quantity_mismatches"
                :columns="reconcileMismatchCols"
                row-key="normalized"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
              >
                <template v-slot:body-cell-normalized="props">
                  <q-td :props="props">{{ props.row.normalized }}</q-td>
                </template>
              </q-table>
            </q-expansion-item>
          </div>

          <div v-else class="text-caption text-grey-7">
            Upload the OPD export and run the check to see what was missed or added wrongly.
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Reconcile with government IPD (in-patient) invoice -->
    <q-dialog v-model="showIpdReconcileDialog" persistent>
      <q-card style="min-width: 720px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">Check billing vs government IPD invoice</div>
          <div v-if="selectedVisit" class="text-caption text-grey-7 q-mt-sm">
            Upload the IPD invoice for this visit, or re-import when new data is added on GHIMS.
          </div>
          <div class="text-caption text-grey-7 q-mt-sm">{{ ipdReconcileStatusText }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-file
            v-model="ipdReconcileFile"
            filled
            dense
            clearable
            accept=".xls,.xlsx"
            label="Upload IPD invoice (.xls/.xlsx)"
          />
          <div class="row q-mt-md items-center q-gutter-sm">
            <q-btn
              unelevated
              color="primary"
              icon="upload_file"
              :label="ipdReconcileFile ? 'Upload & run check' : 'Run check (saved)'"
              :disable="!selectedVisit"
              :loading="ipdReconciling"
              @click="runIpdReconcile"
            />
            <q-btn
              v-if="canAdmin && selectedVisit && ipdReconcileResult && ipdReconcileResult.imported_at"
              flat
              color="negative"
              icon="delete_forever"
              label="Clear saved import"
              :loading="ipdClearingSaved"
              @click="confirmClearSavedIpdImport"
            />
            <q-btn flat color="grey" label="Close" v-close-popup />
          </div>

          <q-separator class="q-my-md" />
          <q-linear-progress v-if="ipdReconciling" indeterminate />

          <div v-else-if="ipdReconcileResult" class="q-mt-sm">
            <div class="row items-center q-col-gutter-md q-mb-sm">
              <div class="col-12 col-sm-6">
                <q-card flat bordered class="q-pa-sm">
                  <div class="text-body2"><strong>Admission No:</strong> {{ ipdReconcileResult.admission_no || ipdReconcileResult.claim_no || '—' }}</div>
                  <div class="text-body2"><strong>Visit No:</strong> {{ ipdReconcileResult.visit_no || '—' }}</div>
                  <div class="text-body2"><strong>Patient No:</strong> {{ ipdReconcileResult.patient_no || '—' }}</div>
                  <div class="text-body2"><strong>Patient Name:</strong> {{ ipdReconcileResult.patient_name || '—' }}</div>
                  <div class="text-body2"><strong>Invoice No:</strong> {{ ipdReconcileResult.invoice_no || '—' }}</div>
                  <div class="text-body2"><strong>Date:</strong> {{ ipdReconcileResult.invoice_date || ipdReconcileResult.admission_date || '—' }}</div>
                </q-card>
              </div>
              <div class="col-12 col-sm-6">
                <q-card flat bordered class="q-pa-sm">
                  <div class="text-body2"><strong>Missing in Companion bill:</strong> {{ (ipdReconcileResult.missing_in_billing || []).length }}</div>
                  <div class="text-body2"><strong>Extra in Companion bill:</strong> {{ (ipdReconcileResult.extra_in_billing || []).length }}</div>
                  <div class="text-body2"><strong>Qty mismatches:</strong> {{ (ipdReconcileResult.quantity_mismatches || []).length }}</div>
                </q-card>
              </div>
            </div>

            <q-expansion-item
              v-if="(ipdReconcileResult.missing_in_billing || []).length"
              label="Missing in Companion bill (present in government IPD)"
              icon="playlist_add"
              class="q-mb-sm"
              default-opened
            >
              <div class="row items-center q-gutter-sm q-pa-sm">
                <q-select
                  v-model="ipdBulkAddCategory"
                  :options="addMissingCategoryOptions"
                  dense
                  outlined
                  emit-value
                  map-options
                  label="Category for selected"
                  style="min-width: 220px"
                />
                <q-btn
                  unelevated
                  color="primary"
                  icon="playlist_add"
                  label="Add selected (price list)"
                  :disable="!ipdMissingSelectedRows.length"
                  :loading="ipdBulkAddingMissing"
                  @click="addSelectedMissingFromIpd"
                />
                <div class="text-caption text-grey-7">Selected: {{ ipdMissingSelectedRows.length }}</div>
              </div>
              <q-table
                :rows="ipdReconcileResult.missing_in_billing"
                :columns="reconcileGovCols"
                row-key="normalized"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
                selection="multiple"
                v-model:selected="ipdMissingSelectedRows"
              >
                <template v-slot:body-cell-actions="props">
                  <q-td :props="props">
                    <q-btn flat dense size="sm" icon="add" color="primary" label="Add" @click="openAddMissingFromIpd(props.row)" />
                    <q-btn flat dense size="sm" icon="search" color="secondary" label="Find price" class="q-ml-sm" @click="openPriceSuggestFromIpd(props.row)" />
                  </q-td>
                </template>
              </q-table>
            </q-expansion-item>

            <q-expansion-item
              v-if="(ipdReconcileResult.extra_in_billing || []).length"
              label="Extra in Companion bill (not in government IPD)"
              icon="remove_circle"
              class="q-mb-sm"
            >
              <q-table
                :rows="ipdReconcileResult.extra_in_billing"
                :columns="reconcileBillCols"
                row-key="id"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
              />
            </q-expansion-item>

            <q-expansion-item
              v-if="(ipdReconcileResult.quantity_mismatches || []).length"
              label="Quantity mismatches"
              icon="difference"
            >
              <q-table
                :rows="ipdReconcileResult.quantity_mismatches"
                :columns="reconcileMismatchCols"
                row-key="normalized"
                flat
                dense
                :rows-per-page-options="[0]"
                hide-pagination
              />
            </q-expansion-item>
          </div>

          <div v-else class="text-caption text-grey-7">
            Upload the IPD invoice and run the check, or run from last saved import.
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add a missing government service to Companion bill -->
    <q-dialog v-model="showAddMissingDialog" persistent>
      <q-card style="min-width: 420px; max-width: 90vw">
        <q-card-section>
          <div class="text-h6">Add missing service</div>
          <div class="text-caption text-grey-7 q-mt-sm">
            Service: <strong>{{ addMissingRow?.description || '—' }}</strong> · Qty: {{ addMissingQty }}
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select
            v-model="addMissingCategory"
            :options="addMissingCategoryOptions"
            filled
            dense
            emit-value
            map-options
            label="Category"
            class="q-mb-md"
          />
          <q-input
            v-model="addMissingCode"
            filled
            dense
            label="Item code (if known)"
            placeholder="e.g. G-DRG code"
            class="q-mb-md"
          />
          <q-input
            v-model.number="addMissingUnitPrice"
            type="number"
            min="0"
            step="0.01"
            filled
            dense
            label="Unit price (copayment)"
            class="q-mb-md"
          />
          <q-input
            v-model.number="addMissingQty"
            type="number"
            min="0"
            step="0.01"
            filled
            dense
            label="Quantity"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Add to bill"
            color="primary"
            :disable="!canSubmitAddMissing"
            :loading="addingMissing"
            @click="confirmAddMissing"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Price suggestions dialog (officer confirms match) -->
    <q-dialog v-model="showPriceSuggestDialog" persistent>
      <q-card style="min-width: 760px; max-width: 95vw">
        <q-card-section>
          <div class="text-h6">Match service to price list</div>
          <div class="text-caption text-grey-7 q-mt-sm">
            Government: <strong>{{ priceSuggestRow?.description || '—' }}</strong> · Qty: {{ priceSuggestQty }}
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="row items-center q-gutter-sm">
            <q-select
              v-model="priceSuggestCategory"
              :options="addMissingCategoryOptions"
              dense
              outlined
              emit-value
              map-options
              label="Category"
              style="min-width: 220px"
            />
            <q-input
              v-model="priceSuggestQuery"
              dense
              outlined
              label="Search term"
              style="flex: 1"
              @keyup.enter="runPriceSuggest"
            />
            <q-btn
              unelevated
              color="primary"
              icon="search"
              label="Search"
              :loading="loadingPriceSuggest"
              @click="runPriceSuggest"
            />
          </div>

          <q-table
            class="q-mt-md"
            :rows="priceSuggestResults"
            :columns="priceSuggestCols"
            row-key="item_code"
            flat
            dense
            :rows-per-page-options="[0]"
            hide-pagination
            selection="single"
            v-model:selected="priceSuggestSelected"
          >
            <template v-slot:body-cell-unit_price="props">
              <q-td :props="props">GH¢ {{ formatPrice(props.row.unit_price) }}</q-td>
            </template>
            <template v-slot:body-cell_score="props">
              <q-td :props="props">{{ (props.row.score * 100).toFixed(0) }}%</q-td>
            </template>
          </q-table>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="grey" v-close-popup />
          <q-btn
            unelevated
            color="primary"
            label="Confirm & add"
            :disable="priceSuggestSelected.length === 0 || !selectedVisit || selectedVisit.status !== 'open'"
            :loading="addingFromSuggestion"
            @click="confirmAddFromSuggestion"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Pay dialog: category receipt + optional per-item overrides + payment method -->
    <q-dialog v-model="showMarkPaidDialog" persistent>
      <q-card style="min-width: 520px; max-width: 90vw">
        <q-card-section>
          <div class="text-h6">Pay {{ payDialogTitle }}</div>
          <div class="text-caption text-grey-7 q-mt-sm">
            By default, one receipt number will be used for all selected items in this category. You can override per item if needed.
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input
            v-model="payDialogDefaultReceipt"
            dense
            outlined
            label="Receipt number (default for this category)"
            class="q-mb-md"
          />
          <q-select
            v-model="payDialogPaymentMethod"
            :options="paymentMethodOptions"
            dense
            outlined
            emit-value
            map-options
            options-dense
            label="Payment method"
            class="q-mb-md"
          >
            <template v-slot:prepend>
              <q-icon name="payments" />
            </template>
          </q-select>
          <q-table
            :rows="itemsToPay"
            :columns="payDialogColumns"
            row-key="id"
            flat
            dense
            hide-pagination
            class="pay-dialog-table"
            style="max-height: 320px;"
          >
            <template v-slot:body-cell-item_name="props">
              <q-td :props="props">
                <div class="text-body2">{{ props.row.item_name }}</div>
                <div class="text-caption text-grey-7">GH¢ {{ formatPrice(rowAmount(props.row)) }}</div>
              </q-td>
            </template>
            <template v-slot:body-cell-receipt_number="props">
              <q-td :props="props">
                <q-input
                  v-model="itemReceipts[props.row.id]"
                  dense
                  outlined
                  placeholder="Override receipt (optional)"
                  class="receipt-input"
                />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Mark as paid"
            color="primary"
            :disable="!hasAnyReceiptInDialog"
            :loading="markingPaid"
            @click="confirmMarkPaid"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add inpatient fee dialog -->
    <q-dialog v-model="showAddInpatientFeeDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">Add inpatient fee</div>
          <div class="text-caption text-grey-7 q-mt-sm">Add a line item for inpatient fee. Visit must be open.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="inpatientFeeAmount"
            type="number"
            min="0"
            step="0.01"
            filled
            dense
            label="Amount (GH¢)"
            class="q-mb-md"
          />
          <q-input
            v-model="inpatientFeeDescription"
            filled
            dense
            label="Description (optional)"
            placeholder="e.g. Inpatient Fee"
            clearable
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Add to bill"
            color="primary"
            :disable="!isInpatientFeeValid"
            :loading="addingInpatientFee"
            @click="confirmAddInpatientFee"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit inpatient fee dialog -->
    <q-dialog v-model="showEditInpatientFeeDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">Edit inpatient fee</div>
          <div class="text-caption text-grey-7 q-mt-sm">Change amount or description. Only unpaid items can be edited.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="editInpatientAmount"
            type="number"
            min="0"
            step="0.01"
            filled
            dense
            label="Amount (GH¢)"
            class="q-mb-md"
          />
          <q-input
            v-model="editInpatientDescription"
            filled
            dense
            label="Description (optional)"
            placeholder="e.g. Inpatient Fee"
            clearable
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Save"
            color="primary"
            :disable="!isEditInpatientFeeValid"
            :loading="editingItemId !== null"
            @click="confirmEditInpatientFee"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Request undertaking dialog: optional deposit -->
    <q-dialog v-model="showRequestUndertakingDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">Request undertaking</div>
          <div class="text-caption text-grey-7 q-mt-sm">Client will pay later. Optionally record a deposit amount (not mapped to items) to solidify the agreement.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="requestUndertakingDeposit"
            type="number"
            min="0"
            step="0.01"
            filled
            dense
            label="Deposit amount (GH¢) – optional"
            placeholder="0 or leave empty"
          />
          <q-input
            v-model="requestUndertakingDepositReceipt"
            filled
            dense
            label="Deposit receipt number (optional)"
            class="q-mt-md"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Request undertaking"
            color="orange"
            :loading="undertakingRequesting"
            @click="confirmRequestUndertaking"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit undertaking dialog: change deposit or cancel -->
    <q-dialog v-model="showEditUndertakingDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">Edit undertaking</div>
          <div class="text-caption text-grey-7 q-mt-sm">Change the deposit amount or cancel the undertaking if the client has paid in full.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model.number="editUndertakingDeposit"
            type="number"
            min="0"
            step="0.01"
            filled
            dense
            label="Deposit amount (GH¢)"
          />
          <q-input
            v-model="editUndertakingDepositReceipt"
            filled
            dense
            label="Deposit receipt number (optional)"
            class="q-mt-md"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel undertaking" color="negative" @click="confirmCancelUndertaking" />
          <q-space />
          <q-btn flat label="Close" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Save"
            color="primary"
            :loading="undertakingUpdating"
            @click="confirmUpdateUndertaking"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Approve undertaking: Management sees amount, time, officer -->
    <q-dialog v-model="showApproveUndertakingDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Approve undertaking</div>
          <div class="text-caption text-grey-7 q-mt-sm">Review and approve. The visit can then be closed even with unpaid items.</div>
          <q-card v-if="selectedVisit" flat bordered class="q-mt-md q-pa-md">
            <div class="text-body2"><strong>Deposit:</strong> GH¢ {{ formatPrice(selectedVisit.undertaking_deposit_amount || 0) }}</div>
            <div class="text-body2 q-mt-sm"><strong>Deposit receipt:</strong> {{ selectedVisit.undertaking_deposit_receipt_number || '—' }}</div>
            <div class="text-body2 q-mt-sm"><strong>Requested at:</strong> {{ formatDate(selectedVisit.undertaking_requested_at) }}</div>
            <div class="text-body2 q-mt-sm"><strong>Requested by:</strong> {{ selectedVisit.undertaking_requested_by_name || '—' }}</div>
          </q-card>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Approve"
            color="teal"
            :loading="undertakingApproving"
            @click="confirmApproveUndertaking"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Unapprove undertaking: Admin only, reason required -->
    <q-dialog v-model="showUnapproveUndertakingDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">Unapprove undertaking</div>
          <div class="text-caption text-grey-7 q-mt-sm">Admin only. Provide a reason for auditing. This will set the undertaking back to Pending.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="unapproveReason"
            filled
            dense
            type="textarea"
            rows="3"
            label="Reason"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Unapprove"
            color="secondary"
            :disable="!unapproveReason.trim()"
            :loading="undertakingUnapproving"
            @click="confirmUnapproveUndertaking"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reopen visit dialog (Admin only, reason required) -->
    <q-dialog v-model="showReopenDialog" persistent>
      <q-card style="min-width: 360px">
        <q-card-section>
          <div class="text-h6">Reopen visit</div>
          <div class="text-caption text-grey-7 q-mt-sm">Only Admin can reopen. A reason is required for auditing.</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="reopenReason"
            filled
            dense
            label="Reason for reopening"
            type="textarea"
            rows="3"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn
            unelevated
            label="Reopen"
            color="secondary"
            :disable="!reopenReason.trim()"
            :loading="reopeningVisit"
            @click="confirmReopenVisit"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../../stores/auth';
import { companionVisitsAPI, billingAPI } from '../../services/api';

const $q = useQuasar();
const authStore = useAuthStore();

const loadingVisits = ref(false);
const loadingItems = ref(false);
const searched = ref(false);
const visits = ref([]);
const selectedVisit = ref(null);
const billItems = ref([]);
const filters = reactive({
  card_number: '',
  visit_number: '',
  status: null,
});
const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

const visitColumns = [
  { name: 'external_card_number', label: 'Card number', field: 'external_card_number', align: 'left' },
  { name: 'external_visit_number', label: 'Visit number', field: 'external_visit_number', align: 'left' },
  { name: 'client_name', label: 'Client name', field: 'client_name', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left' },
  { name: 'actions', label: '', align: 'right' },
];

const billColumns = [
  { name: 'item_name', label: 'Item', field: 'item_name', align: 'left' },
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'created_at', label: 'Added', field: 'created_at', align: 'left' },
  { name: 'unit_price', label: 'Unit price', align: 'right' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'amount', label: 'Amount', align: 'right' },
  { name: 'paid', label: 'Payment', align: 'left' },
  { name: 'actions', label: '', align: 'right' },
];

const payDialogColumns = [
  { name: 'item_name', label: 'Item', align: 'left' },
  { name: 'receipt_number', label: 'Receipt number', align: 'left' },
];

const showMarkPaidDialog = ref(false);
const itemReceipts = ref({});
const payDialogDefaultReceipt = ref('');
  const payDialogPaymentMethod = ref('cash');
const payDialogCategoryKey = ref(null);
const payDialogItemIds = ref([]);
const markingPaid = ref(false);
const refundingItemId = ref(null);

const showReconcileDialog = ref(false);
const reconcileFile = ref(null);
const reconciling = ref(false);
const reconcileResult = ref(null);
const reconcileStatusText = computed(() => {
  if (!reconcileResult.value?.imported_at) return 'No government export imported yet.';
  const who = reconcileResult.value.imported_by_name ? ` by ${reconcileResult.value.imported_by_name}` : '';
  return `Last imported: ${formatDate(reconcileResult.value.imported_at)}${who}.`;
});

const showIpdReconcileDialog = ref(false);
const ipdReconcileFile = ref(null);
const ipdReconciling = ref(false);
const ipdReconcileResult = ref(null);
const ipdReconcileStatusText = computed(() => {
  if (!ipdReconcileResult.value?.imported_at) return 'No government IPD import yet.';
  const who = ipdReconcileResult.value.imported_by_name ? ` by ${ipdReconcileResult.value.imported_by_name}` : '';
  return `Last imported: ${formatDate(ipdReconcileResult.value.imported_at)}${who}.`;
});
const ipdClearingSaved = ref(false);
const ipdBulkAddCategory = ref('lab');
const ipdMissingSelectedRows = ref([]);
const ipdBulkAddingMissing = ref(false);

const addMissingSource = ref('opd'); // 'opd' | 'ipd' - which reconcile dialog opened add-missing
const showAddMissingDialog = ref(false);
const addMissingRow = ref(null);
const addMissingCategory = ref('lab');
const addMissingCode = ref('');
const addMissingUnitPrice = ref(null);
const addMissingQty = ref(1);
const addingMissing = ref(false);
const missingSelectedRows = ref([]);
const bulkAddCategory = ref('lab');
const bulkAddingMissing = ref(false);
const clearingSavedImport = ref(false);

const showPriceSuggestDialog = ref(false);
const priceSuggestRow = ref(null);
const priceSuggestCategory = ref('lab');
const priceSuggestQuery = ref('');
const priceSuggestQty = ref(1);
const loadingPriceSuggest = ref(false);
const priceSuggestResults = ref([]);
const priceSuggestSelected = ref([]);
const addingFromSuggestion = ref(false);
const priceSuggestCols = [
  { name: 'item_name', label: 'Price list item', field: 'item_name', align: 'left' },
  { name: 'item_code', label: 'Code', field: 'item_code', align: 'left' },
  { name: 'service_type', label: 'Service type', field: 'service_type', align: 'left' },
  { name: 'unit_price', label: 'Copay', field: 'unit_price', align: 'right' },
  { name: 'score', label: 'Match', field: 'score', align: 'right' },
];
const addMissingCategoryOptions = [
  { label: 'Lab', value: 'lab' },
  { label: 'Scan', value: 'scan' },
  { label: 'X-ray', value: 'xray' },
  { label: 'Drug', value: 'drug' },
  { label: 'Day surgery', value: 'day_surgery' },
  { label: 'Major surgery', value: 'major_surgery' },
  { label: 'Dressing / Treatment room', value: 'dressing' },
  { label: 'Oxygen', value: 'oxygen' },
  { label: 'Inpatient', value: 'inpatient' },
];

const canSubmitAddMissing = computed(() => {
  if (!selectedVisit.value || selectedVisit.value.status !== 'open') return false;
  const qty = Number(addMissingQty.value);
  // If item code is provided, unit price is required; otherwise we will try price-list matching.
  const code = String(addMissingCode.value || '').trim();
  const price = Number(addMissingUnitPrice.value);
  const priceOk = !code || (Number.isFinite(price) && price >= 0);
  return String(addMissingCategory.value || '').trim() && priceOk
    && Number.isFinite(qty) && qty > 0
    && addMissingRow.value && String(addMissingRow.value.description || '').trim();
});

const reconcileGovCols = [
  { name: 'description', label: 'Service', field: 'description', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'actions', label: '', align: 'right' },
];
const reconcileBillCols = [
  { name: 'item_name', label: 'Item', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit', field: (r) => r.unit_price, align: 'right' },
  { name: 'receipt_number', label: 'Receipt', field: 'receipt_number', align: 'left' },
  { name: 'created_by_name', label: 'Added by', field: 'created_by_name', align: 'left' },
];
const reconcileMismatchCols = [
  { name: 'normalized', label: 'Matched service', field: 'normalized', align: 'left' },
  { name: 'government_quantity', label: 'Gov qty', field: 'government_quantity', align: 'right' },
  { name: 'billed_quantity', label: 'Billed qty', field: 'billed_quantity', align: 'right' },
];

const confirmingGovKey = ref(null);
const pendingGovCols = [
  { name: 'description', label: 'Service', field: 'description', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'actions', label: '', align: 'right' },
];

const pendingGovItems = computed(() => {
  const missing = reconcileResult.value?.missing_in_billing || [];
  return missing.map((x, idx) => ({
    key: `${idx}-${x.normalized || ''}-${x.description || ''}`,
    description: x.description,
    quantity: x.quantity,
  }));
});

const showAddInpatientFeeDialog = ref(false);
const inpatientFeeAmount = ref(null);
const inpatientFeeDescription = ref('');
const addingInpatientFee = ref(false);

const showEditInpatientFeeDialog = ref(false);
const editInpatientFeeRow = ref(null);
const editInpatientAmount = ref(null);
const editInpatientDescription = ref('');
const editingItemId = ref(null);
const deletingItemId = ref(null);
const cancellingItemId = ref(null);

const canMarkPaid = computed(() => authStore.canAccess(['Billing', 'Admin']));
/** Can add services (lab, scan, xray, drugs) and cancel items. Doctor and PA can add/cancel; only Billing/Admin can mark paid. */
const canAddItems = computed(() => authStore.canAccess(['Billing', 'Doctor', 'PA', 'Admin']));
const canAdmin = computed(() => authStore.canAccess(['Admin']));
const isSuperAdmin = computed(() => Boolean(authStore.user?.is_super_admin));
const canEditDeleteInpatient = computed(() => authStore.canAccess(['Admin']));
const canReopenVisitRole = computed(() => authStore.canAccess(['Admin']));
const canApproveUndertakingRole = computed(() => authStore.canAccess(['Management', 'Admin']));

  const paymentMethodOptions = [
    { label: 'Cash', value: 'cash' },
    { label: 'Card', value: 'card' },
    { label: 'Mobile money', value: 'mobile_money' },
    { label: 'Bank transfer', value: 'bank_transfer' },
  ];

const closingVisit = ref(false);
const reopeningVisit = ref(false);
const showReopenDialog = ref(false);
const reopenReason = ref('');
const undertakingRequesting = ref(false);
const undertakingApproving = ref(false);
const undertakingUpdating = ref(false);
const undertakingCancelling = ref(false);
const showRequestUndertakingDialog = ref(false);
const requestUndertakingDeposit = ref(null);
const requestUndertakingDepositReceipt = ref('');
const showEditUndertakingDialog = ref(false);
const editUndertakingDeposit = ref(null);
const editUndertakingDepositReceipt = ref('');
const showApproveUndertakingDialog = ref(false);
const showUnapproveUndertakingDialog = ref(false);
const unapproveReason = ref('');
const undertakingUnapproving = ref(false);

const isInpatientFeeValid = computed(() => {
  const n = Number(inpatientFeeAmount.value);
  return Number.isFinite(n) && n >= 0;
});

const isEditInpatientFeeValid = computed(() => {
  const n = Number(editInpatientAmount.value);
  return Number.isFinite(n) && n >= 0;
});

function rowAmount(row) {
  return (Number(row.unit_price) || 0) * (Number(row.quantity) || 1);
}

function isPaidRow(row) {
  // Amount of 0 means already paid (or free), treat as paid.
  if (rowAmount(row) === 0) return true;
  return Boolean(row.receipt_number);
}

function isCancelledRow(row) {
  return Boolean(row.cancelled);
}

function isInpatientItem(row) {
  return (row.category || '').toLowerCase() === 'inpatient';
}

function paidLabel(row) {
  if (rowAmount(row) === 0) return 'Paid (0.00)';
  return row.receipt_number ? `Receipt ${row.receipt_number}` : 'Paid';
}

function normalizeCategory(cat) {
  const c = String(cat || '').trim().toLowerCase();
  if (!c) return 'other';
  if (c.includes('drug')) return 'drugs';
  if (c.includes('investigation') || c.includes('lab')) return 'investigations';
  if (c.includes('scan')) return 'scans';
  if (c.includes('xray') || c.includes('x-ray') || c.includes('x ray')) return 'xrays';
  // Group day surgery and major surgery as one "Surgeries" section
  if (c === 'day_surgery' || c === 'major_surgery') return 'surgeries';
  if (c === 'dressing' || c === 'dressing_room') return 'dressing';
  if (c === 'oxygen') return 'oxygen';
  if (c === 'inpatient') return 'inpatient';
  return c;
}

function categoryTitle(key) {
  if (key === 'drugs') return 'Drugs';
  if (key === 'investigations') return 'Investigations / Lab';
  if (key === 'scans') return 'Scans';
  if (key === 'xrays') return 'X-rays';
  if (key === 'surgeries') return 'Surgeries';
  if (key === 'dressing') return 'Dressing / Treatment room';
  if (key === 'oxygen') return 'Oxygen';
  if (key === 'inpatient') return 'Inpatient';
  if (key === 'other') return 'Other';
  return key.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

const groupedBillItems = computed(() => {
  const map = new Map();
  for (const item of billItems.value || []) {
    const key = normalizeCategory(item.category);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(item);
  }
  const keys = Array.from(map.keys());
  const preferredOrder = ['drugs', 'investigations', 'scans', 'xrays', 'surgeries', 'dressing', 'oxygen', 'inpatient', 'other'];
  keys.sort((a, b) => {
    const ai = preferredOrder.indexOf(a);
    const bi = preferredOrder.indexOf(b);
    if (ai !== -1 || bi !== -1) return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    return a.localeCompare(b);
  });
  return keys.map((key) => {
    const items = map.get(key) || [];
    // IMPORTANT: keep cancelled items visible, but exclude them from totals.
    const total = items.reduce((sum, i) => (isCancelledRow(i) ? sum : sum + rowAmount(i)), 0);
    const unpaidTotal = items
      .filter((i) => !isPaidRow(i) && !isCancelledRow(i))
      .reduce((sum, i) => sum + rowAmount(i), 0);
    return { key, title: categoryTitle(key), items, total, unpaidTotal };
  });
});

const selectedRowsByCategory = ref({});
const selectedIdsByCategory = computed(() => {
  const out = {};
  for (const group of groupedBillItems.value) {
    out[group.key] = (selectedRowsByCategory.value[group.key] || []).map((r) => r.id);
  }
  return out;
});

const itemsToPay = computed(() => {
  const ids = new Set(payDialogItemIds.value || []);
  const selected = (billItems.value || []).filter((r) => ids.has(r.id) && !isPaidRow(r) && !isCancelledRow(r));
  return selected;
});

const payDialogTitle = computed(() => {
  if (payDialogCategoryKey.value) return categoryTitle(payDialogCategoryKey.value);
  return 'items';
});

const hasAnyReceiptInDialog = computed(() => {
  const defaultReceipt = String(payDialogDefaultReceipt.value || '').trim();
  if (defaultReceipt) return true;
  return itemsToPay.value.some((item) => String(itemReceipts.value[item.id] || '').trim());
});

const billTotal = computed(() => {
  return billItems.value.reduce((sum, i) => {
    if (isCancelledRow(i)) return sum;
    return sum + (Number(i.unit_price) || 0) * (Number(i.quantity) || 1);
  }, 0);
});

const undertakingDepositAmount = computed(() => {
  const v = selectedVisit.value?.undertaking_deposit_amount;
  return v != null && Number(v) >= 0 ? Number(v) : null;
});

const paidAmount = computed(() => {
  // Sum amounts for items already paid (receipt set OR amount 0 treated as paid but contributes 0).
  return (billItems.value || []).reduce((sum, row) => {
    if (isCancelledRow(row)) return sum;
    if (!isPaidRow(row)) return sum;
    return sum + rowAmount(row);
  }, 0);
});

const pendingBalance = computed(() => {
  const total = billTotal.value;
  const deposit = undertakingDepositAmount.value || 0;
  const paid = paidAmount.value || 0;
  return Math.max(0, total - paid - deposit);
});

const allBillItemsPaid = computed(() => {
  const items = billItems.value || [];
  if (items.length === 0) return true;
  return items.filter((row) => !isCancelledRow(row)).every((row) => isPaidRow(row));
});

const undertakingApproved = computed(() => (selectedVisit.value?.undertaking_status || '').toLowerCase() === 'approved');
const undertakingPending = computed(() => (selectedVisit.value?.undertaking_status || '').toLowerCase() === 'pending');

const canCloseVisit = computed(() => {
  if (!selectedVisit.value || selectedVisit.value.status !== 'open' || !canMarkPaid.value) return false;
  return allBillItemsPaid.value || undertakingApproved.value;
});

/** Show "Close visit" beside pending balance when balance is 0 (billing officer can close). */
const showCloseVisitByBalance = computed(() => {
  if (!selectedVisit.value || selectedVisit.value.status !== 'open' || !canMarkPaid.value) return false;
  return Number(pendingBalance.value) <= 0;
});

const canReopenVisit = computed(() => {
  return selectedVisit.value?.status === 'closed' && canReopenVisitRole.value;
});

const canRequestUndertaking = computed(() => {
  if (!selectedVisit.value || selectedVisit.value.status !== 'open' || !canMarkPaid.value) return false;
  const s = (selectedVisit.value.undertaking_status || '').toLowerCase();
  return s !== 'pending' && s !== 'approved';
});

const canApproveUndertaking = computed(() => {
  return selectedVisit.value?.status === 'open' && undertakingPending.value && canApproveUndertakingRole.value;
});

const canEditUndertaking = computed(() => {
  if (!selectedVisit.value || !undertakingPending.value) return false;
  const uid = authStore.user?.id;
  const requesterId = selectedVisit.value.undertaking_requested_by_id;
  return uid === requesterId || canMarkPaid.value;
});

const canCancelUndertaking = computed(() => {
  if (!selectedVisit.value || !undertakingPending.value) return false;
  const uid = authStore.user?.id;
  const requesterId = selectedVisit.value.undertaking_requested_by_id;
  return uid === requesterId || canReopenVisitRole.value;
});

const canUnapproveUndertaking = computed(() => {
  return (selectedVisit.value?.undertaking_status || '').toLowerCase() === 'approved' && canReopenVisitRole.value;
});

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function formatOxygenPeriod(row) {
  if (!row?.start_time || !row?.end_time) return '';
  const start = new Date(row.start_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  const end = new Date(row.end_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  const qty = Number(row.quantity);
  const hours = Number.isNaN(qty) ? '' : (qty === 1 ? '1 hour' : `${qty.toFixed(1)} hours`);
  return hours ? `Start ${start} → End ${end} · ${hours}` : `Start ${start} → End ${end}`;
}

async function loadVisits() {
  loadingVisits.value = true;
  searched.value = true;
  try {
    const params = {};
    if (filters.card_number) params.card_number = filters.card_number;
    if (filters.visit_number) params.visit_number = filters.visit_number;
    if (filters.status) params.status_filter = filters.status;
    const res = await companionVisitsAPI.list(params);
    visits.value = res.data || [];
  } catch (e) {
    visits.value = [];
  } finally {
    loadingVisits.value = false;
  }
}

async function selectVisit(visit) {
  selectedVisit.value = visit;
  billItems.value = [];
  selectedRowsByCategory.value = {};
  reconcileResult.value = null;
  reconcileFile.value = null;
  ipdReconcileResult.value = null;
  ipdReconcileFile.value = null;
  loadingItems.value = true;
  try {
    const [itemsRes, visitRes] = await Promise.all([
      companionVisitsAPI.getItems(visit.id),
      companionVisitsAPI.get(visit.id),
    ]);
    billItems.value = itemsRes.data || [];
    selectedVisit.value = visitRes.data || visit;
    try {
      const recon = await companionVisitsAPI.reconcileOpdGovernmentSaved(visit.id);
      reconcileResult.value = recon.data || null;
    } catch {}
    try {
      const ipdRecon = await companionVisitsAPI.reconcileIpdGovernmentSaved(visit.id);
      ipdReconcileResult.value = ipdRecon.data || null;
    } catch {}
  } catch (e) {
    billItems.value = [];
  } finally {
    loadingItems.value = false;
  }
}

function clearSelection() {
  selectedVisit.value = null;
  billItems.value = [];
}

async function confirmCloseVisit() {
  if (!selectedVisit.value) return;
  $q.dialog({
    title: 'Close visit',
    message: 'No further services can be added after closing. Close this visit?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    closingVisit.value = true;
    try {
      const res = await companionVisitsAPI.close(selectedVisit.value.id);
      selectedVisit.value = res.data;
      $q.notify({ type: 'positive', message: 'Visit closed', position: 'top' });
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to close visit',
        position: 'top',
      });
    } finally {
      closingVisit.value = false;
    }
  });
}

async function confirmReopenVisit() {
  if (!selectedVisit.value || !reopenReason.value.trim()) return;
  reopeningVisit.value = true;
  try {
    const res = await companionVisitsAPI.reopen(selectedVisit.value.id, { reason: reopenReason.value.trim() });
    selectedVisit.value = res.data;
    showReopenDialog.value = false;
    reopenReason.value = '';
    await selectVisit(res.data);
    $q.notify({ type: 'positive', message: 'Visit reopened', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to reopen visit',
      position: 'top',
    });
  } finally {
    reopeningVisit.value = false;
  }
}

async function confirmRequestUndertaking() {
  if (!selectedVisit.value) return;
  const deposit = requestUndertakingDeposit.value != null && Number(requestUndertakingDeposit.value) >= 0
    ? Number(requestUndertakingDeposit.value)
    : null;
  const receipt = String(requestUndertakingDepositReceipt.value || '').trim();
  undertakingRequesting.value = true;
  try {
    const res = await companionVisitsAPI.requestUndertaking(selectedVisit.value.id, {
      deposit_amount: deposit != null ? deposit : undefined,
      deposit_receipt_number: receipt || undefined,
    });
    selectedVisit.value = res.data;
    showRequestUndertakingDialog.value = false;
    requestUndertakingDeposit.value = null;
    requestUndertakingDepositReceipt.value = '';
    $q.notify({ type: 'positive', message: 'Undertaking requested', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to request undertaking',
      position: 'top',
    });
  } finally {
    undertakingRequesting.value = false;
  }
}

function openEditUndertakingDialog() {
  const v = selectedVisit.value?.undertaking_deposit_amount;
  editUndertakingDeposit.value = v != null && Number(v) >= 0 ? Number(v) : null;
  editUndertakingDepositReceipt.value = String(selectedVisit.value?.undertaking_deposit_receipt_number || '');
  showEditUndertakingDialog.value = true;
}

async function confirmUpdateUndertaking() {
  if (!selectedVisit.value) return;
  const deposit = editUndertakingDeposit.value != null && Number(editUndertakingDeposit.value) >= 0
    ? Number(editUndertakingDeposit.value)
    : null;
  const receipt = String(editUndertakingDepositReceipt.value || '').trim();
  undertakingUpdating.value = true;
  try {
    const res = await companionVisitsAPI.updateUndertaking(selectedVisit.value.id, {
      deposit_amount: deposit,
      deposit_receipt_number: receipt,
    });
    selectedVisit.value = res.data;
    showEditUndertakingDialog.value = false;
    $q.notify({ type: 'positive', message: 'Undertaking updated', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to update undertaking',
      position: 'top',
    });
  } finally {
    undertakingUpdating.value = false;
  }
}

async function doCancelUndertaking() {
  if (!selectedVisit.value) return;
  undertakingCancelling.value = true;
  try {
    const res = await companionVisitsAPI.cancelUndertaking(selectedVisit.value.id);
    selectedVisit.value = res.data;
    showEditUndertakingDialog.value = false;
    $q.notify({ type: 'positive', message: 'Undertaking cancelled', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to cancel undertaking',
      position: 'top',
    });
  } finally {
    undertakingCancelling.value = false;
  }
}

function confirmCancelUndertakingFromCard() {
  $q.dialog({
    title: 'Cancel undertaking',
    message: 'Cancel this undertaking? Use this when the client has paid in full. The visit will then need all items paid or a new undertaking to be closed.',
    cancel: true,
    persistent: true,
  }).onOk(doCancelUndertaking);
}

function confirmCancelUndertaking() {
  $q.dialog({
    title: 'Cancel undertaking',
    message: 'Cancel this undertaking? Use this when the client has paid in full.',
    cancel: true,
    persistent: true,
  }).onOk(doCancelUndertaking);
}

async function confirmApproveUndertaking() {
  if (!selectedVisit.value) return;
  showApproveUndertakingDialog.value = false;
  undertakingApproving.value = true;
  try {
    const res = await companionVisitsAPI.approveUndertaking(selectedVisit.value.id);
    selectedVisit.value = res.data;
    $q.notify({ type: 'positive', message: 'Undertaking approved', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to approve undertaking',
      position: 'top',
    });
  } finally {
    undertakingApproving.value = false;
  }
}

async function confirmUnapproveUndertaking() {
  if (!selectedVisit.value || !unapproveReason.value.trim()) return;
  undertakingUnapproving.value = true;
  try {
    const res = await companionVisitsAPI.unapproveUndertaking(selectedVisit.value.id, { reason: unapproveReason.value.trim() });
    selectedVisit.value = res.data;
    showUnapproveUndertakingDialog.value = false;
    unapproveReason.value = '';
    $q.notify({ type: 'positive', message: 'Undertaking unapproved (back to pending)', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to unapprove undertaking',
      position: 'top',
    });
  } finally {
    undertakingUnapproving.value = false;
  }
}

function openAddInpatientFeeDialog() {
  inpatientFeeAmount.value = null;
  inpatientFeeDescription.value = '';
  showAddInpatientFeeDialog.value = true;
}

async function confirmAddInpatientFee() {
  if (!selectedVisit.value || selectedVisit.value.status !== 'open') return;
  const amount = Number(inpatientFeeAmount.value);
  if (!Number.isFinite(amount) || amount < 0) return;
  const name = String(inpatientFeeDescription.value || '').trim() || 'Inpatient Fee';
  addingInpatientFee.value = true;
  try {
    await companionVisitsAPI.addItem(selectedVisit.value.id, {
      item_code: 'INPATIENT_FEE',
      item_name: name,
      category: 'inpatient',
      unit_price: amount,
      quantity: 1,
    });
    $q.notify({ type: 'positive', message: 'Inpatient fee added to bill', position: 'top' });
    showAddInpatientFeeDialog.value = false;
    await selectVisit(selectedVisit.value);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to add inpatient fee',
      position: 'top',
    });
  } finally {
    addingInpatientFee.value = false;
  }
}

function openEditInpatientFee(row) {
  editInpatientFeeRow.value = row;
  editInpatientAmount.value = row.unit_price;
  editInpatientDescription.value = row.item_name || '';
  showEditInpatientFeeDialog.value = true;
}

async function confirmEditInpatientFee() {
  const row = editInpatientFeeRow.value;
  if (!selectedVisit.value || !row || selectedVisit.value.status !== 'open') return;
  const amount = Number(editInpatientAmount.value);
  if (!Number.isFinite(amount) || amount < 0) return;
  const name = String(editInpatientDescription.value || '').trim() || 'Inpatient Fee';
  editingItemId.value = row.id;
  try {
    await companionVisitsAPI.updateItem(selectedVisit.value.id, row.id, {
      unit_price: amount,
      item_name: name,
    });
    $q.notify({ type: 'positive', message: 'Inpatient fee updated', position: 'top' });
    showEditInpatientFeeDialog.value = false;
    editInpatientFeeRow.value = null;
    await selectVisit(selectedVisit.value);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to update inpatient fee',
      position: 'top',
    });
  } finally {
    editingItemId.value = null;
  }
}

function deleteInpatientFee(row) {
  $q.dialog({
    title: 'Remove inpatient fee',
    message: `Remove "${row.item_name}" (GH¢ ${formatPrice(rowAmount(row))}) from the bill?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    if (!selectedVisit.value) return;
    deletingItemId.value = row.id;
    try {
      await companionVisitsAPI.deleteItem(selectedVisit.value.id, row.id);
      $q.notify({ type: 'positive', message: 'Inpatient fee removed', position: 'top' });
      await selectVisit(selectedVisit.value);
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to remove item',
        position: 'top',
      });
    } finally {
      deletingItemId.value = null;
    }
  });
}

function openPayDialogForCategory(categoryKey, itemIdsOverride = null) {
  const group = groupedBillItems.value.find((g) => g.key === categoryKey);
  if (!group) return;
  payDialogCategoryKey.value = categoryKey;
  const ids = Array.isArray(itemIdsOverride) ? itemIdsOverride : (selectedIdsByCategory.value[categoryKey] || []);
  payDialogItemIds.value = ids;

  payDialogDefaultReceipt.value = '';
  const byId = {};
  (billItems.value || []).filter((i) => ids.includes(i.id)).forEach((item) => { byId[item.id] = ''; });
  itemReceipts.value = byId;
  showMarkPaidDialog.value = true;
}

async function confirmMarkPaid() {
  if (!selectedVisit.value || itemsToPay.value.length === 0) return;
  const defaultReceipt = String(payDialogDefaultReceipt.value || '').trim();
  const toMark = itemsToPay.value.filter((item) => {
    const overrideReceipt = String(itemReceipts.value[item.id] || '').trim();
    return Boolean(overrideReceipt || defaultReceipt);
  });
  if (toMark.length === 0) return;
  markingPaid.value = true;
  try {
    const paymentMethod = payDialogPaymentMethod.value || null;
    for (const item of toMark) {
      const receipt = String(itemReceipts.value[item.id] || '').trim() || defaultReceipt;
      if (!receipt) continue;
      await companionVisitsAPI.markItemsPaid(selectedVisit.value.id, {
        receipt_number: receipt,
        item_ids: [item.id],
        payment_method: paymentMethod,
      });
    }
    $q.notify({ type: 'positive', message: `${toMark.length} item(s) marked as paid`, position: 'top' });
    showMarkPaidDialog.value = false;
    await selectVisit(selectedVisit.value);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to mark as paid',
      position: 'top',
    });
  } finally {
    markingPaid.value = false;
  }
}

function paySingle(row) {
  const catKey = normalizeCategory(row.category);
  openPayDialogForCategory(catKey, [row.id]);
}

function refundItem(row) {
  $q.dialog({
    title: 'Refund / Return',
    message: `Reverse payment for "${row.item_name}"? Receipt ${row.receipt_number} will be cleared and the item will show as Unpaid.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    if (!selectedVisit.value) return;
    refundingItemId.value = row.id;
    try {
      await companionVisitsAPI.refundItems(selectedVisit.value.id, [row.id]);
      $q.notify({ type: 'positive', message: 'Payment reversed', position: 'top' });
      await selectVisit(selectedVisit.value);
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Refund failed',
        position: 'top',
      });
    } finally {
      refundingItemId.value = null;
    }
  });
}

async function runReconcile() {
  if (!selectedVisit.value) return;
  reconciling.value = true;
  reconcileResult.value = null;
  try {
    // If a file is selected, upload it and save snapshot in backend.
    // Otherwise, reuse the last saved snapshot for this visit.
    const res = reconcileFile.value
      ? await companionVisitsAPI.reconcileOpdGovernment(selectedVisit.value.id, reconcileFile.value)
      : await companionVisitsAPI.reconcileOpdGovernmentSaved(selectedVisit.value.id);
    reconcileResult.value = res.data || null;
    $q.notify({ type: 'positive', message: 'Reconciliation complete', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Reconciliation failed',
      position: 'top',
    });
  } finally {
    reconciling.value = false;
  }
}

async function runIpdReconcile() {
  if (!selectedVisit.value) return;
  ipdReconciling.value = true;
  ipdReconcileResult.value = null;
  try {
    const res = ipdReconcileFile.value
      ? await companionVisitsAPI.reconcileIpdGovernment(selectedVisit.value.id, ipdReconcileFile.value)
      : await companionVisitsAPI.reconcileIpdGovernmentSaved(selectedVisit.value.id);
    ipdReconcileResult.value = res.data || null;
    $q.notify({ type: 'positive', message: 'IPD reconciliation complete', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'IPD reconciliation failed',
      position: 'top',
    });
  } finally {
    ipdReconciling.value = false;
  }
}

function openAddMissing(row) {
  if (!selectedVisit.value) return;
  addMissingSource.value = 'opd';
  addMissingRow.value = row;
  addMissingCategory.value = 'lab';
  addMissingCode.value = '';
  addMissingUnitPrice.value = null;
  addMissingQty.value = Number(row?.quantity) || 1;
  showAddMissingDialog.value = true;
}

function openAddMissingFromIpd(row) {
  if (!selectedVisit.value) return;
  addMissingSource.value = 'ipd';
  addMissingRow.value = row;
  addMissingCategory.value = 'lab';
  addMissingCode.value = '';
  addMissingUnitPrice.value = null;
  addMissingQty.value = Number(row?.quantity) || 1;
  showAddMissingDialog.value = true;
}

function openPriceSuggestFromIpd(row) {
  if (!selectedVisit.value) return;
  addMissingSource.value = 'ipd';
  openPriceSuggest(row);
  priceSuggestCategory.value = ipdBulkAddCategory.value || 'lab';
}

function openPriceSuggest(row) {
  if (!selectedVisit.value) return;
  priceSuggestRow.value = row;
  priceSuggestCategory.value = bulkAddCategory.value || 'lab';
  priceSuggestQty.value = Number(row?.quantity) || 1;
  priceSuggestQuery.value = String(row?.description || '');
  priceSuggestResults.value = [];
  priceSuggestSelected.value = [];
  showPriceSuggestDialog.value = true;
  runPriceSuggest();
}

async function runPriceSuggest() {
  if (!selectedVisit.value) return;
  const q = String(priceSuggestQuery.value || '').trim();
  if (!q) return;
  loadingPriceSuggest.value = true;
  priceSuggestResults.value = [];
  priceSuggestSelected.value = [];
  try {
    const res = await companionVisitsAPI.getPriceSuggestions(selectedVisit.value.id, priceSuggestCategory.value, q, 15);
    priceSuggestResults.value = res.data?.suggestions || [];
    if (priceSuggestResults.value.length === 0) {
      $q.notify({ type: 'warning', message: 'No similar price list items found', position: 'top' });
    }
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Price suggestion search failed',
      position: 'top',
    });
  } finally {
    loadingPriceSuggest.value = false;
  }
}

async function confirmAddFromSuggestion() {
  if (!selectedVisit.value || priceSuggestSelected.value.length === 0 || !priceSuggestRow.value) return;
  const pick = priceSuggestSelected.value[0];
  addingFromSuggestion.value = true;
  try {
    await companionVisitsAPI.addItem(selectedVisit.value.id, {
      item_code: pick.item_code,
      item_name: pick.item_name,
      category: priceSuggestCategory.value,
      unit_price: Number(pick.unit_price) || 0,
      quantity: Number(priceSuggestQty.value) || 1,
    });
    $q.notify({ type: 'positive', message: 'Added to bill', position: 'top' });
    showPriceSuggestDialog.value = false;
    await selectVisit(selectedVisit.value);
    if (addMissingSource.value === 'ipd') await runIpdReconcile();
    else if (reconcileFile.value) await runReconcile();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to add item',
      position: 'top',
    });
  } finally {
    addingFromSuggestion.value = false;
  }
}

async function confirmAddMissing() {
  if (!canSubmitAddMissing.value || !selectedVisit.value || !addMissingRow.value) return;
  addingMissing.value = true;
  try {
    // Prefer price list auto-match (same logic as bulk add) when code is not provided.
    const code = String(addMissingCode.value || '').trim();
    if (!code) {
      const res = await companionVisitsAPI.addMissingFromOpdExport(selectedVisit.value.id, addMissingCategory.value, [
        { description: String(addMissingRow.value.description || '').trim(), quantity: Number(addMissingQty.value) || 1 },
      ]);
      const added = res.data?.added || [];
      const failed = res.data?.failed || [];
      if (added.length) {
        $q.notify({ type: 'positive', message: 'Added to bill (price list)', position: 'top' });
      } else {
        $q.notify({ type: 'warning', message: failed[0]?.reason || 'Could not match in price list', position: 'top' });
        return;
      }
    } else {
      // If Billing knows the code, allow manual add with explicit price.
      await companionVisitsAPI.addItem(selectedVisit.value.id, {
        item_code: code,
        item_name: String(addMissingRow.value.description || '').trim(),
        category: addMissingCategory.value,
        unit_price: Number(addMissingUnitPrice.value),
        quantity: Number(addMissingQty.value),
      });
      $q.notify({ type: 'positive', message: 'Added to bill', position: 'top' });
    }
    showAddMissingDialog.value = false;
    await selectVisit(selectedVisit.value);
    if (addMissingSource.value === 'ipd') await runIpdReconcile();
    else if (reconcileFile.value) await runReconcile();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to add item',
      position: 'top',
    });
  } finally {
    addingMissing.value = false;
  }
}

async function addSelectedMissingFromPriceList() {
  if (!selectedVisit.value || missingSelectedRows.value.length === 0) return;
  bulkAddingMissing.value = true;
  try {
    const lines = missingSelectedRows.value.map((r) => ({
      description: r.description,
      quantity: Number(r.quantity) || 1,
    }));
    const res = await companionVisitsAPI.addMissingFromOpdExport(selectedVisit.value.id, bulkAddCategory.value, lines);
    const added = res.data?.added || [];
    const failed = res.data?.failed || [];
    if (added.length) {
      $q.notify({ type: 'positive', message: `Added ${added.length} item(s)`, position: 'top' });
    }
    if (failed.length) {
      $q.notify({ type: 'warning', message: `${failed.length} item(s) could not be matched in price list`, position: 'top' });
    }
    missingSelectedRows.value = [];
    await selectVisit(selectedVisit.value);
    if (addMissingSource.value === 'ipd') await runIpdReconcile();
    else if (reconcileFile.value) await runReconcile();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Bulk add failed',
      position: 'top',
    });
  } finally {
    bulkAddingMissing.value = false;
  }
}

async function addSelectedMissingFromIpd() {
  if (!selectedVisit.value || ipdMissingSelectedRows.value.length === 0) return;
  ipdBulkAddingMissing.value = true;
  try {
    const lines = ipdMissingSelectedRows.value.map((r) => ({
      description: r.description,
      quantity: Number(r.quantity) || 1,
    }));
    const res = await companionVisitsAPI.addMissingFromOpdExport(selectedVisit.value.id, ipdBulkAddCategory.value, lines);
    const added = res.data?.added || [];
    const failed = res.data?.failed || [];
    if (added.length) {
      $q.notify({ type: 'positive', message: `Added ${added.length} item(s)`, position: 'top' });
    }
    if (failed.length) {
      $q.notify({ type: 'warning', message: `${failed.length} item(s) could not be matched in price list`, position: 'top' });
    }
    ipdMissingSelectedRows.value = [];
    await selectVisit(selectedVisit.value);
    await runIpdReconcile();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Bulk add failed',
      position: 'top',
    });
  } finally {
    ipdBulkAddingMissing.value = false;
  }
}

function deleteBillItem(row) {
  $q.dialog({
    title: 'Delete item',
    message: `Delete "${row.item_name}" from this bill? This cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    if (!selectedVisit.value) return;
    deletingItemId.value = row.id;
    try {
      await companionVisitsAPI.deleteItem(selectedVisit.value.id, row.id);
      $q.notify({ type: 'positive', message: 'Item deleted', position: 'top' });
      await selectVisit(selectedVisit.value);
      if (reconcileFile.value) await runReconcile();
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to delete item',
        position: 'top',
      });
    } finally {
      deletingItemId.value = null;
    }
  });
}

function cancelBillItem(row) {
  $q.dialog({
    title: 'Cancel service',
    message: `Cancel "${row.item_name}"? It will be struck through and excluded from billing.`,
    prompt: {
      model: '',
      type: 'text',
      label: 'Reason for cancellation',
      isValid: (val) => String(val || '').trim().length >= 3,
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    if (!selectedVisit.value) return;
    cancellingItemId.value = row.id;
    try {
      const res = await companionVisitsAPI.cancelItem(selectedVisit.value.id, row.id, String(reason || '').trim());
      if (res.data?.hard_deleted) {
        $q.notify({ type: 'positive', message: 'Item deleted (superadmin)', position: 'top' });
      } else {
        $q.notify({ type: 'positive', message: 'Item cancelled', position: 'top' });
      }
      await selectVisit(selectedVisit.value);
      if (reconcileFile.value) await runReconcile();
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to cancel item',
        position: 'top',
      });
    } finally {
      cancellingItemId.value = null;
    }
  });
}

function confirmClearSavedImport() {
  if (!selectedVisit.value) return;
  $q.dialog({
    title: 'Clear saved government import',
    message: 'This will remove the saved OPD export snapshot for this visit. You will need to upload the file again to run checks. Continue?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    clearingSavedImport.value = true;
    try {
      await companionVisitsAPI.clearSavedOpdGovernmentExport(selectedVisit.value.id);
      reconcileResult.value = null;
      reconcileFile.value = null;
      missingSelectedRows.value = [];
      $q.notify({ type: 'positive', message: 'Saved import cleared', position: 'top' });
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to clear saved import',
        position: 'top',
      });
    } finally {
      clearingSavedImport.value = false;
    }
  });
}

function confirmClearSavedIpdImport() {
  if (!selectedVisit.value) return;
  $q.dialog({
    title: 'Clear saved IPD import',
    message: 'This will remove the saved IPD invoice snapshot for this visit. You will need to upload the file again to run checks. Continue?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    ipdClearingSaved.value = true;
    try {
      await companionVisitsAPI.clearSavedIpdGovernmentExport(selectedVisit.value.id);
      ipdReconcileResult.value = null;
      ipdReconcileFile.value = null;
      ipdMissingSelectedRows.value = [];
      $q.notify({ type: 'positive', message: 'Saved IPD import cleared', position: 'top' });
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to clear saved import',
        position: 'top',
      });
    } finally {
      ipdClearingSaved.value = false;
    }
  });
}

async function confirmGovItem(row) {
  if (!selectedVisit.value || !row?.description) return;
  confirmingGovKey.value = row.key;
  try {
    const res = await companionVisitsAPI.confirmFromOpdExportLine(
      selectedVisit.value.id,
      String(row.description || '').trim(),
      Number(row.quantity) || 1
    );
    if (res.data?.matched) {
      $q.notify({ type: 'positive', message: 'Confirmed and added to bill', position: 'top' });
      await selectVisit(selectedVisit.value);
      if (reconcileFile.value) await runReconcile();
      else {
        // refresh reconcile from saved snapshot
        try {
          const recon = await companionVisitsAPI.reconcileOpdGovernmentSaved(selectedVisit.value.id);
          reconcileResult.value = recon.data || null;
        } catch {}
      }
    } else {
      $q.notify({ type: 'warning', message: res.data?.reason || 'Could not match in price list', position: 'top' });
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Confirm failed', position: 'top' });
  } finally {
    confirmingGovKey.value = null;
  }
}
</script>
