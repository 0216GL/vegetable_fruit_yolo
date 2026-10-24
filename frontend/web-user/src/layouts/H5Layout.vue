<script setup>
/**
 * H5 布局 —— 手机端的公共外壳。
 *
 * 【为什么要有 max-width】
 * 在电脑浏览器里开发时，页面会被拉满整个窗口，看起来不像手机。
 * 限制成 480px 并居中，开发时看到的就是接近真机的效果。
 * 真机上这个限制不起作用（屏幕本来就窄）。
 */
</script>

<template>
  <div class="h5">
    <main class="frame">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.h5 {
  min-height: 100dvh; /* 用 dvh 不用 vh：iOS 地址栏收起时 vh 会算错，页面会跳 */
  background: var(--color-surface);
}

.frame {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100dvh;

  /* 左右留白 + 底部避开 iPhone 的横条 */
  padding: var(--sp-4);
  padding-bottom: calc(var(--sp-4) + env(safe-area-inset-bottom, 0px));

  display: flex;
  flex-direction: column;
}
</style>
