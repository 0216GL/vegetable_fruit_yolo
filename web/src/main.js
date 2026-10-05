/**
 * 应用入口。
 *
 * 【样式引入顺序很重要，不能随便调】
 * 先引第三方默认样式，再引我们自己的 —— 后引入的优先级更高。
 * 如果倒过来，Element Plus 的默认外观会把我们的令牌盖掉，
 * 结果就是"用了自己的设计系统，但界面还是 Element 的样子"。
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'

// 1. 第三方样式（先引入，等着被我们覆盖）
import 'element-plus/dist/index.css'

// 2. 我们自己的样式（后引入，优先级更高）
import './styles/primitives.css'
import './styles/semantic.css'
import './styles/base.css'
import './styles/element-plus.css'

import App from './App.vue'
import router from './router'

// 3. 产品名从常量读，不写死在 index.html 里（名字后期要改）
import { APP_NAME } from './config/brand.js'

document.title = APP_NAME

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
