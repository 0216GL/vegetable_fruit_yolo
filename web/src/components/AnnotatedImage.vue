<script setup>
/**
 * 逐果标注图 —— 在实拍照片上画出每个果实的检测框和成熟度。
 *
 * 【这个是前端最难的一块，难点在坐标系】
 * 后端返回的 box 是 [x1, y1, x2, y2]，单位是**原图的像素**
 * （比如 1280×1714 的照片上，某个框是 [392, 754, 833, 1129]）。
 * 而页面上图片是缩放显示的（手机屏幕才 375 宽）。
 * 两者不是一个坐标系，必须换算，否则框会跑偏。
 *
 * 【换算方式：用百分比，不用像素】
 * 直觉做法是算出缩放比例 scale = 显示宽 / 原图宽，再把每个坐标乘上去。
 * 但那样一改窗口大小就得全部重算，而且离开 ResizeObserver 就会错。
 *
 * 更稳的做法是把坐标**归一化**：
 *     left  = x1 / 原图宽   →  CSS 里写成百分比
 *     width = (x2-x1) / 原图宽
 * 这样框的位置和图片显示多大**完全无关**，窗口怎么变都不会偏，
 * 一行 ResizeObserver 都不用写。CSS 自己会算。
 *
 * 那 ResizeObserver 还用不用？用，但只用来算**标签的字号**：
 * 图缩小的时候，固定字号的标签会盖住大半张图。
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ripenessByKey } from '@/utils/ripeness.js'

const props = defineProps({
  /** 图片地址（本地 object URL 或后端地址） */
  src: { type: String, required: true },

  /** 后端返回的 detections 数组 */
  detections: { type: Array, default: () => [] },

  /**
   * 原图宽高 —— **必须用后端返回的 image.width/height**，
   * 不要用 <img> 的 naturalWidth。
   * 原因：box 坐标是后端解码后的坐标系，必须和它同源。
   * 万一浏览器解码和后端有差异（旋转信息、EXIF 等），两套数字就对不上了。
   */
  imageWidth: { type: Number, default: 0 },
  imageHeight: { type: Number, default: 0 },

  alt: { type: String, default: '巡检照片' },
})

// ---------------------------------------------------------------------------
// 尺寸兜底：万一后端没给 image 尺寸，就用图片自身的
// ---------------------------------------------------------------------------
const naturalW = ref(0)
const naturalH = ref(0)

const w = computed(() => props.imageWidth || naturalW.value)
const h = computed(() => props.imageHeight || naturalH.value)

function onImgLoad(e) {
  naturalW.value = e.target.naturalWidth
  naturalH.value = e.target.naturalHeight
}

// ---------------------------------------------------------------------------
// 标签字号：跟着容器宽度缩
// ---------------------------------------------------------------------------
const wrapEl = ref(null)
const wrapWidth = ref(0)

let ro = null
onMounted(() => {
  if (!wrapEl.value) return
  ro = new ResizeObserver((entries) => {
    wrapWidth.value = entries[0].contentRect.width
  })
  ro.observe(wrapEl.value)
  wrapWidth.value = wrapEl.value.clientWidth
})

onUnmounted(() => {
  // 一定要断开，否则组件销毁后回调还在跑
  ro?.disconnect()
})

/**
 * 宽高比，写进 CSS 的 aspect-ratio。
 *
 * 【为什么必须有这个】
 * 手机竖拍的柿子照片是 1280×1714（比例 0.75）。如果只写 width:100%，
 * 在大屏那种 950px 宽的栏里，图片高度会变成 1272px —— 直接把 16:9 的
 * 大屏撑爆，右栏被挤到屏幕外面去。
 *
 * 有了 aspect-ratio，父容器就能用 max-height / height 去限制它：
 * 高度定死之后，宽度会按比例自动算出来，**框的百分比坐标依然对得准**。
 *
 * 兜底 4/3：后端没给 image 尺寸、图片又还没加载完的时候用。
 */
const aspectRatio = computed(() => {
  if (!w.value || !h.value) return '4 / 3'
  return `${w.value} / ${h.value}`
})

