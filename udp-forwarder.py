# udp-forwarder.py (HeartRateデータを外部に転送するコード)

from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
# 送信に必要なライブラリをインポート
from pythonosc.udp_client import SimpleUDPClient 
from rich import print 

# =======================================================
# ⚠️ ここを転送先の外部IPアドレスとポートに変更してください
# =======================================================
TARGET_IP = "193.168.1.100"  # 例: 友達のPCのローカルIP、またはグローバルIP
TARGET_PORT = 9001            # 例: 友達のPCのPythonリスナーが待機するポート (9000でも可)

# 送信クライアントを初期化
# このクライアントはサーバー起動時に一度だけ作成されます
client = SimpleUDPClient(TARGET_IP, TARGET_PORT)

def heart_rate_handler(address, *args):
    """OSCメッセージを受信し、表示し、さらに転送する関数"""

    bpm = args[0] if args else "N/A"

    # 1. 受信データの表示
    print(f"❤️  [bold green]📫️Received Heart Rate:[/bold green] [cyan]{bpm}[/cyan] BPM")

    # 2. 受信データを別のIPアドレスとポートに転送
    if isinstance(bpm, (int, float)): # BPMが数値（転送可能）の場合のみ実行
        try:
            # 受信したアドレスと値をそのまま転送
            client.send_message(address, bpm)
            print(f"[yellow]  -> 📮Forwarding to {TARGET_IP}:{TARGET_PORT}[/yellow]")
        except Exception as e:
            # ネットワークエラーが発生した場合
            print(f"[red]  ⚠️ ERROR forwarding data: {e}[/red]")
    else:
        print("[red]  Skipped forwarding (BPM is not a number).[/red]")


if __name__ == "__main__":
    # --- 受信側の設定 --- (HeartRate.exeからデータを受け取る)
    ip = "127.0.0.1" 
    port = 9000

    dispatcher = Dispatcher()
    dispatcher.map("/avatar/parameters/HeartRateBPM", heart_rate_handler)

    # 受信サーバーを起動
    server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
    print(f"✅ [bold]UDPフォワーディングサーバーを起動しました。[/bold]")
    print(f"📫️Listening on {server.server_address}")
    print(f"📮Forwarding to {TARGET_IP}:{TARGET_PORT}")
    print("------------------------------------------")
    server.serve_forever()