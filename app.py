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
    if not df.empty:
        # 強制轉換日期格式確保排序正確，並按日期遞減排序（新到舊）
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df.sort_values(by='date', ascending=False).reset_index(drop=True)
except:
    df = pd.DataFrame(columns=['date', 'type', 'amount', 'category', 'sub_cat', 'item', 'city', 'paid_by', 'share_by', 'payment_method', 'comment'])

# --- 3. 側邊欄：新增帳目 (維持原樣) ---
st.sidebar.header("✍️ 新增帳目")
with st.sidebar.form("add_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    record_type = st.radio("收支類型", ["支出", "收入"], horizontal=True)
    
    if record_type == "支出":
        cat_options = ["🍱 飲食", "🚌 交通", "🛍️ 購物", "🏠 住屋", "🎮 娛樂", "🪙 固定收支", "💡 其他", "✈️ Travel", "🍱 Dine-Out", "🍱 Dessert/Drinks", "🛍️ Beauty&Salon","🛍️ Clothing&Shoes","Grocery-Food", "🍼 Baby" , "Yearly/Monthly Subscription", "House Expense", "Car Other", "Ota/Maple Related", "Entertainment (local)"]
    else:
        cat_options = ["💰 薪資", "🪙 固定收支", "🧧 獎金", "📈 投資收益", "House Rent"]
    
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

    # --- 🤖 自動化工具：一鍵預填 ---
    st.subheader("🤖 自動化工具")
    
    # 建立兩欄，讓畫面更整齊
    tool_col1, tool_col2 = st.columns([1, 2])
    
    with tool_col1:
        if st.button("✨ 預填本月固定收支"):
            # 1. 定義時間範圍
            this_month_str = datetime.now().strftime("%Y-%m")
            last_month_date = datetime.now().replace(day=1) - timedelta(days=1)
            last_month_str = last_month_date.strftime("%Y-%m")
            
            # 2. 篩選上個月分類為「🪙 固定收支」的資料
            fixed_template = df[
                (df['date_dt'].dt.strftime('%Y-%m') == last_month_str) & 
                (df['category'] == "🪙 固定收支")
            ].copy()
            
            if fixed_template.empty:
                st.warning(f"🔍 在 {last_month_str} 中沒找到分類為「🪙 固定收支」的項目。")
            else:
                # 3. 防呆：檢查本月是否已存在（比對 項目名稱+金額）
                # 這裡使用 this_month_df (前面 KPI 區塊已定義)
                existing_check = this_month_df.apply(lambda x: f"{x['item']}_{x['amount']}", axis=1).tolist()
                
                new_entries = []
                skipped_items = []
                
                for _, row in fixed_template.iterrows():
                    item_id = f"{row['item']}_{row['amount']}"
                    
                    if item_id not in existing_check:
                        # 複製資料並更新日期為今日
                        new_row = row.drop(['date_dt']).to_dict()
                        new_row['date'] = datetime.now().strftime("%Y-%m-%d")
                        new_entries.append(new_row)
                    else:
                        skipped_items.append(row['item'])
                
                # 4. 寫入雲端
                if new_entries:
                    new_data_df = pd.DataFrame(new_entries)
                    # 移除可能的 date_dt 欄位再合併，確保 Google Sheets 格式純淨
                    final_update_df = pd.concat([df.drop(columns=['date_dt'], errors='ignore'), new_data_df], ignore_index=True)
                    conn.update(data=final_update_df)
                    
                    st.success(f"✅ 已成功新增 {len(new_entries)} 筆固定收支！")
                    if skipped_items:
                        st.info(f"⏭️ 已跳過重複項目: {', '.join(skipped_items)}")
                    st.rerun()
                else:
                    st.info("查無新項目：本月的所有固定收支似乎都已經記過了。")

    with tool_col2:
        st.caption("💡 說明：系統會抓取上個月分類為「🪙 固定收支」的內容，並自動過濾本月已存在的重複項。")
    
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

        # --- 數據清洗與預處理 ---
        if not df.empty:
            df_clean = df.copy()
            df_clean['amount'] = pd.to_numeric(df_clean['amount'], errors='coerce').fillna(0)
            df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce')
            
            # 1. 月份篩選邏輯
            df_clean['month_year'] = df_clean['date'].dt.strftime('%Y-%m')
            available_months = sorted(df_clean['month_year'].dropna().unique(), reverse=True)
            
            from datetime import date, timedelta
            last_month_str = (date.today().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            default_month = [last_month_str] if last_month_str in available_months else [available_months[0]]

            col1, col2 = st.columns(2)
            with col1:
                selected_months = st.multiselect("📅 選擇統計月份:", options=available_months, default=default_month)
            
            # --- 核心新增：收支類型篩選 ---
            with col2:
                view_type = st.radio("💰 統計類型:", ["支出", "收入"], horizontal=True)

            # 根據月份與收支類型進行過濾
            filtered_df = df_clean[
                (df_clean['month_year'].isin(selected_months)) & 
                (df_clean['type'] == view_type)
            ]
        else:
            filtered_df = pd.DataFrame()

        # 2. 維度選擇
        group_cols = st.multiselect(
            "選擇統計維度 (可拖曳排序):",
            options=['category', 'sub_cat', 'paid_by', 'payment_method', 'city'],
            default=['category', 'sub_cat']
        )
        
        if not filtered_df.empty and group_cols:
            # 計算統計數據
            pivot_df = filtered_df.groupby(group_cols)['amount'].sum().reset_index()
            
            # 顯示表格
            total_amt = pivot_df['amount'].sum()
            st.metric(f"合計總{view_type}", f"${total_amt:,.2f}")
            
            st.write(f"📋 {view_type}分類摘要 ({', '.join(selected_months)}):")
            st.dataframe(
                pivot_df.sort_values(by='amount', ascending=False).style.format({"amount": "${:,.2f}"}), 
                use_container_width=True
            )
            
            # --- 3. 太陽圖 (Sunburst) ---
            # 使用收支類型決定配色：支出用紅橘色調，收入用綠藍色調
            color_scale = 'OrRd' if view_type == "支出" else 'GnBu'
            
            fig = px.sunburst(
                pivot_df, path=group_cols, values='amount',
                color='amount', color_continuous_scale=color_scale
            )
            
            fig.update_traces(
                textinfo="label+value", 
                texttemplate='%{label}<br>$%{value:,.2f}'
            )
            fig.update_layout(height=500, margin=dict(t=30, l=0, r=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 4. 長條圖 (Bar Chart) ---
            fig_bar = px.bar(
                pivot_df, x=group_cols[0], y='amount', 
                color='amount', color_continuous_scale=color_scale
            )
            fig_bar.update_traces(texttemplate='$%{y:,.2f}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        elif filtered_df.empty and not df.empty:
            st.info(f"ℹ️ 選擇的範圍內沒有 {view_type} 數據。")
        else:
            st.warning("⚠️ 請選擇維度。")
    with tab3:
        st.subheader("📈 逐月收支趨勢 (Pivot)")
        
        if not df.empty:
            # 1. 準備資料與清洗
            df_trend_base = df.copy()
            df_trend_base['amount'] = pd.to_numeric(df_trend_base['amount'], errors='coerce').fillna(0)
            df_trend_base['date_dt'] = pd.to_datetime(df_trend_base['date'], errors='coerce')
            df_trend_base['Month'] = df_trend_base['date_dt'].dt.strftime('%Y-%m')
            
            # 移除無效日期並排序
            df_trend_base = df_trend_base.dropna(subset=['Month']).sort_values('Month')

            # --- 核心改進：新增收支切換 ---
            trend_type = st.radio("💰 選擇趨勢類型:", ["支出", "收入"], horizontal=True, key="trend_type_radio")
            
            # 先根據收支類型過濾大框架
            df_type_filtered = df_trend_base[df_trend_base['type'] == trend_type]

            # 2. 選擇維度 (排除 'type'，因為已經在上方選擇了)
            trend_dim = st.selectbox(
                "選擇想分析的趨勢維度:", 
                options=['category', 'sub_cat', 'paid_by', 'payment_method', 'city'],
                key="trend_dim_select"
            )
            
            # 處理混合類型與空值
            df_type_filtered[trend_dim] = df_type_filtered[trend_dim].fillna("Unspecified").astype(str)
            all_items = sorted(df_type_filtered[trend_dim].unique().tolist())
            
            selected_items = st.multiselect(
                f"篩選具體的 {trend_dim} 項目:",
                options=all_items,
                default=all_items[:10] if len(all_items) > 10 else all_items # 若項目太多，預設選前10個避免圖表太亂
            )

            if selected_items:
                # 根據選取項目過濾
                filtered_trend_df = df_type_filtered[df_type_filtered[trend_dim].isin(selected_items)]
                
                # 樞紐分析：加總金額
                trend_df = filtered_trend_df.groupby(['Month', trend_dim])['amount'].sum().reset_index()
                
                # 3. 繪製折線圖
                # 設定配色：支出用溫暖色系，收入用冷色系
                color_scheme = px.colors.qualitative.Prism if trend_type == "支出" else px.colors.qualitative.Safe
                
                fig_trend = px.line(
                    trend_df, 
                    x='Month', 
                    y='amount', 
                    color=trend_dim, 
                    markers=True,
                    title=f"每月 {trend_type} - {trend_dim} 金額走勢",
                    color_discrete_sequence=color_scheme,
                    category_orders={"Month": sorted(trend_df['Month'].unique())}
                )
                
                fig_trend.update_traces(
                    texttemplate='$%{y:,.0f}', 
                    textposition='top center'
                )
                
                fig_trend.update_layout(
                    yaxis_title=f"{trend_type}金額 ($)", 
                    xaxis_title="月份",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
                
                # 4. 顯示數據明細
                st.write(f"📋 {trend_type}趨勢數據明細 (Pivot):")
                if not trend_df.empty:
                    pivot_display = trend_df.pivot(index='Month', columns=trend_dim, values='amount').fillna(0)
                    st.dataframe(pivot_display.style.format("${:,.2f}"), use_container_width=True)
            else:
                st.warning(f"⚠️ 請至少選擇一個項目以顯示{trend_type}趨勢。")
        else:
            st.info("尚無資料可供分析。")

else:
    st.info("請輸入資料開始雲端同步。")












