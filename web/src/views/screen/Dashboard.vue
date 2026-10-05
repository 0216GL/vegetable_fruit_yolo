<script setup>
/**
 * 大屏看板 —— 路演演示用（Persuade 模式）。
 *
 * 【英雄区是那张标注图，不是大数字】
 * 这个产品最独特的画面是"一张果园实拍，每颗柿子都被框出来标着成熟度"。
 * 评委见过一百个数据看板，没见过一百张这样的照片。所以图占主位，
 * "可采收率"这个数字退到右侧竖栏当配角。
 *
 * 【数据从哪来】
 * 优先读 store 里最近一次真实识别结果 —— 所以**先在 H5 上传一张，
 * 再切到这个页面，就能看到真实数据**。
 * 没有的时候显示明确标注的示例数据（不是假装真实）。
 *
 * 配色靠 .surface-screen 覆盖语义令牌实现，组件代码里没有任何深色判断。
 */

import { computed } from 'vue'
import { useInspectionStore } from '@/stores/inspection.js'
import { harvestableRate, normalizeCounts, totalCount } from '@/utils/ripeness.js'
import AnnotatedImage from '@/components/AnnotatedImage.vue'
import RipenessBar from '@/components/RipenessBar.vue'
import { APP_NAME } from '@/config/brand.js'

const store = useInspectionStore()

const current = computed(() => store.current)
const result = computed(() => current.value?.result ?? null)

/** 没有真实结果时用的示例数据。界面上会明确标出"示例"。 */
const SAMPLE = {
  counts: { '1_unripe': 34, '2_turning': 22, '3_coloring': 41, '4_full': 18 },
  detections: [],
}

const isSample = computed(() => !result.value)

const counts = computed(() =>
  normalizeCounts(result.value?.counts ?? SAMPLE.counts),
)

const total = computed(() => totalCount(counts.value))

const rate = computed(() =>
  result.value ? harvestableRate(result.value.counts) : harvestableRate(SAMPLE.counts),
)

const ratePercent = computed(() =>
  rate.value === null ? '—' : Math.round(rate.value * 100),
)

const detections = computed(() => result.value?.detections ?? [])
</script>

<template>
  <div class="dashboard">
    <!-- 顶栏：产品名 + 数据来源说明 -->
    <header class="topbar">
      <span class="app-name">{{ APP_NAME }}</span>
      <span class="source" :class="{ sample: isSample }">
        {{ isSample ? '示例数据' : `${current?.plot || '最近一次巡检'}` }}
      </span>
    </header>

    <div class="body">
      <!-- ============ 左：英雄区 ============ -->
      <section class="hero">
        <AnnotatedImage
          v-if="current"
          :src="current.imageUrl"
          :detections="detections"
          :image-width="result?.image?.width ?? 0"
          :image-height="result?.image?.height ?? 0"
          alt="巡检照片"
        />

        <!-- 没有真实图片时，说明怎么让它出现，不要放一张假图 -->
        <div v-else class="hero-empty">
          <p class="hero-empty-title">还没有巡检数据</p>
          <p class="hero-empty-sub">
            到手机上拍一张，或打开
            <code>/h5</code>
            上传一张照片，这里就会显示实拍标注图和真实统计。
          </p>
        </div>
      </section>

      <!-- ============ 右：数据栏 ============ -->
      <aside class="rail">
        <div class="rate">
          <p class="rate-label">可采收率</p>
          <p class="rate-num tnum">{{ ratePercent }}<span class="pct">%</span></p>
          <p class="rate-note">达到着色期及以上的比例</p>
        </div>

        <div class="divider" />

        <div class="dist">
          <p class="dist-label">成熟度分布</p>
          <RipenessBar :counts="counts" />
          <p class="dist-total">共检出 <span class="tnum">{{ total }}</span> 个果实</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
  min-height: 100dvh;
}

/* ---- 顶栏 ----
   没有居中的大标题、没有版本号标签、没有滚动提示。
   产品名一行放在左边就够。 */
.topbar {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: var(--sp-3);
  border-bottom: 1px solid var(--color-border);
}

.app-name {
  font-size: var(--fs-subhead);
  letter-spacing: 0.02em;
}

.source {
  font-size: var(--fs-label);
  color: var(--color-text-secondary);
}

/* 示例数据要显眼，不能让人误以为是真实结果 */
.source.sample {
  color: var(--color-ripeness-2);
  border: 1px dashed currentColor;
  padding: 1px var(--sp-2);
  border-radius: var(--radius-sm);
}

/* ---- 主体：左图右数据 ----
   刻意做成 2:1 的不对称，避免最常见的"左右对称三栏大屏"。 */
.body {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--sp-6);
  flex: 1;
  align-items: start;
}

/* ---- 英雄区 ----
   ★ 必须限制高度，否则会被手机竖拍照片撑爆。
   手机照片是 1280×1714（比例 0.75），如果宽度铺满 950px 的栏，
   高度会变成 1272px，16:9 的大屏直接装不下，右栏被挤到屏幕外。
   这里把高度定死，宽度交给 aspect-ratio 反算 —— 见 AnnotatedImage 里的说明。 */
.hero {
  min-width: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.hero :deep(.wrap) {
  height: min(64vh, 620px);
  width: auto;
  max-width: 100%;
}

/* 空状态：给一个克制的高度，不要撑成一大块空地 */
.hero-empty {
  width: 100%;
  max-width: 640px;
  height: 320px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--sp-2);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  padding: var(--sp-6);
}

.hero-empty-title {
  font-size: var(--fs-subhead);
}

.hero-empty-sub {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  max-width: 28em;
}

code {
  font-family: var(--font-num);
}

/* ---- 右侧数据栏 ---- */
.rail {
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
}

.rate-label,
.dist-label {
  font-size: var(--fs-label);
  color: var(--color-text-secondary);
}

.rate-num {
  font-family: var(--font-num);
  font-size: 96px;
  line-height: 1;
  font-weight: 600;
  margin-top: var(--sp-2);
}

.pct {
  font-size: 32px;
  margin-left: 2px;
}

.rate-note {
  font-size: var(--fs-caption);
  color: var(--color-text-secondary);
  margin-top: var(--sp-2);
}

.divider {
  height: 1px;
  background: var(--color-border);
}

.dist-total {
  margin-top: var(--sp-3);
  font-size: var(--fs-label);
  color: var(--color-text-secondary);
}
</style>
