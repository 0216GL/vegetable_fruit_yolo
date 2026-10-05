<script setup>
/**
 * 上传页 —— H5 的主入口。
 *
 * 这是整条链路的起点：选图 → 上传 → 拿结果 → 跳结果页。
 * 也是**唯一一个 P1 阶段就能完整跑通的页面**（后端只需要 /inspection/predict）。
 */

import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { predictInspection } from '@/api/inspection.js'
import { useInspectionStore } from '@/stores/inspection.js'
import { APP_NAME } from '@/config/brand.js'

const router = useRouter()
const store = useInspectionStore()

// ---- 状态 ----
const file = ref(null)
const previewUrl = ref('')
const plot = ref('')
const uploading = ref(false)
const progress = ref(0)
const errorText = ref('')

const fileInput = ref(null)

const canSubmit = computed(() => !!file.value && !uploading.value)

// ---------------------------------------------------------------------------
// 选图
// ---------------------------------------------------------------------------
function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e) {
  const f = e.target.files?.[0]
  if (!f) return

  errorText.value = ''

  // 换图前释放上一张的 object URL，否则会一直占内存
  releasePreview()

  file.value = f
  previewUrl.value = URL.createObjectURL(f)
}

function releasePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

// 离开页面时如果还没提交，要把预览 URL 释放掉。
// （提交成功的话所有权已经交给 store，由 store 负责释放。）
onUnmounted(() => {
  if (!uploading.value) releasePreview()
})

function clearFile() {
  releasePreview()
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
}

// ---------------------------------------------------------------------------
// 提交
// ---------------------------------------------------------------------------
async function submit() {
  if (!canSubmit.value) return

  uploading.value = true
  progress.value = 0
  errorText.value = ''

  try {
    const result = await predictInspection(file.value, (p) => {
      progress.value = p
    })

    // 把预览图的 URL 所有权交给 store —— 这里不要再 revoke 了，
    // 否则结果页的图会变成空白。
    store.setResult({
      result,
      imageUrl: previewUrl.value,
      plot: plot.value,
      fileName: file.value.name,
    })
    previewUrl.value = '' // 已交出所有权，本地引用清掉

    router.push({ name: 'h5-result' })
  } catch (e) {
    // request.js 的拦截器已经弹过提示了，这里只负责把页面状态复位。
    // 不重复弹窗 —— 弹两次比不弹更烦。
    errorText.value = e?.message || '识别失败，请重试'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="upload">
    <header class="head">
      <div class="head-row">
        <h1>{{ APP_NAME }}</h1>
        <!-- 历史页的入口。没有这个链接的话 /h5/history 是个进不去的死页面。 -->
        <RouterLink class="history-link" :to="{ name: 'h5-history' }">
          历史
        </RouterLink>
      </div>
      <p class="sub">拍一张果园照片，看看现在能不能采</p>
    </header>

    <!-- ================= 选图 ================= -->
    <section class="picker">
      <img v-if="previewUrl" :src="previewUrl" class="preview" alt="待识别的照片" />

      <div v-else class="placeholder">
        <p>还没有选照片</p>
      </div>

      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden-input"
        @change="onFileChange"
      />

      <div class="picker-actions">
        <button type="button" class="btn btn-secondary" @click="pickFile">
          {{ previewUrl ? '换一张' : '选择照片' }}
        </button>
        <button
          v-if="previewUrl"
          type="button"
          class="btn btn-ghost"
          @click="clearFile"
        >
          移除
        </button>
      </div>
    </section>

    <!-- ================= 地块（可选） =================
         注意：这只是一个文本标签，不是"地块管理"。
         产品范围里明确不做地块的增删改查。 -->
    <section class="field">
      <label for="plot">地块（可不填）</label>
      <input
        id="plot"
        v-model="plot"
        type="text"
        maxlength="20"
        placeholder="例如：东坡地"
      />
    </section>

    <!-- ================= 进度 ================= -->
    <section v-if="uploading" class="progress-block">
      <p class="progress-label">
        正在识别{{ progress < 100 ? `，上传中 ${progress}%` : '…' }}
      </p>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progress}%` }" />
      </div>
      <p class="hint">首次识别要等模型加载，可能十几秒</p>
    </section>

    <!-- ================= 错误 =================
         说清问题 + 怎么补救。不道歉、不含糊。 -->
    <p v-if="errorText" class="error" role="alert">{{ errorText }}</p>

    <!-- ================= 提交 ================= -->
    <div class="submit-zone">
      <button
        type="button"
        class="btn btn-primary btn-block"
        :disabled="!canSubmit"
        @click="submit"
      >
        {{ uploading ? '识别中…' : '开始识别' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.upload {
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
  flex: 1;
}

.head-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
}

.head h1 {
  font-size: var(--fs-title);
}

.history-link {
  flex: none;
  display: inline-flex;
  align-items: center;
  /* 文字本身太矮，撑到最小触摸尺寸，否则在手机上很难点中 */
  min-height: var(--control-min-height);
  padding-left: var(--sp-3);
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  text-decoration: none;
}

.history-link:hover {
  color: var(--color-text-primary);
}

.sub {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  margin-top: var(--sp-1);
}

/* ---- 选图 ---- */
.preview {
  width: 100%;
  border-radius: var(--radius-md);
  display: block;
}

.placeholder {
  aspect-ratio: 4 / 3;
  display: grid;
  place-items: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
}

.hidden-input {
  display: none;
}

.picker-actions {
  display: flex;
  gap: var(--sp-2);
  margin-top: var(--sp-3);
}

/* ---- 表单 ---- */
.field {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.field label {
  font-size: var(--fs-label);
  color: var(--color-text-secondary);
}

.field input {
  min-height: var(--control-min-height);
  padding: 0 var(--sp-3);
  font: inherit;
  color: var(--color-text-primary);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

/* ---- 进度 ---- */
.progress-label {
  font-size: var(--fs-label);
  margin-bottom: var(--sp-2);
}

.progress-track {
  height: 6px;
  background: var(--color-border);
  border-radius: var(--radius-pill);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-ripeness-3);
  transition: width var(--dur-fast) linear;
}

.hint {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
  margin-top: var(--sp-2);
}

/* ---- 错误 ---- */
.error {
  color: var(--color-ripeness-4);
  font-size: var(--fs-label);
  padding: var(--sp-3);
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
}

/* ---- 按钮 ---- */
.submit-zone {
  /* 推到最底，拇指最容易够到的地方 */
  margin-top: auto;
  padding-top: var(--sp-4);
}

.btn {
  min-height: var(--control-min-height);
  padding: 0 var(--sp-4);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  font-size: var(--fs-body);
  transition: opacity var(--dur-fast) var(--ease-out);
}

.btn:active:not(:disabled) {
  opacity: 0.85;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-block {
  width: 100%;
}

.btn-primary {
  background: var(--color-text-primary);
  color: var(--color-surface);
}

.btn-secondary {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.btn-ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
</style>
