# تعليمات رفع الصور

## الخطوات:

### 1. أخذ الصور من المتصفح
قم بأخذ 6 لقطات شاشة للتبويبات التالية:

1. **تبويب المقترح** (Proposal Tab) - الصفحة الرئيسية
2. **تبويب التقييم** (Evaluation Tab)
3. **تبويب دراسة الجدوى** (Feasibility Study Tab)
4. **تبويب التنفيذ** (Execution Tab)
5. **تبويب التسليم** (Handover Tab)
6. **لوحة إدارة المشروع** (Management Dashboard Tab)

### 2. حفظ الصور
احفظ الصور بأي أسماء تريدها (مثلاً: `screenshot1.png`, `screenshot2.png`, إلخ)

### 3. رفع الصور إلى السيرفر
ارفع الصور إلى أي مكان في:
```
/home/erp/frappe-bench/
```

### 4. تشغيل السكريبت
بعد رفع الصور، شغّل السكريبت:
```bash
cd /home/erp/frappe-bench
./process_screenshots.sh
```

السكريبت سيقوم تلقائياً بـ:
- البحث عن ملفات PNG
- إعادة تسميتها بالأسماء الصحيحة
- نسخها إلى: `apps/milestoneksa/milestoneksa/public/screenshots/`

### 5. الأسماء النهائية المطلوبة:

1. `project-proposal-01-main-proposal-tab.png`
2. `project-proposal-02-evaluation-tab.png`
3. `project-proposal-03-feasibility-tab.png`
4. `project-proposal-04-execution-tab.png`
5. `project-proposal-05-handover-tab.png`
6. `project-proposal-06-dashboard-tab.png`

### 6. التحقق
بعد النسخ، ستكون الصور متاحة على:
```
https://milestoneksa.com/assets/milestoneksa/screenshots/project-proposal-XX-XXX.png
```

---

**ملاحظة:** إذا كنت تفضل تسمية الصور يدوياً، يمكنك نسخها مباشرة إلى:
```
/home/erp/frappe-bench/apps/milestoneksa/milestoneksa/public/screenshots/
```
بأسماء الملفات المذكورة أعلاه.
















