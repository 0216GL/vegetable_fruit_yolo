package org.ymg.persimmon.common;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 品种 × 成熟度的编解码 —— <b>{@code capture.ripeness} 这一列的唯一权威解释</b>。
 *
 * <p><b>为什么需要这个类：</b>数据库里只存了一列 {@code species}（品种）和一列
 * {@code ripeness}（一串逗号数字）。一串数字本身没有含义，<b>必须由品种告诉你怎么读</b>：
 *
 * <pre>
 *   species      ripeness        解读（按这个顺序切）
 *   ----------   -------------   ------------------------------------
 *   persimmon    "0,2,4,17"      未熟 0 / 转色期 2 / 着色期 4 / 完熟 17
 *   apple        "1,3,8"         未熟 1 / 转色期 3 / 成熟 8
 * </pre>
 *
 * <p>柿子 4 个数、苹果 3 个数，位置顺序不同、含义不同。这个"位置 → 等级"的对应表
 * <b>只写在这一处</b>：Service 写库、列表接口算比例、文档说明，全都从这里取。
 * 如果哪天某个品种改成 5 级，只改这个类，别的代码不用动。
 *
 * <p><b>为什么不给每个品种建一个枚举/一张表：</b>现在只有两个品种、九个等级，
 * 用 {@code Map} 常量最直观、零依赖、启动最快。真到十几个品种再抽表也不迟——
 * 那时候你才知道要抽什么。
 *
 * <p><b>要改等级名字时注意：</b>键（{@code 1_unripe} 这种）必须和 Python 端
 * {@code ai/config.py} 里的 {@code CLASS_LABELS} 保持一致，否则 {@link #encode}
 * 取不到数，会全部存成 0（不会报错，但结果错——这是最不好查的一类 bug）。
 */
public final class RipenessCodec {

    /** 柿子（项目核心品类，4 级） */
    public static final String PERSIMMON = "persimmon";

    /** 苹果（拓展品类，3 级） */
    public static final String APPLE = "apple";

    /**
     * 品种 → 等级键的有序列表。
     * <p>顺序 = {@code ripeness} 字符串里数字的顺序，从"最不熟"到"最熟"，
     * 不要随便调换，调了历史数据的含义就变了。
     */
    private static final Map<String, String[]> GRADES = new LinkedHashMap<>();

    /**
     * 品种 → 哪几个位置的果实算"可采收"。
     * <p>柿子：着色期(2) + 完熟(3) 能采；苹果：只有最高级 成熟(2) 能采。
     * <p>算 {@code readyRate} 用它，别在别处硬编码 2、3——那是上一版的坑。
     */
    private static final Map<String, int[]> READY_POSITIONS = new LinkedHashMap<>();

    /** 等级键 → 中文名（存库用键，给人看用这个） */
    private static final Map<String, String> LABELS = new LinkedHashMap<>();

    static {
        GRADES.put(PERSIMMON, new String[]{"1_unripe", "2_turning", "3_coloring", "4_full"});
        GRADES.put(APPLE, new String[]{"1_unripe", "2_turning", "3_mature"});

        READY_POSITIONS.put(PERSIMMON, new int[]{2, 3});
        READY_POSITIONS.put(APPLE, new int[]{2});

        LABELS.put("1_unripe", "未熟");
        LABELS.put("2_turning", "转色期");
        LABELS.put("3_coloring", "着色期");
        LABELS.put("4_full", "完熟");
        LABELS.put("3_mature", "成熟");

        // 注意：同一个位置在两个品种里键不同（柿子 3 号是 3_coloring，苹果 3 号是 3_mature），
        // 所以键和位置都不能混用，永远 species + 位置 一起才是完整的坐标。
    }

    private RipenessCodec() {
        // 工具类，不给 new
    }

    /** 这个品种支持不支持（不认识的一律当柿子处理，见 {@link #normalize}）。 */
    public static boolean supports(String species) {
        return species != null && GRADES.containsKey(species);
    }

    /** 不认识的品种兜底成柿子，避免历史调用方不传品种时炸掉。 */
    public static String normalize(String species) {
        return supports(species) ? species : PERSIMMON;
    }

    /** 该品种的等级键，按显示顺序。 */
    public static String[] grades(String species) {
        return GRADES.get(normalize(species));
    }

    /** 等级键 → 中文名。 */
    public static String label(String gradeKey) {
        return LABELS.getOrDefault(gradeKey, gradeKey);
    }

    /**
     * 把 AI 返回的 {@code counts} 编码成库里的那一列。
     *
     * <pre>
     *   encode("persimmon", {1_unripe:0, 2_turning:2, 3_coloring:4, 4_full:17}) → "0,2,4,17"
     *   encode("apple",     {1_unripe:1, 2_turning:3, 3_mature:8})             → "1,3,8"
     * </pre>
     *
     * <p>{@code counts} 里缺的键按 0 算（AI 少返一个键不该让整个接口失败）；
     * 传 null 也返回全 0 串。多出来的键（比如给柿子传了 {@code 3_mature}）会被忽略。
     */
    public static String encode(String species, Map<String, Integer> counts) {
        String[] grades = grades(species);
        StringBuilder sb = new StringBuilder(grades.length * 3);
        for (int i = 0; i < grades.length; i++) {
            if (i > 0) {
                sb.append(',');
            }
            Integer v = counts == null ? null : counts.get(grades[i]);
            sb.append(v == null || v < 0 ? 0 : v);
        }
        return sb.toString();
    }

    /**
     * 把库里的那一列解成数字数组。
     *
     * <p><b>为什么这里要"容错"而不是抛异常：</b>这是一列历史数据，可能存在
     * 手工改过、或老版本写进去的短串。列表接口因为一条脏数据整页 500，
     * 比"这条显示 0"糟糕得多。所以长度不够补 0、超了截断、单个格子脏了当 0。
     */
    public static int[] decode(String species, String ripeness) {
        String[] grades = grades(species);
        int[] out = new int[grades.length];
        if (ripeness == null || ripeness.isBlank()) {
            return out;
        }
        String[] parts = ripeness.split(",");
        for (int i = 0; i < out.length && i < parts.length; i++) {
            try {
                int v = Integer.parseInt(parts[i].trim());
                out[i] = Math.max(v, 0);
            } catch (NumberFormatException ignored) {
                out[i] = 0;
            }
        }
        return out;
    }

    /** 这张图一共检出多少颗果 —— 各级数量相加，不单独存。 */
    public static int total(String species, String ripeness) {
        int sum = 0;
        for (int v : decode(species, ripeness)) {
            sum += v;
        }
        return sum;
    }

    /** 可采收的颗数（柿子的着色期+完熟，苹果的成熟）。 */
    public static int readyCount(String species, String ripeness) {
        int[] counts = decode(species, ripeness);
        int[] positions = READY_POSITIONS.get(normalize(species));
        int sum = 0;
        for (int p : positions) {
            if (p < counts.length) {
                sum += counts[p];
            }
        }
        return sum;
    }

    /**
     * 可采收率（0~100 的整数）。
     *
     * <p><b>★ 多组数据汇总时先加数量再算比例，千万不要 AVG(百分比)。</b>
     * 10 颗里 9 颗可采（90%）和 100 颗里 40 颗可采（40%），
     * 正确做法是 (9+40)/(10+100)=44.5%，不是 (90+40)/2=65%。
     * 样本大小不一样，凭什么各占一半权重。
     */
    public static int readyRate(String species, String ripeness) {
        int total = total(species, ripeness);
        if (total <= 0) {
            return 0;   // 一颗都没检出：0%，别除零
        }
        return (int) Math.round(readyCount(species, ripeness) * 100.0 / total);
    }

    /**
     * 给人看的中文摘要，例如 {@code "未熟 0 / 转色期 2 / 着色期 4 / 完熟 17"}。
     * <p>接口里带上它，前端就不用自己再写一份"品种→等级名"的表了（少一处会写错的地方）。
     */
    public static String describe(String species, String ripeness) {
        String[] grades = grades(species);
        int[] counts = decode(species, ripeness);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < grades.length; i++) {
            if (i > 0) {
                sb.append(" / ");
            }
            sb.append(label(grades[i])).append(' ').append(counts[i]);
        }
        return sb.toString();
    }
}
