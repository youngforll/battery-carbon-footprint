import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# === 数据加载函数 ===
@st.cache_data
def load_emission_factors():
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "emission_factors.csv")
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("找不到排放因子数据库 (emission_factors.csv)，请确保该文件在同一目录下。")
        return pd.DataFrame()

# 初始化全局状态
if 'factors_df' not in st.session_state:
    st.session_state.factors_df = load_emission_factors()

# 预设不同项目的数据模板
project_presets = {
    "LFP-280Ah 储能电芯": {
        'li2co3': 0.6, 'fepo4': 1.2, 'graphite': 1.0, 'electrolyte': 1.5,
        'electricity': 35.0, 'grid': '华东电网', 'water': 0.5,
        'distance': 500.0, 'transport': '重型柴油货车', 'weight': 6.0
    },
    "NMC-811 动力电池": {
        'li2co3': 0.8, 'fepo4': 0.0, 'graphite': 1.2, 'electrolyte': 1.8,
        'electricity': 45.0, 'grid': '华南电网', 'water': 0.8,
        'distance': 800.0, 'transport': '铁路运输', 'weight': 8.0
    },
    "LFP-100Ah 户储电芯": {
        'li2co3': 0.25, 'fepo4': 0.5, 'graphite': 0.4, 'electrolyte': 0.6,
        'electricity': 15.0, 'grid': '100% 绿电 (风光)', 'water': 0.2,
        'distance': 1200.0, 'transport': '海运', 'weight': 2.5
    }
}

if 'current_project' not in st.session_state:
    st.session_state.current_project = "LFP-280Ah 储能电芯"

if 'user_inputs' not in st.session_state:
    st.session_state.user_inputs = project_presets[st.session_state.current_project].copy()


def get_factor(name):
    """根据名称从数据库获取排放因子"""
    if st.session_state.factors_df.empty: return 0.0
    row = st.session_state.factors_df[st.session_state.factors_df['名称'] == name]
    return float(row['排放因子(kgCO2e/单位)'].iloc[0]) if not row.empty else 0.0

def calculate_carbon_footprint():
    """根据输入计算各阶段碳足迹"""
    inputs = st.session_state.user_inputs
    
    # 1. 原材料获取及初加工 (Raw Materials)
    c_li2co3 = inputs['li2co3'] * get_factor('碳酸锂')
    c_fepo4 = inputs['fepo4'] * get_factor('磷酸铁')
    c_graphite = inputs['graphite'] * get_factor('石墨')
    c_electrolyte = inputs['electrolyte'] * get_factor('电解液')
    raw_material_emissions = c_li2co3 + c_fepo4 + c_graphite + c_electrolyte
    
    # 2. 电池制造与装配 (Manufacturing)
    c_electricity = inputs['electricity'] * get_factor(inputs['grid'])
    # 假设水处理也有一点碳排，简化不计入，或者写死一个小因子
    manufacturing_emissions = c_electricity
    
    # 3. 运输与分销 (Transportation)
    # 运输碳排 = 距离(km) * 重量(吨) * 因子(kgCO2e/tkm)
    tkm = inputs['distance'] * (inputs['weight'] / 1000.0)
    transport_emissions = tkm * get_factor(inputs['transport'])
    
    total = raw_material_emissions + manufacturing_emissions + transport_emissions
    
    return {
        'total': total,
        'stages': {
            '原材料获取及初加工': raw_material_emissions,
            '电芯制造及Pack装配': manufacturing_emissions,
            '入库及分销运输': transport_emissions
        },
        'sources': {
            '主材(正极/碳酸锂)': c_li2co3 + c_fepo4,
            '辅材(石墨/电解液)': c_graphite + c_electrolyte,
            '电力消耗': c_electricity,
            '运输排放': transport_emissions
        }
    }

# 计算当前数据
results = calculate_carbon_footprint()

# === 页面基础配置 ===
st.set_page_config(
    page_title="储能电池产品碳足迹核算平台", 
    layout="wide",
    initial_sidebar_state="auto"
)

