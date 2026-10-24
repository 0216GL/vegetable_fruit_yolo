<script setup>
/**
 * 设计令牌自检页（开发用，不对用户开放）
 *
 * 【它解决一个真实问题】
 * primitives.css 里那些成熟度色，是我按经验估的，没有用工具实测过。
 * "估"在这个品类里很危险：橙色放在浅绿底上，肉眼看着清楚，
 * 实际对比度可能只有 2.5:1，低于无障碍要求的 3:1。
 *
 * 所以这个页面**在浏览器里实时计算真实对比度**并标出不合格的。
 * 打开它就知道色值能不能用，不用另外装工具。
 *
 * 顺带检查：字号梯度、间距刻度、数字等宽、焦点环、文字选中色。
 *
 * ⚠️ 这是开发工具，上线前应该删掉或加访问限制。
 */

import { ref, onMounted } from 'vue'

// ============================================================================
// 对比度计算（WCAG 2.x 公式）
// ============================================================================

/** 单个 sRGB 通道线性化 */
function linearize(channel8bit) {
  const c = channel8bit / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

/** 把 #rrggbb 转成相对亮度 */
function relativeLuminance(hex) {
  const h = hex.trim().replace('#', '')
  if (h.length !== 6) return null
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
}

/** 两色对比度，返回 1~21 的比值 */
function contrastRatio(hexA, hexB) {
  const la = relativeLuminance(hexA)
  const lb = relativeLuminance(hexB)
  if (la === null || lb === null) return null
  const hi = Math.max(la, lb)
  const lo = Math.min(la, lb)
  return (hi + 0.05) / (lo + 0.05)
}

// ============================================================================
// 读取真实的令牌值
// ============================================================================
// 注意：自定义属性不会被浏览器解析成最终值 —— 读 --color-ripeness-1
// 拿到的会是字符串 "var(--hue-unripe-on-light)"。
// 所以要拿真实色值，必须读最底层的原始令牌。

const tokens = ref(null)

function readHex(name) {
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim()
  // 万一是 var(...) 链，说明读错层了，返回 null 让页面显示异常而不是显示错的数
  return raw.startsWith('#') ? raw : null
}

onMounted(() => {
  const paper = readHex('--paper')
  const bark = readHex('--bark')

  const lightColors = [
    { key: '1_unripe', label: '未熟', hex: readHex('--hue-unripe-on-light') },
    { key: '2_turning', label: '转色期', hex: readHex('--hue-turning-on-light') },
    { key: '3_coloring', label: '着色期', hex: readHex('--hue-coloring-on-light') },
    { key: '4_full', label: '完熟', hex: readHex('--hue-full-on-light') },
  ]

  const darkColors = [
    { key: '1_unripe', label: '未熟', hex: readHex('--hue-unripe-on-dark') },
    { key: '2_turning', label: '转色期', hex: readHex('--hue-turning-on-dark') },
    { key: '3_coloring', label: '着色期', hex: readHex('--hue-coloring-on-dark') },
    { key: '4_full', label: '完熟', hex: readHex('--hue-full-on-dark') },
  ]

  const textPairs = [
    { name: '正文 on 浅底', fg: readHex('--ink'), bg: paper, need: 4.5 },
    { name: '次要文字 on 浅底', fg: readHex('--ink-2'), bg: paper, need: 4.5 },
    { name: '正文 on 深底', fg: readHex('--ink-on-dark'), bg: bark, need: 4.5 },
    { name: '次要文字 on 深底', fg: readHex('--ink-2-on-dark'), bg: bark, need: 4.5 },
  ]

  tokens.value = {
    paper,
    bark,
    light: lightColors.map((c) => ({
      ...c,
      ratio: contrastRatio(c.hex, paper),
      // 图形元素门槛是 3:1（WCAG 1.4.11 非文本对比度）
      need: 3,
    })),
    dark: darkColors.map((c) => ({
      ...c,
      ratio: contrastRatio(c.hex, bark),
      need: 3,
    })),
    text: textPairs.map((t) => ({
      ...t,
      ratio: contrastRatio(t.fg, t.bg),
    })),
  }
})

// 字号刻度
const typeScale = [
  { token: '--fs-caption', size: '12px', use: '图注、次要说明' },
  { token: '--fs-label', size: '14px', use: '标签' },
  { token: '--fs-body', size: '16px', use: '正文（基准，不许更小）' },
  { token: '--fs-subhead', size: '20px', use: '小标题' },
  { token: '--fs-title', size: '26px', use: '页面标题' },
  { token: '--fs-display', size: '40px', use: '大屏数字' },
]

const spacingScale = ['--sp-1', '--sp-2', '--sp-3', '--sp-4', '--sp-6', '--sp-8']
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1>设计令牌自检</h1>
      <p class="sub">
        开发工具。对比度是浏览器实时算的，不是写死的数字。
        标红的表示不达标。
      </p>
    </header>

    <template v-if="tokens">
      <!-- ================= 成熟度色：浅色面 ================= -->
      <section>
        <h2>成熟度色 · 浅色面（H5）</h2>
        <p class="hint">底色 <code>{{ tokens.paper }}</code>，图形元素门槛 3:1</p>
        <ul class="swatches">
          <li v-for="c in tokens.light" :key="c.key" class="swatch">
            <span class="chip" :style="{ background: c.hex }" />
            <div class="meta">
              <span class="name">{{ c.label }}</span>
              <span class="hex tnum">{{ c.hex }}</span>
              <span class="ratio tnum" :class="{ bad: c.ratio < c.need }">
                {{ c.ratio.toFixed(2) }}:1
                <template v-if="c.ratio < c.need">✗ 不达标</template>
                <template v-else>✓</template>
              </span>
            </div>
          </li>
        </ul>
      </section>

      <!-- ================= 成熟度色：深色面 ================= -->
      <section class="on-dark surface-screen">
        <h2>成熟度色 · 深色面（大屏）</h2>
        <p class="hint">底色 <code>{{ tokens.bark }}</code>，图形元素门槛 3:1</p>
        <ul class="swatches">
          <li v-for="c in tokens.dark" :key="c.key" class="swatch">
            <span class="chip" :style="{ background: c.hex }" />
            <div class="meta">
              <span class="name">{{ c.label }}</span>
              <span class="hex tnum">{{ c.hex }}</span>
              <span class="ratio tnum" :class="{ bad: c.ratio < c.need }">
                {{ c.ratio.toFixed(2) }}:1
                <template v-if="c.ratio < c.need">✗ 不达标</template>
                <template v-else>✓</template>
              </span>
            </div>
          </li>
        </ul>
      </section>

      <!-- ================= 文字对比度 ================= -->
      <section>
        <h2>文字对比度</h2>
        <p class="hint">正文门槛 4.5:1</p>
        <ul class="swatches">
          <li v-for="t in tokens.text" :key="t.name" class="swatch">
            <div class="meta">
              <span class="name">{{ t.name }}</span>
              <span class="hex tnum">{{ t.fg }} / {{ t.bg }}</span>
              <span class="ratio tnum" :class="{ bad: t.ratio < t.need }">
                {{ t.ratio.toFixed(2) }}:1
                <template v-if="t.ratio < t.need">✗ 不达标</template>
                <template v-else>✓</template>
              </span>
            </div>
          </li>
        </ul>
      </section>
    </template>

    <p v-else class="hint">
      读不到令牌值。检查 main.js 里三个 CSS 是否都引入了。
    </p>

    <!-- ================= 字号刻度 ================= -->
    <section>
      <h2>字号刻度</h2>
      <ul class="scale">
        <li v-for="t in typeScale" :key="t.token">
          <span class="sample" :style="{ fontSize: t.size }">柿子成熟度 62%</span>
          <span class="token tnum">{{ t.token }} · {{ t.size }}</span>
          <span class="use">{{ t.use }}</span>
        </li>
      </ul>
    </section>

    <!-- ================= 间距刻度 ================= -->
    <section>
      <h2>间距刻度</h2>
      <ul class="scale">
        <li v-for="s in spacingScale" :key="s">
          <span class="bar" :style="{ width: `var(${s})` }" />
          <span class="token">{{ s }}</span>
        </li>
      </ul>
    </section>

    <!-- ================= 浏览器自带部分 ================= -->
    <section>
      <h2>浏览器自带部分</h2>
      <p class="hint">这些不是我们画的，但用户天天看到。全部接管过。</p>
      <p class="sel-test">
        用鼠标选中这句话，看选中色是不是从我们的配色来的。
      </p>
      <p>
        <button class="btn">按 Tab 键把焦点移到这里</button>
        <span class="hint">　焦点环应该是橙色，不是浏览器默认的蓝。</span>
      </p>
      <p class="tnum">
        数字等宽：<span>1</span><span>1</span><span>1</span><span>1</span>
        &nbsp;vs&nbsp;
        <span>8</span><span>8</span><span>8</span><span>8</span>
        <span class="hint">　应该一样宽，数值跳动时不会左右抖。</span>
      </p>
    </section>
  </div>
</template>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: var(--sp-8) var(--sp-4) calc(var(--sp-8) * 2);
}

