<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to IPD"
        @click="$router.push('/ipd')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">
        Admit Patient
      </div>
    </div>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          Admit Patient Module
        </div>
        <div class="text-body1 glass-text">
          This module will be implemented soon. Use this page to admit patients to the hospital.
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

