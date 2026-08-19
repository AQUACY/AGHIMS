<template>
  <q-page class="hms-page my-theme-page">
    <HmsPageHeader title="My theme colors">
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.back()">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="my-theme-layout">
      <aside class="diag-panel my-theme-intro">
        <div class="my-theme-intro__icon" aria-hidden="true">
          <q-icon name="palette" size="28px" color="primary" />
        </div>
        <h2 class="my-theme-intro__title">Your appearance</h2>
        <p class="my-theme-intro__body">
          Set background, text, and accent colors for your account only. Other users keep their own
          theme. Leave a field empty to use the app default.
        </p>
      </aside>

      <q-card class="diag-panel my-theme-card" flat>
        <q-card-section>
          <MyThemeColorsPanel />
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import MyThemeColorsPanel from '../components/MyThemeColorsPanel.vue';
</script>

<style scoped>
.my-theme-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
  max-width: 1100px;
}

.my-theme-intro {
  padding: 1.25rem 1.15rem;
  position: sticky;
  top: calc(var(--hms-header-height) + 0.75rem);
}

.my-theme-intro__icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-accent-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.85rem;
}

.my-theme-intro__title {
  margin: 0 0 0.45rem;
  font-size: 1.05rem;
  font-weight: 750;
  color: var(--hms-text-primary);
}

.my-theme-intro__body {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--hms-text-secondary);
}

.my-theme-card {
  max-width: 720px;
}

@media (max-width: 900px) {
  .my-theme-layout {
    grid-template-columns: 1fr;
  }

  .my-theme-intro {
    position: static;
  }
}
</style>