.page-head h1 {
  font-size: var(--fs-title);
  margin-bottom: var(--sp-2);
}

.sub,
.hint {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
}

section + section {
  margin-top: var(--sp-8);
}

h2 {
  font-size: var(--fs-subhead);
  margin-bottom: var(--sp-3);
  padding-bottom: var(--sp-2);
  border-bottom: 1px solid var(--color-border);
}

code {
  font-family: var(--font-num);
  font-size: 0.9em;
}

/* ---- 色卡 ---- */
.swatches {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--sp-2);
}

.swatch {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-height: var(--control-min-height);
}

.chip {
  width: 56px;
  height: 36px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

.meta {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.name {
  min-width: 4em;
}

.hex {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
}

.ratio {
  font-size: var(--fs-label);
}

.ratio.bad {
  color: var(--color-ripeness-4);
  font-weight: 600;
}

/* 深色面的那一块，用 .surface-screen 覆盖令牌即可 —— 这里不用改任何东西 */
.on-dark {
  background: var(--color-surface);
  color: var(--color-text-primary);
  padding: var(--sp-4);
  border-radius: var(--radius-md);
}

.on-dark h2 {
  border-color: var(--color-border);
}

/* ---- 刻度 ---- */
.scale {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--sp-2);
}

.scale li {
  display: flex;
  align-items: baseline;
  gap: var(--sp-4);
  flex-wrap: wrap;
}

.sample {
  flex: 1;
  min-width: 12em;
}

.token {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
}

.use {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
}

.bar {
  display: inline-block;
  height: 10px;
  background: var(--color-ripeness-3);
  border-radius: var(--radius-sm);
}

/* ---- 浏览器自带部分 ---- */
.sel-test {
  margin-bottom: var(--sp-3);
}

.btn {
  min-height: var(--control-min-height);
  padding: 0 var(--sp-4);
  background: var(--color-text-primary);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-sm);
}
</style>
