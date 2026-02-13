import subprocess
import time
import re
import datetime

# 監視設定
INTERFACE = "upfgtp"  # 監視するインターフェース名
THRESHOLD_MBPS = 1.0  # 閾値 (これを超えたら混雑とみなす: 1Mbps)
INTERVAL = 1.0        # 監視間隔 (秒)

def get_rx_bytes(interface):
    """ 指定したインターフェースのRXバイト数を取得する """
    try:
        # ip -s link show コマンドを実行
        result = subprocess.run(
            ["ip", "-s", "link", "show", interface],
            capture_output=True, text=True
        )
        # 正規表現で RX: ... の次の行にある数字を探す
        output = result.stdout
        match = re.search(r"RX:.*?\n\s*(\d+)", output, re.DOTALL)
        if match:
            return int(match.group(1))
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 0

def main():
    print(f"Starting NWDAF Monitoring on {INTERFACE}...")
    print(f"Congestion Threshold: {THRESHOLD_MBPS} Mbps")
    
    prev_bytes = get_rx_bytes(INTERFACE)
    prev_time = time.time()

    try:
        while True:
            time.sleep(INTERVAL)
            
            current_bytes = get_rx_bytes(INTERFACE)
            current_time = time.time()
            
            # 経過時間と増加バイト数を計算
            time_diff = current_time - prev_time
            bytes_diff = current_bytes - prev_bytes
            
            # スループット計算 (bits per second)
            if time_diff > 0:
                bps = (bytes_diff * 8) / time_diff
                mbps = bps / 1_000_000  # Mbpsに変換
            else:
                mbps = 0
            
            # 判定ロジック (Analytics)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            status = "GREEN (Normal)"
            
            if mbps > THRESHOLD_MBPS:
                status = "RED (Congestion!) -> Action Required"
                # ★ここに将来的に tc コマンドなどの自動制御を入れる
            
            print(f"[{timestamp}] Load: {mbps:.2f} Mbps | Status: {status}")
            
            # 次のループのために値を更新
            prev_bytes = current_bytes
            prev_time = current_time

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()