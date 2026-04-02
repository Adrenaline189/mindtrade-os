# Realtime Entry Scoring v1

เพิ่มระบบให้คะแนนสัญญาณเข้าเทรดแบบเรียลไทม์ต่อ symbol (0-100) เพื่อช่วยคัดคุณภาพ setup ก่อนเข้าไม้

## สรุปการทำงาน

คะแนนรวม = Trend (40) + Momentum (35) + Volatility (25)

- **Trend (0-40)**
  - มี bias LONG/SHORT จาก EMA50/EMA200
  - ระยะย่อตัวเข้า Golden Zone
  - ความห่างราคาเทียบ EMA200
- **Momentum (0-35)**
  - RSI อยู่ในช่วงที่กำหนด
  - ADX สูงกว่า ADX_MIN
- **Volatility (0-25)**
  - ATR% อยู่ในช่วง ATR_PCT_MIN..ATR_PCT_MAX

ระบบจะเก็บเหตุผล (reasons) และ component score แยกให้ dashboard ใช้ดูและปรับค่าได้

## Runtime Config ใหม่

- `ENTRY_SCORE_SOFT_GATE` (default: `true`)
- `ENTRY_SCORE_THRESHOLD` (default: `65`)

## การตัดสินใจเข้าไม้

เงื่อนไขเดิมยังอยู่ครบ (golden_zone + quality filter + risk guards)

หากเปิด soft gate (`ENTRY_SCORE_SOFT_GATE=true`):
- จะ **block** เมื่อ `score < ENTRY_SCORE_THRESHOLD`
- log reason: `score_gate score=...<threshold ...`

หากปิด soft gate:
- คะแนนยังแสดงใน API/UI และ log แต่ไม่บล็อกการเข้าไม้

## API ใหม่

- `GET /api/signals/realtime`
- `GET /api/tenant/{tenant_id}/signals/realtime`

Response หลัก:
- `threshold`, `soft_gate`
- `signals[]` ต่อ symbol พร้อม fields เช่น `score`, `components`, `score_reasons`, `score_ok`, `golden_zone`, `quality_ok`

## Dashboard

เพิ่ม section `Real-time Entry Scores` แสดง:
- คะแนนต่อ symbol
- PASS/WAIT ตาม threshold
- component score และ reasons แบบย่อ

## ค่าตั้งต้นแนะนำ (conservative)

- มือใหม่/ระวังสูง: `ENTRY_SCORE_THRESHOLD=70-75`
- สมดุล: `65-70`
- Aggressive: `55-60` (ควรลด risk/trade ควบคู่)

แนะนำเริ่มที่ `65` แล้วดู blocked reasons 3-7 วันก่อนปรับ
