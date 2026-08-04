<script setup>
import { computed, ref } from 'vue';
import { Search } from 'lucide-vue-next';
import { cn } from '../../utils/cn';
import HmsEmptyState from './HmsEmptyState.vue';
import HmsSkeleton from './HmsSkeleton.vue';

const props = defineProps({
  rows: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  loading: { type: Boolean, default: false },
  searchable: { type: Boolean, default: false },
  searchPlaceholder: { type: String, default: 'Filter results…' },
  emptyTitle: { type: String, default: 'No records found' },
  emptyDescription: { type: String, default: '' },
  dense: { type: Boolean, default: true },
  class: { type: String, default: '' },
});

const emit = defineEmits(['row-click']);
const filter = ref('');

const filteredRows = computed(() => {
  const q = filter.value.trim().toLowerCase();
  if (!q) return props.rows;
  return props.rows.filter((row) =>
    props.columns.some((col) => {
      if (!col.field || col.name === 'actions') return false;
      const val = typeof col.field === 'function' ? col.field(row) : row[col.field];
      return String(val ?? '')
        .toLowerCase()
        .includes(q);
    })
  );
});

function resolveKey(row, index) {
  if (typeof props.rowKey === 'function') return props.rowKey(row);
  return row[props.rowKey] ?? index;
}

function cellValue(row, col) {
  if (typeof col.field === 'function') return col.field(row);
  const raw = row[col.field];
  if (col.format) return col.format(raw, row);
  return raw;
}
</script>

<template>
  <div :class="cn('hms-table', dense && 'hms-table--dense', props.class)">
    <div v-if="searchable || $slots.toolbar" class="hms-table__toolbar">
      <label v-if="searchable" class="hms-table__search">
        <Search :size="15" class="hms-table__search-icon" aria-hidden="true" />
        <input
          v-model="filter"
          type="search"
          :placeholder="searchPlaceholder"
          aria-label="Filter table"
        />
      </label>
      <div v-if="$slots.toolbar" class="hms-table__toolbar-actions">
        <slot name="toolbar" />
      </div>
    </div>

    <div v-if="loading" class="hms-table__loading">
      <HmsSkeleton :lines="6" />
    </div>

    <HmsEmptyState
      v-else-if="!filteredRows.length"
      :title="emptyTitle"
      :description="emptyDescription"
      class="hms-table__empty"
    />

    <div v-else class="hms-table__scroll">
      <table>
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.name"
              :style="{ textAlign: col.align || 'left', width: col.width }"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in filteredRows"
            :key="resolveKey(row, index)"
            @click="emit('row-click', row)"
          >
            <td
              v-for="col in columns"
              :key="col.name"
              :style="{ textAlign: col.align || 'left' }"
            >
              <slot :name="`cell-${col.name}`" :row="row" :value="cellValue(row, col)">
                {{ cellValue(row, col) }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="$slots.footer" class="hms-table__footer">
      <slot name="footer" :count="filteredRows.length" :total="rows.length" />
    </div>
  </div>
</template>

<style scoped>
.hms-table {
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  box-shadow: var(--hms-shadow-md);
  overflow: hidden;
}

.hms-table__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
}

.hms-table__search {
  position: relative;
  flex: 1;
  min-width: min(240px, 100%);
  max-width: 420px;
}

.hms-table__search-icon {
  position: absolute;
  left: 0.85rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--hms-text-muted);
  pointer-events: none;
}

.hms-table__search input {
  width: 100%;
  height: 2.35rem;
  padding: 0 0.95rem 0 2.35rem;
  border-radius: var(--hms-radius-full);
  border: 1px solid transparent;
  background: var(--hms-surface);
  color: var(--hms-text-primary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  outline: none;
  transition:
    border-color var(--hms-duration-fast) var(--hms-ease-out),
    box-shadow var(--hms-duration-fast) var(--hms-ease-out),
    background-color var(--hms-duration-fast) var(--hms-ease-out);
}

.hms-table__search input:focus {
  border-color: var(--hms-accent);
  background: var(--hms-panel-bg);
  box-shadow: 0 0 0 3px var(--hms-accent-muted);
}

.hms-table__toolbar-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.hms-table__loading,
.hms-table__empty {
  margin: 1rem;
}

.hms-table__scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--hms-surface);
  color: var(--hms-text-muted);
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.65rem 0.9rem;
  border-bottom: 1px solid var(--hms-border);
  white-space: nowrap;
}

tbody tr {
  transition: background-color var(--hms-duration-fast) var(--hms-ease-out);
  cursor: pointer;
}

tbody tr:hover {
  background: var(--hms-accent-muted);
}

tbody tr:not(:last-child) td {
  border-bottom: 1px solid var(--hms-border);
}

td {
  padding: 0.85rem 1rem;
  color: var(--hms-text-primary);
  font-size: var(--hms-text-sm);
  vertical-align: middle;
}

.hms-table--dense td {
  padding: 0.7rem 0.95rem;
}

.hms-table--dense thead th {
  padding: 0.6rem 0.95rem;
}

.hms-table__footer {
  padding: 0.65rem 1rem;
  border-top: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-xs);
  font-weight: 600;
}
</style>
