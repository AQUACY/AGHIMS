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
    </div>
  </q-page>
</template>

<script setup>
import { useRouter } from 'vue-router';
</script>

<style scoped>
.claims-module-tile:hover {
  background: rgba(0, 0, 0, 0.03);
}
</style>
