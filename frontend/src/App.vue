<script setup lang="ts">
import { NConfigProvider, NMessageProvider } from 'naive-ui'
</script>

<template>
  <n-config-provider>
    <n-message-provider>
      <div class="app-shell">
        <router-view />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.app-shell {
  height: 100%;
  min-height: 0;
}
</style>
