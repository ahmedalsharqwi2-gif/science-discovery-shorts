# Auto Publish Reels

خط أنابيب آلي لإنشاء مقاطع Reels عربية قصيرة، مع التحقق من الحقائق، تحويل النص إلى صوت، وإرسال الناتج إلى قنوات النشر.

## هيكل المشروع

- `main.py` — نقطة تشغيل خط الأنابيب.
- `llm_gemini.py` — عميل Gemini المستخدم لتوليد النصوص.
- `fact_check.py` — التحقق من الحقائق والمصادر.
- `tts_quality.py` — توليد الصوت وفحص جودته.
- `make_reference_voice.py` — إنشاء عينة صوت مرجعية عند الحاجة.
- `config/` — مصادر الحقائق وبنك الموضوعات.
- `assets/voices/` — ملفات وأوصاف أصوات SILMA.
- `tools/` — أدوات مساعدة مثل بناء بنك الموضوعات.
- `tests/` — اختبارات المشروع.
- `.github/workflows/` — مهام GitHub Actions للنشر وإنشاء الصوت المرجعي.

## التشغيل

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
```

يتطلب التشغيل الكامل تثبيت `ffmpeg` وضبط مفاتيح الخدمات المطلوبة كمتغيرات بيئية أو أسرار GitHub Actions. لا تُحفظ الملفات الناتجة أو الأسرار داخل المستودع.

## مراجعة الصورة والصوت

راجع [CLIP_REVIEW.md](CLIP_REVIEW.md) لإعداد مراجعة المقاطع الفعلية والصوت قبل النشر، وتشخيص توقف المسار عند عدم وجود مشهد مطابق.


### Bounded visual fallback
Pexels candidates are bounded before falling back to Wikimedia Commons public-domain / CC0 JPEG or PNG images. Images are fitted to the frame, animated with FFmpeg, and inspected by the existing actual-media gate before acceptance. Provider errors never grant approval. Source and license metadata are retained beside each animated clip. No API key is required for Commons. Pixabay and Mixkit are not yet integrated. This does not change the episode duration or publication schedule.
