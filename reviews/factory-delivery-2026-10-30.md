# تقرير مصنع الفيديوهات — ٣٠ أكتوبر ٢٠٢٦

تم الفحص الساعة 15:48 بتوقيت القاهرة. توجد أربعة فيديوهات نهائية جديدة، و١٢ منشورًا بحالة scheduled فعلية لدى Buffer للساعة ١٧:٠٠ اليوم (١٥:٠٠ UTC). هذا تأكيد للجدولة قبل موعد النشر، وليس ادعاءً بأن النشر تم بالفعل.

تم تشغيل الإنتاج والرندر داخل GitHub Actions للمستودعات نفسها، مع مراجعات تحريرية موثقة للنصوص. لم أغيّر المفاتيح أو أضف خدمة مدفوعة.

## الإصلاحات المشتركة

- استبدال شرط الساعة الواحدة بنافذة إنتاج من ٠٩:٠٠ إلى ما قبل ١٥:٠٠ بتوقيت Africa/Cairo، مع موعد نشر لليوم نفسه؛ لا انتقال تلقائي لليوم التالي ولا نشر فوري بعد فوات الموعد.
- تغطية الصيف والشتاء بثلاث فرص cron، مع قفل concurrency وحلقة يومية واحدة وحجز موضوع دائم وفحص الجدولة المكتملة قبل أي إنتاج جديد.
- إصلاح تحويل T وZ إلى حروف صغيرة عند تصدير موعد النشر في GITHUB_OUTPUT؛ القيم المنطقية وحدها تتحول إلى true/false.
- حفظ نية الإرسال قبل API، والاحتفاظ بالإيصالات الجزئية، ومنع إعادة طلب إنشاء منشور غير محسوم، والتحقق من post ID وchannel ID وstatus وdueAt الفعلية.
- منع إعادة استعمال أصل Release ببصمة مختلفة، وتثبيت بصمة الملف الذي بدأ إرساله. لا فيديو قديم لتعويض إنتاج فاشل.
- استهداف ١٢٠–١٨٠ ثانية، مع محاولة مراجعة مصدرية واحدة لنفس الحلقة عند فشل مدة الصوت؛ لا إبطاء أو صمت إضافي أو تكرار للصوت.
- معالجة أسماء البداية المركبة في التوقيت باستخدام أول مرساة كلام فعلية ضمن أول ثماني كلمات، مع بقاء حد التعرّف ٨٥٪ دون تخفيض أو اختراع توقيتات.

## نتيجة كل مستودع

### العلوم — science-discovery-shorts

| البند | النتيجة |
|---|---|
| ١. المشكلة | شرط الساعة كان يمنع التشغيل المتأخر؛ ومحاولة الصوت الأولى كانت ١٠٦٫٦ ثانية. تم توسيع نفس الموضوع من NASA وإنتاج النسخة النهائية الكاملة. |
| ٢. الإصلاحات المرفوعة | [نافذة الوقت](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/commit/314e879) · [ISO](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/commit/27dca5c) · [الحماية والاسترجاع](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/commit/dba65ad) |
| ٣. GitHub Actions | [إنتاج الفيديو](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/actions/runs/41055103244) · [الجدولة النهائية](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/actions/runs/41055103244) · [التدقيق المباشر](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/actions/runs/41061056104) |
| ٤. MP4 الجديد | [درع الأرض المغناطيسي](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/releases/download/auto-publish-daily-2026-10-30/science-video-daily-2026-10-30.mp4) |
| ٥. فحص الملف | PASS: ffprobe وffmpeg كامل؛ 162.367 ثانية؛ 1080×1920؛ 30fps؛ AAC 48000Hz؛ HTTP 200؛ أصل Release مطابق للبصمة؛ لا تطابق مع فيديو سابق. |
| ٦. إيصالات Buffer | ٣/٣ مؤكدة من قراءة المنشورات الفعلية، بما فيها القناة والملف والموعد: [JSON الأصلي](https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts/raw/refs/heads/codex/professional-review-run-41061056104/professional_motion/delivery/daily-publication-audit.json) |
| ٧. موعد النشر المؤكد | ٣٠ أكتوبر ٢٠٢٦، الساعة ١٧:٠٠ بتوقيت Africa/Cairo |
| ٨. عطل إنتاج أو جدولة متبقٍ | لا يوجد في الدفعة النهائية التي تم التحقق منها. |

