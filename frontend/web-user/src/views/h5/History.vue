<script setup>
/**
 * 历史记录页。
 *
 * ⚠️ 依赖后端 P2 阶段的 `GET /api/inspection/list`，**该接口目前不存在**。
 * 所以这个页面必须能优雅地表达"功能还没上线"，而不是白屏或者报一堆错。
 *
 * 【为什么要专门处理这个】
 * 后端接口没就绪是开发期的常态。如果一个页面在这种情况下直接崩了，
 * 演示的时候会很难看。把"未就绪"当成一个正常状态来设计，
 * 是在真实项目里必须养成的习惯。
 */

import { ref, onMounted } from 'vue'
import { listInspections } from '@/api/inspection.js'
import { ripenessLabel } from '@/utils/ripeness.js'

const loading = ref(true)
const errorText = ref('')
const notReady = ref(false)
const items = ref([])

async function load() {
  loading.value = true
  errorText.value = ''
  notReady.value = false

  try {
    const data = await listInspections({ page: 1, size: 20 })
    // 后端可能返回 { list: [], total: 0 } 或者直接一个数组，两种都兜住
    items.value = Array.isArray(data) ? data : data?.list ?? []
  } catch (e) {
    // 404 / 501 说明接口还没实现 —— 这是"未就绪"，不是"出错"
    const status = e?.response?.status
    if (status === 404 || status === 501) {
      notReady.value = true
    } else {
      errorText.value = e?.message || '加载失败'
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="history">
    <header class="head">
      <h1>历史巡检</h1>
      <p class="sub">每一次识别的记录</p>
    </header>

    <!-- 加载中：用骨架而不是转圈 —— 骨架能预示内容形状，转圈不能 -->
    <div v-if="loading" class="skeletons">
      <div v-for="i in 3" :key="i" class="skeleton" />
    </div>

    <!-- 接口未就绪 -->
    <div v-else-if="notReady" class="state">
      <p class="state-title">记录功能还没上线</p>
      <p class="state-sub">
        后端接口 <code>/api/inspection/list</code> 属于 P2 阶段，目前还没实现。
        等巡检记录能落库之后，这里会显示每一次识别的历史。
      </p>
    </div>

    <!-- 出错 -->
    <div v-else-if="errorText" class="state">
      <p class="state-title">加载失败</p>
      <p class="state-sub">{{ errorText }}</p>
      <button type="button" class="btn" @click="load">重试</button>
    </div>

    <!-- 空 -->
    <div v-else-if="!items.length" class="state">
      <p class="state-title">还没有巡检记录</p>
      <p class="state-sub">拍第一张照片开始。</p>
      <router-link class="btn" :to="{ name: 'h5-upload' }">去拍一张</router-link>
    </div>

    <!-- 列表 -->
    <ul v-else class="list">
      <li v-for="it in items" :key="it.id" class="item">
        <div class="item-main">
          <span class="plot">{{ it.regionName || '未知区域' }}</span>
          <span class="time tnum">{{ it.capturedAt }}</span>
        </div>
        <div class="item-side">
          <span class="count tnum">{{ it.total ?? 0 }} 个</span>
          <span v-if="it.readyRate != null" class="rate tnum">
            可采收 {{ it.readyRate }}%
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.history {
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
  flex: 1;
}

.head h1 {
  font-size: var(--fs-title);
}

.sub {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  margin-top: var(--sp-1);
}

/* ---- 骨架 ---- */
.skeletons {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.skeleton {
  height: 64px;
  border-radius: var(--radius-sm);
  background: var(--color-border);
  opacity: 0.6;
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 0.7; }
}

/* ---- 各种状态 ---- */
.state {
  margin: auto 0;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  align-items: center;
}

.state-title {
  font-size: var(--fs-subhead);
}

.state-sub {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  max-width: 34em;
}

code {
  font-family: var(--font-num);
  font-size: 0.9em;
}

/* ---- 列表 ---- */
.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-3) 0;
  border-bottom: 1px solid var(--color-border);
  min-height: var(--control-min-height);
}

.item-main {
  display: flex;
  flex-direction: column;
}

.plot {
  font-size: var(--fs-body);
}

.time {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
}

.item-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.count {
  color: var(--color-text-secondary);
  font-size: var(--fs-label);
}

.rate {
  color: var(--color-text-secondary);
  font-size: var(--fs-caption);
}

/* ---- 按钮 ---- */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--control-min-height);
  padding: 0 var(--sp-4);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
  text-decoration: none;
  font-size: var(--fs-body);
}
</style>
