/**
 * 四个成熟度等级 —— 全站唯一真源。
 *
 * 【这个文件为什么重要】
 * 它和 Java 侧的 `AiPredictResponse`、Python 侧的 `schemas.py` 是同一个思路：
 * 把"四个成熟度等级"定义在一个地方，全站都从这里读。
 *
 * 谁在读它：成熟度色带、逐果标注图、图例、统计表、历史列表、大屏。
 * 以后要加一个"过熟果"等级，或者改中文叫法，**只改这一个文件**。
 *
 * 【顺序是真实顺序，不是排版顺序】
 * 1_unripe → 2_turning → 3_coloring → 4_full 是果实的实际成熟先后。
 * 所以界面上用 1/2/3/4 做标记是**合法的**（结构本身携带信息），
 * 而不是为了好看硬加编号。
 *
 * 【颜色不写死在这里】
 * 这里只写"用哪个 CSS 变量"，具体色值在 styles/primitives.css。
 * 好处：以后要做深色大屏，只改 CSS 变量，这个文件一行不动。
 *
 * 【key 必须和模型输出完全一致】
 * 模型返回的 `ripeness` 字段就是这些 key（见 Python 端 inference.py 的
 * RIPENESS_CLASSES）。改这里等于改接口契约，必须两边同时改。
 */

import { HARVESTABLE_LEVELS } from '../config/brand.js'

/** 可采收率用的门槛。从 brand.js 取，避免两处定义对不上。 */
const HARVESTABLE_KEYS = HARVESTABLE_LEVELS

export const RIPENESS = [
  {
    key: '1_unripe',
    order: 1,
    label: '未熟',
    full: '未熟（青绿）',
    cssVar: '--color-ripeness-1',
  },
  {
    key: '2_turning',
    order: 2,
    label: '转色期',
    full: '转色期（黄橙）',
    cssVar: '--color-ripeness-2',
  },
  {
    key: '3_coloring',
    order: 3,
    label: '着色期',
    full: '着色期（橙红）',
    cssVar: '--color-ripeness-3',
  },
  {
    key: '4_full',
    order: 4,
    label: '完熟',
    full: '完熟（深红）',
    cssVar: '--color-ripeness-4',
  },
]

/** 所有 key 的数组，顺序即成熟顺序 */
export const RIPENESS_KEYS = RIPENESS.map((r) => r.key)

/** 按 key 取等级对象。取不到返回 undefined，调用方自己决定怎么兜底。 */
export function ripenessByKey(key) {
  return RIPENESS.find((r) => r.key === key)
}

/** 按 key 取简称，如 '未熟'。取不到时原样返回 key，方便发现数据异常。 */
export function ripenessLabel(key) {
  return ripenessByKey(key)?.label ?? key
}

/**
 * 把 counts 补成四个等级齐全的对象。
 *
 * 【为什么需要它】
 * 后端返回的 counts 理论上四类都有，但一旦缺了某一类（模型改了、
 * 或某类被过滤掉了），界面直接读 `counts['3_coloring']` 会拿到 undefined，
 * 页面上就会显示 "undefined"。
 * 这里统一补 0，界面代码就不用到处写 `|| 0`。
 */
export function normalizeCounts(counts) {
  const out = {}
  for (const key of RIPENESS_KEYS) {
    out[key] = counts?.[key] ?? 0
  }
  return out
}

/** 检出果实总数 */
export function totalCount(counts) {
  const c = normalizeCounts(counts)
  return RIPENESS_KEYS.reduce((sum, key) => sum + c[key], 0)
}

/**
 * 可采收率 —— 着色期及以上占总数的比例，0~1。
 *
 * ⚠️ 门槛（哪些等级算"可采收"）定义在 `config/brand.js` 的
 * HARVESTABLE_LEVELS，**那是待确认的业务规则，不是模型输出**。
 *
 * 返回 null 表示"没有检出果实"——这和"可采收率是 0%"是两回事，
 * 界面必须分开处理：一张没拍到果子的图不该显示"可采收率 0%"，
 * 那会让人以为果子全没熟。
 */
export function harvestableRate(counts) {
  const total = totalCount(counts)
  if (total === 0) return null
  const c = normalizeCounts(counts)
  const ready = HARVESTABLE_KEYS.reduce((sum, key) => sum + c[key], 0)
  return ready / total
}
