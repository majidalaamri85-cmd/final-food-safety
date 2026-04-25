# النظام الوطني لتقييم المنشآت الغذائية

مشروع Django عربي لإدارة تقييم المنشآت الغذائية، المتابعات، الإجراءات التصحيحية، والتقارير.

## المزايا
- إدارة المحافظات والولايات والمنشآت
- تنفيذ زيارات تقييم ميدانية
- احتساب نسبة الالتزام والتصنيف آليًا
- إدارة سجلات التقييم والصور
- متابعة الإجراءات التصحيحية
- لوحة معلومات وتقارير أساسية
- تصدير Excel و PDF

## التشغيل السريع
```bash
python -m venv venv
# ويندوز
venv\Scripts\activate
# لينكس / ماك
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py runserver
```

## بيانات الدخول
بعد إنشاء المستخدم الإداري:
- لوحة الإدارة: `/admin/`
- النظام: `/`

## التطبيقات
- `inspections`: إدارة البيانات الأساسية والتقييمات والمتابعات
- `food_safety_system`: الإعدادات والروابط العامة


## تحديث النسخة الموحدة
بعد تشغيل المشروع لأول مرة، أنشئ البنود الموحدة عبر:

```bash
python manage.py seed_unified_template
```

ثم افتح:
- `/evaluations/new/` لإنشاء تقييم جديد
- `/evaluations/<id>/edit/` لإدخال البنود مع الصور
- `/evaluations/<id>/pdf/` لتصدير التقرير الرسمي PDF

## النشر على Render والتحويل إلى PostgreSQL

تمت إضافة ملف إعداد جاهز للنشر:
- `render.yaml`

### 1) ربط الخدمات في Render
إذا كنت تستخدم Blueprint، ارفع المشروع وسيتم إنشاء:
- خدمة ويب: `food-safety-system`
- قاعدة PostgreSQL: `food-safety-db`

إذا كانت لديك خدمات موجودة مسبقًا، عدّل أسماء الخدمات داخل `render.yaml` لتطابق الأسماء الحالية.

### 2) المتغيرات البيئية المهمة
يتم ضبط المتغيرات تلقائيًا من `render.yaml`، وأهمها:
- `DEBUG=False`
- `ALLOWED_HOSTS=food-safety-system.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://food-safety-system.onrender.com`
- `DATABASE_URL` (من خدمة PostgreSQL)
- `MEDIA_ROOT=/var/data/media` (صور مرفوعة على قرص دائم)

### 3) أوامر البناء والتشغيل
محددة في `render.yaml` كالتالي:
- البناء: تثبيت المتطلبات + `collectstatic` + `migrate`
- التشغيل: `gunicorn food_safety_system.wsgi:application`

### 4) نقل البيانات من SQLite إلى PostgreSQL (مرة واحدة)
قبل التحويل، صدّر البيانات محليًا من SQLite:

```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > data.json
```

بعد أول نشر على Render وتشغيل الترحيلات، افتح Shell لخدمة الويب ونفّذ:

```bash
python manage.py loaddata data.json
```

ملاحظة: ارفع `data.json` مؤقتًا للمستودع أو انسخ محتواه إلى بيئة Render بالطريقة المناسبة، ثم احذفه بعد اكتمال الاستيراد.

### 5) عدم فقدان الصور عند التحديث
- تم إعداد Render Disk وربطه بمسار `/var/data` داخل خدمة الويب.
- المسار الفعلي للصور في الإنتاج: `/var/data/media`.
- عند أول ترحيل من بيئة قديمة، انسخ محتوى مجلد `media/` إلى القرص الدائم قبل إعادة النشر الكامل.
