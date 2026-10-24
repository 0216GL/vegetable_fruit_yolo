<script setup>
/**
 * 大屏布局 —— 投影用。
 *
 * .surface-screen 这个类会覆盖 semantic.css 里的令牌，
 * 把整套配色切到深色面。所有子组件都跟着变，**组件代码一行都不用改** ——
 * 这就是两级令牌架构的兑现点。
 */
</script>

<template>
  <div class="screen surface-screen">
    <router-view />
  </div>
</template>

<style scoped>
.screen {
  min-height: 100dvh;
  background: var(--color-surface);
  color: var(--color-text-primary);
  padding: var(--sp-8);
}
</style>
