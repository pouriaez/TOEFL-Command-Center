from __future__ import annotations

import sys, sqlite3, json, shutil
from pathlib import Path
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QDialog, QFormLayout, QLineEdit, QSpinBox, QTextEdit,
    QDateEdit, QDoubleSpinBox, QHeaderView, QAbstractItemView, QFrame,
    QProgressBar, QComboBox
)

APP_DIR = Path.home() / ".toefl_command_center"
APP_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / "toefl.db"

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

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con

def cell_text(v: Any) -> str:
    if v is None: return ""
    try:
        if str(v) == "nan": return ""
    except Exception: pass
    return str(v).strip()

class Metric(QFrame):
    def __init__(self, title: str, value: str = "0"):
        super().__init__()
        self.setObjectName("metric")
        lay = QVBoxLayout(self)
        self.caption = QLabel(title); self.caption.setObjectName("muted")
        self.value = QLabel(value); self.value.setObjectName("metricValue")
        lay.addWidget(self.caption); lay.addWidget(self.value)

class TaskDialog(QDialog):
    def __init__(self, parent=None, row=None):
        super().__init__(parent); self.setWindowTitle("ویرایش برنامه روزانه")
        self.setMinimumWidth(440)
        form = QFormLayout(self)
        self.day = QDateEdit(); self.day.setCalendarPopup(True); self.day.setDisplayFormat("yyyy-MM-dd")
        self.day.setDate(QDate.currentDate())
        self.weekday = QLineEdit()
        self.hours = QDoubleSpinBox(); self.hours.setRange(0, 24); self.hours.setSingleStep(.5)
        self.blocks = [QLineEdit() for _ in range(4)]
        self.notes = QTextEdit(); self.notes.setMaximumHeight(75)
        form.addRow("تاریخ", self.day); form.addRow("روز هفته", self.weekday)
        form.addRow("ساعت هدف", self.hours)
        for i, w in enumerate(self.blocks, 1): form.addRow(f"بازه مطالعاتی {i}", w)
        form.addRow("یادداشت", self.notes)
        buttons = QHBoxLayout(); save = QPushButton("ذخیره"); cancel = QPushButton("انصراف")
        save.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        buttons.addWidget(save); buttons.addWidget(cancel); form.addRow(buttons)
        if row:
            self.day.setDate(QDate.fromString(row["study_date"], "yyyy-MM-dd"))
            self.weekday.setText(row["weekday"] or ""); self.hours.setValue(row["hours"] or 0)
            for i, w in enumerate(self.blocks): w.setText(row[f"block{i+1}"] or "")
            self.notes.setPlainText(row["notes"] or "")
    def values(self):
        return (self.day.date().toString("yyyy-MM-dd"), self.weekday.text(),
                self.hours.value(), *[w.text() for w in self.blocks], self.notes.toPlainText())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TOEFL Command Center")
        self.resize(1320, 820)
        self.dark = False
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.build_dashboard(); self.build_plan(); self.build_mocks(); self.build_notes(); self.build_settings()
        self.apply_theme(False); self.refresh_all()
        bar = self.menuBar().addMenu("فایل")
        imp = QAction("ورود اطلاعات از Excel", self); imp.triggered.connect(self.import_excel); bar.addAction(imp)
        exp = QAction("پشتیبان‌گیری از پایگاه داده", self); exp.triggered.connect(self.backup); bar.addAction(exp)

    def page(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(22, 18, 22, 18); l.setSpacing(14)
        return w, l

    def build_dashboard(self):
        w, l = self.page()
        heading = QLabel("مرکز فرماندهی آمادگی تافل"); heading.setObjectName("heading"); l.addWidget(heading)
        cards = QHBoxLayout()
        self.m_total = Metric("روزهای برنامه‌ریزی‌شده")
        self.m_done = Metric("روزهای تکمیل‌شده")
        self.m_hours = Metric("ساعت هدف ثبت‌شده")
        self.m_mock = Metric("آخرین نمره آزمون")
        for m in [self.m_total,self.m_done,self.m_hours,self.m_mock]: cards.addWidget(m)
        l.addLayout(cards)
        self.progress_label = QLabel("پیشرفت برنامه"); l.addWidget(self.progress_label)
        self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setFormat("%p%"); l.addWidget(self.progress)
        l.addWidget(QLabel("نمای کلی مهارت‌ها و وضعیت مطالعه"))
        self.skill_table = QTableWidget(4,3); self.skill_table.setHorizontalHeaderLabels(["مهارت","آخرین نمره ثبت‌شده","هدف"])
        for i,s in enumerate(["Listening","Reading","Speaking","Writing"]):
            self.skill_table.setItem(i,0,QTableWidgetItem(s))
            self.skill_table.setItem(i,1,QTableWidgetItem("—"))
            self.skill_table.setItem(i,2,QTableWidgetItem("5.0 / 6"))
        self.skill_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.skill_table.setMaximumHeight(190); l.addWidget(self.skill_table)
        l.addWidget(QLabel("کارهای پیش‌رو"))
        self.upcoming = QTableWidget(0,4); self.upcoming.setHorizontalHeaderLabels(["تاریخ","روز","ساعت هدف","وضعیت"])
        self.upcoming.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); l.addWidget(self.upcoming)
        self.tabs.addTab(w,"داشبورد")

    def build_plan(self):
        w,l=self.page()
        top=QHBoxLayout(); title=QLabel("برنامه روزانه"); title.setObjectName("heading"); top.addWidget(title); top.addStretch()
        add=QPushButton("＋ افزودن روز"); add.clicked.connect(self.add_task); top.addWidget(add)
        edit=QPushButton("ویرایش"); edit.clicked.connect(self.edit_task); top.addWidget(edit)
        delete=QPushButton("حذف"); delete.clicked.connect(self.delete_task); top.addWidget(delete)
        l.addLayout(top)
        self.plan_table=QTableWidget(0,9)
        self.plan_table.setHorizontalHeaderLabels(["تاریخ","روز","ساعت هدف","بازه ۱","بازه ۲","بازه ۳","بازه ۴","انجام شد","یادداشت"])
        self.plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.plan_table.horizontalHeader().setStretchLastSection(True)
        self.plan_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.plan_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.plan_table.itemChanged.connect(self.task_check_changed)
        l.addWidget(self.plan_table)
        self.tabs.addTab(w,"برنامه روزانه")

    def build_mocks(self):
        w,l=self.page(); top=QHBoxLayout(); title=QLabel("کارنامه آزمون‌های آزمایشی"); title.setObjectName("heading"); top.addWidget(title); top.addStretch()
        b=QPushButton("＋ ثبت آزمون"); b.clicked.connect(self.add_mock); top.addWidget(b); l.addLayout(top)
        self.mock_table=QTableWidget(0,8)
        self.mock_table.setHorizontalHeaderLabels(["تاریخ","آزمون","Listening","Reading","Speaking","Writing","Overall","تحلیل خطا"])
        self.mock_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.mock_table.horizontalHeader().setStretchLastSection(True)
        self.mock_table.setSelectionBehavior(QAbstractItemView.SelectRows); l.addWidget(self.mock_table)
        self.tabs.addTab(w,"آزمون‌های آزمایشی")

    def build_notes(self):
        w,l=self.page(); title=QLabel("یادداشت‌ها و تحلیل خطا"); title.setObjectName("heading"); l.addWidget(title)
        self.note_title=QLineEdit(); self.note_title.setPlaceholderText("عنوان یادداشت")
        self.note_body=QTextEdit(); self.note_body.setPlaceholderText("نکات کلاس، واژگان، تحلیل آزمون و مواردی که باید مرور شوند…")
        save=QPushButton("ذخیره یادداشت"); save.clicked.connect(self.save_note)
        l.addWidget(self.note_title); l.addWidget(self.note_body); l.addWidget(save)
        self.notes_list=QTableWidget(0,2); self.notes_list.setHorizontalHeaderLabels(["زمان","عنوان"])
        self.notes_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.notes_list.cellDoubleClicked.connect(self.open_note)
        l.addWidget(self.notes_list)
        self.tabs.addTab(w,"یادداشت‌ها")

    def build_settings(self):
        w,l=self.page(); title=QLabel("تنظیمات و ابزارها"); title.setObjectName("heading"); l.addWidget(title)
        l.addWidget(QLabel("فایل برنامه اکسل خود را وارد کنید تا برنامه روزانه، روتین هفتگی، سیلابس و کارنامه آزمون‌ها به پایگاه داده منتقل شود."))
        imp=QPushButton("انتخاب و ورود فایل Excel"); imp.clicked.connect(self.import_excel); l.addWidget(imp)
        theme=QPushButton("تغییر پوسته روشن / تیره"); theme.clicked.connect(lambda:self.apply_theme(not self.dark)); l.addWidget(theme)
        backup=QPushButton("پشتیبان‌گیری از اطلاعات"); backup.clicked.connect(self.backup); l.addWidget(backup)
        self.import_status=QLabel("پایگاه داده محلی: "+str(DB_PATH)); self.import_status.setWordWrap(True); l.addWidget(self.import_status)
        l.addStretch(); self.tabs.addTab(w,"تنظیمات")

    def refresh_all(self):
        con=db()
        tasks=con.execute("SELECT * FROM tasks ORDER BY study_date").fetchall()
        done=sum(int(x["done"] or 0) for x in tasks); hours=sum(float(x["hours"] or 0) for x in tasks)
        self.m_total.value.setText(str(len(tasks))); self.m_done.value.setText(str(done)); self.m_hours.value.setText(f"{hours:g}")
        self.progress.setValue(round(100*done/len(tasks)) if tasks else 0)
        self.plan_table.blockSignals(True); self.plan_table.setRowCount(len(tasks))
        for r,x in enumerate(tasks):
            vals=[x["study_date"],x["weekday"],str(x["hours"]),x["block1"],x["block2"],x["block3"],x["block4"],"",x["notes"]]
            for c,v in enumerate(vals):
                item=QTableWidgetItem("✓" if c==7 and x["done"] else ("" if c==7 else cell_text(v)))
                if c==7: item.setFlags(item.flags()|Qt.ItemIsUserCheckable); item.setCheckState(Qt.Checked if x["done"] else Qt.Unchecked)
                self.plan_table.setItem(r,c,item)
            self.plan_table.item(r,0).setData(Qt.UserRole,x["id"])
        self.plan_table.blockSignals(False)
        self.upcoming.setRowCount(0)
        for x in tasks:
            if x["study_date"] >= date.today().isoformat() and not x["done"]:
                r=self.upcoming.rowCount(); self.upcoming.insertRow(r)
                for c,v in enumerate([x["study_date"],x["weekday"],x["hours"],"در انتظار"]): self.upcoming.setItem(r,c,QTableWidgetItem(cell_text(v)))
        mocks=con.execute("SELECT * FROM mocks ORDER BY test_date DESC").fetchall()
        self.mock_table.setRowCount(len(mocks))
        for r,x in enumerate(mocks):
            vals=[x["test_date"],x["test_name"],x["listening"],x["reading"],x["speaking"],x["writing"],x["overall"],x["analysis"]]
            for c,v in enumerate(vals): self.mock_table.setItem(r,c,QTableWidgetItem(cell_text(v)))
        if mocks:
            self.m_mock.value.setText(cell_text(mocks[0]["overall"]) or "—")
            for i,k in enumerate(["listening","reading","speaking","writing"]):
                self.skill_table.item(i,1).setText(cell_text(mocks[0][k]) or "—")
        else: self.m_mock.value.setText("—")
        notes=con.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
        self.notes_list.setRowCount(len(notes))
        for r,x in enumerate(notes):
            time_item=QTableWidgetItem(x["created_at"]); time_item.setData(Qt.UserRole,x["id"])
            self.notes_list.setItem(r,0,time_item); self.notes_list.setItem(r,1,QTableWidgetItem(x["title"]))
        con.close()

    def selected_task_id(self):
        row=self.plan_table.currentRow()
        return self.plan_table.item(row,0).data(Qt.UserRole) if row>=0 else None

    def add_task(self):
        d=TaskDialog(self)
        if d.exec()==QDialog.Accepted:
            v=d.values(); con=db()
            con.execute("INSERT INTO tasks(study_date,weekday,hours,block1,block2,block3,block4,notes) VALUES(?,?,?,?,?,?,?,?)",v)
            con.commit(); con.close(); self.refresh_all()

    def edit_task(self):
        tid=self.selected_task_id()
        if not tid: return
        con=db(); row=con.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone(); con.close()
        d=TaskDialog(self,row)
        if d.exec()==QDialog.Accepted:
            v=d.values(); con=db()
            con.execute("UPDATE tasks SET study_date=?,weekday=?,hours=?,block1=?,block2=?,block3=?,block4=?,notes=? WHERE id=?",(*v,tid))
            con.commit(); con.close(); self.refresh_all()

    def delete_task(self):
        tid=self.selected_task_id()
        if not tid:return
        if QMessageBox.question(self,"حذف","این روز حذف شود؟")==QMessageBox.Yes:
            con=db(); con.execute("DELETE FROM tasks WHERE id=?",(tid,)); con.commit(); con.close(); self.refresh_all()

    def task_check_changed(self,item):
        if item.column()!=7:return
        tid=self.plan_table.item(item.row(),0).data(Qt.UserRole)
        con=db(); con.execute("UPDATE tasks SET done=? WHERE id=?",(1 if item.checkState()==Qt.Checked else 0,tid)); con.commit(); con.close()
        self.refresh_all()

    def add_mock(self):
        d=QDialog(self); d.setWindowTitle("ثبت آزمون آزمایشی"); f=QFormLayout(d)
        name=QLineEdit("Testino"); dt=QDateEdit(); dt.setCalendarPopup(True); dt.setDate(QDate.currentDate())
        scores=[]
        for label in ["Listening","Reading","Speaking","Writing","Overall"]:
            s=QDoubleSpinBox(); s.setRange(0,120); s.setDecimals(1); scores.append(s); f.addRow(label,s)
        analysis=QTextEdit(); analysis.setMaximumHeight(80)
        f.addRow("نام آزمون",name); f.addRow("تاریخ",dt); f.addRow("تحلیل خطا",analysis)
        ok=QPushButton("ذخیره"); ok.clicked.connect(d.accept); f.addRow(ok)
        if d.exec()==QDialog.Accepted:
            con=db(); con.execute("INSERT INTO mocks(test_date,test_name,listening,reading,speaking,writing,overall,analysis) VALUES(?,?,?,?,?,?,?,?)",
                (dt.date().toString("yyyy-MM-dd"),name.text(),*[s.value() for s in scores],analysis.toPlainText()))
            con.commit(); con.close(); self.refresh_all()

    def open_note(self,row,column):
        item=self.notes_list.item(row,0)
        if not item:return
        note_id=item.data(Qt.UserRole)
        con=db(); note=con.execute("SELECT title,body FROM notes WHERE id=?",(note_id,)).fetchone(); con.close()
        if note:
            dlg=QDialog(self); dlg.setWindowTitle(note["title"]); dlg.resize(850,620)
            layout=QVBoxLayout(dlg); view=QTextEdit(); view.setReadOnly(True); view.setPlainText(note["body"])
            layout.addWidget(view); close=QPushButton("بستن"); close.clicked.connect(dlg.accept); layout.addWidget(close); dlg.exec()

    def save_note(self):
        if not self.note_title.text().strip() and not self.note_body.toPlainText().strip():return
        con=db(); con.execute("INSERT INTO notes(created_at,title,body) VALUES(?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"),self.note_title.text(),self.note_body.toPlainText()))
        con.commit(); con.close(); self.note_title.clear(); self.note_body.clear(); self.refresh_all()

    def import_excel(self):
        path,_=QFileDialog.getOpenFileName(self,"انتخاب فایل برنامه تافل","","Excel (*.xlsx)")
        if not path:return
        try:
            from workbook_importer import import_workbook
            con=db()
            result=import_workbook(path,con)
            con.close()
            summary=(f"روزهای برنامه روزانه: {result['daily']}\\n"
                     f"ردیف‌های روتین هفتگی: {result['routine_rows']}\\n"
                     f"ردیف‌های سیلابس: {result['syllabus_rows']}\\n"
                     f"ردیف‌های کارنامه آزمون: {result['mock_rows']}\\n\\n"
                     "محتوای کامل هر چهار شیت در بخش یادداشت‌ها ذخیره شده است.")
            self.import_status.setText(summary)
            self.refresh_all()
            QMessageBox.information(self,"ورود برنامه تافل",summary)
        except Exception as e:
            QMessageBox.critical(self,"خطا در ورود فایل",str(e))

    def backup(self):
        path,_=QFileDialog.getSaveFileName(self,"ذخیره پشتیبان","toefl-backup.db","Database (*.db)")
        if path:
            shutil.copy2(DB_PATH,path); QMessageBox.information(self,"پشتیبان","فایل پشتیبان ذخیره شد.")

    def apply_theme(self,dark):
        self.dark=dark
        if dark:
            self.setStyleSheet("""
            QWidget{background:#171923;color:#e8eaf0;font-family:'Vazirmatn','Tahoma';font-size:13px}
            QLineEdit,QTextEdit,QTableWidget,QDateEdit,QDoubleSpinBox{background:#222635;border:1px solid #3a4053;border-radius:7px;padding:7px}
            QPushButton{background:#5b6ee1;color:white;border:0;border-radius:7px;padding:9px 15px}
            QPushButton:hover{background:#7182ef}
            QTabBar::tab{background:#242a3b;padding:11px 18px;border-radius:5px}
            QTabBar::tab:selected{background:#5b6ee1}
            #heading{font-size:22px;font-weight:700} #metric{background:#242a3b;border:1px solid #343b50;border-radius:12px;padding:12px}
            #metricValue{font-size:25px;font-weight:700;color:#91a0ff} #muted{color:#aab1c4}
            QHeaderView::section{background:#252b3b;padding:8px;border:0}
            """)
        else:
            self.setStyleSheet("""
            QWidget{background:#f5f7fb;color:#202638;font-family:'Vazirmatn','Tahoma';font-size:13px}
            QLineEdit,QTextEdit,QTableWidget,QDateEdit,QDoubleSpinBox{background:white;border:1px solid #dce2ed;border-radius:7px;padding:7px}
            QPushButton{background:#4059c9;color:white;border:0;border-radius:7px;padding:9px 15px}
            QPushButton:hover{background:#3048b5}
            QTabBar::tab{background:#e8ecf5;padding:11px 18px;border-radius:5px}
            QTabBar::tab:selected{background:#4059c9;color:white}
            #heading{font-size:22px;font-weight:700} #metric{background:white;border:1px solid #e2e7f0;border-radius:12px;padding:12px}
            #metricValue{font-size:25px;font-weight:700;color:#4059c9} #muted{color:#6e7890}
            QHeaderView::section{background:#e9edf5;padding:8px;border:0}
            """)

def main():
    app=QApplication(sys.argv); app.setApplicationName("TOEFL Command Center")
    app.setFont(QFont("Tahoma",10))
    win=MainWindow(); win.show(); sys.exit(app.exec())

if __name__=="__main__": main()
