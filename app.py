from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="마이데이터 AI 분석 데모",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #f0f4ff 0%, #fafbff 100%); }
    .block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1200px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── 상수 ──────────────────────────────────────────────────────────────────────
SEGMENT_COLORS: dict[str, str] = {
    "VIP": "#FFB300",
    "일반": "#43A047",
    "절약형": "#1E88E5",
    "비활성": "#757575",
}

SEGMENT_EMOJI: dict[str, str] = {
    "VIP": "👑",
    "일반": "👤",
    "절약형": "💰",
    "비활성": "😴",
}

BANK_COLORS: dict[str, str] = {
    "KB국민": "#FFB300",
    "신한": "#0052A4",
    "하나": "#00843D",
    "우리": "#1B4F8B",
    "NH농협": "#70B244",
}

BANKS = ["KB국민", "신한", "하나", "우리", "NH농협"]

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "dummy_data.csv")


# ── 데이터 로드 ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    # BOM이나 공백으로 인해 컬럼명이 깨진 경우 정규화
    df.columns = df.columns.str.strip().str.lstrip("\ufeff")
    return df


def format_won(amount: float) -> str:
    if amount >= 100_000_000:
        return f"{amount / 100_000_000:.1f}억원"
    if amount >= 10_000:
        return f"{amount / 10_000:.0f}만원"
    return f"{amount:,.0f}원"


# ── 사이드바 ───────────────────────────────────────────────────────────────────
def build_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.title("🔎 필터 설정")

    segments = st.sidebar.multiselect(
        "고객 세그먼트",
        options=["VIP", "일반", "절약형", "비활성"],
        default=["VIP", "일반", "절약형", "비활성"],
    )

    banks = st.sidebar.multiselect(
        "주거래은행",
        options=BANKS,
        default=BANKS,
    )

    age_min, age_max = int(df["age"].min()), int(df["age"].max())
    age_range = st.sidebar.slider("나이 범위", age_min, age_max, (age_min, age_max))

    income_min = int(df["income"].min() / 10_000)
    income_max = int(df["income"].max() / 10_000)
    income_range = st.sidebar.slider(
        "월소득 범위 (만원)", income_min, income_max, (income_min, income_max)
    )

    gender = st.sidebar.multiselect("성별", ["M", "F"], default=["M", "F"])

    if "주거래은행" not in df.columns:
        st.sidebar.error(
            f"'주거래은행' 컬럼을 찾을 수 없습니다. 현재 컬럼: {list(df.columns)}"
        )
        return df

    filtered = df[
        df["segment"].isin(segments)
        & df["주거래은행"].isin(banks)
        & df["age"].between(age_range[0], age_range[1])
        & df["income"].between(income_range[0] * 10_000, income_range[1] * 10_000)
        & df["gender"].isin(gender)
    ]

    st.sidebar.markdown("---")
    st.sidebar.metric("선택된 고객", f"{len(filtered)}명", f"전체 {len(df)}명 중")

    return filtered


