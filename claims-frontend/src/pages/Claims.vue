<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg text-weight-bold glass-text">Claims Module</div>
    <p class="text-body2 text-grey-8 q-mb-lg">
      Choose an option below to manage claims or correct errors from ClaimIT import reports.
    </p>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-sm-6 col-md-4">
        <q-card
          class="claims-module-tile cursor-pointer glass-card"
          flat
          bordered
          @click="$router.push('/claims/list')"
        >
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="description" size="64px" color="primary" class="q-mb-md" />
            <div class="text-h6 text-weight-medium">Claims</div>
            <div class="text-caption text-grey-7 q-mt-sm">
              View finalized encounters, generate and edit claims, export XML for ClaimIT.
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-sm-6 col-md-4">
        <q-card
          class="claims-module-tile cursor-pointer glass-card"
          flat
          bordered
          @click="$router.push('/claims/correct-errors')"
        >
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="error_outline" size="64px" color="orange" class="q-mb-md" />
            <div class="text-h6 text-weight-medium">Correct Errors</div>
            <div class="text-caption text-grey-7 q-mt-sm">
              Upload ClaimIT import reports, view claims with errors, fix and re-export.
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-sm-6 col-md-4">
        <q-card
          class="claims-module-tile cursor-pointer glass-card"
          flat
          bordered
          @click="$router.push('/claims/ghims-import')"
        >
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="upload_file" size="64px" color="teal" class="q-mb-md" />
            <div class="text-h6 text-weight-medium">Import GHIMS XML</div>
            <div class="text-caption text-grey-7 q-mt-sm">
              Upload exported XML, review imported claims, finalize or revert, then export again.
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div v-if="aiVettingActive" class="col-12 col-sm-6 col-md-4">
        <q-card
          class="claims-module-tile cursor-pointer glass-card ai-tile"
          flat
          bordered
          @click="$router.push('/claims/ai-vetting')"
        >
          <q-card-section class="text-center q-pa-xl">
            <q-icon name="auto_awesome" size="64px" color="cyan" class="q-mb-md" />
            <div class="text-h6 text-weight-medium">AI Vetting</div>
            <div class="text-caption text-grey-7 q-mt-sm">
              Batch-scan imports for ZOOM specialty and Ghana Card → HIN, then correct in one pass.
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { moduleSettingsAPI } from '../services/api';

const aiVettingActive = ref(false);

onMounted(async () => {
  try {
    const res = await moduleSettingsAPI.getStatus('ai_claims_vetting');
    aiVettingActive.value = !!res.data?.is_active;
  } catch {
    aiVettingActive.value = false;
  }
});
</script>

<style scoped>
.claims-module-tile:hover {
  background: rgba(0, 0, 0, 0.03);
}
.ai-tile {
  border-color: rgba(0, 188, 212, 0.35) !important;
}
</style>
