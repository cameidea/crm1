import streamlit as st
import pandas as pd
import datetime
import time
import hashlib
import calendar
import base64
import os
from streamlit_gsheets import GSheetsConnection

# --- 設定頁面 ---
st.set_page_config(page_title="CAMEiDEA CRM (Cloud)", page_icon="☁️", layout="wide")

# --- 1. CSS 樣式 ---
def local_css():
    st.markdown("""
    <style>
        header {visibility: hidden;}
        .main .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        .stApp { background-color: #0b0e14; color: #ffffff; }
        section[data-testid="stSidebar"] { background-color: #13151a; border-right: 1px solid #2d3342; }
        
        .stTextInput > div > div > input, .stTextArea > div > div > textarea, 
        .stDateInput > div > div > input, .stSelectbox > div > div > div, .stNumberInput > div > div > input {
            background-color: #13151a; color: #ffffff; border: 1px solid #2d3342; border-radius: 8px; padding: 10px;
        }
        
        .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 1px solid #2d3342; }
        .stTabs [data-baseweb="tab"] {
            height: auto; white-space: pre-wrap; background-color: transparent;
            border-radius: 4px 4px 0 0; color: #a0aec0; padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1a1d24; color: #ffffff; border-bottom: 2px solid #4D5EEE;
        }

        .client-card { background-color: #1a1d24; padding: 15px; border-radius: 10px; border: 1px solid #2d3342; margin-bottom: 10px; }
        .role-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 5px; }
        .role-admin { background-color: #4D5EEE; color: white; }
        .role-op { background-color: #2d3342; color: #a0aec0; }
        .owner-tag { font-size: 0.75em; color: #a0aec0; background-color: #13151a; padding: 2px 6px; border-radius: 4px; margin-top: 5px; display: inline-block;}

        div.stButton > button[kind="primary"] {
            background-color: #4D5EEE; color: white; border: none; border-radius: 6px; padding: 0.6rem 1rem; font-weight: 600; font-size: 1rem;
        }
        div.stButton > button[kind="primary"]:hover { background-color: #3b4bcc; }
        div.stButton > button[kind="secondary"] {
            background-color: transparent; color: #ff4b4b; border: 1px solid #ff4b4b; border-radius: 6px;
        }
        h1, h2, h3 { font-family: 'Inter', sans-serif; color: #ffffff; }
        p, label { color: #a0aec0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Google Sheets 資料庫功能 ---
# 警告：Google Sheets 不是即時資料庫，大量寫入可能會慢，且不適合高併發
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    """讀取某個分頁的所有資料"""
    # ttl=0 代表不快取，每次都重新抓取，確保資料最新
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except Exception as e:
        st.error(f"讀取 {worksheet_name} 失敗: {e}")
        return pd.DataFrame()

def save_data(worksheet_name, df):
    """將 DataFrame 寫回分頁 (覆蓋模式)"""
    try:
        conn.update(worksheet=worksheet_name, data=df)
        st.toast(f"已同步至雲端: {worksheet_name}")
    except Exception as e:
        st.error(f"寫入 {worksheet_name} 失敗: {e}")

def get_next_id(df):
    """產生新的 ID (模擬 Auto Increment)"""
    if df.empty or 'id' not in df.columns:
        return 1
    # 確保 id 是數值型別
    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0)
    return int(df['id'].max()) + 1

def hash_password(password): return hashlib.sha256(str.encode(password)).hexdigest()

def verify_user(username, password):
    df = get_data("users")
    if df.empty: return False, None, None
    
    user_row = df[df['username'] == username]
    if not user_row.empty:
        stored_pw = user_row.iloc[0]['password']
        if stored_pw == hash_password(password):
            return True, user_row.iloc[0]['role'], user_row.iloc[0]['sales_name']
    return False, None, None

def create_user(username, password, name, role='operator'):
    df = get_data("users")
    if not df.empty and username in df['username'].values:
        return False
    
    new_row = pd.DataFrame([{
        "username": username,
        "password": hash_password(password),
        "role": role,
        "sales_name": name
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    save_data("users", df)
    return True

def get_img_as_base64(file):
    if not os.path.exists(file): return None
    try:
        with open(file, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return None

# --- 3. 頁面功能 ---

def page_login_register():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c_left, c_right = st.columns([2, 3], gap="large")
    
    img_path = "png-02.png" 
    img_base64 = get_img_as_base64(img_path)

    with c_left:
        st.markdown("""<div style='display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%;'>""", unsafe_allow_html=True)
        if img_base64:
            st.markdown(f'<img src="data:image/png;base64,{img_base64}" style="max-width: 280px;">', unsafe_allow_html=True)
        else:
            st.markdown("<h1>☁️ CRM</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown("<br>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["登入", "註冊 (操作員)"])
        
        with tab1:
            with st.form("login_form"):
                u = st.text_input("帳號", key="login_u")
                p = st.text_input("密碼", type="password", key="login_p")
                if st.form_submit_button("登入", type="primary", use_container_width=True):
                    is_valid, role, s_name = verify_user(u, p)
                    if is_valid:
                        st.session_state['logged_in'] = True
                        st.session_state['user'] = u
                        st.session_state['role'] = role
                        st.session_state['real_name'] = s_name
                        st.rerun()
                    else: st.error("帳號或密碼錯誤")
        
        with tab2:
            with st.form("reg"):
                nu = st.text_input("設定帳號")
                nn = st.text_input("業務姓名 (顯示名稱)")
                np = st.text_input("設定密碼", type="password")
                if st.form_submit_button("註冊", type="primary", use_container_width=True):
                    if len(nu)>0 and len(np)>0 and len(nn)>0:
                        if create_user(nu, np, nn, 'operator'): 
                            st.success(f"註冊成功！歡迎 {nn}，請重新登入。")
                            time.sleep(1); st.rerun()
                        else: st.error("帳號已存在")
                    else: st.error("所有欄位皆為必填")

def render_client_detail(client_id):
    # 讀取所有需要的資料
    df_clients = get_data("clients")
    # 確保 ID 格式一致
    df_clients['id'] = pd.to_numeric(df_clients['id'], errors='coerce')
    client_row = df_clients[df_clients['id'] == client_id]

    if client_row.empty: st.session_state['selected_client_id'] = None; st.rerun(); return
    
    # 轉成 dict 方便使用
    c_data = client_row.iloc[0].to_dict()
    
    user_role = st.session_state.get('role', 'operator')
    current_user = st.session_state.get('user')
    
    if user_role != 'admin' and c_data['created_by'] != current_user:
        st.error("⛔ 您沒有權限查看此客戶資料。")
        if st.button("返回"): st.session_state['selected_client_id'] = None; st.rerun()
        return

    if st.button("⬅️ 返回客戶列表"):
        st.session_state['selected_client_id'] = None
        st.rerun()

    df_cats = get_data("categories")
    cats = df_cats['name'].tolist() if not df_cats.empty else []
    
    # 計算累積消費
    df_sales = get_data("sales")
    df_sales['client_id'] = pd.to_numeric(df_sales['client_id'], errors='coerce')
    client_sales = df_sales[df_sales['client_id'] == client_id].copy()
    total_spent = client_sales['sale_amount'].sum() if not client_sales.empty else 0

    st.markdown(f"### 👤 {c_data['name']} <span style='font-size:0.6em; color:#a0aec0'>(累積消費: ${total_spent:,.0f})</span>", unsafe_allow_html=True)
    
    with st.expander("✏️ 編輯基本資料"):
        with st.form("edit_client"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nn = st.text_input("名稱", value=c_data['name'])
                nph = st.text_input("電話", value=c_data['phone'])
                nem = st.text_input("Email", value=c_data['email'])
            with c2:
                ncat = st.selectbox("分類", cats, index=cats.index(c_data['category']) if c_data['category'] in cats else 0)
                nproj = st.text_input("專案", value=c_data['project'])
            with c3:
                ntitle = st.text_input("抬頭 (Title)", value=c_data['title'])
                ninv = st.text_input("統編 (Tax ID)", value=c_data['invoice_number'])
            
            if st.form_submit_button("💾 更新資料", type="primary"):
                # 更新 DataFrame
                df_clients.loc[df_clients['id'] == client_id, ['name', 'phone', 'email', 'category', 'project', 'title', 'invoice_number']] = [nn, nph, nem, ncat, nproj, ntitle, ninv]
                save_data("clients", df_clients)
                st.success("已更新"); time.sleep(0.5); st.rerun()

    st.markdown("---")
    t1, t2, t3 = st.tabs(["💰 購買紀錄", "📝 跟進紀錄", "🕒 歷史紀錄"])
    
    with t1:
        # 顯示購買紀錄
        if not client_sales.empty:
            client_sales = client_sales.sort_values('transaction_date', ascending=False)
        
        if user_role == 'admin':
            st.info("➕ 新增購買紀錄")
            sales_owner = c_data['created_by']
            st.caption(f"ℹ️ 業績歸屬：**{sales_owner}**")
            with st.form("add_sale"):
                c1, c2, c3 = st.columns([2,3,2])
                sd = c1.date_input("日期", datetime.date.today())
                si = c2.text_input("項目")
                sinv = c2.text_input("發票")
                sa = c3.number_input("金額", min_value=0)
                if st.form_submit_button("➕ 新增", type="primary"):
                    if si:
                        new_sale = pd.DataFrame([{
                            "id": get_next_id(df_sales),
                            "client_id": client_id,
                            "transaction_date": sd.strftime("%Y-%m-%d"),
                            "item_name": si,
                            "invoice_number": sinv,
                            "sale_amount": sa,
                            "created_by": sales_owner
                        }])
                        df_sales = pd.concat([df_sales, new_sale], ignore_index=True)
                        save_data("sales", df_sales)
                        st.success("已新增"); time.sleep(0.5); st.rerun()
                    else: st.error("請輸入項目")
        else: st.warning("🔒 僅管理員可新增")

        if not client_sales.empty:
            for idx, row in client_sales.iterrows():
                with st.container():
                    cols = st.columns([2, 3, 2, 2])
                    cols[0].write(row['transaction_date'])
                    cols[1].write(f"**{row['item_name']}**")
                    cols[2].write(f"發票: {row['invoice_number']}")
                    cols[3].write(f"${row['sale_amount']:,.0f}")
                    st.markdown("<hr style='margin:5px 0; border-color:#2d3342'>", unsafe_allow_html=True)

    with t2:
        with st.form("add_inter"):
            c1, c2 = st.columns(2)
            ld = c1.date_input("日期", datetime.date.today())
            fd = c2.date_input("提醒日", datetime.date.today()+datetime.timedelta(days=3))
            cnt = st.text_area("內容")
            rem = st.text_input("提醒")
            if st.form_submit_button("💾 儲存", type="primary"):
                df_inter = get_data("interactions")
                if cnt or rem:
                    new_inter = pd.DataFrame([{
                        "id": get_next_id(df_inter),
                        "client_id": client_id,
                        "log_date": ld.strftime("%Y-%m-%d"),
                        "content": cnt,
                        "follow_up_date": fd.strftime("%Y-%m-%d"),
                        "reminder_note": rem,
                        "updated_by": st.session_state['user']
                    }])
                    df_inter = pd.concat([df_inter, new_inter], ignore_index=True)
                    save_data("interactions", df_inter)
                    st.success("已儲存"); time.sleep(0.5); st.rerun()
                else: st.error("需填寫內容")

    with t3:
        df_inter = get_data("interactions")
        if not df_inter.empty:
            df_inter['client_id'] = pd.to_numeric(df_inter['client_id'], errors='coerce')
            c_inter = df_inter[df_inter['client_id'] == client_id].sort_values('log_date', ascending=False)
            st.dataframe(c_inter[['log_date','content','follow_up_date','reminder_note','updated_by']], use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🗑️ 刪除客戶"):
        if user_role == 'admin':
            if st.button("確認永久刪除", type="secondary"):
                # 刪除客戶與相關資料
                df_clients = df_clients[df_clients['id'] != client_id]
                save_data("clients", df_clients)
                # 這裡為了效能，可以選擇不刪除關聯資料，或者如下同步刪除
                df_sales = df_sales[df_sales['client_id'] != client_id]
                save_data("sales", df_sales)
                st.session_state['selected_client_id'] = None; st.rerun()

def render_add_client():
    st.title("➕ 新增客戶")
    df_cats = get_data("categories")
    cats = df_cats['name'].tolist() if not df_cats.empty else []
    
    with st.form("new_c"):
        c1, c2 = st.columns(2)
        n = c1.text_input("名稱 (必填)")
        p = c1.text_input("電話")
        e = c1.text_input("Email")
        cat = c1.selectbox("分類", cats)
        proj = c2.text_input("合作項目")
        title = c2.text_input("抬頭")
        inv = c2.text_input("統編")
        if st.form_submit_button("🚀 建立", type="primary"):
            if n:
                df_clients = get_data("clients")
                # 檢查重複電話 (選用)
                if not df_clients.empty and p and str(p) in df_clients['phone'].astype(str).values:
                    st.warning("此電話號碼已存在")
                else:
                    new_id = get_next_id(df_clients)
                    new_client = pd.DataFrame([{
                        "id": new_id,
                        "name": n, "phone": str(p), "email": e, "project": proj,
                        "title": title, "invoice_number": str(inv), "category": cat,
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "created_by": st.session_state['user']
                    }])
                    df_clients = pd.concat([df_clients, new_client], ignore_index=True)
                    save_data("clients", df_clients)
                    st.success("成功"); time.sleep(1)
            else: st.error("名稱必填")

def render_report():
    st.title("📊 業績報表 (Google Sheets)")
    
    # 讀取資料並合併 (Pandas Join)
    df_sales = get_data("sales")
    df_clients = get_data("clients")
    df_users = get_data("users")
    
    if df_sales.empty: st.info("尚無資料"); return

    # 處理型別以利合併
    df_sales['client_id'] = pd.to_numeric(df_sales['client_id'], errors='coerce')
    df_clients['id'] = pd.to_numeric(df_clients['id'], errors='coerce')
    
    # Merge Sales + Clients
    merged = pd.merge(df_sales, df_clients[['id', 'name']], left_on='client_id', right_on='id', how='left')
    # Merge + Users (取得 sales_name)
    merged = pd.merge(merged, df_users[['username', 'sales_name']], left_on='created_by', right_on='username', how='left')
    
    merged['sales_name'] = merged['sales_name'].fillna(merged['created_by'])
    merged['date'] = pd.to_datetime(merged['transaction_date'])
    merged['Month'] = merged['date'].dt.strftime('%Y-%m')
    merged['Year'] = merged['date'].dt.strftime('%Y')

    unique_users = sorted(merged['sales_name'].unique().tolist())
    users = ["🏢 全公司總覽"] + unique_users
    selected_user = st.selectbox("檢視對象", users)
    display_df = merged if selected_user == "🏢 全公司總覽" else merged[merged['sales_name'] == selected_user]

    # 排行榜
    if selected_user == "🏢 全公司總覽":
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 本月排行")
            this_month = datetime.datetime.now().strftime('%Y-%m')
            rank = merged[merged['Month']==this_month].groupby('sales_name')['sale_amount'].sum().sort_values(ascending=False)
            if not rank.empty: st.bar_chart(rank)
        with c2:
            st.markdown("##### 本年排行")
            this_year = datetime.datetime.now().strftime('%Y')
            rank_y = merged[merged['Year']==this_year].groupby('sales_name')['sale_amount'].sum().sort_values(ascending=False)
            if not rank_y.empty: st.bar_chart(rank_y)

    total = display_df['sale_amount'].sum()
    st.metric("總業績", f"${total:,.0f}")
    
    st.dataframe(display_df[['transaction_date','name','item_name','sale_amount','sales_name']], use_container_width=True)

def render_calendar():
    st.title("📅 行事曆")
    df_inter = get_data("interactions")
    df_clients = get_data("clients")
    
    if df_inter.empty: st.info("無待辦"); return

    df_inter['client_id'] = pd.to_numeric(df_inter['client_id'], errors='coerce')
    df_clients['id'] = pd.to_numeric(df_clients['id'], errors='coerce')
    
    # Join
    merged = pd.merge(df_inter, df_clients[['id', 'name', 'created_by']], left_on='client_id', right_on='id', how='left')
    
    # 權限過濾
    if st.session_state['role'] != 'admin':
        merged = merged[merged['created_by'] == st.session_state['user']]
    
    # 只顯示有提醒日的
    merged = merged[merged['follow_up_date'].notna()]
    
    if 'cal_date' not in st.session_state: st.session_state['cal_date'] = datetime.date.today()
    
    c1, c2 = st.columns([4, 3])
    with c1:
        sel = st.date_input("選擇日期", st.session_state['cal_date'])
        if sel != st.session_state['cal_date']:
            st.session_state['cal_date'] = sel; st.rerun()
            
    with c2:
        target_date = st.session_state['cal_date'].strftime("%Y-%m-%d")
        tasks = merged[merged['follow_up_date'] == target_date]
        st.subheader(f"{target_date} 待辦")
        if not tasks.empty:
            for _, r in tasks.iterrows():
                st.info(f"客戶: {r['name']} | 事項: {r['reminder_note']}")
        else: st.caption("無事項")

def page_dashboard():
    local_css()
    role = st.session_state.get('role', 'operator')
    real_name = st.session_state.get('real_name', st.session_state['user'])
    options = ["👥 客戶名單列表", "➕ 新增客戶", "📅 行事曆與提醒"]
    if role == 'admin': options.append("📊 業績報表")
    
    if 'current_view' not in st.session_state: st.session_state['current_view'] = options[0]

    with st.sidebar:
        st.title(f"Hi, {real_name}")
        st.caption(f"身分: {role}")
        selected = st.radio("選單", options)
        if selected != st.session_state['current_view']:
            st.session_state['current_view'] = selected
            st.session_state['selected_client_id'] = None
            st.rerun()
        if st.button("登出"): st.session_state['logged_in'] = False; st.rerun()

    menu = st.session_state['current_view']
    
    if st.session_state.get('selected_client_id'):
        render_client_detail(st.session_state['selected_client_id']); return

    if menu == "👥 客戶名單列表":
        st.title("👥 客戶名單")
        q = st.text_input("🔍 搜尋")
        
        df_clients = get_data("clients")
        df_users = get_data("users")
        
        # 權限過濾
        if role != 'admin':
            df_clients = df_clients[df_clients['created_by'] == st.session_state['user']]
            
        # Join User Name
        if not df_clients.empty:
            df_clients = pd.merge(df_clients, df_users[['username', 'sales_name']], left_on='created_by', right_on='username', how='left')
            df_clients['sales_name'] = df_clients['sales_name'].fillna('Unknown')
        
        if q and not df_clients.empty:
            df_clients = df_clients[df_clients['name'].astype(str).str.contains(q) | df_clients['phone'].astype(str).str.contains(q)]
            
        if not df_clients.empty:
            for _, row in df_clients.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    c1.markdown(f"**{row['name']}**")
                    c2.text(f"📞 {row['phone']}")
                    c3.markdown(f"<span class='owner-tag'>{row['sales_name']}</span>", unsafe_allow_html=True)
                    if c4.button("查看", key=f"v_{row['id']}"):
                        st.session_state['selected_client_id'] = row['id']; st.rerun()
                    st.markdown("<hr>", unsafe_allow_html=True)
        else: st.info("無資料")
        
    elif menu == "➕ 新增客戶": render_add_client()
    elif menu == "📅 行事曆與提醒": render_calendar()
    elif menu == "📊 業績報表": render_report()

def main():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if not st.session_state['logged_in']: local_css(); page_login_register()
    else: page_dashboard()

if __name__ == "__main__": main()