# ── 탭 1 : 전체 개요 ───────────────────────────────────────────────────────────
def tab_overview(df: pd.DataFrame) -> None:
    # KPI 카드
    col1, col2, col3, col4, col5 = st.columns(5)
    kpis = [
        ("총 고객 수", f"{len(df):,}명", ""),
        ("평균 월소득", format_won(df["income"].mean()), ""),
        ("평균 월지출", format_won(df["monthly_spending"].mean()), ""),
        ("평균 신용점수", f"{df['credit_score'].mean():.0f}점", ""),
        ("평균 저축률", f"{df['savings_rate'].mean():.1%}", ""),
    ]
    for col, (title, val, sub) in zip([col1, col2, col3, col4, col5], kpis):
        col.metric(title, val, sub or None)

    st.markdown("---")

    col_pie, col_bar = st.columns(2)

    with col_pie:
        seg_cnt = df["segment"].value_counts().reset_index()
        seg_cnt.columns = ["segment", "count"]
        fig = px.pie(
            seg_cnt,
            values="count",
            names="segment",
            title="고객 세그먼트 분포",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            hole=0.42,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label+value")
        fig.update_layout(margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_bar:
        seg_agg = (
            df.groupby("segment")
            .agg(평균월소득=("income", "mean"), 평균월지출=("monthly_spending", "mean"))
            .reset_index()
        )
        fig2 = go.Figure()
        for col_name, opacity in [("평균월소득", 1.0), ("평균월지출", 0.65)]:
            fig2.add_trace(
                go.Bar(
                    name=col_name,
                    x=seg_agg["segment"],
                    y=seg_agg[col_name] / 10_000,
                    marker_color=[SEGMENT_COLORS[s] for s in seg_agg["segment"]],
                    opacity=opacity,
                )
            )
        fig2.update_layout(
            title="세그먼트별 평균 소득 / 지출 (만원)",
            barmode="group",
            xaxis_title="세그먼트",
            yaxis_title="금액 (만원)",
            margin=dict(t=50, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # 주거래은행별 고객 분포
    st.markdown("---")
    st.subheader("🏦 주거래은행별 고객 분포")

    col_bank1, col_bank2 = st.columns(2)

    with col_bank1:
        bank_cnt = df["주거래은행"].value_counts().reset_index()
        bank_cnt.columns = ["은행", "고객수"]
        fig_bank = px.bar(
            bank_cnt,
            x="은행",
            y="고객수",
            color="은행",
            color_discrete_map=BANK_COLORS,
            title="주거래은행별 고객 수",
            text="고객수",
        )
        fig_bank.update_traces(textposition="outside")
        fig_bank.update_layout(margin=dict(t=50, b=20), showlegend=False)
        st.plotly_chart(fig_bank, use_container_width=True)

    with col_bank2:
        bank_seg = (
            df.groupby(["주거래은행", "segment"])
            .size()
            .reset_index(name="고객수")
        )
        fig_bs = px.bar(
            bank_seg,
            x="주거래은행",
            y="고객수",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="주거래은행별 세그먼트 구성",
            barmode="stack",
            category_orders={"주거래은행": BANKS},
        )
        fig_bs.update_layout(margin=dict(t=50, b=20))
        st.plotly_chart(fig_bs, use_container_width=True)

    # 은행별 평균 자산 현황
    bank_asset = (
        df.groupby("주거래은행")
        .agg(
            평균여신=("여신잔액_만원", "mean"),
            평균수신=("수신잔액_만원", "mean"),
            평균펀드=("펀드잔액_만원", "mean"),
        )
        .reset_index()
    )
    fig_asset = go.Figure()
    for col_name, color in [("평균여신", "#EF5350"), ("평균수신", "#42A5F5"), ("평균펀드", "#66BB6A")]:
        fig_asset.add_trace(
            go.Bar(name=col_name, x=bank_asset["주거래은행"], y=bank_asset[col_name])
        )
    fig_asset.update_layout(
        title="주거래은행별 평균 여신·수신·펀드 잔액 (만원)",
        barmode="group",
        xaxis_title="은행",
        yaxis_title="금액 (만원)",
        margin=dict(t=50, b=20),
    )
    st.plotly_chart(fig_asset, use_container_width=True)

    # 요약 테이블
    st.subheader("세그먼트별 주요 지표 요약")
    summary = (
        df.groupby("segment")
        .agg(
            고객수=("customer_id", "count"),
            평균나이=("age", "mean"),
            평균월소득=("income", "mean"),
            평균월지출=("monthly_spending", "mean"),
            평균저축률=("savings_rate", "mean"),
            평균신용점수=("credit_score", "mean"),
            평균거래횟수=("transaction_count", "mean"),
        )
        .round(1)
        .reset_index()
    )
    summary["평균월소득"] = summary["평균월소득"].apply(format_won)
    summary["평균월지출"] = summary["평균월지출"].apply(format_won)
    summary["평균저축률"] = summary["평균저축률"].apply(lambda x: f"{x:.1%}")
    st.dataframe(summary, use_container_width=True, hide_index=True)


# ── 탭 2 : 세그먼트 분석 ─────────────────────────────────────────────────────
def tab_segment(df: pd.DataFrame) -> None:
    st.subheader("세그먼트별 심층 분석")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.box(
            df,
            x="segment",
            y="income",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="세그먼트별 월소득 분포",
            labels={"income": "월소득 (원)", "segment": "세그먼트"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            df,
            x="income",
            y="monthly_spending",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="월소득 vs 월지출",
            labels={"income": "월소득 (원)", "monthly_spending": "월지출 (원)"},
            hover_data=["customer_id", "age", "credit_score"],
            opacity=0.8,
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig = px.violin(
            df,
            x="segment",
            y="savings_rate",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            title="세그먼트별 저축률 분포",
            labels={"savings_rate": "저축률", "segment": "세그먼트"},
            box=True,
        )
        fig.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.scatter(
            df,
            x="days_since_last_transaction",
            y="transaction_count",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            size="income",
            title="거래 활성도 분석",
            labels={
                "days_since_last_transaction": "마지막 거래 후 경과일",
                "transaction_count": "월 거래 횟수",
            },
            hover_data=["customer_id", "segment"],
            opacity=0.75,
        )
        st.plotly_chart(fig, use_container_width=True)

    # 은행별 여신·수신·카드 실적 비교
    st.markdown("---")
    st.subheader("🏦 은행별 여신 / 수신 / 카드 실적 비교")

    bank_seg_agg = (
        df.groupby(["주거래은행", "segment"])
        .agg(
            평균여신=("여신잔액_만원", "mean"),
            평균수신=("수신잔액_만원", "mean"),
            평균카드=("카드실적_만원", "mean"),
            평균외환=("외환거래_달러", "mean"),
            평균펀드=("펀드잔액_만원", "mean"),
            고객수=("customer_id", "count"),
        )
        .reset_index()
    )

    metric_tab1, metric_tab2, metric_tab3 = st.tabs(["여신잔액", "수신잔액", "카드실적"])

    with metric_tab1:
        fig_loan = px.bar(
            bank_seg_agg,
            x="주거래은행",
            y="평균여신",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            barmode="group",
            title="은행별 세그먼트별 평균 여신잔액 (만원)",
            labels={"평균여신": "평균 여신잔액 (만원)", "주거래은행": "은행"},
            category_orders={"주거래은행": BANKS},
        )
        st.plotly_chart(fig_loan, use_container_width=True)

    with metric_tab2:
        fig_dep = px.bar(
            bank_seg_agg,
            x="주거래은행",
            y="평균수신",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            barmode="group",
            title="은행별 세그먼트별 평균 수신잔액 (만원)",
            labels={"평균수신": "평균 수신잔액 (만원)", "주거래은행": "은행"},
            category_orders={"주거래은행": BANKS},
        )
        st.plotly_chart(fig_dep, use_container_width=True)

    with metric_tab3:
        fig_card = px.bar(
            bank_seg_agg,
            x="주거래은행",
            y="평균카드",
            color="segment",
            color_discrete_map=SEGMENT_COLORS,
            barmode="group",
            title="은행별 세그먼트별 평균 카드실적 (만원)",
            labels={"평균카드": "평균 카드실적 (만원)", "주거래은행": "은행"},
            category_orders={"주거래은행": BANKS},
        )
        st.plotly_chart(fig_card, use_container_width=True)

    # 은행별 종합 실적 버블 차트
    bank_total = (
        df.groupby("주거래은행")
        .agg(
            평균여신=("여신잔액_만원", "mean"),
            평균수신=("수신잔액_만원", "mean"),
            평균카드=("카드실적_만원", "mean"),
            고객수=("customer_id", "count"),
        )
        .reset_index()
    )
    fig_bubble = px.scatter(
        bank_total,
        x="평균여신",
        y="평균수신",
        size="고객수",
        color="주거래은행",
        color_discrete_map=BANK_COLORS,
        text="주거래은행",
        title="은행별 여신 vs 수신 잔액 비교 (버블 크기=고객수)",
        labels={"평균여신": "평균 여신잔액 (만원)", "평균수신": "평균 수신잔액 (만원)"},
        size_max=60,
    )
    fig_bubble.update_traces(textposition="top center")
    st.plotly_chart(fig_bubble, use_container_width=True)

    # 레이더 차트
    st.subheader("세그먼트 특성 비교 (레이더 차트)")
    seg_avg = (
        df.groupby("segment")
        .agg(
            income=("income", "mean"),
            monthly_spending=("monthly_spending", "mean"),
            transaction_count=("transaction_count", "mean"),
            savings_rate=("savings_rate", "mean"),
            credit_score=("credit_score", "mean"),
        )
        .reset_index()
    )

    # 0-1 정규화
    for c in ["income", "monthly_spending", "transaction_count", "savings_rate", "credit_score"]:
        lo, hi = seg_avg[c].min(), seg_avg[c].max()
        seg_avg[c + "_n"] = (seg_avg[c] - lo) / (hi - lo) if hi != lo else 0.5

    categories = ["월소득", "월지출", "거래횟수", "저축률", "신용점수"]
    norm_cols = [c + "_n" for c in ["income", "monthly_spending", "transaction_count", "savings_rate", "credit_score"]]

    fig = go.Figure()
    for _, row in seg_avg.iterrows():
        vals = [row[c] for c in norm_cols] + [row[norm_cols[0]]]
        fig.add_trace(
            go.Scatterpolar(
                r=vals,
                theta=categories + [categories[0]],
                fill="toself",
                name=row["segment"],
                line_color=SEGMENT_COLORS.get(row["segment"], "#888"),
                opacity=0.6,
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="세그먼트별 특성 비교 (정규화 0~1)",
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── 탭 3 : 고객 상세 ──────────────────────────────────────────────────────────
def tab_detail(df: pd.DataFrame) -> None:
    st.subheader("고객 상세 데이터")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        credit_min = st.slider("최소 신용점수 필터", 500, 1000, 500)
    with col_f2:
        bank_filter = st.multiselect(
            "주거래은행 필터",
            options=BANKS,
            default=BANKS,
        )

    detail = df[
        (df["credit_score"] >= credit_min) & (df["주거래은행"].isin(bank_filter))
    ].copy()

    disp = detail.copy()
    disp["income"] = disp["income"].apply(format_won)
    disp["monthly_spending"] = disp["monthly_spending"].apply(format_won)
    disp["loan_balance"] = disp["loan_balance"].apply(format_won)
    disp["savings_rate"] = disp["savings_rate"].apply(lambda x: f"{x:.1%}")
    disp["여신잔액_만원"] = disp["여신잔액_만원"].apply(lambda x: f"{x:,.0f}만원")
    disp["수신잔액_만원"] = disp["수신잔액_만원"].apply(lambda x: f"{x:,.0f}만원")
    disp["카드실적_만원"] = disp["카드실적_만원"].apply(lambda x: f"{x:,.0f}만원")
    disp["외환거래_달러"] = disp["외환거래_달러"].apply(lambda x: f"${x:,.0f}")
    disp["펀드잔액_만원"] = disp["펀드잔액_만원"].apply(lambda x: f"{x:,.0f}만원")

    disp = disp.rename(columns={
        "customer_id": "고객ID",
        "age": "나이",
        "gender": "성별",
        "income": "월소득",
        "monthly_spending": "월지출",
        "transaction_count": "거래횟수",
        "days_since_last_transaction": "마지막거래(일전)",
        "savings_rate": "저축률",
        "loan_balance": "대출잔액",
        "credit_score": "신용점수",
        "num_accounts": "보유계좌수",
        "segment": "세그먼트",
        "주거래은행": "주거래은행",
        "여신잔액_만원": "여신잔액",
        "수신잔액_만원": "수신잔액",
        "카드실적_만원": "카드실적",
        "외환거래_달러": "외환거래",
        "펀드잔액_만원": "펀드잔액",
    })

    st.markdown(f"**{len(disp):,}명** 표시 중")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    csv_bytes = detail.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="⬇️ CSV 다운로드",
        data=csv_bytes,
        file_name="mydata_filtered.csv",
        mime="text/csv",
    )


# ── 탭 4 : AI 인사이트 ────────────────────────────────────────────────────────
RECOMMENDATIONS: dict[str, list[str]] = {
    "VIP": [
        "👑 **프리미엄 자산관리 서비스 제안** — 평균 소득이 높은 VIP 고객에게 맞춤형 투자 포트폴리오 상담을 제공하세요.",
        "💳 **프리미엄 카드 업그레이드** — 월 거래 빈도가 높으므로 포인트 적립률이 높은 플래티넘 카드를 추천하세요.",
        "🏡 **부동산·투자 크로스셀링** — 대출 잔액이 있는 VIP에게 금리 우대 및 담보대출 재구성을 제안하세요.",
        "📱 **VIP 전담 PB 연결** — 실시간 자산 현황 알림과 전담 매니저 1:1 채널을 제공하세요.",
    ],
    "일반": [
        "📊 **자산 증대 플랜** — 저축률 향상을 위한 자동이체 적금 및 목돈 마련 상품을 추천하세요.",
        "💡 **생활비 절약 서비스** — 지출 패턴 분석 기반으로 카테고리별 절약 팁과 할인 혜택을 제공하세요.",
        "📈 **중위험 투자 상품** — 안정적인 소득을 바탕으로 중위험-중수익 펀드 또는 ETF를 소개하세요.",
        "🔄 **대출 금리 최적화** — 보유 대출의 금리를 점검하고 더 낮은 금리 상품으로 전환을 안내하세요.",
    ],
    "절약형": [
        "🏦 **고금리 예·적금 우선 안내** — 최고 금리 정기예금 및 특판 상품을 제일 먼저 안내하세요.",
        "🏆 **저축 챌린지 프로그램** — 월별 저축 목표 달성 시 보너스 이자를 제공하는 캠페인을 기획하세요.",
        "🛡️ **보장성 보험 리뷰** — 안정 지향 성향을 고려해 실손의료보험 및 종신보험 재점검을 제안하세요.",
        "💡 **ISA 계좌 절세 투자** — 소액 투자 진입 장벽을 낮춰 절세 투자 첫 경험을 도와드리세요.",
    ],
    "비활성": [
        "📩 **재활성화 캠페인** — 특별 이자율 혜택과 함께 서비스 재이용을 개인화 메시지로 권유하세요.",
        "🎁 **복귀 혜택 제공** — 앱 재접속 시 포인트 적립 또는 수수료 면제 쿠폰으로 활성화를 유도하세요.",
        "📞 **1:1 맞춤 상담** — 비활성 원인 파악을 위한 짧은 설문 또는 상담 연결 서비스를 제공하세요.",
        "📱 **앱 UX 가이드 발송** — 주요 기능 튜토리얼 푸시 알림으로 서비스 재진입 장벽을 낮추세요.",
    ],
    "전체": [
        "🗂️ **통합 포트폴리오 분석** — 세그먼트 데이터를 종합해 CLV(고객 생애 가치) 예측 모델을 구축하세요.",
        "🎯 **세그먼트별 맞춤 마케팅** — 각 고객 그룹의 특성에 맞는 차별화된 커뮤니케이션 전략을 수립하세요.",
        "🔄 **세그먼트 이동 모니터링** — 고객의 세그먼트 변화를 추적해 상향/하향 이동 패턴을 분석하세요.",
        "⚡ **실시간 이상 거래 탐지** — 비활성 고객의 갑작스러운 고액 거래를 이상 징후로 모니터링하세요.",
    ],
}


def tab_insights(df: pd.DataFrame) -> None:
    st.subheader("AI 기반 고객 인사이트")

    selected = st.selectbox(
        "분석할 세그먼트",
        ["전체", "VIP", "일반", "절약형", "비활성"],
        format_func=lambda s: f"{SEGMENT_EMOJI.get(s, '')} {s}",
    )

    analysis = df if selected == "전체" else df[df["segment"] == selected]

    if analysis.empty:
        st.warning("선택된 조건에 해당하는 고객이 없습니다.")
        return

    # 주요 지표 + 추천 전략
    col_metrics, col_reco = st.columns([1, 1], gap="large")

    with col_metrics:
        st.markdown("### 📈 주요 지표")
        spend_ratio = analysis["monthly_spending"].mean() / analysis["income"].mean()
        high_loan_cnt = (analysis["loan_balance"] > 10_000_000).sum()
        rows = [
            ("평균 월소득", format_won(analysis["income"].mean())),
            ("평균 월지출", format_won(analysis["monthly_spending"].mean())),
            ("소득 대비 지출률", f"{spend_ratio:.1%}"),
            ("평균 저축률", f"{analysis['savings_rate'].mean():.1%}"),
            ("평균 신용점수", f"{analysis['credit_score'].mean():.0f}점"),
            ("평균 거래횟수", f"{analysis['transaction_count'].mean():.1f}회/월"),
            ("마지막 거래 경과", f"{analysis['days_since_last_transaction'].mean():.1f}일 전"),
            ("고액 대출자 비율", f"{high_loan_cnt}/{len(analysis)}명 ({high_loan_cnt/len(analysis):.1%})"),
            ("평균 여신잔액", f"{analysis['여신잔액_만원'].mean():.0f}만원"),
            ("평균 수신잔액", f"{analysis['수신잔액_만원'].mean():.0f}만원"),
            ("평균 카드실적", f"{analysis['카드실적_만원'].mean():.0f}만원"),
            ("평균 펀드잔액", f"{analysis['펀드잔액_만원'].mean():.0f}만원"),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["지표", "값"]),
            use_container_width=True,
            hide_index=True,
        )

    with col_reco:
        st.markdown("### 💡 AI 추천 전략")
        for rec in RECOMMENDATIONS[selected]:
            st.markdown(f"> {rec}")
            st.markdown("")

    # 리스크 분석
    st.markdown("---")
    st.subheader("⚠️ 리스크 분석")

    c1, c2, c3 = st.columns(3)
    high_loan = analysis[analysis["loan_balance"] > 10_000_000]
    low_credit = analysis[analysis["credit_score"] < 600]
    risk_group = analysis[
        (analysis["days_since_last_transaction"] > 30) & (analysis["loan_balance"] > 5_000_000)
    ]

    c1.metric("고액 대출 고객", f"{len(high_loan)}명", f"{len(high_loan)/len(analysis)*100:.1f}%")
    c2.metric("저신용 고객 (600 미만)", f"{len(low_credit)}명", f"{len(low_credit)/len(analysis)*100:.1f}%")
    c3.metric("비활성+대출 위험군", f"{len(risk_group)}명", f"{len(risk_group)/len(analysis)*100:.1f}%")

    fig = px.bar(
        df.groupby("segment")["loan_balance"].mean().reset_index(),
        x="segment",
        y="loan_balance",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        title="세그먼트별 평균 대출 잔액",
        labels={"loan_balance": "평균 대출 잔액 (원)", "segment": "세그먼트"},
        text_auto=".3s",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 신용점수 히스토그램
    fig2 = px.histogram(
        analysis,
        x="credit_score",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        nbins=20,
        title="신용점수 분포",
        labels={"credit_score": "신용점수", "count": "고객 수"},
        barmode="overlay",
        opacity=0.7,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── 은행별 경쟁력 분석 ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🏦 은행별 경쟁력 분석")

    bank_comp = (
        df.groupby("주거래은행")
        .agg(
            고객수=("customer_id", "count"),
            평균여신=("여신잔액_만원", "mean"),
            평균수신=("수신잔액_만원", "mean"),
            평균카드=("카드실적_만원", "mean"),
            평균외환=("외환거래_달러", "mean"),
            평균펀드=("펀드잔액_만원", "mean"),
            평균신용점수=("credit_score", "mean"),
            평균저축률=("savings_rate", "mean"),
        )
        .reset_index()
    )

    col_bc1, col_bc2 = st.columns(2)

    with col_bc1:
        # 은행별 종합 수익성 지표 (여신+카드실적 합산)
        bank_comp["수익성지표"] = bank_comp["평균여신"] * 0.04 + bank_comp["평균카드"] * 0.01
        fig_profit = px.bar(
            bank_comp.sort_values("수익성지표", ascending=False),
            x="주거래은행",
            y="수익성지표",
            color="주거래은행",
            color_discrete_map=BANK_COLORS,
            title="은행별 추정 수익성 지표 (여신×4%+카드×1%)",
            text_auto=".1f",
        )
        fig_profit.update_layout(showlegend=False)
        st.plotly_chart(fig_profit, use_container_width=True)

    with col_bc2:
        # 은행별 평균 외환거래 (글로벌 역량)
        fig_fx = px.bar(
            bank_comp.sort_values("평균외환", ascending=False),
            x="주거래은행",
            y="평균외환",
            color="주거래은행",
            color_discrete_map=BANK_COLORS,
            title="은행별 평균 외환거래액 (달러)",
            text_auto=".0f",
        )
        fig_fx.update_layout(showlegend=False)
        st.plotly_chart(fig_fx, use_container_width=True)

    # 은행별 종합 경쟁력 테이블
    st.markdown("**은행별 종합 경쟁력 현황**")
    comp_display = bank_comp.copy()
    comp_display["평균여신"] = comp_display["평균여신"].apply(lambda x: f"{x:.0f}만원")
    comp_display["평균수신"] = comp_display["평균수신"].apply(lambda x: f"{x:.0f}만원")
    comp_display["평균카드"] = comp_display["평균카드"].apply(lambda x: f"{x:.0f}만원")
    comp_display["평균외환"] = comp_display["평균외환"].apply(lambda x: f"${x:.0f}")
    comp_display["평균펀드"] = comp_display["평균펀드"].apply(lambda x: f"{x:.0f}만원")
    comp_display["평균신용점수"] = comp_display["평균신용점수"].apply(lambda x: f"{x:.0f}점")
    comp_display["평균저축률"] = comp_display["평균저축률"].apply(lambda x: f"{x:.1%}")
    comp_display = comp_display.drop(columns=["수익성지표"]).rename(columns={"주거래은행": "은행"})
    st.dataframe(comp_display, use_container_width=True, hide_index=True)

    # ── 이탈 위험 고객 분석 ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🚨 이탈 위험 고객 분석")

    # 이탈 위험 점수 계산 (거래 경과일 + 낮은 신용점수 + 비활성 세그먼트)
    churn_df = df.copy()
    churn_df["이탈위험점수"] = (
        (churn_df["days_since_last_transaction"] > 30).astype(int) * 30
        + (churn_df["credit_score"] < 650).astype(int) * 25
        + (churn_df["segment"] == "비활성").astype(int) * 30
        + (churn_df["transaction_count"] < 5).astype(int) * 15
    )
    churn_high = churn_df[churn_df["이탈위험점수"] >= 55]

    col_ch1, col_ch2, col_ch3 = st.columns(3)
    col_ch1.metric("이탈 고위험 고객", f"{len(churn_high)}명", f"전체의 {len(churn_high)/len(df)*100:.1f}%")
    col_ch2.metric("평균 이탈위험점수", f"{churn_df['이탈위험점수'].mean():.1f}점", "55점 이상 = 고위험")
    col_ch3.metric(
        "고위험 고객 평균 대출",
        f"{churn_high['여신잔액_만원'].mean():.0f}만원" if len(churn_high) > 0 else "N/A",
        "회수 위험 모니터링 필요",
    )

    col_churn1, col_churn2 = st.columns(2)

    with col_churn1:
        # 은행별 이탈 위험 고객 비율
        bank_churn = (
            churn_df.groupby("주거래은행")
            .apply(lambda x: pd.Series({
                "전체": len(x),
                "고위험": (x["이탈위험점수"] >= 55).sum(),
            }))
            .reset_index()
        )
        bank_churn["이탈위험비율"] = bank_churn["고위험"] / bank_churn["전체"] * 100
        fig_churn = px.bar(
            bank_churn.sort_values("이탈위험비율", ascending=False),
            x="주거래은행",
            y="이탈위험비율",
            color="주거래은행",
            color_discrete_map=BANK_COLORS,
            title="은행별 이탈 위험 고객 비율 (%)",
            text_auto=".1f",
        )
        fig_churn.update_layout(showlegend=False, yaxis_title="이탈 위험 비율 (%)")
        st.plotly_chart(fig_churn, use_container_width=True)

    with col_churn2:
        # 이탈위험점수 분포
        fig_score = px.histogram(
            churn_df,
            x="이탈위험점수",
            color="주거래은행",
            color_discrete_map=BANK_COLORS,
            nbins=15,
            title="은행별 이탈위험점수 분포",
            labels={"이탈위험점수": "이탈위험점수", "count": "고객 수"},
            barmode="overlay",
            opacity=0.7,
        )
        fig_score.add_vline(x=55, line_dash="dash", line_color="red", annotation_text="고위험 기준선(55)")
        st.plotly_chart(fig_score, use_container_width=True)

    # 고위험 고객 목록
    if len(churn_high) > 0:
        st.markdown("**이탈 고위험 고객 상세 목록**")
        churn_display = churn_high[
            ["customer_id", "segment", "주거래은행", "이탈위험점수",
             "days_since_last_transaction", "credit_score", "여신잔액_만원", "수신잔액_만원"]
        ].sort_values("이탈위험점수", ascending=False).rename(columns={
            "customer_id": "고객ID",
            "segment": "세그먼트",
            "days_since_last_transaction": "마지막거래(일전)",
            "credit_score": "신용점수",
            "여신잔액_만원": "여신잔액(만원)",
            "수신잔액_만원": "수신잔액(만원)",
        })
        st.dataframe(churn_display, use_container_width=True, hide_index=True)


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main() -> None:
    df_full = load_data()
    filtered = build_sidebar(df_full)

    st.title("🏦 마이데이터 AI 분석 대시보드")
    st.caption("80명의 더미 고객 데이터 기반 — VIP · 일반 · 절약형 · 비활성 4개 세그먼트 · 5개 주거래은행 분석")
    st.markdown("---")

    if filtered.empty:
        st.warning("선택된 조건에 해당하는 고객이 없습니다. 필터를 조정해주세요.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 전체 개요", "🔍 세그먼트 분석", "👤 고객 상세", "🤖 AI 인사이트"]
    )

    with tab1:
        tab_overview(filtered)
    with tab2:
        tab_segment(filtered)
    with tab3:
        tab_detail(filtered)
    with tab4:
        tab_insights(filtered)


if __name__ == "__main__":
    main()
