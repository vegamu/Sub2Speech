# Sub2Speech

Sub2Speech la ung dung desktop dung PySide6 de chuyen file phu de SRT hoac file van ban TXT thanh audio MP3 192 kbps bang `edge-tts`.

## Version

- `0.0.1`

## Tinh nang chinh

- Ho tro SRT/TXT.
- SRT: giu timeline theo subtitle (speed-up/pad silence theo tung dong).
- TXT: tu dong chia doan (toi da 500 tu/doan), tao audio lan luot, ghep thanh file cuoi.
- Quan ly nhieu nguoi noi, gan voice theo danh sach doan.
- Nghe thu trong app (player tich hop), khong can mo app ngoai.
- Chon thu muc output va nho lai cho lan sau.
- Tuy chon luu file audio goc theo tung dong subtitle.
- Co che bo qua segment loi, cho phep tao lai segment loi.
- Giao dien hien dai 3 vung: Top bar, Workspace 2 cot, Bottom action bar.

## Bo cuc giao dien moi

- Top bar: nut `Chon file phu de/van ban`, `Tro giup`, `Thong tin` va trang thai file.
- Workspace: trai la bang `Noi dung`, phai la panel `Chon giong doc`.
- Bottom action bar:
  - Hang 1: thu muc xuat + preview + xuat MP3 + tuy chon luu audio goc.
  - Hang 2: player tich hop (Play/Pause, Stop, slider).

## Quick Start

### 1) Cai dat

```bat
setup.bat
```

### 2) Chay ung dung

```bat
run.bat
```

## Quy trinh su dung

### Luong SRT (nhieu speaker)

1. Mo file `.srt`.
2. Gan voice cho speaker/nhom doan.
3. Preview de nghe thu.
4. Bam `Xuat MP3`.
5. Neu co segment loi, bam `Xuat MP3` de tao lai segment loi cho den khi hoan tat.

### Luong TXT (1 voice toan bo)

1. Mo file `.txt`.
2. App chuyen sang che do TXT, chi can chon voice + rate/volume/pitch.
3. Preview de nghe thu.
4. Bam `Xuat MP3`.

## Xu ly loi thuong gap

- `Thiếu voice`: chua gan giọng cho tat ca segment.
- `No audio was received`: loi mang/edge-tts tam thoi, thu xuat lai.
- `ffmpeg error`: xem log CMD chi tiet (app da in stderr cu the).

## Tai lieu bo sung

- Xem them file `USER_GUIDE.md` de co huong dan day du.
