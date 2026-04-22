# USER GUIDE - Sub2Speech v0.0.1

## 1. Gioi thieu

Sub2Speech la ung dung chuyen phu de/van ban thanh giong noi bang edge-tts.

## 2. Cai dat va khoi dong

1. Chay `setup.bat` de tao `.venv` va cai thu vien.
2. Chay `run.bat` de mo app.

## 3. Luong su dung tong quat

1. Mo file SRT/TXT.
2. Chon voice va tham so giong doc.
3. Preview.
4. Chon thu muc xuat.
5. Xuat MP3.

## 3.1 Bo cuc giao dien

- Top bar:
  - `Chon file phu de/van ban`
  - `Tro giup`
  - `Thong tin`
  - Dong trang thai file, mode, so segment
- Workspace:
  - Trai: bang `Noi dung`
  - Phai: panel `Chon giong doc` (Voice setup + Speaker mapping)
- Bottom:
  - `Thu muc xuat`, `Chon thu muc`, `Nghe thu dong phu de`, `Xuat MP3`
  - Lua chon `Luu audio goc theo tung dong phu de`
  - Player tich hop o hang duoi

## 4. Huong dan voi file SRT

1. Nhom ben phai cho phep gan voice theo nguoi noi/doan.
2. Co the nhap range doan: `1-5,8,10`.
3. Dung preview de kiem tra.
4. Bam xuat.

## 5. Huong dan voi file TXT

1. App tu dong vao TXT mode.
2. Khong can tao nguoi noi hay danh sach doan.
3. Chon 1 voice + rate/volume/pitch cho toan bo noi dung.
4. App tu dong chia noi dung thanh nhieu doan (toi da 500 tu/doan) va ghep ket qua.

## 6. Retry segment loi

- Neu mot so segment loi trong luc tao giong:
  - App ghi nhan danh sach segment loi.
  - Bam `Xuat MP3` lan nua de tao lai chi cac segment loi.
  - Khi khong con loi, app se render file cuoi.

## 7. Player tich hop

- Preview va file xuat duoc phat ngay trong app.
- Co slider, Play/Pause, Stop.

## 8. Cac tham so giong doc

- `Rate`: toc do doc, vi du `+10%`, `-10%`.
- `Volume`: am luong, vi du `+0%`, `-10%`.
- `Pitch`: cao do, vi du `+0Hz`, `+20Hz`.

## 9. Thong tin va tro giup trong app

- Nut `Tro giup`: mo huong dan nhanh trong app.
- Nut `Thong tin`: hien version va thong tin he thong app.
