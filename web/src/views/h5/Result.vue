<script setup>
/**
 * 结果页。
 *
 * 【关于那句"结论"怎么写】
 * 产品上最该给的是一句"能不能采"。但"多少比例算可以采"是**农业上的业务规则，
 * 不是模型输出** —— 我们没跟果园确认过，所以不能写成"可以摘了"这种指令。
 *
 * 这里的处理：把门槛**明写出来**，让用户自己判断。
 *   大数字 = 达到着色期及以上的比例
 *   下面一行 = 这个比例是按什么算的
 * 这样既给了决策依据，又没有假装自己懂农艺。
 */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useInspectionStore } from '@/stores/inspection.js'
import AnnotatedImage from '@/components/AnnotatedImage.vue'
import RipenessBar from '@/components/RipenessBar.vue'
import RipenessBadge from '@/components/RipenessBadge.vue'
import { harvestableRate, normalizeCounts, ripenessLabel } from '@/utils/ripeness.js'

const router = useRouter()
const store = useInspectionStore()

const current = computed(() => store.current)
const result = computed(() => current.value?.result ?? null)

const counts = computed(() => normalizeCounts(result.value?.counts))
const rate = computed(() => harvestableRate(result.value?.counts))

const ratePercent = computed(() =>
  rate.value === null ? null : Math.round(rate.value * 100),
)

const detections = computed(() => result.value?.detections ?? [])

/** 逐果清单按成熟度从高到低排 —— 要采的排前面 */
const sortedDetections = computed(() =>
  [...detections.value].sort((a, b) => (b.ripeness_conf ?? 0) - (a.ripeness_conf ?? 0)),
)

const timing = computed(() => result.value?.timing ?? null)

function goBack() {
  router.push({ name: 'h5-upload' })
}
</script>

<template>
  <div class="result">
    <!-- ================= 没有结果 =================
         刷新页面就会到这里（结果存在内存里，不落盘）。
         这不是 bug，是设计：要持久化就得后端落库。 -->
    <div v-if="!result" class="no-result">
      <p class="no-result-title">没有可显示的结果</p>
      <p class="no-result-sub">
        刷新页面会让结果丢失。请重新拍一张。
      </p>
      <button type="button" class="btn btn-primary btn-block" @click="goBack">
        去拍一张
      </button>
    </div>

    <!-- ================= 有结果 ================= -->
    <template v-else>
      <!-- 标注图 —— 英雄区 -->
      <AnnotatedImage
        :src="current.imageUrl"
        :detections="detections"
        :image-width="result.image?.width ?? 0"
        :image-height="result.image?.height ?? 0"
        alt="标注了成熟度的巡检照片"
      />

      <!-- 结论 -->
      <section class="verdict">
        <p v-if="ratePercent === null" class="verdict-main">
          这张图里没有检出果实
        </p>
        <template v-else>
          <p class="verdict-main">
            <span class="num tnum">{{ ratePercent }}%</span>
          </p>
          <p class="verdict-sub">达到着色期及以上的比例</p>
          <p class="verdict-note">
            该门槛可按果园自己的采收标准调整
          </p>
        </template>
      </section>

      <!-- 成熟度色带 -->
      <section class="block">
        <h2>成熟度分布</h2>
        <RipenessBar :counts="counts" />
      </section>

      <!-- 逐果清单 -->
      <section v-if="detections.length" class="block">
        <h2>逐个果实（{{ detections.length }} 个）</h2>
        <ul class="fruit-list">
          <li v-for="(d, i) in sortedDetections" :key="i" class="fruit-item">
            <span class="idx tnum">{{ i + 1 }}</span>
            <RipenessBadge :ripeness-key="d.ripeness" :conf="d.ripeness_conf" />
            <span class="det-conf tnum">
              框 {{ Math.round((d.det_conf ?? 0) * 100) }}%
            </span>
          </li>
        </ul>
      </section>

      <!-- 元信息 -->
      <section class="meta">
        <p v-if="current.plot">
          <span class="meta-key">地块</span>{{ current.plot }}
        </p>
        <p>
          <span class="meta-key">耗时</span>
          <span class="tnum">
            检测 {{ Math.round(timing?.detect_ms ?? 0) }}ms
            ＋ 分类 {{ Math.round(timing?.classify_ms ?? 0) }}ms
          </span>
        </p>
        <p class="meta-dim">
          模型对"着色期"和"完熟期"的判断最容易混。这是已知的困难点，
          在成熟度接近的两级之间准确率会下降。
        </p>
      </section>

      <div class="actions">
        <button type="button" class="btn btn-primary btn-block" @click="goBack">
          再拍一张
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.result {
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
  flex: 1;
}

/* ---- 无结果 ---- */
.no-result {
  margin: auto 0;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.no-result-title {
  font-size: var(--fs-subhead);
}

.no-result-sub {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  margin-bottom: var(--sp-4);
}

/* ---- 结论 ---- */
.verdict-main {
  font-size: var(--fs-display);
  line-height: 1.1;
  font-weight: 600;
}

.num {
  font-family: var(--font-num);
}

.verdict-sub {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  margin-top: var(--sp-1);
}

.verdict-note {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
  margin-top: var(--sp-1);
}

/* ---- 区块 ---- */
.block h2 {
  font-size: var(--fs-subhead);
  margin-bottom: var(--sp-3);
}

/* ---- 逐果清单 ---- */
.fruit-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.fruit-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
  border-bottom: 1px solid var(--color-border);
  min-height: var(--control-min-height);
}

.fruit-item:last-child {
  border-bottom: none;
}

.idx {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
  min-width: 1.6em;
}

.det-conf {
  margin-left: auto;
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
}

/* ---- 元信息 ---- */
.meta {
  font-size: var(--fs-label);
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-4);
  border-top: 1px solid var(--color-border);
}

.meta-key {
  display: inline-block;
  min-width: 4em;
}

.meta-dim {
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
}

/* ---- 按钮 ---- */
.actions {
  margin-top: auto;
  padding-top: var(--sp-4);
}

.btn {
  min-height: var(--control-min-height);
  padding: 0 var(--sp-4);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  font-size: var(--fs-body);
}

.btn-block {
  width: 100%;
}

.btn-primary {
  background: var(--color-text-primary);
  color: var(--color-surface);
}
</style>
