# 🌐 Meeting Translator
Công cụ nhận diện giọng nói và dịch ngôn ngữ theo thời gian thực (Real-time Speech-to-Text & Translation) từ system audio (loa/headphone), đặc biệt hữu ích khi tham gia các cuộc họp trên MS Teams, Zoom, Google Meet.

App bắt luồng âm thanh thông qua WASAPI loopback, giải mã bằng mô hình AI **Whisper** chạy hoàn toàn trên máy tính, sau đó sử dụng Google Translate để dịch tự động sang Tiếng Việt.

---

## 🚀 Hướng dẫn cài đặt và chạy project

### Yêu cầu hệ thống:
- Hệ điều hành: Windows (vì sử dụng WASAPI loopback để bắt audio).
- Cài đặt sẵn [Python 3.10 trở lên](https://www.python.org/downloads/) (Khi cài đặt, nhớ tích chọn ô **"Add Python to PATH"**).

### Các bước cài đặt thiết lập (Khởi chạy trên máy tính mới):

**Bước 1: Clone repo này về máy**
Mở Terminal (cmd / powershell / git bash) và chạy lệnh sau:
```bash
git clone https://github.com/dachienit/audio-translate.git
cd audio-translate
```

**Bước 2: Chạy ứng dụng bằng 1 click**
Tại thư mục project `audio-translate`, bạn chỉ cần:
- Double-click vào file **`start.bat`**.

Script này sẽ tự động:
1. Kiểm tra Python đã được cài đặt chưa.
2. Tự động tải và cài đặt toàn bộ thư viện bắt buộc (từ `requirements.txt`).
3. Khởi động backend Server (Python).
4. Bạn chỉ cần mở trình duyệt và truy cập: **[http://localhost:3000](http://localhost:3000)**.

> **💡 LƯU Ý LẦN CHẠY ĐẦU TIÊN:**
> Ở lần chạy máy chủ (start.bat) đầu tiên, ứng dụng sẽ có độ trễ khoảng vài chục giây để tải mô hình AI ngôn ngữ (`Whisper-tiny` ~40MB) về máy. Những lần chạy sau sẽ load ngay lập tức.

### Hướng dẫn sử dụng:
1. Mở MS Teams (hoặc Zoom, YouTube). Đảm bảo âm thanh đang được phát ra bình thường.
2. Tại trình duyệt `http://localhost:3000`, phần **"Thiết bị âm thanh"**, chọn đúng thiết bị Loa/Tai nghe mà bạn đang nghe âm thanh cuộc họp.
3. Chọn thiết lập cặp ngôn ngữ: Ví dụ nguồn `English`, đích `Tiếng Việt`.
4. Bấm **Bắt đầu lắng nghe**. Kết quả dịch sẽ hiển thị real-time. Bạn có thể Bấm tải file Text sau khi meeting kết thúc.

---
*Dự án sử dụng Faster-Whisper, Flask, SocketIO, Deep-Translator và Soundcard.*
