import subprocess
import time
import re
import datetime

# --- 設定 ---
INTERFACE = "upfgtp"     # 監視・制御するインターフェース
THRESHOLD_MBPS = 1.0     # 閾値 (1Mbps超えたら規制)
LIMIT_RATE = "0.5mbit"   # 規制時の速度
CHECK_INTERVAL = 0.5     # 監視間隔 (秒)

# 状態管理フラグ
is_congested = False

def get_tx_bytes(interface):
    """ 送信量(TX)を取得します (今回はダウンロードテストなのでTXを見ます) """
    try:
        result = subprocess.run(["ip", "-s", "link", "show", interface], capture_output=True, text=True)
        # TX: の下の行の数字を取得
        match = re.search(r"TX:.*?\n\s*(\d+)", result.stdout, re.DOTALL)
        if match:
            return int(match.group(1))
        return 0
    except:
        return 0

def apply_limit():
    """ 帯域制限(tc)を適用するコマンド """
    print(f"!!! APPLYING TRAFFIC CONTROL: Limit to {LIMIT_RATE} !!!")
    # 一旦既存の設定を消してから、TBF(Token Bucket Filter)でシンプルに制限
    cmd_del = f"tc qdisc del dev {INTERFACE} root 2> /dev/null"
    cmd_add = f"tc qdisc add dev {INTERFACE} root tbf rate {LIMIT_RATE} burst 32kbit latency 400ms"
    
    subprocess.run(cmd_del, shell=True)
    subprocess.run(cmd_add, shell=True)

def remove_limit():
    """ 帯域制限を解除するコマンド """
    print(">>> REMOVING TRAFFIC CONTROL: Back to normal")
    cmd_del = f"tc qdisc del dev {INTERFACE} root 2> /dev/null"
    subprocess.run(cmd_del, shell=True)

def main():
    global is_congested
    print(f"--- NWDAF Auto-Slicing Started on {INTERFACE} ---")
    
    # 起動時に一度制限を解除しておく（クリーンな状態）
    remove_limit()
    
    prev_bytes = get_tx_bytes(INTERFACE)
    prev_time = time.time()

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            curr_bytes = get_tx_bytes(INTERFACE)
            curr_time = time.time()
            
            # スループット計算
            bps = ((curr_bytes - prev_bytes) * 8) / (curr_time - prev_time)
            mbps = bps / 1_000_000
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

            # --- 判定ロジック ---
            if mbps > THRESHOLD_MBPS:
                status = "RED (Congestion!)"
                if not is_congested:
                    # 正常 -> 混雑 に変わった瞬間だけコマンド実行
                    apply_limit()
                    is_congested = True
            else:
                status = "GREEN (Normal)"
                # 今回は実験なので、自動解除はせず「制限しっぱなし」にします
                # (解除ロジックを入れると、速度低下→解除→速度上昇→規制…とバタつくため)

            print(f"[{timestamp}] Load: {mbps:.2f} Mbps | Status: {status}")

            prev_bytes = curr_bytes
            prev_time = curr_time

    except KeyboardInterrupt:
        # スクリプトを止めたら制限も解除してあげる（親切設計）
        print("\nStopping... Cleaning up rules.")
        remove_limit()

if __name__ == "__main__":
    main()