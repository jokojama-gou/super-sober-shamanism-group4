# receive-data.py (転送されたHeartRateデータを受信するコード)

from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from rich import print
import socket # 自分のIPアドレスを取得するために使用
import sys # コマンドライン引数を受け取るために追加

# =======================================================
# ⚠️ ここをデータを受信するPCのIPアドレスとポートに設定
# =======================================================

# IPアドレスの設定
# ほとんどの場合、これで動作します
LISTEN_IP = "0.0.0.0" 

# ポート番号はコマンドライン引数から取得するように変更
# LISTEN_PORT の固定値設定を削除

def forwarded_heart_rate_handler(address, *args):
    """転送されてきた心拍数データを受信して表示する関数"""
    
    # argsタプルからBPMの値を取得 (args[0]に格納されている)
    bpm = args[0] if args else "N/A"
    
    # 受信したデータを表示
    print(f"❤️  [bold magenta]受信完了:[/bold magenta] [cyan]{bpm}[/cyan] BPM (from {address})🫀")

if __name__ == "__main__":
    # --- ポート番号を引数から取得する処理 ---
    if len(sys.argv) < 2:
        # 引数が指定されていない場合はエラーメッセージを表示し、終了
        # デフォルト値を持たせることも可能ですが、ここでは引数必須とします。
        print("[bold red]エラー:[/bold red] 待ち受けポート番号を引数として指定してください。")
        print(f"使用方法: [yellow]python {sys.argv[0]} <ポート番号>[/yellow]")
        sys.exit(1)
        
    try:
        # 1つ目の引数をポート番号として取得し、整数に変換
        LISTEN_PORT = int(sys.argv[1])
    except ValueError:
        print("[bold red]エラー:[/bold red] ポート番号は整数である必要があります。")
        sys.exit(1)
    # ------------------------------------------

    # ディスパッチャーを初期化
    dispatcher = Dispatcher()
    
    # 受信するOSCアドレスと、それを処理する関数をマッピング
    dispatcher.map("/avatar/parameters/HeartRateBPM", forwarded_heart_rate_handler)

    # OSCサーバーを起動
    server = osc_server.ThreadingOSCUDPServer((LISTEN_IP, LISTEN_PORT), dispatcher)
    
    print(f"✅ [bold]OSC受信サーバーを起動しました。[/bold]")
    print(f"📫️ IPアドレス [yellow]{LISTEN_IP}[/yellow]、ポート [yellow]{LISTEN_PORT}[/yellow] で待機中...")
    print("------------------------------------------")
    
    # サーバーを永続的に実行
    server.serve_forever()