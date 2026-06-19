<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-lg text-weight-bold glass-text">Suhum</div>
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card class="glass-card cursor-pointer" flat bordered @click="$router.push({ name: 'PriceListManagement' })">
          <q-card-section>
            <div class="row items-center q-gutter-md">
              <q-icon name="price_check" size="48px" color="primary" />
              <div>
                <div class="text-h6">Price list management</div>
                <div class="text-grey-7">Upload and manage NHIA price lists</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card class="glass-card cursor-pointer" flat bordered @click="$router.push({ name: 'Icd10DrgMapping' })">
          <q-card-section>
            <div class="row items-center q-gutter-md">
              <q-icon name="hub" size="48px" color="teal" />
              <div>
                <div class="text-h6">ICD-10 DRG mapping</div>
                <div class="text-grey-7">Manage ICD-10 to DRG code mappings</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card class="glass-card cursor-pointer" flat bordered @click="$router.push({ name: 'GhimsXmlImport' })">
          <q-card-section>
            <div class="row items-center q-gutter-md">
              <q-icon name="upload_file" size="48px" color="secondary" />
              <div>
                <div class="text-h6">Import GHIMS XML</div>
                <div class="text-grey-7">Upload, edit, and export claim XML batches</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="authStore.isAdmin" class="col-12 col-md-6">
        <q-card class="glass-card cursor-pointer" flat bordered @click="$router.push({ name: 'UserManagement' })">
          <q-card-section>
            <div class="row items-center q-gutter-md">
              <q-icon name="group" size="48px" color="deep-orange" />
              <div>
                <div class="text-h6">User management</div>
                <div class="text-grey-7">Create and manage staff accounts</div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();
</script>

<style scoped>
.glass-card {
  transition: transform 0.15s ease;
}
.glass-card:hover {
  transform: translateY(-2px);
}
</style>
