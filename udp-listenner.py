# udp-listenner.py (最終的な推奨コード)

from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from rich import print # あなたが使っていたrichライブラリを反映

def heart_rate_handler(address, *args):
    """OSCメッセージを受信したときに呼び出される関数"""
    
    # argsに受信したデータ（例: 75）がタプルとして入る -> (75,)
    bpm = args[0] if args else "N/A"
    
    # richの機能を使ってきれいに表示
    print(f"❤️  [bold green]Received Heart Rate:[/] [cyan]{bpm}[/] BPM🫀")


if __name__ == "__main__":
    # IPとポートの設定
    ip = "127.0.0.1" 
    port = 9010

    # ディスパッチャーの準備
    dispatcher = Dispatcher()
    # /avatar/parameters/HeartRateBPM というアドレスのメッセージを
    # heart_rate_handler 関数に渡すよう設定
    dispatcher.map("/avatar/parameters/HeartRateBPM", heart_rate_handler)

    # サーバーを起動
    server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
    print(f"✅ [bold]UDPサーバーを起動しました。[/]")
    print(f"Listening on {server.server_address}")
    print("HeartRateアプリからのデータを待っています...")
    print("------------------------------------------")
    server.serve_forever()