SHA-256: `9ab745fc7ee29ae136ad9eead22f41d5ba87020bdc4af366797e323ff318cfc9`

### الرعب — arabic-horror-stories

| البند | النتيجة |
|---|---|
| ١. المشكلة | تعديل سابق سمح بالإنتاج حتى الساعة ١٧ دون هامش كافٍ. وظهرت صياغة خاطئة للسنوات المكتوبة؛ تم تصحيح نص الشاشة وفق المصدر ونتائج ASR مع الاحتفاظ بالصوت الأصلي byte-for-byte. |
| ٢. الإصلاحات المرفوعة | [نافذة الوقت](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/commit/ef514af) · [ISO](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/commit/5b261ba) · [الحماية والاسترجاع](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/commit/01c7ea7) |
| ٣. GitHub Actions | [إنتاج الفيديو](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/actions/runs/41055885506) · [الجدولة النهائية](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/actions/runs/41055885506) · [التدقيق المباشر](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/actions/runs/41061062315) |
| ٤. MP4 الجديد | [بعثة فرانكلين](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/releases/download/auto-publish-daily-2026-10-30/science-video-daily-2026-10-30.mp4) |
| ٥. فحص الملف | PASS: ffprobe وffmpeg كامل؛ 155.167 ثانية؛ 1080×1920؛ 30fps؛ AAC 48000Hz؛ HTTP 200؛ أصل Release مطابق للبصمة؛ لا تطابق مع فيديو سابق. |
| ٦. إيصالات Buffer | ٣/٣ مؤكدة من قراءة المنشورات الفعلية، بما فيها القناة والملف والموعد: [JSON الأصلي](https://github.com/ahmedalsharqwi2-gif/arabic-horror-stories/raw/refs/heads/codex/professional-review-run-41061062315/professional_motion/delivery/daily-publication-audit.json) |
| ٧. موعد النشر المؤكد | ٣٠ أكتوبر ٢٠٢٦، الساعة ١٧:٠٠ بتوقيت Africa/Cairo |
| ٨. عطل إنتاج أو جدولة متبقٍ | لا يوجد في الدفعة النهائية التي تم التحقق منها. |

SHA-256: `9fd01c8243a510deda3bd582c39418533494f9438cb50e0f43f279e92bde47dd`

### التاريخ — documented-history-stories

| البند | النتيجة |
|---|---|
| ١. المشكلة | نافذة البدء وISO، ثم خطأ ١٢٦ بدل ١٢٨ دعامة وجملة غير مسندة عن منع التسريب. أُنتجت نسخة مصححة، وعدّل Buffer نفس المنشورات الثلاثة بعد تمرير عنوان يوتيوب وتصنيفه صراحةً. |
| ٢. الإصلاحات المرفوعة | [نافذة الوقت](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/commit/ac455ca) · [ISO](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/commit/71f6ccc) · [الحماية والاسترجاع](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/commit/fd615c7) |
| ٣. GitHub Actions | [إنتاج الفيديو](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/actions/runs/41058540009) · [الجدولة النهائية](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/actions/runs/41063563019) · [التدقيق المباشر](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/actions/runs/41064476565) |
| ٤. MP4 الجديد | [قناطر سيغوفيا — النسخة المصححة](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/releases/download/auto-publish-daily-2026-10-30-corrected/science-video-daily-2026-10-30-corrected.mp4) |
| ٥. فحص الملف | PASS: ffprobe وffmpeg كامل؛ 153.367 ثانية؛ 1080×1920؛ 30fps؛ AAC 48000Hz؛ HTTP 200؛ أصل Release مطابق للبصمة؛ لا تطابق مع فيديو سابق. |
| ٦. إيصالات Buffer | ٣/٣ مؤكدة من قراءة المنشورات الفعلية، بما فيها القناة والملف والموعد: [JSON الأصلي](https://github.com/ahmedalsharqwi2-gif/documented-history-stories/raw/refs/heads/codex/professional-review-run-41064476565/professional_motion/delivery/daily-publication-audit.json) |
| ٧. موعد النشر المؤكد | ٣٠ أكتوبر ٢٠٢٦، الساعة ١٧:٠٠ بتوقيت Africa/Cairo |
| ٨. عطل إنتاج أو جدولة متبقٍ | لا يوجد في الدفعة النهائية التي تم التحقق منها. |

SHA-256: `5e86d1838c39279eb97b8d99d9bf02ec023e3b74bef6b9c9171bcac36a21e267`

### أخبار الذكاء الاصطناعي — ai-news-daily

| البند | النتيجة |
|---|---|
| ١. المشكلة | شرط الساعة، وصوت قصير وقلة القفشات، ثم فشل فحص بداية اسم مركب رغم مطابقة أكثر من ٩١٪. تم توسيع نفس الخبر بأربع قفشات أصلية، واستئناف الصوت الصحيح الكامل دون توليد بديل. |
| ٢. الإصلاحات المرفوعة | [نافذة الوقت](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/commit/0b028b3) · [ISO](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/commit/4c6c1d8) · [الحماية والاسترجاع](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/commit/33c0cf2) |
| ٣. GitHub Actions | [إنتاج الفيديو](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/actions/runs/41057377563) · [الجدولة النهائية](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/actions/runs/41057377563) · [التدقيق المباشر](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/actions/runs/41061069091) |
| ٤. MP4 الجديد | [تحديث دليل سلوك OpenAI مع تعليق ساخر](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/releases/download/auto-publish-daily-2026-10-30/science-video-daily-2026-10-30.mp4) |
| ٥. فحص الملف | PASS: ffprobe وffmpeg كامل؛ 148.367 ثانية؛ 1080×1920؛ 30fps؛ AAC 48000Hz؛ HTTP 200؛ أصل Release مطابق للبصمة؛ لا تطابق مع فيديو سابق. |
| ٦. إيصالات Buffer | ٣/٣ مؤكدة من قراءة المنشورات الفعلية، بما فيها القناة والملف والموعد: [JSON الأصلي](https://github.com/ahmedalsharqwi2-gif/ai-news-daily/raw/refs/heads/codex/professional-review-run-41061069091/professional_motion/delivery/daily-publication-audit.json) |
| ٧. موعد النشر المؤكد | ٣٠ أكتوبر ٢٠٢٦، الساعة ١٧:٠٠ بتوقيت Africa/Cairo |
| ٨. عطل إنتاج أو جدولة متبقٍ | لا يوجد في الدفعة النهائية التي تم التحقق منها. |

SHA-256: `c023c8543dc8f3eda4fdf3e1f087df3faaee292042b16db190b7c347699b0d22`

ملاحظة التاريخ: تشغيل الرندر الأول انتهى بفشل خطوة تعديل Buffer، رغم اكتمال الفيديو. رابط الاستكمال أعلاه يثبت نجاح تحديث الأصول على المعرفات الثلاثة نفسها. لم تُنشأ منشورات بديلة أو مكررة.

## الإيصالات الفعلية للوجهات الاثنتي عشرة

| المستودع | الوجهة | post ID | channel ID | scheduled_at الفعلي | الحالة |
|---|---|---|---|---|---|
| science-discovery-shorts | tiktok | `6ae490454233ff6805bdc5b2` | `6a9edf14cd8b9c702c230272` | `2026-10-30T15:00:00.000Z` | scheduled |
| science-discovery-shorts | youtube | `6ae490476516a7746a2a59ac` | `6a9edee8cd8b9c702c2301cb` | `2026-10-30T15:00:00.000Z` | scheduled |
| science-discovery-shorts | facebook | `6ae4904a6516a7746a2a5a49` | `6a9edebbcd8b9c702c230128` | `2026-10-30T15:00:00.000Z` | scheduled |
| arabic-horror-stories | youtube | `6ae491663dc61ec0c2ffdd23` | `6aaa8778ea19ca0bde57da16` | `2026-10-30T15:00:00.000Z` | scheduled |
| arabic-horror-stories | facebook | `6ae491614233ff6805be1cb9` | `6aaa853fea19ca0bde57b5f7` | `2026-10-30T15:00:00.000Z` | scheduled |
| arabic-horror-stories | instagram | `6ae491644233ff6805be1d24` | `6aad267dea19ca0bde778d5e` | `2026-10-30T15:00:00.000Z` | scheduled |
| documented-history-stories | youtube | `6ae48f48abdb62a0e37cc839` | `6ab67b4fea19ca0bdee58218` | `2026-10-30T15:00:00.000Z` | scheduled |
| documented-history-stories | facebook | `6ae48f4ae560b6bf642a6b22` | `6ab67b0dea19ca0bdee58014` | `2026-10-30T15:00:00.000Z` | scheduled |
| documented-history-stories | instagram | `6ae48f4de560b6bf642a6bc5` | `6ab67accea19ca0bdee57e17` | `2026-10-30T15:00:00.000Z` | scheduled |
| ai-news-daily | youtube | `6ae493f1f522e615d3a49b00` | `6ad3ef9d778b240e2f3fa5b9` | `2026-10-30T15:00:00.000Z` | scheduled |
| ai-news-daily | facebook | `6ae493f3e560b6bf642ba4ab` | `6ad3ef2c778b240e2f3fa387` | `2026-10-30T15:00:00.000Z` | scheduled |
| ai-news-daily | instagram | `6ae493f5f522e615d3a49bdd` | `6ad3eeea778b240e2f3fa23b` | `2026-10-30T15:00:00.000Z` | scheduled |

كل رابط فيديو في هذه الإيصالات قورن بالأصل الحالي المرفوع؛ معرّفات المنشورات الاثنا عشر فريدة. منشورات التاريخ احتفظت بمعرفاتها، وتغير أصل الفيديو فيها إلى النسخة المصححة.

## الاختبارات والشعارات

نجحت المجموعة الشاملة: العلوم ٣٤٥، الرعب ٢٦٦، التاريخ ٢٧٤، الأخبار ١٢٤ — الإجمالي ١٠٠٩ اختبارات، إضافة لفحص JavaScript وتجربة شعار الأخبار في متصفح حقيقي. تغطي الاختبارات التأخير، التوقيت الصيفي والشتوي، إغلاق نافذة الإنتاج وموعد النشر، إعادة التشغيل اليومية، تعطل الصوت، غياب MP4، تعطل وجهة أو بيانات الاتصال، الإيصالات الجزئية، منع تكرار الطلبات، وبصمة أصل Release.

أُضيف مسار شعار مستقل لكل مستودع أعلى الفيديو وبعيدًا عن الترجمة، مع التحقق من تطابق ملف إعداد الشعار مع القناة. شعار أخبار AI أُخذ كما هو من الفيديو الذي أرسله المستخدم وثُبّت للفيديوهات القادمة. صور شعارات العلوم والرعب والتاريخ ظاهرة داخل المحادثة، لكن ملفاتها الأصلية القابلة للنسخ لم تتوفر في workspace؛ يلزم إرسالها كمرفقات PNG/JPG أو ZIP لإدراج نفس الصور الأصلية، دون إعادة رسمها. لا يعطل غياب الشعار الاختياري إنتاج الفيديو، ويظل اسم القناة ظاهرًا. فيديوهات اليوم المجدولة لم تُعد لإضافة شعارات؛ طلب المستخدم يخص الفيديوهات القادمة.
