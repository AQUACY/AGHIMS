<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat dense icon="arrow_back" :to="backLink" />
      <div class="text-h5 text-weight-bold glass-text q-ml-sm">Add drugs (Pharmacy)</div>
    </div>

    <q-card v-if="visitClosed" class="glass-card q-mb-md" flat>
      <q-card-section>
        <q-banner class="bg-warning/20 text-warning rounded-borders">
          This visit is closed. You cannot add or remove drugs.
        </q-banner>
      </q-card-section>
    </q-card>

    <!-- Added to bill -->
    <q-card v-if="addedItems.length > 0" class="glass-card q-mb-lg" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">Added to client's bill</div>
        <q-list bordered class="rounded-borders">
          <q-item v-for="item in addedItems" :key="item.id" class="q-pa-md">
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ item.item_name }}</q-item-label>
              <q-item-label caption>{{ item.item_code }} · {{ item.quantity }} × GH¢ {{ formatPrice(item.unit_price) }} = GH¢ {{ formatPrice(item.unit_price * item.quantity) }}</q-item-label>
              <q-item-label v-if="item.created_at" caption class="text-grey-7 q-mt-xs">Service date & time: {{ formatDateTime(item.created_at) }}</q-item-label>
              <div v-if="item.receipt_number" class="receipt-badge q-mt-sm">
                <q-icon name="receipt" size="18px" class="q-mr-xs" />
                <span class="text-weight-medium">Receipt {{ item.receipt_number }}</span>
                <span v-if="item.paid_at" class="q-ml-sm text-caption">· Paid {{ formatDateTime(item.paid_at) }}</span>
              </div>
              <div v-else class="unpaid-badge q-mt-sm">
                <q-icon name="pending" size="18px" class="q-mr-xs" />
                <span>Not paid</span>
                <span class="text-caption q-ml-sm">— will be marked at central billing</span>
              </div>
            </q-item-section>
            <q-item-section side>
              <q-btn
                v-if="!visitClosed && !item.receipt_number"
                flat
                dense
                round
                icon="delete"
                color="negative"
                @click="removeItem(item)"
              >
                <q-tooltip>Remove from bill</q-tooltip>
              </q-btn>
              <q-tooltip v-else-if="item.receipt_number" content="Paid — cannot remove">
                <q-icon name="check_circle" color="positive" size="24px" />
              </q-tooltip>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <!-- Import from government PDF or Excel -->
    <q-card class="glass-card q-mb-lg" flat>
      <q-card-section>
        <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Import from government list</div>
        <div class="text-caption glass-text-muted q-mb-sm">Upload a drugs list from the government system. Use <strong>Excel</strong> (.xls or .xlsx) for best results; PDF is also supported. Only the <strong>Item description</strong> and <strong>Quantity</strong> columns are used.</div>
        <div class="row q-col-gutter-sm items-center q-mb-md">
          <q-file
            v-model="excelFile"
            accept=".xls,.xlsx"
            label="Choose Excel (.xls / .xlsx)"
            outlined
            dense
            clearable
            class="col-12 col-sm-5"
            :disable="visitClosed || parsingFile"
            @update:model-value="onExcelSelected"
          />
          <q-file
            v-model="pdfFile"
            accept=".pdf"
            label="Or PDF"
            outlined
            dense
            clearable
            class="col-12 col-sm-4"
            :disable="visitClosed || parsingFile"
            @update:model-value="onPdfSelected"
          />
          <q-btn
            v-if="parsedLines.length > 0"
            flat
            dense
            color="primary"
            label="Clear list"
            @click="clearParsed"
          />
        </div>
        <q-linear-progress v-if="parsingFile" indeterminate class="q-mb-md" />
        <q-table
          v-if="parsedLines.length > 0"
          :rows="parsedLines"
          :columns="parsedColumns"
          row-key="id"
          flat
          bordered
          dense
          class="q-mb-md"
          :rows-per-page-options="[10, 25, 50]"
        >
          <template v-slot:body-cell-match="props">
            <q-td :props="props">
              <template v-if="props.row.matched">
                <span class="text-weight-medium">{{ props.row.matched.service_name || props.row.matched.product_name }}</span>
                <div class="text-caption text-grey-7">{{ props.row.matched.medication_code || props.row.matched.item_code }}</div>
              </template>
              <span v-else class="text-negative">No match</span>
            </q-td>
          </template>
          <template v-slot:body-cell-unit_price="props">
            <q-td :props="props">
              <template v-if="props.row.matched">
                GH¢ {{ formatPrice(copaymentPrice(props.row.matched)) }}
              </template>
              <span v-else>—</span>
            </q-td>
          </template>
          <template v-slot:body-cell-amount="props">
            <q-td :props="props">
              <template v-if="props.row.matched">
                GH¢ {{ formatPrice((copaymentPrice(props.row.matched)) * props.row.quantity) }}
              </template>
              <span v-else>—</span>
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!visitClosed && props.row.matched"
                flat
                dense
                size="sm"
                label="Add"
                color="primary"
                @click="addParsedRow(props.row)"
              />
            </q-td>
          </template>
        </q-table>
        <q-btn
          v-if="parsedLines.length > 0 && hasAnyMatched && !visitClosed"
          label="Add all matched to bill"
          color="primary"
          :loading="addingAll"
          @click="addAllMatched"
        />
      </q-card-section>
    </q-card>

    <!-- Search and add (manual) -->
    <q-card class="glass-card q-mb-lg" flat>
      <q-card-section>
        <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Search and add drug</div>
        <div class="text-caption glass-text-muted q-mb-sm">Type to search the price list, then add with quantity.</div>
        <q-input
          v-model="searchText"
          filled
          dense
          placeholder="Drug name or code..."
          class="q-mb-sm"
          clearable
        />
        <q-list v-if="searchText.trim() && filteredProducts.length > 0" bordered class="rounded-borders" style="max-height: 280px; overflow-y: auto;">
          <q-item
            v-for="p in filteredProducts.slice(0, 20)"
            :key="p.id || p.medication_code"
            clickable
            v-ripple
            @click="openAddQuantityDialog(p)"
          >
            <q-item-section>
              <q-item-label>{{ p.service_name || p.product_name }}</q-item-label>
              <q-item-label caption>{{ p.medication_code || p.item_code }} · GH¢ {{ formatPrice(copaymentPrice(p)) }} per unit</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn flat dense size="sm" label="Add" class="glass-button" @click.stop="openAddQuantityDialog(p)" />
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else-if="searchText.trim() && !loadingProducts" class="text-caption text-grey-7">
          No matching drugs.
        </div>
      </q-card-section>
    </q-card>

    <q-dialog v-model="showQuantityDialog" persistent>
      <q-card style="min-width: 320px">
        <q-card-section>
          <div class="text-h6">Add to bill</div>
          <div class="text-body2 q-mt-sm">{{ quantityDialogProduct?.service_name || quantityDialogProduct?.product_name }}</div>
          <q-input
            v-model.number="quantityDialogQty"
            type="number"
            min="0.5"
            step="0.5"
            label="Quantity"
            filled
            dense
            class="q-mt-md"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="grey" v-close-popup />
          <q-btn flat label="Add" color="primary" :disable="!(quantityDialogQty > 0)" @click="confirmAddWithQuantity" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { companionVisitsAPI, priceListAPI } from '../../services/api';

