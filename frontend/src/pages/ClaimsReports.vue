<template>
  <q-page class="hms-page">
    <HmsPageHeader title="Claims reports" subtitle="Structured reports for claims analysis and auditing.">
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/claims')">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Coming soon</div>
          <div class="panel-sub">Monthly submission summaries, vetting/audit reports, and exports</div>
        </div>
      </div>
      <div class="panel-body empty-hint">
        Reports will live here. Next we can add monthly submission summaries, vetting/audit reports, and exports.
      </div>
    </section>
  </q-page>
</template>

<script setup>
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
</script>

<style scoped>
.diag-panel {
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  overflow: hidden;
}
.panel-head {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--hms-border);
}
.panel-title { font-size: var(--hms-text-base); font-weight: 750; color: var(--hms-text-primary); }
.panel-sub { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.panel-body { padding: 0.95rem 1rem; }
.empty-hint { color: var(--hms-text-muted); font-size: var(--hms-text-sm); }
</style>
