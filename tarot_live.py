"""塔罗牌直播辅助提词器 (Tarot Live Prompter)

Usage:
    streamlit run tarot_live.py --server.address 0.0.0.0 --server.port 8501
"""



import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

# ==================== 78 张塔罗牌 ====================
MAJOR_ARCANA = [
    "0. 愚者 The Fool",
    "1. 魔术师 The Magician",
    "2. 女祭司 The High Priestess",
    "3. 皇后 The Empress",
    "4. 皇帝 The Emperor",
    "5. 教皇 The Hierophant",
    "6. 恋人 The Lovers",
    "7. 战车 The Chariot",
    "8. 力量 Strength",
    "9. 隐士 The Hermit",
    "10. 命运之轮 Wheel of Fortune",
    "11. 正义 Justice",
    "12. 倒吊人 The Hanged Man",
    "13. 死神 Death",
    "14. 节制 Temperance",
    "15. 恶魔 The Devil",
    "16. 高塔 The Tower",
    "17. 星星 The Star",
    "18. 月亮 The Moon",
    "19. 太阳 The Sun",
    "20. 审判 Judgement",
    "21. 世界 The World",
]


def _suit(suit_cn: str, suit_en: str, element: str):
    pairs = [
        ("Ace", "一"), ("2", "二"), ("3", "三"), ("4", "四"), ("5", "五"),
        ("6", "六"), ("7", "七"), ("8", "八"), ("9", "九"), ("10", "十"),
        ("Page", "侍从"), ("Knight", "骑士"), ("Queen", "皇后"), ("King", "国王"),
    ]
    return [f"{suit_cn}{cn} {suit_en} of {en} ({element})" for en, cn in pairs]

WANDS = _suit("权杖", "Wands", "火")
CUPS = _suit("圣杯", "Cups", "水")
SWORDS = _suit("宝剑", "Swords", "风")
PENTACLES = _suit("钱币", "Pentacles", "土")

DECKS = {
    "大阿尔卡那 (大牌 22张)": MAJOR_ARCANA,
    "权杖 (火元素 14张)": WANDS,
    "圣杯 (水元素 14张)": CUPS,
    "宝剑 (风元素 14张)": SWORDS,
    "钱币 (土元素 14张)": PENTACLES,
}

# ==================== 牌阵定义 ====================
SPREADS = {
    "时间流 (过去-现在-未来)": [
        "过去:事件根源与既定影响",
        "现在:当下处境与核心能量",
        "未来:趋势走向与可能结果",
    ],
    "圣三角 (现状-阻碍-建议)": [
        "现状:当前真实状态",
        "阻碍:核心问题与挑战",
        "建议:破局方向与行动",
    ],
    "二选一 (选项A-选项B-内心倾向)": [
        "选项A:选择A的发展走向",
        "选项B:选择B的发展走向",
        "内心倾向:你潜意识更靠近哪一方",
    ],
    "身心灵 (身体-情感-精神)": [
        "身体层面:现实物质状况",
        "情感层面:内心感受与关系",
        "精神层面:灵性指引与课题",
    ],
    "恋人金字塔 (你-TA-关系)": [
        "你:你在这段关系里的能量",
        "TA:对方的真实状态与想法",
        "关系:你们之间的核心动态",
    ],
}

# ==================== 客户问题 ====================
QUESTION_TYPES = [
    "感情:单身脱单运势",
    "感情:复合可能性",
    "感情:暧昧关系走向",
    "感情:婚姻稳定度",
    "事业:当前工作发展",
    "事业:跳槽换行建议",
    "事业:创业项目运势",
    "财运:近期财富走向",
    "财运:投资决策参考",
    "学业:考试与升学",
    "健康:身心状态指引",
    "综合:本月整体运势",
]

# ==================== Prompt 模板 ====================
PROMPT_TEMPLATE = """Role: 20年经验资深塔罗师
Goal: 结合牌意、阵法位置及客户问题,提供精准、有神秘感且疗愈的直播口播解说。
Context:
  UserQuestion: {question}
  SpreadName: {spread}
  CardResults:
    - Position: {pos1}
      Card: {card1}
    - Position: {pos2}
      Card: {card2}
    - Position: {pos3}
      Card: {card3}
Requirements:
  Style: 神秘感、疗愈感、专业、关键词式
  Constraint: |
    严禁长篇铺垫与客套,总字数严格控制在 150 字左右。
    必须按以下三个短模块输出,每块 2-3 句或关键词:
    【核心能量】:3-5 个关键词概括整体场域
    【牌面暗示】:点出最关键的冲突点或象征
    【给客户的直接建议】:一句可落地的行动方向
  Format: Markdown,每模块用 ## 二级标题,关键词 **加粗**,便于直播扫视。
"""


def build_prompt(question, spread, positions, cards):
    return PROMPT_TEMPLATE.format(
        question=question,
        spread=spread,
        pos1=positions[0], card1=cards[0],
        pos2=positions[1], card2=cards[1],
        pos3=positions[2], card3=cards[2],
    )


# ==================== Streamlit UI ====================
st.set_page_config(page_title="塔罗直播提词器", page_icon="🔮", layout="wide")

