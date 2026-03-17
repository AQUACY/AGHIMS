<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Companion / Copayment
    </div>
    <div class="text-body1 glass-text-muted q-mb-lg">
      Service requests and copayment billing from the government system. Records create services here; Lab, Scan, Xray, and Pharmacy add line items for copayment.
    </div>
    <div class="row q-gutter-md">
      <q-card class="col-12 col-sm-6 col-md-4 glass-card" flat clickable @click="$router.push({ name: 'CompanionVisitList' })">
        <q-card-section class="text-center">
          <q-icon name="list_alt" size="48px" />
          <div class="text-h6 q-mt-md glass-text">Service list</div>
          <p class="glass-text-muted text-body2">View visits created from card + visit number.</p>
          <q-btn flat class="glass-button q-mt-sm" label="Open" @click.prevent="$router.push({ name: 'CompanionVisitList' })" />
        </q-card-section>
      </q-card>
      <q-card v-if="canAccessRecords" class="col-12 col-sm-6 col-md-4 glass-card" flat clickable @click="$router.push({ name: 'CompanionCreateService' })">
        <q-card-section class="text-center">
          <q-icon name="add_circle" size="48px" />
          <div class="text-h6 q-mt-md glass-text">Create service</div>
          <p class="glass-text-muted text-body2">Records: add a service using government card and visit number.</p>
          <q-btn flat class="glass-button q-mt-sm" label="Create" @click.prevent="$router.push({ name: 'CompanionCreateService' })" />
        </q-card-section>
      </q-card>
      <q-card class="col-12 col-sm-6 col-md-4 glass-card" flat>
        <q-card-section>
          <div class="text-h6 q-mb-sm glass-text">Billing & reports</div>
          <p class="glass-text-muted text-body2">Coming next: copayment billing and reporting.</p>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();
const canAccessRecords = computed(() => authStore.canAccess(['Records', 'Admin']));
</script>
