import streamlit as st
import pandas as pd
import plotly.express as px
import os
import base64

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

    :root {{
        --bg: #e0e0e0;
        --text: #3b3b3b;
        --muted: #666666;
        --shadow-dark: #bebebe;
        --shadow-light: #ffffff;
        --radius: 18px;
    }}

    /* 全局背景与字体 */
    html, body, .stApp {{
        background: var(--bg) !important;
        color: var(--text) !important;
    }}
    html, body, .stApp, h1, h2, h3, h4, h5, h6, p, input, label, textarea {{
        font-family: 'GlobalFont', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }}

    /* 标题（偏柔和、无强烈色块） */
    h1, h2, h3 {{
        color: var(--text) !important;
        letter-spacing: 0.2px;
    }}
    h1 {{
        font-weight: 750;
    }}
    h2 {{
        font-weight: 700;
        border-bottom: none;
        padding-bottom: 0;
    }}
    h3 {{
        color: var(--muted) !important;
        font-weight: 650;
    }}

    /* 主体内容间距更“软”一点 */
    .block-container {{
        padding-top: 1.2rem;
    }}

    /* 侧边栏（同底色 + 内凹） */
    section[data-testid="stSidebar"] {{
        background: var(--bg) !important;
        border-radius: var(--radius);
        margin: 10px;
        padding: 6px;
        box-shadow: inset 8px 8px 16px var(--shadow-dark), inset -8px -8px 16px var(--shadow-light);
    }}

    /* 指标卡片（外凸 neumorphism） */
    div[data-testid="stMetric"] {{
        background: var(--bg);
        border-radius: var(--radius);
        padding: 16px 18px;
        box-shadow: 10px 10px 20px var(--shadow-dark), -10px -10px 20px var(--shadow-light);
        border: none;
    }}
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {{
        color: var(--text) !important;
    }}

    /* 信息/提示框：弱化边框，保持柔和 */
    div[data-testid="stAlert"] {{
        background: var(--bg);
        border-radius: var(--radius);
        border: none;
        box-shadow: 8px 8px 16px var(--shadow-dark), -8px -8px 16px var(--shadow-light);
    }}

    /* 按钮（外凸 + 按下内凹） */
    .stButton>button {{
        background: var(--bg) !important;
        color: var(--text) !important;
        border: none !important;
        border-radius: 999px;
        padding: 0.55rem 1.1rem;
        font-weight: 650;
        box-shadow: 8px 8px 16px var(--shadow-dark), -8px -8px 16px var(--shadow-light);
    }}
    .stButton>button:active {{
        box-shadow: inset 6px 6px 12px var(--shadow-dark), inset -6px -6px 12px var(--shadow-light);
    }}

    /* 输入控件（内凹） */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea {{
        background: var(--bg) !important;
        border: none !important;
        border-radius: 999px !important;
        box-shadow: inset 6px 6px 12px var(--shadow-dark), inset -6px -6px 12px var(--shadow-light);
        color: var(--text) !important;
    }}
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stTextArea"] textarea:focus {{
        outline: none !important;
        box-shadow: inset 8px 8px 16px var(--shadow-dark), inset -8px -8px 16px var(--shadow-light);
    }}

    /* 下拉/多选（BaseWeb） */
    div[data-baseweb="select"] > div {{
        background: var(--bg) !important;
        border: none !important;
        border-radius: 999px !important;
        box-shadow: inset 6px 6px 12px var(--shadow-dark), inset -6px -6px 12px var(--shadow-light);
    }}

    /* Tabs（柔和外凸） */
    button[role="tab"] {{
        background: var(--bg) !important;
        border-radius: 999px !important;
        margin-right: 8px;
        box-shadow: 6px 6px 12px var(--shadow-dark), -6px -6px 12px var(--shadow-light);
        color: var(--text) !important;
        border: none !important;
    }}
    button[role="tab"][aria-selected="true"] {{
        box-shadow: inset 6px 6px 12px var(--shadow-dark), inset -6px -6px 12px var(--shadow-light);
        color: var(--text) !important;
    }}

    /* 分隔线淡化 */
    hr {{
        border-color: rgba(0,0,0,0.08) !important;
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
@st.cache_data
def load_data():
    # 确保从脚本所在目录读取资源，避免因启动目录不同导致找不到 data/static
    app_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(app_dir, "data")
    
    # 1. 加载成绩数据
    score_file = os.path.join(base_path, "赋分后的高考模拟数据.csv")
    if os.path.exists(score_file):
        df_score = pd.read_csv(score_file)
        # 计算总成绩: 语数英 + 赋分科目
        # 识别赋分列 (假设列名包含'赋分') 和 主科
        fufen_cols = [c for c in df_score.columns if '赋分' in c]
        main_cols = ['语文', '数学', '英语']
        calc_cols = [c for c in main_cols + fufen_cols if c in df_score.columns]
        
        if calc_cols:
            df_score['总成绩'] = df_score[calc_cols].sum(axis=1)
        else:
            st.error("未找到成绩列，无法计算总分")
    else:
        st.error(f"文件未找到: {score_file}")
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

# 加载数据
df_score, df_rank, df_plan, df_vol = load_data()

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
                fig_hist.update_layout(
                    bargap=0.1,
                    showlegend=False,
                    paper_bgcolor="#e0e0e0",
                    plot_bgcolor="#e0e0e0",
                    font=dict(color="#3b3b3b"),
                    title_font=dict(color="#3b3b3b"),
                )
                fig_hist.update_xaxes(
                    gridcolor="rgba(0,0,0,0.08)",
                    linecolor="rgba(0,0,0,0.18)",
                    zerolinecolor="rgba(0,0,0,0.08)",
                )
                fig_hist.update_yaxes(
                    gridcolor="rgba(0,0,0,0.08)",
                    linecolor="rgba(0,0,0,0.18)",
                    zerolinecolor="rgba(0,0,0,0.08)",
                )
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
                    fig_box.update_layout(
                        paper_bgcolor="#e0e0e0",
                        plot_bgcolor="#e0e0e0",
                        font=dict(color="#3b3b3b"),
                        title_font=dict(color="#3b3b3b"),
                    )
                    fig_box.update_xaxes(
                        gridcolor="rgba(0,0,0,0.08)",
                        linecolor="rgba(0,0,0,0.18)",
                        zerolinecolor="rgba(0,0,0,0.08)",
                    )
                    fig_box.update_yaxes(
                        gridcolor="rgba(0,0,0,0.08)",
                        linecolor="rgba(0,0,0,0.18)",
                        zerolinecolor="rgba(0,0,0,0.08)",
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
                            <div style="background: #e0e0e0; padding: 20px; border-radius: 18px; box-shadow: 10px 10px 20px #bebebe, -10px -10px 20px #ffffff;">
                                <h2 style="color: #3b3b3b; border: none; margin: 0 0 8px 0;">{row['总成绩']} <span style="font-size: 16px; color: #666666;">分</span></h2>
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
                            if subjects:
                                scores = [row[s] for s in subjects]
                                df_radar = pd.DataFrame(dict(
                                    r=scores,
                                    theta=subjects
                                ))
                                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, title="学科能力雷达图", template="plotly_white")
                                fig_radar.update_traces(fill='toself', line_color='#1E88E5')
                                fig_radar.update_layout(
                                    paper_bgcolor="#e0e0e0",
                                    plot_bgcolor="#e0e0e0",
                                    font=dict(color="#3b3b3b"),
                                    title_font=dict(color="#3b3b3b"),
                                )
                                st.plotly_chart(fig_radar, width='stretch')
            else:
                st.warning("未找到匹配的学生信息，请检查输入是否正确。")

    # --- Tab 3: 志愿填报参考 ---
    with tab3:
        st.header("🏫 智能志愿推荐参考")
        
        if df_plan is not None:
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
                            fig_schools.update_layout(
                                paper_bgcolor="#e0e0e0",
                                plot_bgcolor="#e0e0e0",
                                font=dict(color="#3b3b3b"),
                                title_font=dict(color="#3b3b3b"),
                            )
                            fig_schools.update_xaxes(
                                gridcolor="rgba(0,0,0,0.08)",
                                linecolor="rgba(0,0,0,0.18)",
                                zerolinecolor="rgba(0,0,0,0.08)",
                            )
                            fig_schools.update_yaxes(
                                gridcolor="rgba(0,0,0,0.08)",
                                linecolor="rgba(0,0,0,0.18)",
                                zerolinecolor="rgba(0,0,0,0.08)",
                            )
                            st.plotly_chart(fig_schools, width='stretch')
                            
                except Exception as e:
                    st.error(f"数据处理出错: {e}")
            else:
                st.warning("在招生计划表中未找到分数线相关列，无法自动推荐。请检查数据源。")
                st.dataframe(df_plan.head())
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
