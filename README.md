# GM1 MIDI Reset

โปรแกรม Windows หน้าต่างภาษาไทย สำหรับรีเซ็ตไฟล์ `.mid` / `.midi` เป็นการตั้งค่า GM1 รองรับไฟล์เดียวและหลายไฟล์ พร้อมรายงานผลแต่ละไฟล์ ไม่เขียนทับต้นฉบับหรือไฟล์ผลลัพธ์ที่มีอยู่แล้ว

## เปิดใช้งานบน Windows

1. ติดตั้ง Python 3.12 จาก https://www.python.org/downloads/windows/ (เลือกติดตั้ง Tcl/Tk และ Python Launcher)
2. ดาวน์โหลด repository ผ่าน **Code → Download ZIP** แล้วแตกไฟล์
3. ดับเบิลคลิก `start_windows.bat` ครั้งแรกต้องใช้อินเทอร์เน็ตเพื่อติดตั้ง dependency
4. เพิ่มไฟล์หรือเพิ่มโฟลเดอร์ (เฉพาะไฟล์ในโฟลเดอร์นั้น ไม่รวมโฟลเดอร์ย่อย)
5. เลือกปลายทาง ตั้งน้ำหนักโน้ตตามต้องการ (เริ่มต้น 100) แล้วกด **รีเซ็ตและบันทึกไฟล์ใหม่**

ชื่อผลลัพธ์เป็น `ชื่อเดิม_GM1.mid` ถ้าซ้ำจะเพิ่ม `_1`, `_2` ตามลำดับ ข้อผิดพลาดแต่ละไฟล์แสดงในตารางและไม่หยุดไฟล์อื่น

## สร้าง EXE

บน Windows ดับเบิลคลิก `build_windows.bat` จะได้ `dist/GM1-MIDI-Reset.exe` ซึ่งเปิดได้โดยไม่ต้องติดตั้ง Python บนเครื่องปลายทาง

GitHub Actions ในแท็บ **Actions → Test and build Windows app** จะทดสอบและสร้าง EXE บน Windows ให้ด้วย ดาวน์โหลด ZIP จากส่วน **Artifacts → GM1-MIDI-Reset-Windows** ของ run ที่สำเร็จ แล้วแตกไฟล์ก่อนเปิด EXE (ต้องลงชื่อเข้าใช้ GitHub เพื่อดาวน์โหลด artifact)

## การแปลง

- รองรับ Standard MIDI File Type 0 และ 1; ปฏิเสธ Type 2 พร้อมข้อความชัดเจน
- เพิ่ม GM System On ที่ tick 0 และตั้ง Bank MSB/LSB = 0, Volume = 100, Pan = 64, Expression = 127, Sustain/Reverb/Chorus = 0, Pitch Bend = 0 ในทุกแชนเนลที่ใช้งาน
- กำหนดเสียงเริ่มต้นเป็น GM program 0 (Acoustic Grand Piano) เมื่อไม่มีคำสั่งเลือกเสียง แล้วรักษา Program Change ของแชนเนลเครื่องดนตรีตามเวลาเดิม
- แชนเนล 10 ใช้ Standard Drum Kit และลบ Program Change เดิมของแชนเนลนี้
- Note On ที่ velocity > 0 เปลี่ยนเป็นค่าที่เลือก; Note On velocity 0 ยังคงเป็นคำสั่งหยุดโน้ต และ Note Off คงเดิม
- ลบ Control Change **ทุกชนิด**, SysEx เดิม, Pitch Bend เดิม และ Aftertouch ทั้งเพลง เพื่อไม่ให้การตั้งค่า GS/XG หรือคำสั่งระหว่างเพลงเปลี่ยนค่ากลับ
- คง tick ของเหตุการณ์ที่เก็บไว้ รวมทั้งโน้ต Tempo, Time Signature, Key Signature, ชื่อแทร็ก เนื้อร้อง และจุดจบแทร็ก

**ข้อจำกัด:** นี่คือการรีเซ็ต ไม่ใช่การกู้ต้นฉบับ เสียงเฉพาะ GS/XG อาจเปลี่ยนไป การล้าง Sustain และ Controller เช่น All Notes Off อาจเปลี่ยนระยะเสียงที่ได้ยิน แม้ตำแหน่ง Note On/Off คงเดิม การลบ RPN/NRPN ทำให้ tuning และ pitch bend range เดิมไม่ถูกเก็บไว้ เสียงจริงขึ้นอยู่กับเครื่องเล่นและ SoundFont; GM1 ไม่ได้กำหนดให้ Velocity ต้องเท่ากับ 100 โปรแกรมไม่มีเครื่องเล่นเสียงในตัว

## พัฒนาและทดสอบ

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m gm_reset
```

ส่วนแปลง MIDI อยู่ใน `gm_reset/core.py`; หน้าต่าง Tkinter อยู่ใน `gm_reset/gui.py` งานแปลงทำใน background thread เพื่อไม่ให้หน้าต่างค้าง