# 隐藏 Streamlit 默认的右上角菜单和底部 Watermark，提升 SaaS 专业感
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* ===== 图表卡片阴影（桌面+手机均生效）===== */
            [data-testid="stVerticalBlockBorderWrapper"] {
                border-color: #e5ecef !important;
                border-radius: 10px !important;
                box-shadow: 0 2px 10px rgba(0,0,0,0.06) !important;
                overflow: hidden;
            }
            /* ===== 顶部标题 ===== */
            .main-page-header {
                font-size: 1.55rem; font-weight: 800; color: #1d5f72;
                margin: 0 0 2px 0 !important; line-height: 1.2; letter-spacing: -0.3px;
            }
            /* 桌面端隐藏移动顶栏和项目切换 */
            @media (min-width: 769px) {
                /* 桌面端恢复侧边栏折叠/展开按钮 */
                header button { visibility: visible !important; pointer-events: auto !important; }
                .main-page-header { display: none !important; }
                /* 哨兵在 stHorizontalBlock 内部，直接通过 :has() 隐藏整个列块 */
                [data-testid="stHorizontalBlock"]:has(#mob-proj-sentinel) {
                    display: none !important; height: 0 !important;
                    overflow: hidden !important; margin: 0 !important; padding: 0 !important;
                }
                /* 桌面端外层主导航 tab：放大加粗 + 选中下划线加粗 */
                [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"],
                [data-testid="stTabs"] [data-baseweb="tab-list"] [role="tab"],
                [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"] p,
                [data-testid="stTabs"] [data-baseweb="tab-list"] [role="tab"] p {
                    font-size: 1.1rem !important; font-weight: 700 !important;
                }
                [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
                    height: 3.5px !important;
                }
                /* 桌面端子导航 tab：正常尺寸 */
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"],
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"] [role="tab"],
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"] p,
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"] [role="tab"] p {
                    font-size: 0.88rem !important; font-weight: 400 !important;
                }
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
                    height: 2px !important;
                }
            }
            /* 手机端：完全隐藏侧边栏及展开箭头 */
            @media (max-width: 768px) {
                section[data-testid="stSidebar"],
                [data-testid="stSidebarCollapsedControl"],
                [data-testid="stSidebarNavToggleButton"] { display: none !important; }
            }
            /* Section 标题 */
            .section-header {
                padding: 6px 0; font-size: 1rem; font-weight: 600;
                color: #1a1a1a; margin: 6px 0 10px 0; background: transparent;
                border: none;
            }
            .section-header-form {
                font-size: 0.92rem; font-weight: 600; color: #1a1a1a;
                border-left: 3px solid #4A9BB5; padding-left: 10px;
                margin: 12px 0 4px 0;
            }
            /* 描述文字辅助样式 */
            .dash-desc { color: #666; margin-bottom: 0 !important; }
            /* ===== 移动端适配 ===== */
            .mobile-only { display: none; }
            .desktop-only { display: block; }
            @media only screen and (max-width: 768px) {
                /* 列默认：单列堆叠 */
                [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 16px !important; }
                [data-testid="column"] { min-width: 100% !important; flex: 1 1 100% !important; padding: 0 !important; }
                /* 页面内边距収窄 */
                .block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; padding-top: 0.6rem !important; }
                /* 显示/隐藏 */
                .mobile-only { display: block !important; }
                .desktop-only { display: none !important; }
                /* 描述文字：手机端缩小变淡 */
                .dash-desc { font-size: 0.75rem !important; color: #bbb !important; margin-bottom: 2px !important; }
                /* Section 标题：手机端加边框 */
                .section-header {
                    border: 1px solid #c8d8de !important; border-radius: 6px !important;
                    padding: 8px 14px !important; font-size: 0.9rem !important;
                }
                /* 字号适配 */
                .main-page-header { font-size: 1.15rem !important; margin-bottom: 12px !important; }
                h1 { font-size: 1.05rem !important; margin-bottom: 0.15rem !important; }
                h2, h3 { font-size: 0.9rem !important; }
                h4, h5, h6 { font-size: 0.82rem !important; font-weight: 600 !important; }
                [data-testid="stMetricValue"] { font-size: 1rem !important; }
                [data-testid="stMetricLabel"] { font-size: 0.67rem !important; }
                [data-testid="stMetricDelta"] { font-size: 0.61rem !important; }
                /* tablist 横向滚动 */
                [role="tablist"] { overflow-x: auto !important; flex-wrap: nowrap !important; -webkit-overflow-scrolling: touch !important; scrollbar-width: none !important; }
                [role="tablist"]::-webkit-scrollbar { display: none !important; }
                /* ---- 主导航（外层 stTabs）：单层边框 ---- */
                [data-testid="stTabs"] [data-baseweb="tab-list"],
                [data-testid="stTabs"] [role="tablist"] {
                    background: transparent !important; border-radius: 8px !important;
                    padding: 3px !important; border: 1px solid #c8d6dc !important; gap: 2px !important;
                }
                /* tab 按钮文字：加粗 */
                [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"],
                [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"] p {
                    white-space: nowrap !important;
                    font-size: 0.95rem !important; font-weight: 600 !important;
                    color: #666 !important; padding: 8px 16px !important;
                    background: transparent !important; border-radius: 6px !important;
                    box-shadow: none !important;
                }
                /* 隐藏下划线指示器 */
                [data-testid="stTabs"] [data-baseweb="tab-highlight"],
                [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }
                /* 选中态：淡背景 + 主色文字 */
                [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"][aria-selected="true"],
                [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"][aria-selected="true"] p {
                    color: #1d5f72 !important; font-weight: 700 !important;
                    background: #eef5f7 !important; box-shadow: none !important;
                }
                /* ---- 子导航（内层嵌套 stTabs）：覆盖为下划线风格 ---- */
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"],
                [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"] {
                    background: transparent !important; border: none !important;
                    border-bottom: 1px solid #e8e8e8 !important;
                    padding: 0 !important; border-radius: 0 !important; gap: 0 !important;
                }
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"],
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"] [data-baseweb="tab"] p {
                    font-size: 0.8rem !important; font-weight: 400 !important;
                    color: #555 !important; padding: 8px 14px !important;
                }
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: block !important; height: 2px !important; }
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-border"] { display: block !important; }
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"],
                [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p {
                    background: transparent !important; box-shadow: none !important;
                    border-radius: 0 !important; color: #4A9BB5 !important;
                }
                /* LCA子Tab 右侧渐隐提示 */
                [data-testid="stTabs"] [data-testid="stTabs"]:has([role="tab"]:nth-child(3)) [role="tablist"] {
                    -webkit-mask-image: linear-gradient(to right, black 62%, transparent 100%);
                    mask-image: linear-gradient(to right, black 62%, transparent 100%);
                }
            }
            /* Tab 激活态下划线 */
            [data-baseweb="tab-highlight"],
            [data-baseweb="tab-border"] {
                background-color: #4A9BB5 !important;
            }
            /* Tab 激活态文字 */
            button[data-baseweb="tab"][aria-selected="true"] p,
            button[data-baseweb="tab"][aria-selected="true"] div {
                color: #4A9BB5 !important;
            }
            /* Primary 按钮（含表单提交按钮） */
            [data-testid="baseButton-primary"],
            .stButton button[kind="primary"],
            [data-testid="stFormSubmitButton"] > button {
                background-color: #4A9BB5 !important;
                border-color: #4A9BB5 !important;
                color: #FFFFFF !important;
            }
            [data-testid="baseButton-primary"]:hover,
            .stButton button[kind="primary"]:hover,
            [data-testid="stFormSubmitButton"] > button:hover {
                background-color: #2d7a95 !important;
                border-color: #2d7a95 !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# === 侧边栏导航 ===
st.sidebar.title("⚡ 电池碳足迹系统")

# 模拟多项目管理 (体现SaaS系统的项目隔离概念)
st.sidebar.markdown("---")
project_list = ["LFP-280Ah 储能电芯", "NMC-811 动力电池", "LFP-100Ah 户储电芯"]
selected_project = st.sidebar.selectbox(
    "切换核算项目", 
    project_list, 
    index=project_list.index(st.session_state.current_project)
)

# 当切换项目时，重置用户输入数据并重新运行
if selected_project != st.session_state.current_project:
    st.session_state.current_project = selected_project
    st.session_state.user_inputs = project_presets[selected_project].copy()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(
    "**核算边界**：从摇篮到大门 (Cradle-to-Gate)\n\n"
    "**核算标准**：参考 ISO 14067 / 电池护照 (Battery Passport)"
)

# === 主内容区顶栏：应用标题 + 项目切换（仅手机端显示，桌面端通过CSS隐藏）===
st.markdown('<p class="main-page-header">⚡ 电池碳足迹系统</p>', unsafe_allow_html=True)
_sel_col, _spacer_col = st.columns([1, 2])
with _sel_col:
    st.markdown('<span id="mob-proj-sentinel"></span>', unsafe_allow_html=True)
    _proj_list = ["LFP-280Ah 储能电芯", "NMC-811 动力电池", "LFP-100Ah 户储电芯"]
    _proj_choice = st.selectbox("", _proj_list,
                                index=_proj_list.index(st.session_state.current_project),
                                label_visibility="collapsed", key="main_proj_select")
    if _proj_choice != st.session_state.current_project:
        st.session_state.current_project = _proj_choice
        st.session_state.user_inputs = project_presets[_proj_choice].copy()
        st.rerun()

# === 主导航 ===
tab_dash, tab_lca = st.tabs(["碳足迹看板", "数据填报"])

with tab_dash:
    st.title(f"{selected_project.split(' ')[0]} 碳足迹总览")
    st.markdown('<p class="dash-desc">基于输入数据，实时核算该型号电池的生命周期碳排放，满足《欧盟电池法》护照声明要求。</p>', unsafe_allow_html=True)
    st.markdown('<hr class="mobile-only" style="margin:4px 0 10px 0; border-color:#eee;">', unsafe_allow_html=True)
    # 核心指标卡片（2×2布局，手机友好）
    total_emission = results['total']
    cbam_cost = (total_emission / 1000.0) * 70 * 7.8
    main_stage = max(results['stages'], key=results['stages'].get)
    main_source = max(results['sources'], key=results['sources'].get)
    main_source_val = results['sources'][main_source]
    m_row1 = st.columns(2)
    m_row2 = st.columns(2)
    m_row1[0].metric("单台产品碳足迹", f"{total_emission:.1f} kg", f"{((total_emission/98.2)-1)*100:.1f}% 较行业平均", help="功能单位为1kWh。行业平均采用基准线98.2 kg CO2e/kWh。")
    m_row1[1].metric("主要排放源", main_source.split('(')[0], f"占总排放 {(main_source_val/total_emission)*100:.0f}%", help="在全生命周期中贡献温室气体排放最多的物理源。")
    m_row2[0].metric("数据质量(DQI)", "B级 (良好)", "实测数据驱动", help="DQI (Data Quality Indicator) 反映了LCA计算中使用的数据的可靠性。A级为最高。")
    m_row2[1].metric("预估出海碳税 (CBAM)", f"¥ {cbam_cost:.2f} /台", "按欧盟 €70/吨 估算", delta_color="inverse", help="基于欧盟碳边境调节机制（CBAM），未来产品出口欧洲需缴纳的预估碳关税。")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 图表布局：第一排
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        with st.container(border=True):
            st.subheader("各生命周期阶段碳排放占比")
            st.caption("展示从摇篮到大门 (Cradle-to-Gate) 各LCA阶段的温室气体排放分布。")
            df_lca = pd.DataFrame(list(results['stages'].items()), columns=['生命周期阶段', '碳排放量 (kg CO2e)'])
            fig_lca = px.pie(
                df_lca, 
                names='生命周期阶段', 
                values='碳排放量 (kg CO2e)', 
                hole=0.4,
                color_discrete_sequence=['#5A7B86', '#87A2A9', '#B0BFC4', '#D4DCDA']
            )
            fig_lca.update_layout(margin=dict(t=20, b=20, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_lca, use_container_width=True)

    with row1_col2:
        with st.container(border=True):
            st.subheader("按排放源分类结构")
            st.caption("识别关键排放因子，寻找减碳抓手（如绿电替代、回收料使用）。")
            df_source = pd.DataFrame(list(results['sources'].items()), columns=['排放源', '碳排放量 (kg CO2e)'])
            fig_source = px.bar(
                df_source.sort_values('碳排放量 (kg CO2e)', ascending=True), 
                x='碳排放量 (kg CO2e)', 
                y='排放源', 
                orientation='h',
                color='碳排放量 (kg CO2e)',
                color_continuous_scale=['#D4DCDA', '#5A7B86']
            )
            fig_source.update_layout(margin=dict(t=20, b=20, l=0, r=0), coloraxis_showscale=False, bargap=0.55)
            st.plotly_chart(fig_source, use_container_width=True)

    # 图表布局：第二排（桑基图全宽）
    with st.container(border=True):
        st.subheader("碳流向桑基图")
        st.caption("直观展示从生产要素到生命周期阶段，再到最终碳足迹的流向路径。")
        v_elec = results['sources']['电力消耗']
        v_main = results['sources']['主材(正极/碳酸锂)']
        v_aux = results['sources']['辅材(石墨/电解液)']
        v_trans = results['sources']['运输排放']
        v_raw_stage = results['stages']['原材料获取及初加工']
        v_mfg_stage = results['stages']['电芯制造及Pack装配']
        fig_sankey = go.Figure(data=[go.Sankey(
            textfont=dict(color="black", size=12),
            node = dict(
              pad = 15,
              thickness = 20,
              line = dict(color = "black", width = 0.5),
              label = ["电力消耗", "主辅材料", "运输燃料", "原材料阶段", "电池制造阶段", "物流运输阶段", "总碳足迹"],
              color = ["#7B8C9E", "#A4B1B6", "#C5C9C7", "#5A7B86", "#7B8C9E", "#8C9C9A", "#4A5D66"]
            ),
            link = dict(
              source = [0, 1, 2, 3, 4, 5],
              target = [4, 3, 5, 6, 6, 6],
              value =  [v_elec, v_main+v_aux, v_trans, v_raw_stage, v_mfg_stage, v_trans]
          ))])
        fig_sankey.update_layout(
            margin=dict(t=20, b=20, l=0, r=0), 
            height=420,
            font=dict(color="black", size=12)
        )
        st.plotly_chart(fig_sankey, use_container_width=True)

with tab_lca:
    st.title("生命周期清单分析 (LCI) 数据填报")
    st.markdown('<div class="mobile-only" style="background:#f0f7fa;border-left:3px solid #4A9BB5;border-right:3px solid #4A9BB5;padding:8px 12px;border-radius:4px;font-size:0.82rem;color:#3d6b7a;margin-bottom:8px;">手机端已优化为单列布局，建议使用桌面端体验完整功能。</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["手动逐项填报 (Manual)", "批量导入BOM (Auto-Mapping)", "供应链协同 (Supplier API)"])
    st.markdown("""<script>
    (function(){
        document.addEventListener('click', function(e){
            var t = e.target.closest('[role="tab"]');
            if(t){ setTimeout(function(){ t.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'}); }, 80); }
        }, true);
    })();
    </script>""", unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="section-header">供应链主数据采集</div>', unsafe_allow_html=True)
        st.caption("向核心供应商下发数据填报邮件，获取第一手实测碳足迹数据（Primary Data），逐步替代行业平均因子以提升系统整体 DQI 评级。")
        st.text_input("目标供应商企业邮箱")
        st.button("发送数据填报邀请", type="secondary")

    with tab2:
        st.markdown('<div class="section-header">批量数据导入</div>', unsafe_allow_html=True)
        st.caption("为降低企业人工填报成本，支持通过标准模板批量映射 ERP/MES 系统导出的物料与能耗清单。")
        st.file_uploader("上传产品 BOM 清单及能耗表 (Excel/CSV格式)", type=['xlsx', 'csv'])
        st.button("解析并自动匹配因子", disabled=True)
        
    with tab1:
        st.caption("系统已预置该型号的基准数据模板。修改以下活动数据后，系统将基于底层因子库自动执行计算流。")
        with st.form("lca_input_form", border=True):
            st.markdown('<p class="section-header-form">01 / 原材料获取与初加工</p>', unsafe_allow_html=True)
            st.caption("填写单台产品（或功能单位）核心主辅材的消耗量。")
            col1, col2 = st.columns(2)
            with col1:
                li2co3 = st.number_input("碳酸锂消耗量 (kg)", min_value=0.0, value=st.session_state.user_inputs['li2co3'])
                fepo4 = st.number_input("磷酸铁消耗量 (kg)", min_value=0.0, value=st.session_state.user_inputs['fepo4'])
            with col2:
                graphite = st.number_input("石墨消耗量 (kg)", min_value=0.0, value=st.session_state.user_inputs['graphite'])
                electrolyte = st.number_input("电解液消耗量 (kg)", min_value=0.0, value=st.session_state.user_inputs['electrolyte'])

            st.markdown("---")
            
            st.markdown('<p class="section-header-form">02 / 电池制造与装配</p>', unsafe_allow_html=True)
            st.caption("填写生产制造环节的直接能源与辅料消耗。")
            col1, col2 = st.columns(2)
            with col1:
                electricity = st.number_input("生产用电量 (kWh)", min_value=0.0, value=st.session_state.user_inputs['electricity'], help="包括电芯化成、化容等高耗电工序")
                grid_opts = ["华东电网", "华南电网", "100% 绿电 (风光)"]
                grid = st.selectbox("电力来源", grid_opts, index=grid_opts.index(st.session_state.user_inputs['grid']), help="选择不同电网将应用不同的发改委电网排放基准")
            with col2:
                water = st.number_input("生产用水量 (吨)", min_value=0.0, value=st.session_state.user_inputs['water'], help="纯水制备及冷却循环用水")

            st.markdown("---")

            st.markdown('<p class="section-header-form">03 / 运输与分销</p>', unsafe_allow_html=True)
            st.caption("填写产品交付至主要目标市场的干线物流情况。")
            col1, col2 = st.columns(2)
            with col1:
                distance = st.number_input("平均运输距离 (km)", min_value=0.0, value=st.session_state.user_inputs['distance'])
            with col2:
                trans_opts = ["重型柴油货车", "铁路运输", "海运"]
                transport = st.selectbox("主要运输方式", trans_opts, index=trans_opts.index(st.session_state.user_inputs['transport']))
                
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("保存并执行", type="primary", use_container_width=True)
        
        if submitted:
            # 更新 Session State
            st.session_state.user_inputs.update({
                'li2co3': li2co3, 'fepo4': fepo4, 'graphite': graphite, 'electrolyte': electrolyte,
                'electricity': electricity, 'grid': grid, 'water': water,
                'distance': distance, 'transport': transport
            })
            st.success("数据计算完成，正在更新看板...")
            st.rerun()

    # 在页面下方展示数据库内容供面试官查看
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">数据底层：排放因子库</div>', unsafe_allow_html=True)
    st.caption("当前系统加载的本地因子库 (emission_factors.csv)。真实业务中将通过 API 接入 Ecoinvent 等商业数据库。")
    st.dataframe(st.session_state.factors_df, use_container_width=True)
