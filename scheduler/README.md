# مشغّل مستقل لمصنع الفيديوهات

هذه الخدمة تبدأ GitHub Actions فقط. كتابة الموضوع والصوت والإخراج والنشر تظل داخل المستودعات الخمسة وبمفاتيح كل مستودع الحالية. لا تستخدم ChatGPT أو بيئة هذه المحادثة بعد النشر.

## المواعيد والحماية

- تشغيل ٩ صباحًا بتوقيت `Africa/Cairo`، واحتياطي ٩:١٧. التعامل مع الصيف والشتاء داخل المشغّل، مع بقاء احتياطي GitHub.
- النشر ٥ مساءً في اليوم نفسه. فحص النشر المستقل يُطلب عند ٥:٣٥ مساءً.
- لكل مستودع ويوم ونوع مهمة قفل دائم في Cloudflare Durable Objects. يُسجّل قصد الإرسال قبل الاتصال بـGitHub.
- تُقرأ نتيجة التشغيل المكتمل قبل اعتباره إنتاجًا؛ اختبار `dry_run` أو تشغيل التوقيت الصيفي غير المستحق لا يمنع بدء الإنتاج الحقيقي. التشغيل الجاري يُترك، ثم يعاد فحص نتيجته في الموعد الاحتياطي.
- ضياع تأكيد الطلب لا يسبب طلبًا ثانيًا. وجود تشغيل إنتاج سابق، حتى لو فشل، يُحفظ ويحتاج فحصًا؛ لا يعاد توليد الصوت أو إرسال المنشورات تلقائيًا. فحص النشر قراءة فقط، ويمكن أن يعيد التحقق بعد اكتمال فحص سابق فاشل دون إرسال منشور جديد.
- لا ترحيل لموعد فائت، ولا تشغيل إنتاج ظهرًا لتعويض حدث قديم. المشغّل لا يحمل مفاتيح Gemini أو Buffer.
- HTTP العام يعيد404. منافذ الفحص محمية بمفتاح عشوائي ينشئه برنامج النشر؛ اختبار الربط يُجبر `dry_run=true`.

## الوصول المطلوب مرة واحدة

أضف إلى **Secrets في بيئة التنفيذ**، وليس في الملفات أو المحادثة:

1. `CLOUDFLARE_API_TOKEN`: لحساب Cloudflare المقصود، بصلاحية **Workers Scripts: Edit** و**Account Settings: Read**. لا يلزم الوصول إلى DNS أو كل الحسابات.
2. `GITHUB_DISPATCH_TOKEN`: **Fine-grained personal access token** من [GitHub](https://github.com/settings/personal-access-tokens/new)، مقيّد بالمستودعات الخمسة فقط، بصلاحية **Actions: Read and write**. لا يحتاج صلاحيات حذف المستودعات أو تعديل الكود أو قراءة أسرارها.

`CLOUDFLARE_ACCOUNT_ID` موجود بالفعل في البيئة. صلاحية اتصال GitHub داخل ChatGPT لا تُصدّر كمفتاح دائم إلى Cloudflare؛ لذلك يحتاج المشغّل تفويضه المحدود الخاص.

احتفظ بمدة صلاحية المفاتيح وسجّل موعد تجديدها؛ إلغاؤها أو انتهاء صلاحيتها يوقف الاستدعاء. لا تُنسخ مفاتيح Gemini أو Buffer إلى Cloudflare. يحتاج النشر نقل مفتاح GitHub إلى Secret خاص داخل Worker، وليس إلى ملفات المشروع.

المستودعات: `science-discovery-shorts` و`arabic-horror-stories` و`documented-history-stories` و`ai-news-daily` و`stickman-what-if-shorts`، تحت `ahmedalsharqwi2-gif`.

## الاختبار والتفعيل

```sh
npm ci
npm run check
npm run bundle
node runtime.test.mjs
npm run deploy:verified
```

يلزم Node.js24. يستخدم أمر النشر إعدادات الـproxy الموجودة في البيئة ويحافظ على التحقق من TLS.

برنامج النشر يرفض استبدال Worker ليس له علامة ملكية هذا المشروع. أول نشر يكون **probe-only** والإنتاج معطلاً؛ ثم ينتظر حدث Cron حقيقي من Cloudflare، ويطلب اختبارًا للخمسة في وضع `dry_run`، ويتحقق من نجاح التشغيلات وسجل مصدرها وتاريخها. بعد ذلك فقط يفعّل مواعيد الإنتاج، ويتحقق من تسجيلها. قد يستغرق انتشار Cron على Cloudflare حتى١٥ دقيقة.

إذا فشلت الاختبارات لا تُفعّل الخدمة. وإذا فشل تأكيد التفعيل الأخير يحاول تعطيلها ويذكر صراحةً إن تعذر إثبات التعطيل. التقرير `live-verification.json` لا يحتوي مفاتيح. لا تعني استجابة dispatch قبولًا بإكمال الفيديو أو نشره؛ الإكمال يثبته فحص المستودع وإيصالات المنصات.

التهيئة الحالية محفوظة مع `DISPATCH_ENABLED=false` و`PROBE_ONLY=true`. **وجود هذه الملفات لا يعني أن الخدمة نُشرت أو أن الربط الحي اكتمل.**

## المصدر الفني

- [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
- [Cloudflare SQLite Durable Objects](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)
- [GitHub workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
