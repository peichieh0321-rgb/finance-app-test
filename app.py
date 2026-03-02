import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. 初始化介面 ---
st.set_page_config(page_title="雲端記帳表", layout="wide")
st.title("👨‍👩‍👧‍👦 家庭記帳看板 (進階趨勢版)")

# --- 2. 建立 Google Sheets 連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl=0)
except:
    df = pd.DataFrame(columns=['date', 'type', 'amount', 'category', 'sub_cat', 'item', 'city', 'paid_by', 'share_by', 'payment_method', 'comment'])

# --- 3. 側邊欄：新增帳目 (維持原樣) ---
st.sidebar.header("✍️ 新增帳目")
with st.sidebar.form("add_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    record_type = st.radio("收支類型", ["支出", "收入"], horizontal=True)
    
    if record_type == "支出":
        cat_options = ["🍱 飲食", "🚌 交通", "🛍️ 購物", "🏠 住屋", "🎮 娛樂", "💡 其他", "🍱 Dine-Out", "🍱 Dessert/Drinks", "🛍️ Beauty&Salon","🛍️ Clothing&SHoes","Grocery-Food","Theo", "Loan & Insurance & HOA/DayCare", "Suncreek House Expense", "Yearly/Monthly Subscription", "House Expense", "Car Other Expense", "Ota/Maple Related Expense", "Entertainment (local)"]
    else:
        cat_options = ["💰 薪資", "🧧 獎金", "📈 投資收益", "House Rent"]
    
    category = st.selectbox("分類", cat_options)
    payment_method = st.selectbox("支付方式", ["Chase checking","Chase Freedom","Chase Unlimited","Chase CSP","Chase CSR","Chase Amazon","Chase Hyatt",
        "Citi DC","Citi Strata","Citi Costco",
        "BOA Alaska","BOA Travel","Amex Blue","Amex Everyday","Amex Hilton",
        "💵 Cash", "Recognition"])
    
    col_sub, col_city = st.columns(2)
    with col_sub:
        sub_cat = st.text_input("子分類 (Sub-Cat)", value="")
    with col_city:
        city = st.text_input("城市", value="Lake Oswego")
    
    col_paid, col_share = st.columns(2)
    with col_paid:
        paid_by = st.selectbox("付款人", ["Betty", "Jack", "Both", "Other"])
    with col_share:
        share_by = st.selectbox("拆帳", ["50/50", "Betty Only", "Jack Only"])

    item = st.text_input("項目名稱")
    amount = st.number_input("金額 ($$$)", min_value=0.0)
    comment = st.text_area("備註")
    
    submit = st.form_submit_button("💾 儲存到雲端")

    if submit and item:
        new_row = pd.DataFrame([{"date": date.strftime("%Y-%m-%d"), "type": record_type, "amount": amount, "category": category, "sub_cat": sub_cat, "item": item, "city": city, "paid_by": paid_by, "share_by": share_by, "payment_method": payment_method, "comment": comment}])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.sidebar.success("✅ 雲端儲存成功！")
        st.rerun()

# --- 4. 數據處理與 KPI ---
if not df.empty:
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    
    # 計算本月
    current_month = datetime.now().month
    current_year = datetime.now().year
    this_month_df = df[(df['date_dt'].dt.month == current_month) & (df['date_dt'].dt.year == current_year)]
    
    # (a) 計算上月盈餘
    first_day_this_month = datetime.now().replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    last_month_df = df[(df['date_dt'].dt.month == last_day_last_month.month) & (df['date_dt'].dt.year == last_day_last_month.year)]
    
    lm_income = last_month_df[last_month_df['type'] == '收入']['amount'].sum()
    lm_expense = last_month_df[last_month_df['type'] == '支出']['amount'].sum()
    lm_balance = lm_income - lm_expense

    st.markdown(f"### 🗓️ {current_year} 年 {current_month} 月 概況")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("本月總支出", f"${this_month_df[this_month_df['type'] == '支出']['amount'].sum():,.2f}")
    kpi2.metric("本月總收入", f"${this_month_df[this_month_df['type'] == '收入']['amount'].sum():,.2f}")
    kpi3.metric("本月盈餘", f"${(this_month_df[this_month_df['type'] == '收入']['amount'].sum() - this_month_df[this_month_df['type'] == '支出']['amount'].sum()):,.2f}")
    kpi4.metric("💰 上月總盈餘", f"${lm_balance:,.2f}", delta_color="normal")
    
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📝 編輯帳目", "📊 分類統計", "📈 趨勢分析"])

    with tab1:
        st.subheader("📋 雲端資料管理")
        edited_df = st.data_editor(df.drop(columns=['date_dt']), use_container_width=True, num_rows="dynamic", hide_index=True)
        if st.button("🚀 同步修改"):
            conn.update(data=edited_df)
            st.rerun()

    with tab2:
        st.subheader("📊 現階段分類佔比")
        group_cols = st.multiselect("統計維度:", options=['type', 'category', 'sub_cat', 'paid_by'], default=['category', 'sub_cat'])
        if group_cols:
            pivot_df = df.groupby(group_cols)['amount'].sum().reset_index()
            fig = px.sunburst(pivot_df, path=group_cols, values='amount', color='amount', color_continuous_scale='RdBu')
            fig.update_traces(textinfo="label+value", texttemplate='%{label}<br>$%{value:,.2f}')
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📈 逐月收支趨勢 (Pivot)")
        # 建立「月份」欄位供樞紐分析
        df['Month'] = df['date_dt'].dt.strftime('%Y-%m')
        
        # 讓使用者選取想追蹤的維度
        trend_dim = st.selectbox("選擇想分析的趨勢維度:", options=['category', 'type', 'paid_by', 'payment_method'])
        
        # 樞紐分析表：X軸為月份，分類為欄位
        trend_df = df.groupby(['Month', trend_dim])['amount'].sum().reset_index()
        
        # 繪製折線圖
        fig_trend = px.line(
            trend_df, 
            x='Month', 
            y='amount', 
            color=trend_dim, 
            markers=True,
            title=f"每月 {trend_dim} 金額走勢"
        )
        
        # 在折線點上直接顯示金額
        fig_trend.update_traces(
            texttemplate='$%{y:,.2f}', 
            textposition='top center'
        )
        fig_trend.update_layout(yaxis_title="金額 ($)", xaxis_title="月份")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # 顯示原始趨勢數據表格
        st.write("📋 趨勢數據明細:")
        st.dataframe(trend_df.pivot(index='Month', columns=trend_dim, values='amount').fillna(0).style.format("${:,.2f}"))

else:
    st.info("請輸入資料開始雲端同步。")

