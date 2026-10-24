<script setup>
/**
 * 成熟度标签。
 *
 * 【关于那个小圆点】
 * 有经验的设计规范会警告"不要在每个列表项前面加装饰性色点"，
 * 因为那是纯装饰。但这个点**携带真实语义** —— 它表示成熟度等级，
 * 是这条信息的一部分，不是装饰。这属于规范的例外情况。
 *
 * 另外：文字始终存在。颜色是辅助，不是唯一区分手段
 * （只靠颜色传达信息是无障碍反模式）。
 */

import { computed } from 'vue'
import { ripenessByKey } from '@/utils/ripeness.js'

const props = defineProps({
  /** 成熟度 key，如 '3_coloring'。必须和模型输出的 ripeness 字段一致 */
  ripenessKey: { type: String, required: true },
  /** 置信度 0~1。不传就不显示百分比 */
  conf: { type: Number, default: null },
  /** 显示全称还是简称 */
  full: { type: Boolean, default: false },
})

const level = computed(() => ripenessByKey(props.ripenessKey))

const text = computed(() => {
  if (!level.value) return props.ripenessKey // 认不出的 key 原样显示，便于发现数据异常
  return props.full ? level.value.full : level.value.label
})

const percent = computed(() =>
  props.conf === null ? null : Math.round(props.conf * 100),
)
</script>

<template>
  <span class="badge" :style="{ '--dot': `var(${level?.cssVar ?? '--color-text-secondary'})` }">
    <span class="dot" aria-hidden="true" />
    <span class="text">{{ text }}</span>
    <span v-if="percent !== null" class="conf tnum">{{ percent }}%</span>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 2px var(--sp-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--fs-label);
  line-height: 1.6;
  white-space: nowrap;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--dot);
  flex-shrink: 0;
}

.conf {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
}
</style>
