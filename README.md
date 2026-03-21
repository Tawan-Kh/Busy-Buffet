# 🍽️ Busy Buffet - Data Analytics Dashboard

แดชบอร์ดสรุปผลการวิเคราะห์ข้อมูลลูกค้า การรอคิว และระยะเวลาการทานอาหารสำหรับร้านอาหารบุฟเฟต์ ได้อย่างง่ายดายผ่านการอัปโหลดไฟล์ Excel หรือ CSV

**🌐 Live Demo:** [Busy Buffet Dashboard](https://busy-buffet-acpkvngbksncvdq6v4fw7t.streamlit.app/)

## ✨ ฟีเจอร์หลัก (Features)

* **File Upload:** รองรับการอัปโหลดไฟล์ `.csv` และ `.xlsx` (หากเป็น Excel ระบบจะดึงข้อมูลจากทุก Sheet มาวิเคราะห์เป็นรายวัน)
* **Per-sheet Analytics:** สรุปข้อมูลรายวัน (ราย Sheet) เช่น จำนวนลูกค้าทั้งหมด, กลุ่มที่ทิ้งคิว (Walk-away), และเวลารอคิวเฉลี่ย
* **Queue Performance & Attrition:** เปรียบเทียบเวลารอคิวและจำนวนการทิ้งคิวระหว่างลูกค้าระบุประเภท (In-house vs Walk-in)
* **Daily Guest Volume:** กราฟแท่งแสดงปริมาณลูกค้าในแต่ละวันเพื่อดูความหนาแน่น (Peak Demand)
* **Meal Duration Dynamics:** วิเคราะห์ระยะเวลาการทานอาหารเฉลี่ย โดยมีการตัดข้อมูลที่ผิดปกติ (99th Percentile Outliers Trimmed) ออกเพื่อให้ได้ค่าสถิติที่แม่นยำยิ่งขึ้น

## 📊 รูปแบบข้อมูลที่รองรับ (Data Format)

ไฟล์ที่นำมาอัปโหลดจะต้องมีชื่อคอลัมน์ (Column Headers) ตรงกับที่ระบบกำหนดไว้ ดังนี้:

| ชื่อคอลัมน์ | คำอธิบาย | ประเภทข้อมูล / ตัวอย่าง |
| --- | --- | --- |
| `service_no.` | หมายเลขคิวหรือหมายเลขบริการ | Text / Number |
| `pax` | จำนวนลูกค้าต่อกลุ่ม | Number |
| `queue_start` | เวลาที่เริ่มรับคิว | Time (`HH:MM:SS`) |
| `queue_end` | เวลาที่ได้โต๊ะ (สิ้นสุดการรอ) | Time (`HH:MM:SS`) |
| `table_no.` | หมายเลขโต๊ะ | Text / Number |
| `meal_start` | เวลาที่เริ่มทานอาหาร | Time (`HH:MM:SS`) |
| `meal_end` | เวลาที่ทานเสร็จและเช็คบิล | Time (`HH:MM:SS`) |
| `Guest_type` | ประเภทลูกค้า | ต้องเป็น `Walk In` หรือ `In House` เท่านั้น |

> **💡 หมายเหตุ:**
> * หากไม่มีการรอคิว สามารถเว้นว่าง `queue_start` และ `queue_end` ได้
> * หากลูกค้าทิ้งคิว (Walk-away) ให้มีข้อมูล `queue_start` แต่เว้นว่างคอลัมน์ `meal_start` ไว้ ระบบจะคำนวณว่าลูกค้ายกเลิกคิวอัตโนมัติ