const route = useRoute();
const $q = useQuasar();
const visitId = computed(() => route.params.id);
const backLink = computed(() => ({ name: 'CompanionVisitDetail', params: { id: visitId.value } }));

const visit = ref(null);
const visitClosed = computed(() => visit.value?.status === 'closed');
const addedItems = ref([]);
const products = ref([]);
const loadingProducts = ref(true);
const searchText = ref('');
const pdfFile = ref(null);
const excelFile = ref(null);
const parsingFile = ref(false);
const parsedLines = ref([]);
const addingAll = ref(false);
const showQuantityDialog = ref(false);
const quantityDialogProduct = ref(null);
const quantityDialogQty = ref(1);

const parsedColumns = [
  { name: 'drug_name', label: 'Drug name (from PDF)', field: 'drug_name', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'match', label: 'Matched product', align: 'left' },
  { name: 'unit_price', label: 'Unit price', align: 'right' },
  { name: 'amount', label: 'Amount', align: 'right' },
  { name: 'actions', label: '', align: 'center' },
];

const filteredProducts = computed(() => {
  const t = (searchText.value || '').trim().toLowerCase();
  if (!t) return [];
  return products.value.filter(
    (p) =>
      (p.service_name && p.service_name.toLowerCase().includes(t)) ||
      (p.product_name && p.product_name.toLowerCase().includes(t)) ||
      (p.medication_code && p.medication_code.toLowerCase().includes(t)) ||
      (p.item_code && p.item_code.toLowerCase().includes(t))
  );
});

