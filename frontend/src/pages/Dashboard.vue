<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold">
      Dashboard
    </div>

    <div class="row q-gutter-md">
      <!-- Today's Patients Card -->
      <q-card class="col-12 col-md-4 glass-card" flat>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Today's Patients</div>
          <div class="text-h3 q-mt-sm" style="font-weight: 600;">
            {{ dashboardStore.stats.todayPatients }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Pending Encounters Card -->
      <q-card class="col-12 col-md-4 glass-card" flat>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Pending Encounters</div>
          <div class="text-h3 q-mt-sm" style=" font-weight: 600;">
            {{ dashboardStore.stats.pendingEncounters }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Unpaid Bills Card -->
      <q-card class="col-12 col-md-4 glass-card" flat>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Unpaid Bills</div>
          <div class="text-h3 q-mt-sm" style=" font-weight: 600;">
            {{ dashboardStore.stats.unpaidBills }}
          </div>
        </q-card-section>
      </q-card>
    </div>

    <!-- Quick Actions -->
    <div class="row q-gutter-md q-mt-lg">
      <q-card
        v-if="canAccess(['Records', 'Admin'])"
        class="col-12 col-sm-6 col-md-3 glass-card"
        flat
      >
        <q-card-section class="text-center">
          <q-icon name="person_add" size="48px" />
          <div class="text-subtitle1 q-mt-md" style=" font-weight: 500;">
            Register Patient
          </div>
          <q-btn
            flat
            class="glass-button q-mt-md"
            label="Go"
            @click="$router.push('/patients/register')"
          />
        </q-card-section>
      </q-card>

      <q-card
        v-if="canAccess(['Nurse', 'Doctor', 'Admin'])"
        class="col-12 col-sm-6 col-md-3 glass-card"
        flat
      >
        <q-card-section class="text-center">
          <q-icon name="favorite" size="48px" />
          <div class="text-subtitle1 q-mt-md" style=" font-weight: 500;">
            Record Vitals
          </div>
          <q-btn
            flat
            class="glass-button q-mt-md"
            label="Go"
            @click="$router.push('/vitals')"
          />
        </q-card-section>
      </q-card>

      <q-card
        v-if="canAccess(['Doctor', 'Admin'])"
        class="col-12 col-sm-6 col-md-3 glass-card"
        flat
      >
        <q-card-section class="text-center">
          <q-icon name="medical_services" size="48px" />
          <div class="text-subtitle1 q-mt-md" style=" font-weight: 500;">
            Consultation
          </div>
          <q-btn
            flat
            class="glass-button q-mt-md"
            label="Go"
            @click="$router.push('/consultation')"
          />
        </q-card-section>
      </q-card>

      <q-card
        v-if="canAccess(['Billing', 'Admin'])"
        class="col-12 col-sm-6 col-md-3 glass-card"
        flat
      >
        <q-card-section class="text-center">
          <q-icon name="receipt" size="48px" />
          <div class="text-subtitle1 q-mt-md" style=" font-weight: 500;">
            Billing
          </div>
          <q-btn
            flat
            class="glass-button q-mt-md"
            label="Go"
            @click="$router.push('/billing')"
          />
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue';
import { useDashboardStore } from '../stores/dashboard';
import { useAuthStore } from '../stores/auth';

const dashboardStore = useDashboardStore();
const authStore = useAuthStore();

const canAccess = (roles) => authStore.canAccess(roles);

onMounted(() => {
  dashboardStore.fetchStats();
});
</script>

