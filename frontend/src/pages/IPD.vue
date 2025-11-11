<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Inpatient Department (IPD)
    </div>

    <div class="text-subtitle1 text-secondary q-mb-lg">
      Select a module to manage inpatient operations
    </div>

    <!-- Module Cards Grid -->
    <div class="row q-col-gutter-md">
      <!-- Admission Recommendations Module -->
      <div class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/admission-recommendations')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="local_hospital" size="64px" color="primary" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Admission Recommendations
              </div>
              <div class="text-caption text-secondary">
                View and manage patient admission recommendations
              </div>
            </div>
      </q-card-section>
    </q-card>
      </div>

      <!-- Admit Patient Module (Admin Only) -->
      <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/admit-patient')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="person_add" size="64px" color="secondary" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Admit Patient
              </div>
              <div class="text-caption text-secondary">
                Admit patients to the hospital
              </div>
            </div>
      </q-card-section>
    </q-card>
      </div>

      <!-- Transfer Patient Module (Admin Only) -->
      <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/transfer-patient')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="swap_horiz" size="64px" color="purple" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Transfer Patient
              </div>
              <div class="text-caption text-secondary">
                Transfer patients between wards or beds
              </div>
            </div>
          </q-card-section>
        </q-card>
          </div>

      <!-- Doctor/Nursing Station Module (Admin Only) -->
      <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/doctor-nursing-station')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="medical_services" size="64px" color="accent" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Doctor/Nursing Station
              </div>
              <div class="text-caption text-secondary">
                View and manage ward patients
              </div>
            </div>
          </q-card-section>
        </q-card>
        </div>

             <!-- Bed Management Module (Admin Only) -->
             <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
               <q-card 
                 class="glass-card module-card cursor-pointer" 
                 flat 
                 bordered
                 @click="navigateToModule('/ipd/bed-management')"
               >
                 <q-card-section class="q-pa-lg">
                   <div class="column items-center text-center">
                     <q-icon name="hotel" size="64px" color="orange" class="q-mb-md" />
                     <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                       Bed Management
                     </div>
                     <div class="text-caption text-secondary">
                       Manage beds for wards
                     </div>
                   </div>
                 </q-card-section>
               </q-card>
             </div>

             <!-- Registers Module (Admin Only) -->
             <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
               <q-card 
                 class="glass-card module-card cursor-pointer" 
                 flat 
                 bordered
                 @click="navigateToModule('/ipd/registers')"
               >
                 <q-card-section class="q-pa-lg">
                   <div class="column items-center text-center">
                     <q-icon name="assignment" size="64px" color="teal" class="q-mb-md" />
                     <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                       Registers
                </div>
                <div class="text-caption text-secondary">
                       View admission and discharge records
                     </div>
                   </div>
                 </q-card-section>
               </q-card>
             </div>

             <!-- Daily Ward State Module (Admin Only) -->
             <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
               <q-card 
                 class="glass-card module-card cursor-pointer" 
                 flat 
                 bordered
                 @click="navigateToModule('/ipd/daily-ward-state')"
               >
                 <q-card-section class="q-pa-lg">
                   <div class="column items-center text-center">
                     <q-icon name="today" size="64px" color="indigo" class="q-mb-md" />
                     <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                       Daily Ward State
                </div>
                <div class="text-caption text-secondary">
                       View daily ward statistics and occupancy
                     </div>
                   </div>
                 </q-card-section>
               </q-card>
             </div>

             <!-- Transfer Acceptance Module (Admin Only) -->
             <div v-if="isAdmin" class="col-12 col-md-6 col-lg-3">
               <q-card 
                 class="glass-card module-card cursor-pointer" 
                 flat 
                 bordered
                 @click="navigateToModule('/ipd/transfer-acceptance')"
               >
                 <q-card-section class="q-pa-lg">
                   <div class="column items-center text-center">
                     <q-icon name="check_circle" size="64px" color="amber" class="q-mb-md" />
                     <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                       Transfer Acceptance
                </div>
                <div class="text-caption text-secondary">
                       Accept or reject pending transfers
                </div>
              </div>
                 </q-card-section>
               </q-card>
              </div>

      <!-- Future modules can be added here -->
      <!-- Example:
      <div class="col-12 col-md-6 col-lg-4">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/module-name')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="icon_name" size="64px" color="primary" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Module Name
                </div>
                <div class="text-caption text-secondary">
                Module description
                </div>
              </div>
      </q-card-section>
    </q-card>
      </div>
      -->
    </div>
  </q-page>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const isAdmin = computed(() => {
  return authStore.user?.role === 'Admin';
});

const navigateToModule = (path) => {
  router.push(path);
};
</script>

<style scoped>
/* Light mode adjustments */
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

/* Dark mode adjustments */
.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

/* Module card styling */
.module-card {
  transition: transform 0.2s, box-shadow 0.2s;
  height: 100%;
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.body--dark .module-card:hover {
  box-shadow: 0 8px 16px rgba(255, 255, 255, 0.15);
}
</style>

