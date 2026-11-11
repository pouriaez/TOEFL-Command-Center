"""Workbook importer for TOEFL Study Plan (Persian workbook)."""
from __future__ import annotations
import re
from datetime import date, datetime
from pathlib import Path
from openpyxl import load_workbook

SHEET_DAILY = "برنامه روزانه (۱۹آبان-۱۲دی)"
SHEET_ROUTINE = "روتین ساعتی روزهای هفته"
SHEET_SYLLABUS = "سیلابس هفتگی (تا ۱۲ دی)"
SHEET_MOCKS = "کارنامه آزمون‌های تستینو"

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
MONTHS = {"فروردین":1,"اردیبهشت":2,"خرداد":3,"تیر":4,"مرداد":5,"شهریور":6,
          "مهر":7,"آبان":8,"آذر":9,"دی":10,"بهمن":11,"اسفند":12}

def norm(v):
    s = str(v or "").translate(DIGITS).strip().replace("\u200c","")
    return re.sub(r"\s+"," ",s)

def jalali_to_gregorian(jy, jm, jd):
    jy += 1595
    days = -355668 + 365*jy + (jy//33)*8 + ((jy%33+3)//4) + jd
    if jm < 7: days += (jm-1)*31
    else: days += 186 + (jm-7)*30
    gy = 400*(days//146097); days %= 146097
    if days > 36524:
        gy += 100*((days-1)//36524); days = (days-1)%36524
        if days >= 365: days += 1
    gy += 4*(days//1461); days %= 1461
    if days > 365: gy += (days-1)//365; days = (days-1)%365
    gd = days+1
    leap = (gy%4==0 and gy%100!=0) or gy%400==0
    mdays=[31,29 if leap else 28,31,30,31,30,31,31,30,31,30,31]
    gm=1
    while gm<=12 and gd>mdays[gm-1]:
        gd-=mdays[gm-1]; gm+=1
    return date(gy,gm,gd).isoformat()

def parse_date(value, fallback_year=1405):
    if isinstance(value, datetime): return value.date().isoformat()
    if isinstance(value, date): return value.isoformat()
    s=norm(value)
    # Persian/Jalali forms: ۱۹ آبان، 1405/08/19, 19-آبان
    m=re.search(r"(\d{1,2})\s*[-/]?\s*(فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)",s)
    if m: return jalali_to_gregorian(fallback_year, MONTHS[m.group(2)], int(m.group(1)))
    m=re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",s)
    if m:
        y,mo,d=map(int,m.groups())
        if y>1700:
            try:return date(y,mo,d).isoformat()
            except ValueError:return None
        try:return jalali_to_gregorian(y,mo,d)
        except ValueError:return None
    m=re.search(r"(\d{1,2})\s+(\d{1,2})",s)
    if m:
        try:return jalali_to_gregorian(fallback_year,int(m.group(2)),int(m.group(1)))
        except ValueError:return None
    return None

def clean(v):
    if v is None:return ""
    if isinstance(v,(date,datetime)):return v.isoformat()
    return norm(v)

def sheet_rows(ws):
    return [[clean(c) for c in row] for row in ws.iter_rows(values_only=True)]

def find_daily_rows(rows):
    out=[]
    for row in rows:
        joined=" ".join(row)
        d=None
        for value in row:
            d=parse_date(value)
            if d: break
        if not d: continue
        # The original sheet has 12 columns and four daily study blocks.
        # Keep every source field visible; identify numeric target-hours safely.
        hours=0.0
        for value in row:
            s=norm(value).replace(",",".")
            if re.fullmatch(r"\d{1,2}(?:\.\d+)?",s):
                n=float(s)
                if 0<n<=12: hours=n; break
        weekday=next((x for x in row if any(k in x for k in
            ["شنبه","یکشنبه","دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه"])), "")
        # Preserve source sequence in blocks rather than dropping columns.
        nonempty=[x for x in row if x and parse_date(x) is None and x!=weekday]
        blocks=[" | ".join(nonempty[i::4])[:1200] for i in range(4)]
        out.append((d,weekday,hours,*blocks,""))
    return out

def import_workbook(path, connection):
    wb=load_workbook(Path(path),read_only=True,data_only=True)
    imported={"daily":0,"routine_rows":0,"syllabus_rows":0,"mock_rows":0,"sheets":[]}
    for ws in wb.worksheets:
        name=ws.title
        rows=sheet_rows(ws)
        imported["sheets"].append(name)
        if "روزانه" in name:
            for item in find_daily_rows(rows):
                existing=connection.execute("SELECT id FROM tasks WHERE study_date=?",(item[0],)).fetchone()
                if existing:
                    connection.execute("""UPDATE tasks SET weekday=?,hours=?,block1=?,block2=?,block3=?,block4=? WHERE id=?""",
                        (*item[1:7],existing[0]))
                else:
                    connection.execute("""INSERT INTO tasks(study_date,weekday,hours,block1,block2,block3,block4,notes)
                        VALUES(?,?,?,?,?,?,?,?)""",item)
                imported["daily"]+=1
        elif "روتین" in name:
            imported["routine_rows"]=sum(1 for r in rows if any(r))
        elif "سیلابس" in name:
            imported["syllabus_rows"]=sum(1 for r in rows if any(r))
        elif "کارنامه" in name or "آزمون" in name:
            nonblank=[r for r in rows if any(r)]
            imported["mock_rows"]=max(0,len(nonblank)-1)
            header_index=next((i for i,r in enumerate(rows[:5]) if any(
                any(k in x.lower() for k in ["listening","reading","speaking","writing","overall","شنیدار","خواندن","گفتار","نوشتار","تاریخ"])
                for x in r)),None)
            if header_index is not None:
                headers=[x.lower() for x in rows[header_index]]
                def col(keys):
                    return next((i for i,h in enumerate(headers) if any(k in h for k in keys)),None)
                date_col=col(["تاریخ","date"])
                name_col=col(["آزمون","test","نام"])
                score_cols=[
                    col(["listening","شنیدار"]),
                    col(["reading","خواندن"]),
                    col(["speaking","گفتار"]),
                    col(["writing","نوشتار"]),
                    col(["overall","total","کل","مجموع"])
                ]
                analysis_col=col(["تحلیل","اشتباه","error","analysis"])
                for row in rows[header_index+1:]:
                    if not any(row): continue
                    d=parse_date(row[date_col]) if date_col is not None and date_col<len(row) else None
                    vals=[]
                    for idx in score_cols:
                        raw=norm(row[idx]) if idx is not None and idx<len(row) else ""
                        try: vals.append(float(raw.replace(",", ".")) if raw else 0.0)
                        except ValueError: vals.append(0.0)
                    test_name= row[name_col] if name_col is not None and name_col<len(row) else "Testino"
                    if d and any(vals):
                        connection.execute("""INSERT INTO mocks(test_date,test_name,listening,reading,speaking,writing,overall,analysis)
                            VALUES(?,?,?,?,?,?,?,?)""",
                            (d,test_name,*vals,
                             row[analysis_col] if analysis_col is not None and analysis_col<len(row) else ""))
        # Save all sheet data so no workbook content is discarded.
        connection.execute("INSERT INTO notes(created_at,title,body) VALUES(?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"),"Workbook: "+name,
             "\n".join(" | ".join(r) for r in rows)[:30000]))
    wb.close()
    connection.commit()
    return imported
