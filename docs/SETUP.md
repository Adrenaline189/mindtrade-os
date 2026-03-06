# MindTrade OS — Setup Guide (Quick Start)

อัปเดตล่าสุดสำหรับการใช้งานจริง (soft launch)

## 1) Runtime Settings ที่แนะนำ

ไปที่หน้า **Dashboard → Runtime Settings** แล้วตั้งค่า:

- **Order Size (USDT)**: `10`
- **Risk / Trade**: `0.005`
- **Cooldown minutes**: `90`
- **Leverage (x)**: `3-5`
- **Max trades/day**: `2-3`
- **Daily loss cap %**: `1.5-2.5`

> หมายเหตุ: ระบบมีขั้นต่ำรายเหรียญอัตโนมัติ แม้ตั้ง 10 USDT ก็จะถูกยกขั้นต่ำให้ตรงกติกาแต่ละเหรียญ

## 2) ขั้นต่ำรายเหรียญ (Auto Min Notional)

ระบบจะใช้ขั้นต่ำอัตโนมัติแบบนี้:

- `BTC/USDT` = **25 USDT**
- `ETH/USDT` = **12 USDT**
- `SOL/USDT` = **10 USDT**
- `BNB/USDT` = **10 USDT**
- `XRP/USDT` = **10 USDT**

## 3) กันไม้ซ้อน (One Position at a Time)

เปิดค่าเริ่มต้นแล้ว:

- `ONE_POSITION_AT_A_TIME = True`

ผลลัพธ์:
- ถ้ามี position เปิดอยู่ ระบบจะไม่เปิดไม้ใหม่
- ใน log จะเห็นเหตุผลบล็อก: `open_position_exists`

## 4) สถานะระบบที่ควรเช็กก่อนรัน

1. `/health` ต้องตอบ `ok: true`
2. worker ต้อง `running: true` (หรือกด Start ที่ Dashboard)
3. API Binance เชื่อมต่อผ่าน (Test API)
4. Futures balance มี free margin เพียงพอ

## 5) Troubleshooting สั้น ๆ

### เจอ `below_min_qty`
- เพิ่ม Order Size (USDT) หรือปล่อยให้ระบบ auto-min

### เจอ `margin is insufficient`
- ลด leverage
- ลดจำนวนสัญลักษณ์พร้อมกัน
- เพิ่ม Free margin ใน Futures wallet

### เหมือนเข้าไม้ซ้อน
- เช็กว่าเป็นคนละ tenant หรือเป็น TP/SL ไม่ใช่ entry ใหม่
- ตอนนี้ระบบบล็อกไม้ใหม่เมื่อมี position ค้างแล้ว

## 6) Suggested Soft-Launch Mode (3–5 users)

- ใช้ค่า conservative ก่อน 24–48 ชม.
- ติดตามหน้า Proof + Dashboard ทุก 4–6 ชม.
- เก็บ blocked reasons และปรับทีละจุด
- อย่าปรับหลายพารามิเตอร์พร้อมกันในรอบเดียว

---

อัปเดตโดยน้องมายด์ 🚀
