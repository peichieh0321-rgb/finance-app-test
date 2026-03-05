import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. 初始化介面 ---
st.set_page_config(page_title="雲端記帳表", layout="wide")
st.title("👨‍👩‍👧‍👦 家庭記帳App (Jack/Betty)")

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
        st.subheader("📊 動態樞紐分析與統計")

        # --- 關鍵修復：強制轉換 amount 為數字，避免排序報錯 ---
        if not df.empty:
            df['amount'] = pd.to_numeric(df[ 'amount'], errors='coerce').fillna(0)
            # 同時確保日期格式正確，方便後續月份篩選
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # --------------------------------------------------

        # ... 接續後面的月份篩選與統計代碼 ...
        # --- 1. 月份篩選邏輯 ---
        if not df.empty:
            # 確保日期欄位是 datetime 格式
            temp_df = df.copy()
            temp_df['date'] = pd.to_datetime(temp_df['date'])
            # 建立「年-月」字串欄位用於篩選
            temp_df['month_year'] = temp_df['date'].dt.strftime('%Y-%m')
            
            # 取得所有唯一的月份並排序（新到舊）
            available_months = sorted(temp_df['month_year'].unique(), reverse=True)
            
            # 計算「上個月」的字串 (以今天日期為準往前推一個月)
            from datetime import date, timedelta
            first_day_this_month = date.today().replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            last_month_str = last_day_last_month.strftime('%Y-%m')

            # 如果資料裡有上個月就當 default，沒有就選最新的月份
            default_val = [last_month_str] if last_month_str in available_months else [available_months[0]]

            # 月份多選器
            selected_months = st.multiselect(
                "📅 選擇要統計的月份:",
                options=available_months,
                default=default_val
            )

            # 根據選取月份過濾資料
            filtered_df = temp_df[temp_df['month_year'].isin(selected_months)]
        else:
            filtered_df = pd.DataFrame()

        # --- 2. 原有的統計維度選擇 ---
        group_cols = st.multiselect(
            "選擇統計維度 (可拖曳排序):",
            options=['type', 'category', 'sub_cat', 'paid_by', 'payment_method', 'city'],
            default=['category', 'sub_cat']
        )
        
        if not filtered_df.empty and group_cols:
            # 1. 計算統計數據
            pivot_df = filtered_df.groupby(group_cols)['amount'].sum().reset_index()
            
            # 2. 顯示表格
            st.write(f"📋 統計結果摘要 ({', '.join(selected_months)}):")
            st.dataframe(
                pivot_df.sort_values(by='amount', ascending=False).style.format({"amount": "${:,.2f}"}), 
                use_container_width=True
            )
            
            # --- 3. 太陽圖 (Sunburst) ---
            st.write("🎯 層級分布 (點擊區塊可縮放):")
            fig = px.sunburst(
                pivot_df, 
                path=group_cols, 
                values='amount',
                color='amount',
                color_continuous_scale='RdBu'
            )
            
            fig.update_traces(
                textinfo="label+value", 
                texttemplate='%{label}<br>$%{value:,.2f}',
                hovertemplate='<b>%{label}</b><br>總額: $%{value:,.2f}'
            )
            fig.update_layout(height=600, margin=dict(t=50, l=0, r=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 4. 長條圖 (Bar Chart) ---
            st.write("📈 各類別金額對比:")
            fig_bar = px.bar(
                pivot_df, 
                x=group_cols[0], 
                y='amount', 
                color=group_cols[1] if len(group_cols) > 1 else None
            )
            
            fig_bar.update_traces(
                texttemplate='$%{y:,.2f}', 
                textposition='outside'
            )
            fig_bar.update_layout(
                yaxis_title="金額 ($)", 
                xaxis_title=group_cols[0],
                uniformtext_minsize=8, 
                uniformtext_mode='hide'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        elif filtered_df.empty and not df.empty:
            st.info("ℹ️ 請選擇至少一個月份來顯示統計數據。")
        else:
            st.warning("⚠️ 請選擇維度。")
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





