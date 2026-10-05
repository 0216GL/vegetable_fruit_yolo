/**
 * 存放「最近一次巡检结果」。
 *
 * 【为什么需要 store，直接用路由参数不行吗】
 * 上传页拿到结果后要跳到结果页。图片文件本身很大，不适合塞进 URL；
 * 而结果对象（检测框、成熟度）更不适合。
 * 所以放在内存里，两个页面共享。
 *
 * ⚠️ 刷新页面这个 state 就没了（浏览器内存，不落盘）。
 * 结果页必须处理"没有结果"的情况 —— 见 Result.vue。
 * 这不是 bug，是设计：真正要持久化的记录由后端落库，前端不重复存一份。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useInspectionStore = defineStore('inspection', () => {
  /**
   * 最近一次结果。
   * 结构：{ result, imageUrl, plot, fileName, createdAt }
   *   result    后端返回的 AiPredictResponse
   *   imageUrl  本地图片的 object URL，用来在结果页显示原图
   *   plot      用户填的地块标签（可能为空）
   */
  const current = ref(null)

  function setResult({ result, imageUrl, plot, fileName }) {
    // 换新结果前，先把上一张图的 object URL 释放掉。
    // 不释放会一直占着内存 —— 一次性上传很多张时能看出来。
    revokeCurrent()
    current.value = {
      result,
      imageUrl,
      plot: plot || '',
      fileName: fileName || '',
      createdAt: Date.now(),
    }
  }

  function revokeCurrent() {
    if (current.value?.imageUrl) {
      URL.revokeObjectURL(current.value.imageUrl)
    }
  }

  function clear() {
    revokeCurrent()
    current.value = null
  }

  return { current, setResult, clear }
})
