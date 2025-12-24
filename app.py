import streamlit as st
import pandas as pd
import plotly.express as px
import os
import base64
import requests
import numpy as np
import json


CORE_150_COLS = ["语文", "数学", "英语"]
ELECTIVE_FUFEN_COLS = [
    "历史赋分",
    "地理赋分",
    "政治赋分",
    "物理赋分",
    "化学赋分",
    "生物赋分",
    "技术赋分",
]
ELECTIVE_SUBJECTS = ["历史", "地理", "政治", "物理", "化学", "生物", "技术"]

DEFAULT_AI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_AI_MODEL = "qwen-plus"

# 设置页面配置
st.set_page_config(
    page_title="高考数据分析看板",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 读取字体文件并转换为 Base64
@st.cache_data
def get_font_base64(font_path):
    with open(font_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# 尝试加载字体
app_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(app_dir, "static", "京華老宋体v3.0.ttf")
font_base64 = ""
font_loaded = False
font_error = None

# 说明：在 Streamlit Cloud 上把大字体文件以 Base64 内嵌到 CSS，
# 可能导致首屏传输内容过大，触发 WebSocket 断开，从而表现为页面一直加载。
# 因此默认仅在字体较小或显式开启时才进行内嵌。
EMBED_FONT_MAX_BYTES = 200_000  # 约 200KB
embed_font_for_css = os.environ.get("GAOKAO_EMBED_FONT", "0") == "1"
try:
    if os.path.exists(font_path):
        font_size = os.path.getsize(font_path)
        if embed_font_for_css or font_size <= EMBED_FONT_MAX_BYTES:
            font_base64 = get_font_base64(font_path)
            font_loaded = bool(font_base64)
        else:
            # 字体存在但不内嵌（使用后备字体），以提升线上稳定性
            font_loaded = False
    else:
        font_error = f"字体文件未找到: {font_path}"
except Exception as e:
    font_error = f"字体加载失败: {e}"

font_face_css = ""
if font_loaded:
    font_face_css = f"""
    /* 引入本地字体 (Base64 嵌入) */
    @font-face {{
        font-family: 'GlobalFont';
        src: url('data:font/ttf;base64,{font_base64}') format('truetype');
    }}
    """

# 自定义 CSS 美化
st.markdown(f"""
    <style>
    {font_face_css}

    /* 全局字体优化 */
    html, body, .stApp, h1, h2, h3, h4, h5, h6, p, input, label, textarea {{
        font-family: 'GlobalFont', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }}
    
    /* 标题样式 */
    h1 {{
        color: #1E88E5;
        font-weight: 700;
    }}
    h2 {{
        color: #424242;
        border-bottom: 2px solid #1E88E5;
        padding-bottom: 10px;
    }}
    h3 {{
        color: #616161;
    }}
    
    /* 指标卡片样式 */
    div[data-testid="stMetric"] {{
        background-color: #F5F5F5;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        border-left: 5px solid #1E88E5;
    }}
    
    /* 侧边栏美化 */
    section[data-testid="stSidebar"] {{
        background-color: #f8f9fa;
    }}
    
    /* 按钮样式 */
    .stButton>button {{
        border-radius: 20px;
        font-weight: bold;
    }}
    </style>
""", unsafe_allow_html=True)

# 标题区域
col_header1, col_header2 = st.columns([1, 5])
with col_header1:
    # 使用本地图片，如果不存在则使用 emoji
    logo_path = os.path.join(app_dir, "static", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.markdown("# 🎓")
with col_header2:
    st.title("高考模拟数据与志愿填报分析系统")
    st.markdown("### 🚀 智能分析 · 科学填报 · 模拟录取")

st.markdown("---")

# 数据加载函数 (使用缓存提高性能)
def _data_cache_buster() -> float:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(app_dir, "data")
    candidates = [
        "赋分后的高考模拟数据_with_sciences.csv",
        "赋分后的高考模拟数据.csv",
        "高考考生位次.csv",
        "招生计划.csv",
        "志愿填报结果.csv",
    ]
    mtimes = []
    for fn in candidates:
        path = os.path.join(base_path, fn)
        if os.path.exists(path):
            try:
                mtimes.append(os.path.getmtime(path))
            except OSError:
                pass
    return float(max(mtimes)) if mtimes else 0.0


@st.cache_data
def load_data(cache_buster: float):
    # 确保从脚本所在目录读取资源，避免因启动目录不同导致找不到 data/static
    app_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(app_dir, "data")
    
    # 1. 加载成绩数据（优先使用带三科的文件，如果存在）
    candidate_files = [
        "赋分后的高考模拟数据_with_sciences.csv",
        "赋分后的高考模拟数据.csv",
    ]
    score_file = None
    for fn in candidate_files:
        path = os.path.join(base_path, fn)
        if os.path.exists(path):
            score_file = path
            break

    if score_file:
        df_score = pd.read_csv(score_file)
        # 计算总成绩（浙江3+3）：语数英原始分(150) + 选考等级分(100)中的最高三门
        for c in CORE_150_COLS:
            if c not in df_score.columns:
                st.error(f"未找到成绩列: {c}")
                return None, None, None, None

        main = df_score[CORE_150_COLS].apply(pd.to_numeric, errors="coerce")
        elective_cols = [c for c in ELECTIVE_FUFEN_COLS if c in df_score.columns]

        if elective_cols:
            elective = df_score[elective_cols].apply(pd.to_numeric, errors="coerce")
            vals = elective.to_numpy(dtype=float)
            vals = np.where(np.isnan(vals), -np.inf, vals)
            top3 = np.sort(vals, axis=1)[:, -3:]
            top3_sum = np.where(np.isneginf(top3), 0.0, top3).sum(axis=1)
        else:
            top3_sum = 0.0

        df_score["总成绩"] = main.sum(axis=1) + top3_sum
    else:
        st.error(f"未找到成绩文件（尝试过: {candidate_files}）")
        return None, None, None, None

    # 2. 加载位次数据
    rank_file = os.path.join(base_path, "高考考生位次.csv")
    if os.path.exists(rank_file):
        df_rank = pd.read_csv(rank_file)
    else:
        df_rank = None

    # 3. 加载招生计划
    plan_file = os.path.join(base_path, "招生计划.csv")
    if os.path.exists(plan_file):
        df_plan = pd.read_csv(plan_file)
    else:
        df_plan = None

    # 4. 加载志愿填报结果 (用于录取模拟)
    vol_file = os.path.join(base_path, "志愿填报结果.csv")
    if os.path.exists(vol_file):
        df_vol = pd.read_csv(vol_file)
    else:
        df_vol = None
        
    return df_score, df_rank, df_plan, df_vol

# 加载数据（cache_buster 用于当 CSV 更新后自动刷新缓存）
df_score, df_rank, df_plan, df_vol = load_data(_data_cache_buster())

if df_score is not None:
    # 侧边栏 - 全局筛选
    with st.sidebar:
        st.header("🔍 控制面板")
        st.info("欢迎使用高考数据分析系统。请在下方选择筛选条件。")
        
        # 假设数据中有班级字段，如果没有则跳过
        if '班级' in df_score.columns:
            selected_class = st.multiselect(
                "🏫 选择班级",
                options=df_score['班级'].unique(),
                default=df_score['班级'].unique()
            )
            # 过滤数据
            df_filtered = df_score[df_score['班级'].isin(selected_class)]
        else:
            df_filtered = df_score
            
        st.markdown("---")
        st.markdown("### 📊 数据概览")
        st.write(f"当前展示人数: **{len(df_filtered)}**")
        st.progress(len(df_filtered) / len(df_score))

        st.markdown("---")
        st.markdown("### 🤖 AI 助手")

        default_system_prompt = (
            "你是‘浙江 2025 高考模拟与志愿填报’AI 助手。\n"
            "环境约束与背景：\n"
            "- 浙江新高考 3+3，总分 750。统考：语文/数学/外语各 150（原始分）。\n"
            "- 选考：历史/地理/政治/物理/化学/生物/技术，考生只选 3 门，每门满分 100（等级赋分）。\n"
            "- 当前系统内的成绩与志愿数据为模拟数据；你的建议仅供参考，不替代官方信息与个人咨询。\n\n"
            "回答规则：\n"
            "- 优先给出可执行步骤与检查点；涉及分数/位次/志愿时，先说明使用了哪些输入与假设。\n"
            "- 如用户未提供必要信息（如省份、科目组合、分数/位次、目标地区/专业），先问 1-3 个关键澄清问题。\n"
            "- 避免编造政策细节；不确定时明确说明‘基于模拟数据/通用规则’。"
        )

        api_base_url = os.environ.get("AI_BASE_URL", DEFAULT_AI_BASE_URL)
        api_model = os.environ.get("AI_MODEL", DEFAULT_AI_MODEL)

        # API Key 仅从 secrets/env 读取，避免写入代码或展示在 UI
        api_key = ""
        try:
            api_key = st.secrets.get("AI_API_KEY", "")
        except Exception:
            api_key = ""
        api_key = api_key or os.environ.get("AI_API_KEY", "")

        if "ai_messages" not in st.session_state:
            st.session_state.ai_messages = [
                {"role": "system", "content": os.environ.get("AI_SYSTEM_PROMPT", default_system_prompt)}
            ]

        def _call_openai_compatible(messages):
            if not api_base_url or not api_key:
                raise ValueError("AI 未配置：请在 Streamlit secrets 或环境变量中设置 AI_API_KEY")

            base = api_base_url.rstrip("/")
            if base.endswith("/v1"):
                url = f"{base}/chat/completions"
            else:
                url = f"{base}/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload = {
                "model": api_model,
                "messages": messages,
                "temperature": 0.2,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        with st.container(height=300):
            for m in st.session_state.ai_messages:
                if m["role"] == "system":
                    continue
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        user_prompt = st.chat_input("输入你的问题…")
        if user_prompt and user_prompt.strip():
            st.session_state.ai_messages.append({"role": "user", "content": user_prompt.strip()})
            try:
                with st.spinner("AI 思考中..."):
                    answer = _call_openai_compatible(st.session_state.ai_messages)
                st.session_state.ai_messages.append({"role": "assistant", "content": answer})
                st.rerun()
            except Exception as e:
                st.session_state.ai_messages.append({"role": "assistant", "content": f"调用失败：{e}"})
                st.rerun()

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📈 成绩整体分析", "🔍 个人成绩查询", "🏫 志愿填报参考", "🎓 录取模拟"])

    # --- Tab 1: 成绩整体分析 ---
    with tab1:
        st.header("📊 模拟高考成绩概览")
        
        # 关键指标 (KPI)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 参考人数", f"{len(df_filtered)} 人", delta="本批次")
        with col2:
            avg_score = df_filtered['总成绩'].mean()
            st.metric("📈 平均总分", f"{avg_score:.1f} 分", delta=f"{avg_score - 500:.1f} (vs 基准)" if avg_score > 500 else None)
        with col3:
            st.metric("🏆 最高分", f"{df_filtered['总成绩'].max()} 分")
        with col4:
            st.metric("📉 最低分", f"{df_filtered['总成绩'].min()} 分")

        st.markdown("### 📈 深度可视化分析")
        
        c1, c2 = st.columns(2)
        
        with c1:
            with st.container():
                # 直方图：总成绩分布
                fig_hist = px.histogram(
                    df_filtered, 
                    x="总成绩", 
                    nbins=30, 
                    title="总成绩分布直方图",
                    color_discrete_sequence=['#1E88E5'],
                    template="plotly_white"
                )
                fig_hist.update_layout(bargap=0.1, showlegend=False)
                st.plotly_chart(fig_hist, width='stretch')
            
        with c2:
            with st.container():
                # 箱线图：各科成绩分布 (需要数据转换)
                # 动态获取科目：语数英 + 赋分科目
                subjects = [col for col in df_filtered.columns if col in ['语文', '数学', '英语'] or '赋分' in col]
                
                # 简单的melt操作用于绘图
                if subjects:
                    df_melted = df_filtered.melt(value_vars=subjects, var_name="科目", value_name="分数")
                    fig_box = px.box(
                        df_melted, 
                        x="科目", 
                        y="分数", 
                        color="科目", 
                        title="各学科成绩箱线图",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_box, width='stretch')
                else:
                    st.info("未检测到分科成绩列，无法展示箱线图。")

    # --- Tab 2: 个人成绩查询 ---
    with tab2:
        st.header("🔍 个人成绩单查询")
        
        col_search, col_padding = st.columns([1, 2])
        with col_search:
            search_input = st.text_input("请输入姓名或准考证号进行查询:", placeholder="例如: 张三 或 KS001")
        
        if search_input:
            # 模糊匹配
            mask = (df_score['姓名'].astype(str).str.contains(search_input)) | \
                   (df_score['准考证号'].astype(str).str.contains(search_input))
            student_result = df_score[mask]
            
            if not student_result.empty:
                st.success(f"🎉 查询成功！共找到 {len(student_result)} 条记录")
                for index, row in student_result.iterrows():
                    with st.expander(f"📄 {row['姓名']} (准考证号: {row['准考证号']})", expanded=True):
                        # 展示个人详细分数
                        sc1, sc2 = st.columns([1, 2])
                        with sc1:
                            st.markdown(f"""
                            <div style="background-color: #E3F2FD; padding: 20px; border-radius: 10px;">
                                <h2 style="color: #1565C0; border: none;">{row['总成绩']} <span style="font-size: 16px; color: #555;">分</span></h2>
                                <p><strong>姓名:</strong> {row['姓名']}</p>
                                <p><strong>准考证号:</strong> {row['准考证号']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 如果有位次数据，尝试查找
                            if df_rank is not None:
                                # 假设位次表里也有总成绩和位次对应，或者直接在成绩表里就有位次
                                # 这里简单演示，如果成绩表里有'位次'列
                                if '位次' in row:
                                    st.metric("当前位次", f"{row['位次']}")
                                else:
                                    # 尝试从位次表查找 (假设位次表是 分数-位次 对应表)
                                    # 这里简化处理，仅展示已有信息
                                    pass
                        
                        with sc2:
                            # 雷达图展示各科能力
                            elective_for_student = [
                                c for c in ELECTIVE_FUFEN_COLS
                                if c in df_score.columns and pd.notna(row.get(c))
                            ]
                            core_for_radar = [c for c in CORE_150_COLS if c in df_score.columns and pd.notna(row.get(c))]

                            if core_for_radar and elective_for_student:
                                scores = [row[c] for c in core_for_radar] + [row[c] for c in elective_for_student]
                                labels = core_for_radar + [c.replace("赋分", "") for c in elective_for_student]

                                # 确保是数值
                                scores = pd.to_numeric(pd.Series(scores), errors="coerce").fillna(0).tolist()
                                df_radar = pd.DataFrame({"r": scores, "theta": labels})
                                fig_radar = px.line_polar(
                                    df_radar,
                                    r="r",
                                    theta="theta",
                                    line_close=True,
                                    title="学科能力雷达图（语数英 + 选考赋分）",
                                    template="plotly_white",
                                )
                                fig_radar.update_traces(fill="toself", line_color="#1E88E5")
                                st.plotly_chart(fig_radar, width='stretch')
                            else:
                                st.info("未检测到该考生完整的主课/选考数据。")
            else:
                st.warning("未找到匹配的学生信息，请检查输入是否正确。")

    # --- Tab 3: 志愿填报参考 ---
    with tab3:
        st.header("🏫 智能志愿推荐参考")
        
        if df_plan is not None:
            # 子标签页：总分推荐 和 详细成绩推荐
            sub_tab1, sub_tab2 = st.tabs(["📊 基于总分推荐", "📝 输入详细成绩推荐"])
            
            with sub_tab1:
                st.info("💡 基于您的总成绩和位次，筛选历年录取情况（模拟数据）。")
                
                col_input, col_help = st.columns([1, 2])
                with col_input:
                    my_score = st.number_input("输入你的预估总分", min_value=0, max_value=750, value=int(df_filtered['总成绩'].mean()))
                
                # 简单的推荐逻辑：推荐 录取分 <= 我的分数 的学校，且分差在一定范围内
                # 假设招生计划表有 '最低投档分' 或类似字段
                # 先检查列名
                # st.write(df_plan.columns) # 调试用
                
                # 尝试寻找分数线列
                score_col = None
                for col in df_plan.columns:
                    if '分' in col:
                        score_col = col
                        break
                
                if score_col:
                    # 筛选逻辑： 录取分 <= 我的分数 且 录取分 > 我的分数 - 30 (冲稳保的简单模拟)
                    # 注意：实际数据中可能是字符串或含有非数字，需要处理
                    try:
                        # 清洗数据，确保是数字
                        df_plan_clean = df_plan.copy()
                        df_plan_clean[score_col] = pd.to_numeric(df_plan_clean[score_col], errors='coerce')
                        df_plan_clean = df_plan_clean.dropna(subset=[score_col])
                        
                        # 推荐区间：[我的分数-40, 我的分数+10] (可以冲一点，也可以保底)
                        recommendations = df_plan_clean[
                            (df_plan_clean[score_col] <= my_score + 10) & 
                            (df_plan_clean[score_col] >= my_score - 40)
                        ].sort_values(by=score_col, ascending=False)
                        
                        st.write(f"为您推荐 **{len(recommendations)}** 个可能的志愿方向 (分数范围: {my_score-40} - {my_score+10}):")
                        
                        # 使用 data_editor 展示更美观的表格
                        st.dataframe(
                            recommendations,
                            width='stretch',
                            column_config={
                                "院校名称": st.column_config.TextColumn("院校名称", help="学校名称"),
                                score_col: st.column_config.ProgressColumn(
                                    "最低投档分",
                                    help="历年最低投档分数",
                                    format="%d",
                                    min_value=0,
                                    max_value=750,
                                ),
                            }
                        )
                        
                        if not recommendations.empty:
                            # 简单的统计图
                            if '院校名称' in recommendations.columns:
                                top_schools = recommendations['院校名称'].value_counts().head(10)
                                fig_schools = px.bar(
                                    x=top_schools.index, 
                                    y=top_schools.values, 
                                    title="推荐院校频次 (Top 10)",
                                    template="plotly_white",
                                    color_discrete_sequence=['#66BB6A']
                                )
                                st.plotly_chart(fig_schools, width='stretch')
                                
                    except Exception as e:
                        st.error(f"数据处理出错: {e}")
                else:
                    st.warning("在招生计划表中未找到分数线相关列，无法自动推荐。请检查数据源。")
                    st.dataframe(df_plan.head())
            
            with sub_tab2:
                st.info("💡 输入您的详细成绩，我们将计算总分并推荐适合的学校和专业。")

                chosen = st.multiselect(
                    "选择 3 门选考科目（历史/地理/政治/物理/化学/生物/技术）",
                    options=ELECTIVE_SUBJECTS,
                    default=["物理", "化学", "生物"],
                    max_selections=3,
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    chinese = st.number_input("语文原始分", min_value=0, max_value=150, value=100)
                    math = st.number_input("数学原始分", min_value=0, max_value=150, value=100)
                    english = st.number_input("英语原始分", min_value=0, max_value=150, value=100)

                elective_scores = {}
                with col2:
                    st.caption("选考请输入‘等级分(40-100)’")
                    for subj in chosen:
                        elective_scores[subj] = st.number_input(
                            f"{subj} 等级分",
                            min_value=40,
                            max_value=100,
                            value=80,
                            step=1,
                        )

                with col3:
                    if len(chosen) != 3:
                        st.warning("请先选择 3 门选考科目")
                    total_score = float(chinese + math + english + sum(elective_scores.values()))
                    st.metric("总成绩", f"{total_score:.0f} 分")
                    st.write("计分明细:")
                    st.write(f"语文: {chinese}")
                    st.write(f"数学: {math}")
                    st.write(f"英语: {english}")
                    for subj, sc in elective_scores.items():
                        st.write(f"{subj}: {sc}")
                
                if st.button("🔍 生成推荐", type="primary"):
                    # 使用计算的总分进行推荐
                    my_score = total_score
                    
                    score_col = None
                    for col in df_plan.columns:
                        if '分' in col:
                            score_col = col
                            break
                    
                    if score_col:
                        try:
                            df_plan_clean = df_plan.copy()
                            df_plan_clean[score_col] = pd.to_numeric(df_plan_clean[score_col], errors='coerce')
                            df_plan_clean = df_plan_clean.dropna(subset=[score_col])
                            
                            # 推荐区间：[我的分数-40, 我的分数+10]
                            recommendations = df_plan_clean[
                                (df_plan_clean[score_col] <= my_score + 10) & 
                                (df_plan_clean[score_col] >= my_score - 40)
                            ].sort_values(by=score_col, ascending=False)
                            
                            st.success(f"为您推荐 **{len(recommendations)}** 个可能的志愿方向 (分数范围: {my_score-40:.1f} - {my_score+10:.1f}):")
                            
                            st.dataframe(
                                recommendations,
                                width='stretch',
                                column_config={
                                    "院校名称": st.column_config.TextColumn("院校名称", help="学校名称"),
                                    "专业名称": st.column_config.TextColumn("专业名称", help="专业名称"),
                                    score_col: st.column_config.ProgressColumn(
                                        "最低投档分",
                                        help="历年最低投档分数",
                                        format="%.1f",
                                        min_value=0,
                                        max_value=750,
                                    ),
                                }
                            )
                            
                            if not recommendations.empty:
                                # 按学校分组显示
                                school_recs = recommendations.groupby('院校名称').size().sort_values(ascending=False).head(10)
                                fig_schools = px.bar(
                                    x=school_recs.index, 
                                    y=school_recs.values, 
                                    title="推荐院校频次 (Top 10)",
                                    template="plotly_white",
                                    color_discrete_sequence=['#66BB6A']
                                )
                                st.plotly_chart(fig_schools, width='stretch')
                                
                        except Exception as e:
                            st.error(f"数据处理出错: {e}")
                    else:
                        st.warning("在招生计划表中未找到分数线相关列，无法自动推荐。请检查数据源。")
        else:
            st.warning("缺少招生计划数据文件 (招生计划.csv)，无法进行志愿推荐。")

    # --- Tab 4: 录取模拟 ---
    with tab4:
        st.header("🎓 平行志愿录取模拟")
        st.markdown("根据 **招生计划** 和 **考生志愿填报结果**，模拟平行志愿录取过程，并生成录取结果文件。")

        if df_plan is not None and df_vol is not None:
            col_sim1, col_sim2 = st.columns(2)
            with col_sim1:
                st.info(f"招生计划总数: {df_plan['招收人数'].sum()} 人")
            with col_sim2:
                st.info(f"填报志愿人数: {len(df_vol)} 人")

            if st.button("🚀 开始模拟录取", type="primary"):
                with st.spinner("正在进行模拟录取，请稍候..."):
                    # 1. 初始化招生计划字典 {(院校, 专业): 剩余名额}
                    plan_dict = {}
                    for _, row in df_plan.iterrows():
                        key = (row['院校名称'], row['专业名称'])
                        plan_dict[key] = row['招收人数']
                    
                    # 2. 准备录取结果列表
                    admission_results = []
                    
                    # 3. 按位次排序 (确保位次小的优先)
                    # 假设 df_vol 已经有 '位次' 列，如果没有则需要合并
                    if '位次' not in df_vol.columns:
                        st.error("志愿填报数据中缺少 '位次' 列，无法进行排序录取。")
                    else:
                        df_vol_sorted = df_vol.sort_values(by='位次')
                        
                        # 4. 遍历每一位考生
                        for _, student in df_vol_sorted.iterrows():
                            admitted = False
                            admitted_school = None
                            admitted_major = None
                            
                            # 遍历该考生的6个志愿
                            for i in range(1, 7):
                                school_col = f'报考院校{i}'
                                major_col = f'报考专业{i}'
                                
                                # 检查列是否存在
                                if school_col not in student or major_col not in student:
                                    continue
                                    
                                school = student[school_col]
                                major = student[major_col]
                                
                                # 跳过空志愿
                                if pd.isna(school) or pd.isna(major):
                                    continue
                                
                                key = (school, major)
                                
                                # 检查是否有剩余名额
                                if key in plan_dict and plan_dict[key] > 0:
                                    # 录取成功
                                    plan_dict[key] -= 1
                                    admitted = True
                                    admitted_school = school
                                    admitted_major = major
                                    break # 退出志愿循环，处理下一位考生
                            
                            # 记录结果
                            admission_results.append({
                                '位次': student['位次'],
                                '准考证号': student['准考证号'],
                                '姓名': student['姓名'],
                                '录取状态': '录取' if admitted else '滑档',
                                '录取院校': admitted_school if admitted else None,
                                '录取专业': admitted_major if admitted else None
                            })
                        
                        # 5. 生成结果 DataFrame
                        df_result = pd.DataFrame(admission_results)
                        
                        # 展示结果统计
                        st.success("模拟录取完成！")
                        
                        res_col1, res_col2, res_col3 = st.columns(3)
                        total_students = len(df_result)
                        admitted_count = len(df_result[df_result['录取状态'] == '录取'])
                        failed_count = total_students - admitted_count
                        
                        res_col1.metric("总考生数", total_students)
                        res_col2.metric("成功录取", admitted_count)
                        res_col3.metric("滑档人数", failed_count)
                        
                        # 展示详细数据
                        st.subheader("录取结果详情")
                        st.dataframe(df_result)
                        
                        # 下载按钮
                        csv = df_result.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 下载录取结果文件 (CSV)",
                            data=csv,
                            file_name='录取结果文件.csv',
                            mime='text/csv',
                        )
        else:
            if df_plan is None:
                st.error("缺少 '招生计划.csv' 文件。")
            if df_vol is None:
                st.error("缺少 '志愿填报结果.csv' 文件。")

else:
    st.warning("请确保 data 目录下存在数据文件。")
