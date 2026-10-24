/**
 * 巡检相关的接口。
 *
 * 路径不带 /api 前缀 —— axios 实例的 baseURL 已经是 '/api' 了（见 request.js）。
 * 所以这里写 '/inspection/predict'，实际请求的是 '/api/inspection/predict'。
 *
 * 后端接口清单见 docs/ARCHITECTURE.md 第六节。
 */

import request from './request.js'

/**
 * 上传一张图，做「检测 + 成熟度分类」。
 *
 * @param {File} file  用户选的图片文件
 * @param {number} regionId  区域 id，后端落库用
 * @param {string} species  果品品种：'persimmon' | 'apple'
 *   后端据此选对应的检测模型 + 成熟度分类模型（两级解耦，各品种独立）。
 * @param {(percent: number) => void} [onProgress]  上传进度回调，0~100
 * @returns {Promise<object>} AiPredictResponse
 *   形状见 Java 侧 AiPredictResponse.java：
 *   { ok, species, image:{width,height}, detections:[{box,det_conf,ripeness,
 *     ripeness_label,ripeness_conf}], counts:{...}, timing:{...}, error }
 *   counts 的键跟着品种走：柿子 4 类、苹果 3 类。
 */
export function predictInspection(file, regionId, species, onProgress) {
  const form = new FormData()

  // ⚠️ 字段名必须是 'file'。
  // Java 端写的是 @RequestParam("file")，Python 端写的是 file: UploadFile = File(...)。
  // 名字对不上会直接 400："Required request part 'file' is not present"。
  form.append('file', file)

  // regionId 也一起带上，后端落库时写进 capture.region_id。
  form.append('regionId', regionId)

  // 品种：Python 端是 species: str = Form("persimmon")
  form.append('species', species || 'persimmon')

  return request.post('/inspection/predict', form, {
    // 不手动设 Content-Type —— 让浏览器自己带上 multipart 的 boundary。
    // 手动写 'multipart/form-data' 会丢掉 boundary，服务端解析不出文件，
    // 这是上传接口最常见的坑之一。

    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
}

/**
 * 区域列表 —— 上传页下拉框的数据源。
 * 后端直接返回数组 [{ id, name, remark }]，不套分页（区域就那么几条）。
 */
export function listRegions() {
  return request.get('/region/list')
}

/**
 * 历史巡检记录（分页）。—— 需要后端 P2 阶段
 */
export function listInspections(params) {
  // params 形如 { page: 1, size: 20, plot: '东坡地' }
  return request.get('/inspection/list', { params })
}

/**
 * 某次巡检的详情（含所有检测框）。—— 需要后端 P2 阶段
 */
export function getInspectionDetail(id) {
  return request.get(`/inspection/${id}`)
}

/**
 * 看板聚合数据。—— 需要后端 P4 阶段
 */
export function getStatsOverview() {
  return request.get('/stats/overview')
}

/**
 * 健康检查。这个 P1 阶段就有了，可以用来确认 AI 服务是否就绪。
 */
export function getHealth() {
  return request.get('/health')
}
