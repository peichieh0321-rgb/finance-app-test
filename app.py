import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px

# --- 1. 資料庫初始化 (增加 sub_cat) ---
def init_db():
    conn = sqlite3.connect('my_expenses.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS expenses 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   date TEXT, 
                   type TEXT,
                   amount REAL,
                   category TEXT, 
                   sub_cat TEXT,
                   item TEXT, 
                   city TEXT,
                   paid_by TEXT,
                   share_by TEXT,
                   payment_method TEXT,
                   comment TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- 2. 介面設定 ---
st.set_page_config(page_title="簡易記帳表", layout="wide")
st.title("👨‍👩‍👧‍👦 家庭記帳 App (r1- 26 Mar 1)")

# --- 3. 側邊欄：新增帳目 (微調版) ---
st.sidebar.header("✍️ 新增帳目")
with st.sidebar.form("add_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    record_type = st.radio("收支類型", ["支出", "收入"], horizontal=True)
    
    # 1. 分類 (獨立一行)
    if record_type == "支出":
        cat_options = ["🍱 飲食", "🚌 交通", "🛍️ 購物", "🏠 住屋", "🎮 娛樂", "💡 其他", "🍱 Dine-Out", "🍱 Dessert/Drinks", "🛍️ Beauty&Salon","🛍️ Clothing&SHoes","Grocery-Food","Theo", "Loan & Insurance & HOA/DayCare", "Suncreek House Expense", "Yearly/Monthly Subscription", "House Expense", "Car Other Expense", "Ota/Maple Related Expense", "Entertainment (local)"]
    else:
        cat_options = ["💰 薪資", "🧧 獎金", "📈 投資收益", "House Rent"]
    
    category = st.selectbox("分類", cat_options)

    # 2. 支付方式 (獨立一行 - 因為你的選項非常多)
    payment_method = st.selectbox("支付方式", [
        "Chase checking","Chase Freedom","Chase Unlimited","Chase CSP","Chase CSR","Chase Amazon","Chase Hyatt",
        "Citi DC","Citi Strata","Citi Costco",
        "BOA Alaska","BOA Travel","Amex Blue","Amex Everyday","Amex Hilton",
        "💵 Cash", "Recognition"
    ])
    
    # 3. 子分類與城市 (併排一行)
    col_sub, col_city = st.columns(2)
    with col_sub:
        sub_cat = st.text_input("子分類 (Sub-Cat)", value="")
    with col_city:
        city = st.text_input("城市", value="Lake Oswego")
    
    # 4. 付款人與拆帳 (併排一行)
    col_paid, col_share = st.columns(2)
    with col_paid:
        paid_by = st.selectbox("付款人", ["Betty", "Jack", "Both", "Other"])
    with col_share:
        share_by = st.selectbox("拆帳", ["50/50", "Betty Only", "Jack Only"])

    item = st.text_input("項目名稱")
    amount = st.number_input("金額 ($$$)", min_value=0.0)
    comment = st.text_area("備註")
    
    submit = st.form_submit_button("💾 儲存紀錄")

    # (後續的插入資料邏輯與之前相同，請確保 SQL 指令中有包含 sub_cat)
    if submit and item:
        c = conn.cursor()
        c.execute('''INSERT INTO expenses (date, type, amount, category, sub_cat, item, city, paid_by, share_by, payment_method, comment) 
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)''', 
                  (date.strftime("%Y-%m-%d"), record_type, amount, category, sub_cat, item, city, paid_by, share_by, payment_method, comment))
        conn.commit()
        st.sidebar.success("儲存成功！")
        st.rerun()

# --- 4. 數據讀取與計算 ---
df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date DESC", conn)

if not df.empty:
    df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
    df['date_dt'] = df['date_dt'].fillna(datetime.now().replace(day=1))
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    this_month_df = df[(df['date_dt'].dt.month == current_month) & (df['date_dt'].dt.year == current_year)]
    
    m_income = this_month_df[this_month_df['type'] == '收入']['amount'].sum()
    m_expense = this_month_df[this_month_df['type'] == '支出']['amount'].sum()
    m_balance = m_income - m_expense

    st.markdown(f"### 🗓️ {current_year} 年 {current_month} 月 概況")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("本月總支出", f"${m_expense:,.2f}")
    kpi2.metric("本月總收入", f"${m_income:,.2f}")
    kpi3.metric("本月盈餘", f"${m_balance:,.2f}", delta=f"{m_balance:,.2f}")
    
    st.divider()

    # --- 5. 分頁功能 ---
    tab1, tab2, tab3 = st.tabs(["📝 編輯帳目", "📊 統計圖表", "🧮 拆帳建議"])

    with tab1:
        st.subheader("📋 帳目管理")
        display_df = df.drop(columns=['date_dt'])
        
        # 重新排序 DataFrame 欄位，讓 sub_cat 緊跟在 category 後面
        cols = list(display_df.columns)
        if 'sub_cat' in cols and 'category' in cols:
            cols.insert(cols.index('category') + 1, cols.pop(cols.index('sub_cat')))
            display_df = display_df[cols]

        edited_df = st.data_editor(
            display_df, 
            key="data_editor_subcat", 
            use_container_width=True,
            num_rows="dynamic",
            disabled=["id"],
            hide_index=True
        )

        if st.button("🚀 儲存所有修改"):
            try:
                c = conn.cursor()
                c.execute("DELETE FROM expenses")
                # 確保存回去的順序跟資料庫一致
                edited_df.to_sql('expenses', conn, if_exists='append', index=False)
                conn.commit()
                st.success("資料庫已更新！")
                st.rerun()
            except Exception as e:
                st.error(f"儲存失敗: {e}")

    with tab2:
        st.subheader("📊 動態樞紐分析與統計")
        group_cols = st.multiselect(
            "請選擇統計維度 (可複選並調整順序):",
            options=['type', 'category', 'sub_cat', 'paid_by', 'payment_method', 'city'],
            default=['category', 'sub_cat']
        )
        
        if group_cols:
            # 1. 基礎統計資料
            pivot_df = df.groupby(group_cols)['amount'].sum().reset_index()
            
            # 2. 顯示統計表格 (加上金額排序)
            st.write("統計結果摘要:")
            st.dataframe(
                pivot_df.sort_values(by='amount', ascending=False).style.format({"amount": "${:,.2f}"}), 
                use_container_width=True
            )
            
            # --- 3. 太陽圖 (Sunburst) 優化顯示金額 ---
            st.write("視覺化層級結構 (點擊區塊可縮放):")
            fig = px.sunburst(
                pivot_df, 
                path=group_cols, 
                values='amount',
                color='amount',
                color_continuous_scale='RdBu',
                title=f"按 {' > '.join(group_cols)} 統計之比例"
            )
            
            # 關鍵：強制在圖表上顯示文字 + 金額
            fig.update_traces(
                textinfo="label+value", # 顯示標籤 + 數值
                hovertemplate='<b>%{label}</b><br>金額: $%{value:,.2f}' # 滑鼠懸停格式
            )
            fig.update_layout(height=600, margin=dict(t=50, l=0, r=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 4. 長條圖 (Bar Chart) 直接顯示數字 ---
            if len(group_cols) >= 1:
                st.write("各類別金額對比:")
                fig_bar = px.bar(
                    pivot_df, 
                    x=group_cols[0], 
                    y='amount', 
                    color=group_cols[1] if len(group_cols) > 1 else None,
                    text_auto='.2s', # 自動顯示縮寫數字 (如 1.5k)
                    title="各類別總額分析"
                )
                
                # 強制長條圖顯示完整金額與格式
                fig_bar.update_traces(
                    texttemplate='$%{y:,.2f}', 
                    textposition='outside' # 數字顯示在柱子上方
                )
                fig_bar.update_layout(yaxis_title="金額 ($)", xaxis_title=group_cols[0])
                st.plotly_chart(fig_bar, use_container_width=True)
                
        else:
            st.warning("請至少選擇一個維度進行統計。")

    with tab3:
        shared_df = df[(df['type'] == '支出') & (df['share_by'] == '50/50')]
        if not shared_df.empty:
            b_paid = shared_df[shared_df['paid_by'] == 'Betty']['amount'].sum()
            j_paid = shared_df[shared_df['paid_by'] == 'Jack']['amount'].sum()
            diff = (b_paid - j_paid) / 2
            st.metric("Betty 應收回" if diff > 0 else "Jack 應收回", f"${abs(diff):,.2f}")
else:
    st.info("請在左側輸入第一筆資料。")