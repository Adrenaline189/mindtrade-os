# คู่มือตั้งค่า Binance API (MindTrade OS)

## สิ่งที่ต้องมี
- บัญชี Binance
- เปิดใช้งาน Futures (ถ้าจะเทรด Futures)
- เปิด 2FA

## ขั้นตอน
1. ไปหน้า API Management และสร้าง API Key
2. เปิดสิทธิ์:
   - Enable Reading = ON
   - Enable Futures = ON
   - Withdraw = OFF
3. ถ้าใช้ IP Restriction ให้เพิ่ม IP VPS:
   - `185.230.138.51`
4. บันทึก API Key/Secret ลง `.env`
5. Restart service
6. ตรวจสอบที่ `/api/connection`

## อาการผิดพลาดที่เจอบ่อย
- `-2015` = key/ip/permission ไม่ถูก
- `-1021` = เวลาเครื่องไม่ตรง

## Checklist ก่อน LIVE
- PAPER ผ่านอย่างน้อย 24-72 ชั่วโมง
- ตั้ง Daily loss cap
- ตั้ง cooldown / max trades ต่อวัน
