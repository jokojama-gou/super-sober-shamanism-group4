"""
ターミナル（コマンドプロンプト）を開き、以下のコマンドで実行します。

デフォルトの範囲（8000〜9000番）をスキャンする場合:
python osc-sample-code.py 


スキャン範囲を指定する場合（例: 5000〜5010番）:
python osc-sample-code.py  --start 5000 --end 5010


IPアドレスを指定する場合:
python osc-sample-code.py --ip 192.168.1.10 --start 8000 --end 8010

"""


import argparse
from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher
import threading
from rich import print





def check_port(ip, port, available_ports, used_ports):
    """
    単一のポートをチェックする関数
    """
    try:
        # サーバーのインスタンスを作成しようと試みる
        # これが成功すれば、そのポートは利用可能
        server = osc_server.ThreadingOSCUDPServer((ip, port), Dispatcher())
        # 成功したら、すぐにサーバーを閉じてリソースを解放する
        server.server_close()
        available_ports.append(port)
    except OSError:
        # OSErrorが発生した場合、そのポートは既に使用中か、権限がない
        used_ports.append(port)
    except Exception:
        # その他の予期せぬエラー
        used_ports.append(port)


def scan_ports_threaded(ip, start_port, end_port):
    """
    スレッドを使用してポートスキャンを高速化する
    """
    print(f"--- ポートスキャン開始: {ip}:{start_port}-{end_port} ---")
    
    threads = []
    available_ports = []
    used_ports = []

    for port in range(start_port, end_port + 1):
        # 各ポートのチェックを別々のスレッドで実行
        thread = threading.Thread(target=check_port, args=(ip, port, available_ports, used_ports))
        threads.append(thread)
        thread.start()

    # すべてのスレッドが終了するのを待つ
    for thread in threads:
        thread.join()

    # 結果をソートして表示
    available_ports.sort()
    used_ports.sort()

    print("\n✅ 利用可能なポート:")
    if available_ports:
        print(available_ports)
    else:
        print("見つかりませんでした。")
        
    print("\n❌ 使用中またはアクセス不可のポート:")
    if used_ports:
        print(used_ports)
    else:
        print("見つかりませんでした。")

    print("\n--- ポートスキャン終了 ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="指定したIPアドレスのポートが利用可能かスキャンします。")
    parser.add_argument("--ip",
                        default="127.0.0.1", help="スキャンするIPアドレス")
    parser.add_argument("--start",
                        type=int, default=0000, help="スキャンを開始するポート番号")
    parser.add_argument("--end",
                        type=int, default=9999, help="スキャンを終了するポート番号")
    args = parser.parse_args()

    if args.start > args.end:
        print("エラー: 開始ポート番号は終了ポート番号より小さくする必要があります。")
    else:
        scan_ports_threaded(args.ip, args.start, args.end)