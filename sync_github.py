import subprocess
import datetime
import sys
from pathlib import Path

def auto_push_to_github(commit_message: str = None):
    """
    Tự động commit và đẩy các thay đổi của Bảng điều hành (index.html, data/) lên GitHub.
    """
    if commit_message is None:
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        commit_message = f"Cập nhật tiến độ thi công từ Zalo lúc {now_str} [auto-sync]"

    base_dir = Path(__file__).resolve().parent

    try:
        # 1. Git add
        print("[Git Sync] Đang thêm các file thay đổi (index.html, data, core)...")
        subprocess.run(["git", "add", "index.html", "data/Bang_dieu_hanh_TD3.html", "core/", "database/"], cwd=str(base_dir), check=True)

        # 2. Git commit
        print(f"[Git Sync] Đang tạo commit: '{commit_message}'...")
        res = subprocess.run(["git", "commit", "-m", commit_message], cwd=str(base_dir), capture_output=True, text=True)
        if "nothing to commit" in res.stdout:
            print("[Git Sync] Dữ liệu đã ở trạng thái mới nhất, không có thay đổi cần đẩy.")
            return True

        # 3. Git push
        print("[Git Sync] Đang đẩy lên GitHub...")
        push_res = subprocess.run(["git", "push"], cwd=str(base_dir), capture_output=True, text=True)
        if push_res.returncode == 0:
            print("✅ Đã đồng bộ lên GitHub thành công! GitHub Pages sẽ cập nhật trong ít giây.")
            return True
        else:
            print(f"⚠️ Chưa đẩy được lên GitHub (có thể do chưa cấu hình remote origin): {push_res.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi thực hiện git sync: {e}")
        return False

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else None
    auto_push_to_github(msg)
