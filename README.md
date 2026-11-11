# TOEFL Command Center — Web Edition

نسخه وب فارسی برای مدیریت آمادگی آزمون TOEFL. این مخزن اکنون فقط نسخه وب مبتنی بر **Python + Streamlit** را نگهداری می‌کند؛ کد و ابزارهای نسخه دسکتاپ Windows حذف شده‌اند.

## اجرا

نیازمندی: Python 3.11 یا جدیدتر.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run web_app.py
```

مرورگر را در `http://localhost:8501` باز کنید.

## صفحات و قابلیت‌ها

- داشبورد پیشرفت و ساعات مطالعه
- برنامه روزانه: افزودن، ویرایش، حذف و ثبت انجام کار
- کارنامه آزمون‌های آزمایشی و خروجی CSV
- یادداشت‌ها و تحلیل خطا
- ورود فایل Excel فارسی
- دانلود نسخه پشتیبان SQLite
- رابط راست‌چین فارسی

## استقرار

برای Streamlit Community Cloud، مخزن را متصل و فایل اصلی را `web_app.py` انتخاب کنید. وابستگی‌ها در `requirements.txt` قرار دارند.

در محیط ابری، برای حفظ اطلاعات باید فضای ذخیره‌سازی پایدار تنظیم شود. مسیر دیتابیس با متغیر محیطی `TOEFL_DB_PATH` قابل تنظیم است. برنامه فعلاً احراز هویت و پشتیبانی چندکاربره ندارد؛ پیش از انتشار عمومی باید این موارد اضافه شوند.

## اجرای داخل Gemini / محیط توسعه

این پروژه یک اپ Streamlit است و با `npm install` اجرا نمی‌شود. محیط اجرا باید Python 3.11+ و امکان اجرای سرور Streamlit و نمایش/forward کردن پورت 8501 را داشته باشد. اگر محیط فقط پروژه‌های Node.js را پشتیبانی می‌کند، باید از runtime پایتون استفاده شود یا رابط به فناوری وب مورد پشتیبانی آن محیط منتقل شود.

## فایل‌های اصلی

- `web_app.py`: رابط وب و عملیات پایگاه داده
- `workbook_importer.py`: واردکننده فایل Excel فارسی
- `requirements.txt`: وابستگی‌های نسخه وب
- `GEMINI_HANDOFF.md`: دستورالعمل ادامه کار در Gemini
