from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_NAME = "TOEFL Command Center"
DATA_DIR = Path(os.getenv("TOEFL_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("TOEFL_DB_PATH", str(DATA_DIR / "toefl.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY, study_date TEXT, weekday TEXT, hours REAL DEFAULT 0,
 block1 TEXT, block2 TEXT, block3 TEXT, block4 TEXT, done INTEGER DEFAULT 0,
 notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS mocks (
 id INTEGER PRIMARY KEY, test_date TEXT, test_name TEXT,
 listening REAL DEFAULT 0, reading REAL DEFAULT 0, speaking REAL DEFAULT 0,
 writing REAL DEFAULT 0, overall REAL DEFAULT 0, analysis TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS notes (
 id INTEGER PRIMARY KEY, created_at TEXT, title TEXT, body TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

def connect():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con

def query(sql, params=()):
    with connect() as con:
        return con.execute(sql, params).fetchall()

def execute(sql, params=()):
    with connect() as con:
        cur = con.execute(sql, params)
        return cur.lastrowid

def inject_style():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {font-family:'Vazirmatn',Tahoma,sans-serif;}
    .stApp {direction:rtl;}
    [data-testid="stSidebar"] {direction:rtl; border-left:1px solid rgba(120,130,150,.18);}
    .block-container {padding-top:2rem; max-width:1440px;}
    h1,h2,h3,p,label,div {text-align:right;}
    [data-testid="stMetric"] {background:var(--secondary-background-color); padding:16px 18px; border:1px solid rgba(120,130,150,.18); border-radius:14px;}
    [data-testid="stMetricLabel"] {justify-content:flex-start;}
    [data-testid="stMetricValue"] {direction:ltr; text-align:right;}
    .hero {padding:22px 26px; border-radius:18px; background:linear-gradient(120deg,#182b55,#4059c9); color:white; margin-bottom:18px;}
    .hero h1,.hero p {color:white; margin:0; text-align:right;}
    .muted {color:var(--text-color); opacity:.68;}
    div.stButton>button, div.stDownloadButton>button {border-radius:10px; min-height:42px;}
    </style>
    """, unsafe_allow_html=True)

def fmt_date(value):
    return str(value or "")[:10]

def dashboard():
    st.markdown('<div class="hero"><h1>مرکز فرماندهی آمادگی تافل</h1><p>برنامه‌ریزی، پیگیری پیشرفت و تحلیل آزمون‌های آزمایشی</p></div>', unsafe_allow_html=True)
    tasks = query("SELECT * FROM tasks ORDER BY study_date")
    mocks = query("SELECT * FROM mocks ORDER BY test_date DESC, id DESC")
    total = len(tasks)
    done = sum(int(x["done"] or 0) for x in tasks)
    hours = sum(float(x["hours"] or 0) for x in tasks)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("روزهای برنامه‌ریزی‌شده", total)
    c2.metric("روزهای تکمیل‌شده", done)
    c3.metric("ساعت هدف ثبت‌شده", f"{hours:g}")
    c4.metric("آخرین نمره آزمون", mocks[0]["overall"] if mocks else "—")
    st.subheader("پیشرفت برنامه")
    st.progress(done/total if total else 0, text=f"{round(done/total*100) if total else 0}% تکمیل")
    if mocks:
        st.subheader("آخرین وضعیت مهارت‌ها")
        m=mocks[0]
        scores=pd.DataFrame({"مهارت":["Listening","Reading","Speaking","Writing"],"آخرین نمره":[m["listening"],m["reading"],m["speaking"],m["writing"]]})
        st.dataframe(scores, hide_index=True, use_container_width=True)
        if len(mocks)>1:
            trend=pd.DataFrame([dict(تاریخ=x["test_date"],Overall=x["overall"]) for x in reversed(mocks)])
            st.line_chart(trend.set_index("تاریخ"))
    st.subheader("کارهای پیش‌رو")
    upcoming=[dict(تاریخ=x["study_date"],روز=x["weekday"],ساعت=x["hours"],وضعیت="انجام‌شده" if x["done"] else "در انتظار") for x in tasks if x["study_date"] >= date.today().isoformat() and not x["done"]]
    if upcoming: st.dataframe(pd.DataFrame(upcoming), hide_index=True, use_container_width=True)
    else: st.info("در حال حاضر کار برنامه‌ریزی‌شده‌ای برای روزهای آینده وجود ندارد.")

def planner():
    st.title("برنامه روزانه")
    with st.expander("＋ افزودن روز جدید", expanded=False):
        with st.form("add_task", clear_on_submit=True):
            d=st.date_input("تاریخ", value=date.today(), format="YYYY/MM/DD")
            weekday=st.text_input("روز هفته")
            hours=st.number_input("ساعت هدف",0.0,24.0,4.0,.5)
            cols=st.columns(2)
            blocks=[cols[i%2].text_input(f"بازه مطالعاتی {i+1}") for i in range(4)]
            note=st.text_area("یادداشت")
            if st.form_submit_button("ذخیره روز", type="primary"):
                execute("INSERT INTO tasks(study_date,weekday,hours,block1,block2,block3,block4,notes) VALUES(?,?,?,?,?,?,?,?)",(d.isoformat(),weekday,hours,*blocks,note))
                st.success("روز جدید ذخیره شد."); st.rerun()
    rows=query("SELECT * FROM tasks ORDER BY study_date")
    if not rows:
        st.info("هنوز برنامه‌ای ثبت نشده است."); return
    df=pd.DataFrame([{"شناسه":x["id"],"تاریخ":x["study_date"],"روز":x["weekday"],"ساعت هدف":x["hours"],"بازه ۱":x["block1"],"بازه ۲":x["block2"],"بازه ۳":x["block3"],"بازه ۴":x["block4"],"انجام شد":bool(x["done"]),"یادداشت":x["notes"]} for x in rows])
    edited=st.data_editor(df, hide_index=True, use_container_width=True, disabled=["شناسه","تاریخ","روز","ساعت هدف","بازه ۱","بازه ۲","بازه ۳","بازه ۴","یادداشت"], column_config={"انجام شد":st.column_config.CheckboxColumn("انجام شد")}, key="tasks_editor")
    if st.button("ذخیره وضعیت انجام کارها"):
        with connect() as con:
            for _,r in edited.iterrows(): con.execute("UPDATE tasks SET done=? WHERE id=?",(int(r["انجام شد"]),int(r["شناسه"])))
        st.success("وضعیت‌ها ذخیره شد."); st.rerun()
    st.divider()
    st.subheader("ویرایش یا حذف روز")
    ids={f'{x["study_date"]} — {x["weekday"] or "بدون عنوان"} (#{x["id"]})':x["id"] for x in rows}
    selected=st.selectbox("روز موردنظر",list(ids))
    row=next(x for x in rows if x["id"]==ids[selected])
    with st.form("edit_task"):
        d=st.date_input("تاریخ روز",value=date.fromisoformat(row["study_date"]),key="edit_date")
        wd=st.text_input("روز هفته",row["weekday"] or "",key="edit_wd")
        hrs=st.number_input("ساعت هدف",0.0,24.0,float(row["hours"] or 0),.5,key="edit_hours")
        vals=[st.text_input(f"بازه مطالعاتی {i+1}",row[f"block{i+1}"] or "",key=f"edit_b{i}") for i in range(4)]
        note=st.text_area("یادداشت",row["notes"] or "",key="edit_note")
        save=st.form_submit_button("ثبت ویرایش",type="primary")
    if save:
        execute("UPDATE tasks SET study_date=?,weekday=?,hours=?,block1=?,block2=?,block3=?,block4=?,notes=? WHERE id=?",(d.isoformat(),wd,hrs,*vals,note,row["id"]))
        st.success("تغییرات ذخیره شد."); st.rerun()
    if st.button("حذف این روز", type="secondary"):
        execute("DELETE FROM tasks WHERE id=?",(row["id"],)); st.rerun()

def mock_tests():
    st.title("کارنامه آزمون‌های آزمایشی")
    with st.expander("＋ ثبت آزمون جدید"):
        with st.form("new_mock",clear_on_submit=True):
            name=st.text_input("نام آزمون","Testino")
            d=st.date_input("تاریخ آزمون",date.today(),key="mock_date")
            cols=st.columns(5)
            scores=[cols[i].number_input(label,0.0,120.0,0.0,.5,key=f"score_{i}") for i,label in enumerate(["Listening","Reading","Speaking","Writing","Overall"])]
            analysis=st.text_area("تحلیل خطا و نکات قابل بهبود")
            if st.form_submit_button("ذخیره آزمون",type="primary"):
                execute("INSERT INTO mocks(test_date,test_name,listening,reading,speaking,writing,overall,analysis) VALUES(?,?,?,?,?,?,?,?)",(d.isoformat(),name,*scores,analysis))
                st.success("آزمون ثبت شد."); st.rerun()
    rows=query("SELECT * FROM mocks ORDER BY test_date DESC,id DESC")
    if rows:
        st.dataframe(pd.DataFrame([{"تاریخ":x["test_date"],"آزمون":x["test_name"],"Listening":x["listening"],"Reading":x["reading"],"Speaking":x["speaking"],"Writing":x["writing"],"Overall":x["overall"],"تحلیل خطا":x["analysis"]} for x in rows]),hide_index=True,use_container_width=True)
        st.download_button("دریافت خروجی CSV",pd.DataFrame([dict(x) for x in rows]).to_csv(index=False).encode("utf-8-sig"),"toefl-mock-results.csv","text/csv")
    else: st.info("هنوز آزمون آزمایشی ثبت نشده است.")

def notes_page():
    st.title("یادداشت‌ها و تحلیل خطا")
    with st.form("new_note",clear_on_submit=True):
        title=st.text_input("عنوان یادداشت")
        body=st.text_area("متن یادداشت",height=160,placeholder="نکات کلاس، واژگان، تحلیل آزمون و مواردی که باید مرور شوند…")
        if st.form_submit_button("ذخیره یادداشت",type="primary"):
            if title.strip() or body.strip():
                execute("INSERT INTO notes(created_at,title,body) VALUES(?,?,?)",(datetime.now().strftime("%Y-%m-%d %H:%M"),title,body))
                st.success("یادداشت ذخیره شد."); st.rerun()
    st.divider()
    rows=query("SELECT * FROM notes ORDER BY id DESC")
    if not rows: st.info("یادداشتی ثبت نشده است.")
    for x in rows:
        with st.expander(f'{x["title"] or "بدون عنوان"} — {x["created_at"]}'):
            st.write(x["body"])
            if st.button("حذف یادداشت",key=f'del_note_{x["id"]}'):
                execute("DELETE FROM notes WHERE id=?",(x["id"],)); st.rerun()

def settings_page():
    st.title("تنظیمات و ابزارها")
    st.subheader("ورود برنامه از Excel")
    st.caption("فایل اصلی Excel تغییر نمی‌کند. اطلاعات برنامه روزانه، کارنامه و محتوای شیت‌ها به پایگاه داده برنامه منتقل می‌شود.")
    uploaded=st.file_uploader("فایل برنامه تافل (.xlsx)",type=["xlsx"])
    if uploaded and st.button("شروع ورود اطلاعات",type="primary"):
        try:
            from workbook_importer import import_workbook
            suffix=Path(uploaded.name).suffix or ".xlsx"
            with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as tmp:
                tmp.write(uploaded.getvalue()); temp_path=tmp.name
            try:
                with connect() as con: result=import_workbook(temp_path,con)
            finally: Path(temp_path).unlink(missing_ok=True)
            st.success("ورود فایل با موفقیت انجام شد.")
            st.json(result)
        except Exception as exc:
            st.error(f"خطا در ورود فایل: {exc}")
    st.divider()
    st.subheader("پشتیبان‌گیری")
    if DB_PATH.exists():
        st.download_button("دانلود نسخه پشتیبان پایگاه داده",DB_PATH.read_bytes(),"toefl-command-center-backup.db","application/octet-stream")
    st.caption(f"مسیر پایگاه داده روی سرور: {DB_PATH}")
    st.warning("در میزبانی‌های ابری با فضای ذخیره‌سازی موقت، اطلاعات ممکن است پس از راه‌اندازی مجدد پاک شوند. برای استفاده دائمی چندکاربره، پایگاه داده ابری یا دیسک پایدار متصل کنید.")

def main():
    st.set_page_config(page_title=APP_NAME,page_icon="📘",layout="wide",initial_sidebar_state="expanded")
    inject_style()
    st.sidebar.markdown("## 📘 TOEFL Command Center")
    st.sidebar.caption("سامانه مدیریت آمادگی تافل")
    page=st.sidebar.radio("ناوبری",["داشبورد","برنامه روزانه","آزمون‌های آزمایشی","یادداشت‌ها","تنظیمات و ورود Excel"])
    st.sidebar.divider()
    st.sidebar.caption("نسخه وب — Python / Streamlit")
    if page=="داشبورد": dashboard()
    elif page=="برنامه روزانه": planner()
    elif page=="آزمون‌های آزمایشی": mock_tests()
    elif page=="یادداشت‌ها": notes_page()
    else: settings_page()

if __name__=="__main__":
    main()
