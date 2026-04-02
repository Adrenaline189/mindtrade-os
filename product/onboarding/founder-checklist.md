# Founder Onboarding Checklist

## 1) Kickoff (10 นาที)
- [ ] ยืนยันโหมดเริ่มต้น = PAPER
- [ ] เลือก symbols ที่ต้องการ
- [ ] ตั้ง risk/trade

## 2) Account & Security
- [ ] สร้าง API key (trade only)
- [ ] ปิดถอนเงิน (withdrawal)
- [ ] ใส่ .env ให้ครบ
- [ ] ตั้ง TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID

## 3) Risk setup
- [ ] ตั้ง MAX_TRADES_PER_DAY
- [ ] ตั้ง COOLDOWN_MINUTES
- [ ] ตั้ง DAILY_LOSS_CAP_PCT
- [ ] ทดสอบ PANIC/UNPANIC

## 4) Validation
- [ ] รัน PAPER อย่างน้อย 48 ชม.
- [ ] ตรวจ log ว่ามี ENTRY / TP / SL / BLOCKED ครบ
- [ ] สรุป expectancy + drawdown

## 5) Go-Live (ทุนเล็ก)
- [ ] เปิด LIVE + allow_live=true
- [ ] ทุนเล็กมาก 1–2 ไม้แรก
- [ ] เฝ้าหน้าจอจนจบ cycle แรก
