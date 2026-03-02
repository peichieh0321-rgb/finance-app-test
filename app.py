import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. 初始化介面 ---
st.set_page_config(page_title="雲端記帳表", layout="wide")
st.title("👨‍👩‍👧‍👦 家庭記帳看板 (Google Sheets 版)")

# --- 2. 建立 Google Sheets 連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取現有資料
try:
    df = conn.read(ttl=0) # ttl=0 表示每次都讀取最新資料，不使用快取
except:
    # 如果表單全空，建立一個空的 DataFrame
    df = pd.DataFrame(columns=['date', 'type', 'amount', 'category', 'sub_cat', 'item', 'city', 'paid_by', 'share_by', 'payment_method', 'comment'])

# --- 3. 側邊欄：新增帳目 ---
st.sidebar.header("✍️ 新增帳目")
with st.sidebar.form("add_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    record_type = st.radio("收支類型", ["支出", "收入"], horizontal=True)
    
    if record_type == "支出":
        cat_options = ["🍱 飲食", "🚌 交通", "🛍️ 購物", "🏠 住屋", "🎮 娛樂", "💡 其他", "🍱 Dine-Out", "🍱 Dessert/Drinks", "🛍️ Beauty&Salon","🛍️ Clothing&SHoes","Grocery-Food","Theo", "Loan & Insurance & HOA/DayCare", "Suncreek House Expense", "Yearly/Monthly Subscription", "House Expense", "Car Other Expense", "Ota/Maple Related Expense", "Entertainment (local)"]
    else:
        cat_options = ["💰 薪資", "🧧 獎金", "📈 投資收益", "House Rent"]
    
    category = st.selectbox("分類", cat_options)
    payment_method = st.selectbox("支付方式", ["Cash", "Chase checking","BOA Travel","Citi DC","Chase Unlimited","Amex Blue","Chase CSP","Citi Costco","Chase Freedom","Chase CSR","Chase Hyatt","BOA Alaska","Amex Everyday","Amex Hilton","Citi Strata","Chase Amazon","Recognition"])
    
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
        # 建立新資料列
        new_row = pd.DataFrame([{
            "date": date.strftime("%Y-%m-%d"),
            "type": record_type,
            "amount": amount,
            "category": category,
            "sub_cat": sub_cat,
            "item": item,
            "city": city,
            "paid_by": paid_by,
            "share_by": share_by,
            "payment_method": payment_method,
            "comment": comment
        }])
        
        # 合併並更新 Google Sheets
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.sidebar.success("✅ 雲端儲存成功！")
        st.rerun()

# --- 4. 看板與圖表顯示 (與之前邏輯相同) ---
if not df.empty:
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    current_month = datetime.now().month
    current_year = datetime.now().year
    this_month_df = df[(df['date_dt'].dt.month == current_month) & (df['date_dt'].dt.year == current_year)]
    
    m_income = this_month_df[this_month_df['type'] == '收入']['amount'].sum()
    m_expense = this_month_df[this_month_df['type'] == '支出']['amount'].sum()
    
    st.markdown(f"### 🗓️ {current_year} 年 {current_month} 月 概況")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("本月總支出", f"${m_expense:,.2f}")
    kpi2.metric("本月總收入", f"${m_income:,.2f}")
    kpi3.metric("本月盈餘", f"${(m_income - m_expense):,.2f}")
    
    st.divider()

    tab1, tab2 = st.tabs(["📝 編輯帳目", "📊 統計圖表"])

    with tab1:
        st.subheader("📋 雲端資料同步管理")
        edited_df = st.data_editor(df.drop(columns=['date_dt']), use_container_width=True, num_rows="dynamic", hide_index=True)
        if st.button("🚀 同步修改到 Google Sheets"):
            conn.update(data=edited_df)
            st.success("✅ 雲端已同步！")
            st.rerun()

    with tab2:
        group_cols = st.multiselect("統計維度:", options=['type', 'category', 'sub_cat', 'paid_by'], default=['category', 'sub_cat'])
        if group_cols:
            pivot_df = df.groupby(group_cols)['amount'].sum().reset_index()
            fig = px.sunburst(pivot_df, path=group_cols, values='amount')
            fig.update_traces(textinfo="label+value", texttemplate='%{label}<br>$%{value:,.2f}')
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("請輸入資料開始雲端同步。")
