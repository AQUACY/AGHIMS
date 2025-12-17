<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Inventory Management
    </div>

    <div class="text-subtitle1 text-secondary q-mb-lg">
      Select a module to manage inventory operations
    </div>

    <!-- Module Cards Grid -->
    <div class="row q-col-gutter-md">
      <!-- Requisitions Module -->
      <div v-if="canAccessRequisitions" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/pharmacy/requisitions')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="shopping_cart" size="64px" color="primary" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Requisitions
              </div>
              <div class="text-caption text-secondary">
                Request items from stores and manage requisitions
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Department/Ward Stock Module -->
      <div v-if="canAccessDepartmentStock" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/pharmacy/ward-stock')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="warehouse" size="64px" color="secondary" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Department/Ward Stock
              </div>
              <div class="text-caption text-secondary">
                View and manage department/ward stock levels
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Store Stock Management Module -->
      <div v-if="canAccessStoreStock" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/admin/store-stock')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="inventory" size="64px" color="purple" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Store Stock Management
              </div>
              <div class="text-caption text-secondary">
                Add, approve, and manage store stock with vendors
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Store Management Module -->
      <div v-if="canAccessStoreManagement" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/store-management')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="store" size="64px" color="accent" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Store Management
              </div>
              <div class="text-caption text-secondary">
                Configure and manage stores
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Department Management Module -->
      <div v-if="canAccessDepartmentManagement" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/ipd/ward-management')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="meeting_room" size="64px" color="orange" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Department Management
              </div>
              <div class="text-caption text-secondary">
                Configure and manage departments/units
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Inventory Debits Module -->
      <div v-if="canAccessInventoryDebits" class="col-12 col-md-6 col-lg-3">
        <q-card 
          class="glass-card module-card cursor-pointer" 
          flat 
          bordered
          @click="navigateToModule('/pharmacy/inventory-debits')"
        >
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="remove_shopping_cart" size="64px" color="teal" class="q-mb-md" />
              <div class="text-h6 text-weight-bold glass-text q-mb-xs">
                Inventory Debits
              </div>
              <div class="text-caption text-secondary">
                Track and manage inventory debits
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';

const router = useRouter();
const authStore = useAuthStore();

// Check if user has access to any inventory module
const hasAnyAccess = computed(() => {
  return canAccessRequisitions.value ||
         canAccessDepartmentStock.value ||
         canAccessStoreStock.value ||
         canAccessStoreManagement.value ||
         canAccessDepartmentManagement.value ||
         canAccessInventoryDebits.value;
});

// Access checks for each module
const canAccessRequisitions = computed(() => {
  return authStore.canAccess(['Nurse', 'Doctor', 'PA', 'Pharmacy Head', 'Store Manager', 'Admin']);
});

const canAccessDepartmentStock = computed(() => {
  return authStore.canAccess(['Nurse', 'Doctor', 'PA', 'Pharmacy Head', 'Store Manager', 'Admin']);
});

const canAccessStoreStock = computed(() => {
  return authStore.canAccess(['Admin', 'Store Manager', 'Department Head', 'Pharmacy Head']);
});

const canAccessStoreManagement = computed(() => {
  return authStore.canAccess(['Admin']);
});

const canAccessDepartmentManagement = computed(() => {
  return authStore.canAccess(['Admin']);
});

const canAccessInventoryDebits = computed(() => {
  return authStore.canAccess(['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin']);
});

const navigateToModule = (path) => {
  router.push(path);
};

onMounted(() => {
  // Redirect if no access
  if (!hasAnyAccess.value) {
    router.push('/dashboard');
    return;
  }
});
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.module-card {
  transition: transform 0.2s, box-shadow 0.2s;
  height: 100%;
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

