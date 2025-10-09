# receive-data.py (転送されたHeartRateデータを受信するコード)

from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from rich import print
import socket # 自分のIPアドレスを取得するために使用

# =======================================================
# ⚠️ ここをデータを受信するPCのIPアドレスとポートに設定
# =======================================================
# 'udp-forwarder.py'のTARGET_IPとTARGET_PORTと一致させる必要があります

# IPアドレスを自動で取得する場合 (推奨)
# try:
#     # ローカルネットワーク上のIPアドレスを取得
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     s.connect(("8.8.8.8", 80)) # GoogleのDNSサーバーに接続を試みる
#     LISTEN_IP = s.getsockname()[0]
#     s.close()
# except Exception:
#     # 取得できない場合は '0.0.0.0' を使う
#     LISTEN_IP = "0.0.0.0"

# IPアドレスを手動で設定する場合 (例: 193.168.1.100)
LISTEN_IP = "0.0.0.0" # フォワーダー側のTARGET_IPと同じIPアドレス

# もし特定のIPでうまくいかない場合は、'0.0.0.0'を試してください
# '0.0.0.0'は、このPCで利用可能なすべてのネットワークインターフェースで待機するという意味です
# LISTEN_IP = "0.0.0.0" 

LISTEN_PORT = 9001          # フォワーダー側のTARGET_PORTと同じポート番号

def forwarded_heart_rate_handler(address, *args):
    """転送されてきた心拍数データを受信して表示する関数"""
    
    # argsタプルからBPMの値を取得 (args[0]に格納されている)
    bpm = args[0] if args else "N/A"
    
    # 受信したデータを表示
    print(f"❤️  [bold magenta]受信完了:[/bold magenta] [cyan]{bpm}[/cyan] BPM (from {address})")

if __name__ == "__main__":
    # ディスパッチャーを初期化
    dispatcher = Dispatcher()
    
    # 受信するOSCアドレスと、それを処理する関数をマッピング
    # フォワーダーは元のアドレスをそのまま転送するので、アドレスは同じ
    dispatcher.map("/avatar/parameters/HeartRateBPM", forwarded_heart_rate_handler)

    # OSCサーバーを起動
    server = osc_server.ThreadingOSCUDPServer((LISTEN_IP, LISTEN_PORT), dispatcher)
    
    print(f"✅ [bold]OSC受信サーバーを起動しました。[/bold]")
    print(f"📫️ IPアドレス [yellow]{LISTEN_IP}[/yellow]、ポート [yellow]{LISTEN_PORT}[/yellow] で待機中...")
    print("------------------------------------------")
    
    # サーバーを永続的に実行
    server.serve_forever()