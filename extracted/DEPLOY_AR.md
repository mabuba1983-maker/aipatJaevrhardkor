# نشر نواة على سيرفر (واجهة ويب + API)

## ما اللي ينعرض
- صفحة محادثة عربية تشتغل على الجوال والكمبيوتر: `http://عنوان-السيرفر:8000`
- API: `POST /api/chat` جسمه `{"message": "..."}` يرجع `{"reply": "..."}`، و`GET /api/health`.
- التعليم `POST /api/teach` للمدير فقط (يحتاج `Authorization: Bearer <NUWAA_ADMIN_TOKEN>`)، حتى ما يخرّب الغرباء النموذج.

## أسهل طريقة (سيرفر Ubuntu، أي مزود، ~5$ شهريا يكفي للمعرفة بدون نموذج مدرَّب)
```bash
# 1) ارفع مجلد Nuwaa للسيرفر ثم:
cd Nuwaa
NUWAA_ADMIN_TOKEN="اكتب-كلمة-سر-طويلة" python3 server/server.py
```
يشتغل بدون تثبيت أي مكتبة. لو عندك نموذج مدرَّب (`model.pt`) ثبّت PyTorch (`pip install torch numpy`) وحط الملف بجانب `server/`، أو حدد مساره بـ `NUWAA_MODEL`.

### تشغيل دائم (يرجع يشتغل بعد إعادة التشغيل)
```bash
sudo tee /etc/systemd/system/nuwaa.service <<'UNIT'
[Unit]
Description=Nuwaa
After=network.target
[Service]
WorkingDirectory=/home/ubuntu/Nuwaa
Environment=NUWAA_ADMIN_TOKEN=غيّر-هذه
ExecStart=/usr/bin/python3 server/server.py
Restart=always
User=ubuntu
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl enable --now nuwaa
```

### دومين + HTTPS (مطلوب إذا الناس بيستخدمونه)
ثبّت Caddy (`sudo apt install caddy`) وضع في `/etc/caddy/Caddyfile`:
```
نطاقك.com {
    reverse_proxy localhost:8000
}
```
ثم `sudo systemctl reload caddy`. يجيب شهادة HTTPS تلقائيا.

### بديل: Docker
```bash
docker build -t nuwaa --build-arg WITH_TORCH=0 .
docker run -d --restart always -p 8000:8000 -e NUWAA_ADMIN_TOKEN=غيّر-هذه \
  -v $PWD/knowledge:/app/knowledge -v $PWD/data:/app/data nuwaa
```

## التطوير (تشغّله أنت)
```bash
python3 server/improve.py --stage s5m --steps 20000             # يدرّب ويختبر ويكتب تقريرا فقط
python3 server/improve.py --stage s5m --steps 20000 --approve   # يستبدل النموذج لو نجح كل شيء وتفوّق فعلا
```
- يجمع ما تعلّمته (`/api/teach`) ويعقّمه، يدرّب **من الصفر** على كل البيانات، يشغّل كل الفحوصات، ويقارن بالنموذج المعتمد على أسئلة ما دخلت التدريب (`data/eval/`).
- إذا تفوّق بدقة يُستبدل `model.pt` والسيرفر يحمّله **بدون إعادة تشغيل**، وإذا لا يبقى القديم.
- للتشغيل التلقائي كل أسبوع (cron): `0 3 * * 0 cd /home/ubuntu/Nuwaa && python3 server/improve.py --stage s5m --approve >> improve.log 2>&1`
- التدريب يحتاج كرت شاشة عمليا. على سيرفر بدون GPU يكون بطيئا جدا، فدرّب على Colab (`tools/Nuwaa_training.ipynb`) وانسخ `model.pt`.

## صدق
- **هذا تطوير للأوزان والبيانات، مو إعادة كتابة المحرك لنفسه.** الكود نفسه (المعمارية) ما يعدّله النموذج.
- **اختبار القبول الحالي صغير (14 سؤالا)**. كبّره (`data/eval/benchmark.jsonl`) وإلا ممكن يقبل نموذجا ما تحسّن فعلا.
- تعليم المدير يدخل مباشرة. راجع `data/user_feedback.jsonl` قبل ما تدرّب لو فتحت التعليم لغيرك.
- المحادثات ما تُسجَّل افتراضيا. لو فعّلت `NUWAA_LOG=1` أبلغ المستخدمين.
