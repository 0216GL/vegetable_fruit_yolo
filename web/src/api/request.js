/**
 * axios 实例 —— 全站发请求的唯一出口。
 *
 * 【这个文件是"统一响应体"这笔投资的兑现处】
 * 后端所有接口都返回 { code, message, data } 这个结构（见 Java 侧的 R.java）。
 * 代价是后端多写了一点，回报就在这里：
 * 拦截器负责拆掉外壳、统一弹错误提示，
 * 于是**所有调用方拿到的直接就是业务数据**，不用再判 code。
 *
 * 没有这一层的话，每个页面都要写：
 *   const res = await axios.post(...)
 *   if (res.data.code === 0) { ... } else { ... }
 * 全站重复几十遍，漏一处就是一个 bug。
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  // 走 Vite 开发代理（见 vite.config.js），不写死 http://localhost:8080。
  // 好处：前端代码里全是相对路径，上线后前后端同域部署，一个字不用改。
  baseURL: '/api',

  // 超时给足。模型冷启动要十几秒，第一次推理可能等很久。
  // 这个值和 Java 侧 application.yml 的 read-timeout-ms 对齐。
  timeout: 60000,
})

// ============================================================================
// 请求拦截器
// ============================================================================
request.interceptors.request.use(
  (config) => {
    // 目前还没有登录功能。等做了鉴权，在这里统一挂 token：
    //
    //   const token = useUserStore().token
    //   if (token) config.headers.Authorization = `Bearer ${token}`
    //
    // 放这里而不是每个请求里，是为了避免漏挂、以及将来换鉴权方案时改一处。
    return config
  },
  (error) => Promise.reject(error),
)

// ============================================================================
// 响应拦截器
// ============================================================================
request.interceptors.response.use(
  // ---- HTTP 2xx ----
  (response) => {
    const body = response.data

    // 后端约定 code === 0 才是成功。
    // 注意：业务失败走的也是 HTTP 200，这是国内项目的主流做法
    // （见 persimmon/ 的 GlobalExceptionHandler 注释），所以这里必须判 code。
    if (body?.code !== 0) {
      const message = body?.message || '请求失败'
      ElMessage.error(message)
      // 往外抛，调用方可以用 try/catch 决定要不要额外处理
      // （比如"没有检出果实"不该弹错误提示，那种情况后端不会返回非 0）
      return Promise.reject(new Error(message))
    }

    // ★ 剥掉外壳：调用方直接拿到 data
    return body.data
  },

  // ---- 非 2xx，或者压根没连上 ----
  (error) => {
    // 分情况给提示。统一说"网络错误"等于没说，用户不知道该干什么。
    let message

    if (error.code === 'ECONNABORTED') {
      message = '请求超时，识别服务可能正忙，请稍后重试'
    } else if (error.response) {
      // 服务器有响应，但状态码不对
      const status = error.response.status
      if (status === 413) {
        message = '图片太大，请压缩后再上传'
      } else if (status >= 500) {
        message = '识别服务出错了，请稍后重试'
      } else {
        message = `请求失败（${status}）`
      }
    } else {
      // 连 TCP 都没建立起来
      message = '连不上服务器，请确认后端已启动'
    }

    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