# ---------- 关键 CSS:屏蔽下拉框输入法 + 大字号直播风格 ----------
st.markdown(
    """
<style>
    /* 屏蔽下拉框的搜索输入功能,彻底防止 iPad 弹出键盘 */
    div[data-baseweb="select"] input {
        caret-color: transparent !important;
        cursor: default !important;
        user-select: none !important;
    }
    /* 优化 iPad 上的点击感 */
    .stSelectbox div[role="button"] {
        cursor: pointer !important;
    }
    /* 直播风格:大字号、深紫卡片 */
    .stMarkdown p { font-size: 18px; line-height: 1.7; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #6a1b9a; }
    .reading-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #2d1b4e 100%);
        color: #f0e6ff;
        padding: 28px;
        border-radius: 14px;
        font-size: 22px !important;
        line-height: 1.9 !important;
        border: 1px solid #6a1b9a;
        white-space: pre-wrap;
    }
    .reading-box strong { color: #ffd700; }
    /* 下拉框本体放大,iPad 好点 */
    div[data-baseweb="select"] > div { min-height: 48px; font-size: 17px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🔮 塔罗牌直播辅助提词器")
st.caption("提问 → 选牌 → 一键流式生成神秘感口播稿")

# ---------- JS 巡检器:强制给所有下拉输入框加 readonly,彻底屏蔽 iPad 键盘 ----------
components.html(
    """
<script>
(function () {
    const root = window.parent.document;
    const lock = () => {
        root.querySelectorAll('input[role="combobox"]').forEach(el => {
            el.setAttribute('readonly', 'true');
            el.setAttribute('inputmode', 'none');
            el.setAttribute('autocomplete', 'off');
            el.blur && el.blur();
        });
        root.querySelectorAll('div[data-baseweb="select"] input').forEach(el => {
            el.setAttribute('readonly', 'true');
            el.setAttribute('inputmode', 'none');
        });
    };
    lock();
    setInterval(lock, 500);
})();
</script>
""",
    height=0,
)

# ---------- 侧边栏:API 配置 ----------
with st.sidebar:
    st.header("⚙️ API 配置")
    api_key = st.text_input("API Key", type="password", key="api_key",
                            help="OpenAI 兼容接口的 Key")
    base_url = st.text_input("Base URL", value="https://api.openai.com/v1",
                             help="可填 OpenAI / DeepSeek / 月之暗面 等兼容地址")
    model_name = st.text_input("模型名", value="gpt-4o-mini")
    temperature = st.slider("发挥度 (Temperature)", 0.0, 1.5, 0.85, 0.05)
    st.divider()
    st.markdown("**💡 提示**\n\n抽牌后点底部 *生成口播* 按钮即可。")

# ---------- 提问 + 牌阵 ----------
col_q, col_s = st.columns(2)
with col_q:
    st.subheader("① 客户问题")
    question = st.selectbox("问题类型", QUESTION_TYPES, key="q")
    custom_q = st.text_input("补充细节(可选)", placeholder="例:对方天秤男,认识3个月")

with col_s:
    st.subheader("② 选择牌阵")
    spread_name = st.selectbox("牌阵", list(SPREADS.keys()), key="sp")
    positions = SPREADS[spread_name]

st.divider()

# ---------- 抽牌区:三列并排 ----------
st.subheader("③ 动态抽牌(三列并排,iPad 横屏一眼看全)")
cols = st.columns([1, 1, 1])
chosen_cards = []
for i, (col, pos_meaning) in enumerate(zip(cols, positions)):
    with col:
        st.markdown(f"**位置 {i+1}**")
        st.caption(f"📍 {pos_meaning}")
        deck = st.selectbox("牌组", list(DECKS.keys()), key=f"deck_{i}")
        card = st.selectbox("具体卡牌", DECKS[deck], key=f"card_{i}")
        orient = st.radio("正逆位", ["正位", "逆位"], horizontal=True, key=f"o_{i}")
        chosen_cards.append(f"{card} [{orient}]")

st.divider()

# ---------- 拼 Prompt ----------
final_question = f"{question}({custom_q})" if custom_q else question
prompt_text = build_prompt(final_question, spread_name, positions, chosen_cards)

with st.expander("🔍 查看完整 Prompt"):
    st.code(prompt_text, language="yaml")

# ---------- 流式生成 ----------
if st.button("✨ 生成直播口播稿", type="primary", use_container_width=True):
    if not api_key:
        st.error("请先在左侧填写 API Key")
    else:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            st.success("解读中(流式输出)↓")
            placeholder = st.empty()
            buffer = ""
            stream = client.chat.completions.create(
                model=model_name,
                temperature=temperature,
                max_tokens=300,
                stream=True,
                messages=[
                    {"role": "system", "content": "你是一位20年经验的资深塔罗师,擅长直播口播。"},
                    {"role": "user", "content": prompt_text},
                ],
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    buffer += delta
                    placeholder.markdown(
                        f'<div class="reading-box">{buffer}▌</div>',
                        unsafe_allow_html=True,
                    )
            placeholder.markdown(
                f'<div class="reading-box">{buffer}</div>',
                unsafe_allow_html=True,
            )
            st.download_button("📥 下载文本", buffer, file_name="tarot_reading.md")
        except Exception as e:
            st.error(f"调用失败: {e}")
