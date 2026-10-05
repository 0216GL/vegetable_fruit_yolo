/**
 * 路由表。
 *
 * 【两个表面，两套路由树】
 *   /h5/*     手机端，Operate 模式：完成一次巡检任务
 *   /screen   大屏，Persuade 模式：路演演示（电脑全屏打开）
 *
 * 两者共用同一套设计令牌和 API 层，但**不共用布局** ——
 * 它们的信息架构差别太大，硬套一个框架两边都会难用。
 *
 * 【路由懒加载】
 * 每个页面用 () => import(...) 写成动态导入。
 * 好处：首屏只下载当前页面需要的代码。大屏用到的东西
 * 不会拖慢手机上打开上传页。
 */

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 手机端是主入口 —— 用户实际是在果园里用手机拍照
  { path: '/', redirect: '/h5' },

  // ---------------------------------------------------------------------------
  // H5（手机端）
  // ---------------------------------------------------------------------------
  {
    path: '/h5',
    component: () => import('@/layouts/H5Layout.vue'),
    children: [
      {
        path: '',
        name: 'h5-upload',
        component: () => import('@/views/h5/Upload.vue'),
      },
      {
        path: 'result',
        name: 'h5-result',
        component: () => import('@/views/h5/Result.vue'),
      },
      {
        path: 'history',
        name: 'h5-history',
        component: () => import('@/views/h5/History.vue'),
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // 大屏（投影）—— 路演时在电脑上全屏打开
  // ---------------------------------------------------------------------------
  {
    path: '/screen',
    component: () => import('@/layouts/ScreenLayout.vue'),
    children: [
      {
        path: '',
        name: 'screen',
        component: () => import('@/views/screen/Dashboard.vue'),
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // 开发用：设计令牌自检页。上线前应删掉。
  // 它会实时计算成熟度色的对比度，标出不合格的色值。
  // ---------------------------------------------------------------------------
  {
    path: '/dev/tokens',
    name: 'dev-tokens',
    component: () => import('@/views/DevTokens.vue'),
  },

  // 兜底：认不出的路径回首页
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,

  // 切换页面时回到顶部，否则从长页面跳到短页面会停在奇怪的位置
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
