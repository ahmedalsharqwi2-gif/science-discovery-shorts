# دليل التشغيل الحالي

| الملف | وظيفته | متى يعمل؟ |
|---|---|---|
| `remotion-daily.yml` | إنتاج فيديو كامل أو التحقق من الفيلم المحجوز، ثم جدولة الوجهات الثلاث | يوميًا ٩ صباحًا بتوقيت القاهرة؛ النشر ٥ مساءً في نفس اليوم |
| `remotion-health.yml` | فحص الإنتاج والملف والإيصالات الفعلية والتنبيه عند الفشل | بعد الإنتاج، و١١:٣٠ صباحًا و٣ عصرًا و٤:١٥ و٥:٣٠ مساءً |
| `checks.yml` | اختبارات Python ومحركات المشاهد وTypeScript/Remotion؛ لا يولّد ولا ينشر | عند تغيير الكود أو تشغيله يدويًا |
| `remotion-cleanup.yml` | صيانة يدوية محددة بخطة محفوظة، دون نشر أو توليد | يدويًا أو عند تغيير طلب الصيانة فقط |
| `arabic_guard.yml` | فحص قواعد العربية | عند تغيير الكود |
| `validation.yml` | اختبارات المستودع الأصلية | عند تغيير الكود أو Pull Request |

التشغيل اليومي والفحص هما الوحيدان اللذان لهما مواعيد دورية. لا يلزم تشغيل أي workflow قديم يدويًا.

الفروع المرجعية والملفات والسجلات والفيديوهات القديمة محفوظة. أزيلت تعريفات التجارب والإصلاحات المنتهية من المسار النشط، وجُمعت اختبارات المحركات في checks.yml. النسخة الأصلية قبل التنظيف: `archive/housekeeping-41535654634-1/main-before-cleanup`.

التقارير: `reviews/daily_health/`؛ إيصالات الإنتاج: `state/remotion_registry.json`؛ تقرير تنظيف التشغيل: `reviews/cleanup/workflow-simplification.json` و`workflow-catalog-latest.json`.

قد يعرض GitHub أسماء تشغيلات قديمة تحت العناصر غير النشطة؛ تاريخ التشغيل وإرفاقاته محفوظان للاسترجاع، ولا يعني ظهوره أنها تعمل يوميًا.


### موعد الإنتاج الاحتياطي

الموعد الأساسي ٩ صباحًا بتوقيت القاهرة، مع تحقق احتياطي ٩:١٧ صباحًا في نفس workflow. يستكمل الملف المحفوظ فقط عندما تسمح حالته وإيصالاته بذلك، ويتوقف إذا كانت الوجهات الثلاث محجوزة للفيلم الصحيح. لا يتغير موعد النشر ٥ مساءً في نفس اليوم، ولا يُرحّل موعد فائت.

إطلاق أحداث schedule يعتمد على GitHub وقد يتأخر أو لا يحدث؛ وجود تعريف cron وحده ليس دليل تنفيذ. يُثبت التنفيذ بسجل التشغيل الفعلي وفحص الملف وإيصالات الوجهات. غياب حدث ٩ صباحًا يوم ٣ نوفمبر موثّق، ولا تُنسب المعالجة اليدوية اللاحقة إلى ذلك الموعد.


### مشغّل Cloudflare المستقل

الكود وخطوات الوصول والنشر في [scheduler/README.md](scheduler/README.md). حالة التفعيل الفعلية وأدلة الاختبار في [تقرير الربط](reviews/independent-clock-setup.json). وجود الكود أو نجاح الاختبارات لا يعني أن المشغّل نُشر. لا يستخدم المشغّل مفاتيح الصوت أو Buffer، ولا يضيف workflow جديدًا.


تم تفعيل مشغّل Cloudflare يوم ٣ نوفمبر ٢٠٢٦ بعد نبضة فعلية وخمسة اختبارات GitHub ناجحة للقراءة فقط. يعمل مستقلاً عن المحادثة: إنتاج/فحص الفيلم المحجوز ٩ صباحًا، احتياطي ٩:١٧، ونشر ٥ مساءً في نفس اليوم؛ وفحص نشر مستقل ٥:٣٥. أول موعد صباحي تالٍ: ٤ نوفمبر ٢٠٢٦. [إيصال التفعيل](reviews/independent-clock-live-verification-2026-11-03.json). لم يُدّعَ بعد رصد تشغيل الإنتاج عند ذلك الموعد المستقبلي.

## Owner-approved noon trial: November 4–17, 2026

During these publication dates, prepare at **19:00 Cairo the previous day** and publish at **12:00 Cairo**. Preserve the date across retries and Cairo daylight-saving offsets. A 19:17 backup trigger must reuse existing reservations and post IDs. November 4 uses existing completed inventory, rescheduled in place; the first new evening production is November 4 for November 5. After November 17 the configured baseline resumes unless the owner changes it.

Health reports check tomorrow at 21:30, today at 09:30 and 11:15, and actual publication at 12:30. Reports retain preparation/publication instants, readiness, immutable media proof, destination receipts and errors. A green workflow alone is never proof of actual publication.

The one-time `[schedule-migration]` push runs only the exact existing-post time-change job. It changes dueAt in place and retains a before snapshot and independently read-back IDs. It never creates posts, renders videos or invokes voice generation. Uncertain writes require reconciliation rather than blind retry.