const labelFontSize = computed(() => {
  // 容器越窄，标签越小；下限 10px 保证还能看清
  const size = wrapWidth.value / 26
  return `${Math.min(14, Math.max(10, size))}px`
})

// ---------------------------------------------------------------------------
// 计算每个框的位置（归一化）
// ---------------------------------------------------------------------------
const boxes = computed(() => {
  if (!w.value || !h.value) return []

  return props.detections
    .map((d, i) => {
      const box = d.box
      if (!Array.isArray(box) || box.length !== 4) return null

      const [x1, y1, x2, y2] = box
      const level = ripenessByKey(d.ripeness)

      return {
        key: i,
        // 归一化成百分比 —— 见文件头说明，这是不跑偏的关键
        left: `${(x1 / w.value) * 100}%`,
        top: `${(y1 / h.value) * 100}%`,
        width: `${((x2 - x1) / w.value) * 100}%`,
        height: `${((y2 - y1) / h.value) * 100}%`,

        // 认不出的等级用中性色，不硬套一个错的颜色
        color: `var(${level?.cssVar ?? '--color-text-secondary'})`,
        label: `${level?.label ?? d.ripeness} ${Math.round((d.ripeness_conf ?? 0) * 100)}%`,

        // 逐个出现的动画延迟，见 style 里的 animation-delay
        delay: `${i * 60}ms`,
      }
    })
    .filter(Boolean)
})
</script>

<template>
  <div ref="wrapEl" class="wrap" :style="{ aspectRatio }">
    <img
      :src="src"
      :alt="alt"
      class="photo"
      @load="onImgLoad"
    />

    <!--
      每个框一个绝对定位的 span。
      纯展示元素，不加 tabindex —— 逐果信息在下面的清单里，
      键盘用户不需要在这里走一遍。
    -->
    <span
      v-for="b in boxes"
      :key="b.key"
      class="box"
      :style="{
        left: b.left,
        top: b.top,
        width: b.width,
        height: b.height,
        borderColor: b.color,
        animationDelay: b.delay,
      }"
    >
      <span
        class="label"
        :style="{ background: b.color, fontSize: labelFontSize }"
      >{{ b.label }}</span>
    </span>
  </div>
</template>

<style scoped>
.wrap {
  position: relative;
  width: 100%;
  /* aspect-ratio 由 JS 按原图宽高写进来（见 script 里的 aspectRatio）。
     这样父容器可以用 height 限制它，而框的百分比坐标不受影响。 */
  background: var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.photo {
  display: block;
  width: 100%;
  height: 100%;
  /* 容器比例 = 图片比例，所以 contain 和 fill 等价；
     写 contain 是防止后端给的宽高和真实图片对不上时把图片拉变形。 */
  object-fit: contain;
}

.box {
  position: absolute;
  border: 2px solid;
  border-radius: 2px;
  box-sizing: border-box;
  /* 框本身不接收点击，否则会挡住图片的其它交互 */
  pointer-events: none;

  /* 结果出现时逐个画入 —— 全局唯一的动效，见 FRONTEND_DESIGN.md 第九节 */
  animation: box-in var(--dur-slow) var(--ease-out) both;

  /* 从"已经可见"的状态出发：不要先隐藏再出现，
     否则一旦动画没跑（比如用户开了减少动态效果），元素就永远不显示了。
     base.css 里已全局处理 prefers-reduced-motion。 */
  opacity: 1;
}

@keyframes box-in {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.label {
  position: absolute;
  /* 标签放在框的【内侧】左上角。
     为什么不放在框外面：果实长在图片顶边时，框外的标签会被容器裁掉。
     放内侧任何位置都不会被裁，代价是遮住一点点果实，可以接受。 */
  top: 0;
  left: 0;
  padding: 1px 4px;
  border-radius: 2px 0 2px 0;
  color: var(--color-text-inverse);
  line-height: 1.4;
  white-space: nowrap;
  font-family: var(--font-num);
}
</style>
