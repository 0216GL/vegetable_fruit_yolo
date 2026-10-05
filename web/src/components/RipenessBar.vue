<script setup>
/**
 * 成熟度色带 —— 这个产品的记忆点组件。
 *
 * 【为什么是色带，不是饼图或柱状图】
 * 模型领域里最核心的技术洞察是：成熟度是**连续量，不是四个离散的桶**
 * （着色期和完熟期的平均色相只差 6°，这正是模型最难的地方）。
 * 饼图把这个连续性表达成四块割裂的类目，**表达错了**。
 * 一条按比例分配的色带，才是这个问题的真实形状。
 *
 * 【为什么色块下面一定要有文字】
 * 只靠颜色传达信息是无障碍反模式，而且柿果的「着色期（橙）」和
 * 「完熟（深红）」对色觉障碍用户本来就难分。
 * 所以这里是三重编码：色块 + 中文名 + 数量。任何一层缺失都不影响理解。
 */

import { computed } from 'vue'
import { RIPENESS, normalizeCounts, totalCount } from '@/utils/ripeness.js'

const props = defineProps({
  /** 后端返回的 counts，形如 { '1_unripe': 34, ... } */
  counts: { type: Object, default: () => ({}) },
})

const safeCounts = computed(() => normalizeCounts(props.counts))
const total = computed(() => totalCount(props.counts))

/** 只给有数量的等级画色块 —— 数量为 0 的画出来是一条看不见的线，反而干扰 */
const segments = computed(() =>
  RIPENESS.map((level) => ({
    ...level,
    count: safeCounts.value[level.key],
    percent: total.value ? (safeCounts.value[level.key] / total.value) * 100 : 0,
  })).filter((s) => s.count > 0),
)

const legend = computed(() =>
  RIPENESS.map((level) => ({
    ...level,
    count: safeCounts.value[level.key],
  })),
)
</script>

<template>
  <div class="bar-block">
    <!-- 没有检出果实：说清楚，不要显示一条空带子让人猜 -->
    <p v-if="total === 0" class="empty">这张图里没有检出果实</p>

    <template v-else>
      <!-- 色带 -->
      <div
        class="band"
        role="img"
        :aria-label="
          legend.map((l) => `${l.label} ${l.count} 个`).join('，')
        "
      >
        <span
          v-for="s in segments"
          :key="s.key"
          class="seg"
          :style="{
            width: `${s.percent}%`,
            background: `var(${s.cssVar})`,
          }"
        />
      </div>

      <!-- 图例：文字和数量在这里，不依赖颜色 -->
      <ul class="legend">
        <li v-for="l in legend" :key="l.key" class="legend-item">
          <span class="swatch" :style="{ background: `var(${l.cssVar})` }" aria-hidden="true" />
          <span class="name">{{ l.label }}</span>
          <span class="count tnum">{{ l.count }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.bar-block {
  width: 100%;
}

.empty {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  padding: var(--sp-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  text-align: center;
}

/* ---- 色带 ----
   高度不用太大：它是"一眼看比例"的图形，不是主视觉。 */
.band {
  display: flex;
  height: 20px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.seg {
  height: 100%;
  transition: width var(--dur-slow) var(--ease-out);
}

/* ---- 图例 ---- */
.legend {
  list-style: none;
  margin: var(--sp-3) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--sp-2) var(--sp-4);
}

@media (min-width: 640px) {
  .legend {
    grid-template-columns: repeat(4, 1fr);
  }
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--fs-label);
}

.swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.name {
  color: var(--color-text-secondary);
}

.count {
  margin-left: auto;
  font-weight: 600;
}
</style>