const hasAnyMatched = computed(() => parsedLines.value.some((r) => r.matched));

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function copaymentPrice(p) {
  const co = p.nhia_claim_co_payment;
  if (co != null && co !== '' && !Number.isNaN(Number(co))) return Number(co);
  return Number(p.base_rate) || 0;
}

function normalize(s) {
  return (s || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

// Government: "Paracetamol Tablet 500mg", "Calamine Lotion"
// HMS: "Paracetamol (500 mg) (PARACETA1 | Paracetamol) (Tablet)", "Calamine (0.15) (CALAMILO1 | Calamine) (Lotion)"
// Extract base drug name, form (tablet/lotion), and strength number for matching.
function parseGovernmentDrugName(govName) {
  const n = normalize(govName);
  if (!n) return { base: '', form: '', strengthNum: '' };
  const forms = ['tablet', 'tablets', 'lotions', 'lotion', 'capsule', 'capsules', 'syrup', 'injection', 'cream', 'gel', 'drops', 'suppository', 'suspension', 'solution'];
  const strengthMatch = n.match(/(\d+(?:\.\d+)?)\s*(?:mg|g|ml|%|mg\/ml)?/);
  const strengthNum = strengthMatch ? strengthMatch[1] : '';
  let form = '';
  let base = n;
  for (const f of forms) {
    const idx = n.indexOf(f);
    if (idx >= 0) {
      form = f.replace(/s$/, '');
      base = n.substring(0, idx).trim();
      break;
    }
  }
  base = base.replace(/\d+(?:\.\d+)?\s*(?:mg|g|ml|%|mg\/ml)?/g, '').trim();
  if (!base) base = n.split(/\s+/)[0] || n;
  return { base: base.trim(), form, strengthNum };
}

function matchParsedToProduct(drugName) {
  const n = normalize(drugName);
  if (!n) return null;
  const exact = products.value.find(
    (p) =>
      normalize(p.service_name) === n ||
      normalize(p.product_name) === n ||
      normalize(p.item_name) === n
  );
  if (exact) return exact;
  const { base, form, strengthNum } = parseGovernmentDrugName(drugName);
  if (!base) return null;
  const productText = (p) => [p.service_name, p.product_name, p.item_name].filter(Boolean).join(' ').toLowerCase();
  let best = null;
  let bestScore = 0;
  for (const p of products.value) {
    const text = productText(p);
    if (!text.includes(base)) continue;
    let score = 1;
    if (form && text.includes(form)) score += 2;
    if (strengthNum && text.includes(strengthNum)) score += 2;
    if (score > bestScore) {
      bestScore = score;
      best = p;
    }
  }
  if (best) return best;
  const contains = products.value.find(
    (p) =>
      normalize(p.service_name).includes(base) ||
      normalize(p.product_name).includes(base) ||
      (p.item_name && normalize(p.item_name).includes(base))
  );
  return contains || null;
}

function fillParsedLines(lines) {
  let id = 0;
  parsedLines.value = (lines || []).map((l) => {
    return {
      id: ++id,
      drug_name: l.drug_name || '',
      quantity: Number(l.quantity) || 1,
      matched: matchParsedToProduct(l.drug_name),
    };
  });
}

async function onExcelSelected(file) {
  if (!file || visitClosed.value) return;
  pdfFile.value = null;
  parsingFile.value = true;
  parsedLines.value = [];
  try {
    const res = await companionVisitsAPI.parseDrugsExcel(file);
    const lines = res.data || [];
    fillParsedLines(lines);
    if (parsedLines.value.length === 0) {
      $q.notify({ type: 'info', message: 'No drug lines found in Excel', position: 'top' });
    } else {
      $q.notify({ type: 'positive', message: `Found ${parsedLines.value.length} line(s)`, position: 'top' });
    }
  } catch (e) {
    const detail = e.response?.data?.detail;
    $q.notify({ type: 'negative', message: typeof detail === 'string' ? detail : 'Failed to parse Excel', position: 'top' });
  } finally {
    parsingFile.value = false;
  }
}

async function onPdfSelected(file) {
  if (!file || visitClosed.value) return;
  excelFile.value = null;
  parsingFile.value = true;
  parsedLines.value = [];
  try {
    const res = await companionVisitsAPI.parseDrugsPdf(file);
    const lines = res.data || [];
    fillParsedLines(lines);
    if (parsedLines.value.length === 0) {
      $q.notify({ type: 'info', message: 'No drug lines found in PDF', position: 'top' });
    } else {
      $q.notify({ type: 'positive', message: `Found ${parsedLines.value.length} line(s)`, position: 'top' });
    }
  } catch (e) {
    const detail = e.response?.data?.detail;
    $q.notify({ type: 'negative', message: typeof detail === 'string' ? detail : 'Failed to parse PDF', position: 'top' });
  } finally {
    parsingFile.value = false;
  }
}

function clearParsed() {
  pdfFile.value = null;
  excelFile.value = null;
  parsedLines.value = [];
}

async function addParsedRow(row) {
  if (visitClosed.value || !row.matched) return;
  try {
    await companionVisitsAPI.addItem(visitId.value, {
      item_code: row.matched.medication_code || row.matched.item_code,
      item_name: row.matched.service_name || row.matched.product_name,
      category: 'drug',
      unit_price: copaymentPrice(row.matched),
      quantity: row.quantity,
    });
    $q.notify({ type: 'positive', message: 'Added to bill', position: 'top' });
    await loadAddedItems();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to add', position: 'top' });
  }
}

async function addAllMatched() {
  if (visitClosed.value) return;
  const toAdd = parsedLines.value.filter((r) => r.matched);
  if (toAdd.length === 0) return;
  addingAll.value = true;
  let ok = 0;
  let err = 0;
  for (const row of toAdd) {
    try {
      await companionVisitsAPI.addItem(visitId.value, {
        item_code: row.matched.medication_code || row.matched.item_code,
        item_name: row.matched.service_name || row.matched.product_name,
        category: 'drug',
        unit_price: copaymentPrice(row.matched),
        quantity: row.quantity,
      });
      ok++;
    } catch {
      err++;
    }
  }
  addingAll.value = false;
  await loadAddedItems();
  if (ok) $q.notify({ type: 'positive', message: `Added ${ok} item(s) to bill`, position: 'top' });
  if (err) $q.notify({ type: 'warning', message: `${err} item(s) failed to add`, position: 'top' });
}

function openAddQuantityDialog(p) {
  quantityDialogProduct.value = p;
  quantityDialogQty.value = 1;
  showQuantityDialog.value = true;
}

async function confirmAddWithQuantity() {
  const p = quantityDialogProduct.value;
  if (!p || quantityDialogQty.value <= 0) return;
  showQuantityDialog.value = false;
  try {
    await companionVisitsAPI.addItem(visitId.value, {
      item_code: p.medication_code || p.item_code,
      item_name: p.service_name || p.product_name,
      category: 'drug',
      unit_price: copaymentPrice(p),
      quantity: quantityDialogQty.value,
    });
    $q.notify({ type: 'positive', message: 'Added to bill', position: 'top' });
    await loadAddedItems();
    searchText.value = '';
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to add', position: 'top' });
  }
}

async function loadVisit() {
  try {
    const res = await companionVisitsAPI.get(visitId.value);
    visit.value = res.data;
  } catch {
    visit.value = null;
  }
}

async function loadAddedItems() {
  try {
    const res = await companionVisitsAPI.getItems(visitId.value, 'drug');
    addedItems.value = res.data || [];
  } catch {
    addedItems.value = [];
  }
}

async function loadProducts() {
  loadingProducts.value = true;
  try {
    const res = await priceListAPI.search(undefined, undefined, 'product');
    const list = res.data || [];
    products.value = Array.isArray(list) ? list : (list.results || list.items || []);
  } catch {
    products.value = [];
  } finally {
    loadingProducts.value = false;
  }
}

async function removeItem(item) {
  if (visitClosed.value) return;
  try {
    await companionVisitsAPI.deleteItem(visitId.value, item.id);
    $q.notify({ type: 'positive', message: 'Removed from bill', position: 'top' });
    await loadAddedItems();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to remove', position: 'top' });
  }
}

onMounted(async () => {
  await loadVisit();
  await loadAddedItems();
  await loadProducts();
});
</script>

<style scoped>
.receipt-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(46, 139, 87, 0.2);
  border: 1px solid rgba(46, 139, 87, 0.5);
  color: var(--q-primary);
}
.body--dark .receipt-badge {
  background: rgba(46, 139, 87, 0.15);
  border-color: rgba(46, 139, 87, 0.4);
}
.unpaid-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(255, 152, 0, 0.15);
  border: 1px solid rgba(255, 152, 0, 0.5);
  color: #e65100;
}
.body--dark .unpaid-badge {
  background: rgba(255, 152, 0, 0.1);
  border-color: rgba(255, 152, 0, 0.4);
  color: #ffb74d;
}
</style>
