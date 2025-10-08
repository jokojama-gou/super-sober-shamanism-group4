"""
自分へのメモ

関数1 デヴァイスをpythonでスキャンし、接続する
関数2 心拍数データを配信するのを、購読する。


"""


from rich import print


import asyncio
import sys
import csv
from datetime import datetime
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

# 標準のHeart Rate Service関連のUUID
HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

# グローバル変数で切断イベントを管理
disconnected_event = asyncio.Event()

def parse_heart_rate_data(sender: int, data: bytearray):
    """
    受信したバイト列データを解析し、心拍数(BPM)とRR間隔を抽出する。
    Heart Rate Measurement Characteristicの仕様に基づく。
    """
    flags = data[0]
    
    # BPMのフォーマット (Bit 0: 0ならUINT8, 1ならUINT16)
    is_bpm_uint16 = (flags & 0x01)
    if is_bpm_uint16:
        bpm = int.from_bytes(data[1:3], byteorder='little')
        next_byte_index = 3
    else:
        bpm = data[1]
        next_byte_index = 2

    # RR間隔データの有無 (Bit 4: 1なら存在する)
    is_rr_interval_present = (flags & 0x10)
    rr_intervals = []
    if is_rr_interval_present:
        while len(data) >= next_byte_index + 2:
            # RR間隔は 1/1024 秒単位のUINT16
            rr_interval_raw = int.from_bytes(data[next_byte_index:next_byte_index+2], byteorder='little')
            # ミリ秒に変換
            rr_interval_ms = (rr_interval_raw / 1024.0) * 1000.0
            rr_intervals.append(rr_interval_ms)
            next_byte_index += 2
            
    return bpm, rr_intervals


def notification_handler(sender: int, data: bytearray, csv_writer):
    """
    デバイスから通知があった際に呼び出されるコールバック関数。
    """
    bpm, rr_intervals = parse_heart_rate_data(sender, data)
    timestamp = datetime.now()
    
    # FR-O-01: コンソール出力
    print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Heart Rate: {bpm} BPM")

    # FR-O-02: CSVファイルへの出力
    if not rr_intervals:
        # RR間隔がない場合はBPMのみ記録
        csv_writer.writerow([timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'), bpm, ""])
    else:
        # 複数のRR間隔がある場合、それぞれを新しい行として記録
        for rr in rr_intervals:
            print(f"  - RR Interval: {rr:.1f} ms")
            csv_writer.writerow([timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'), bpm, f"{rr:.4f}"])


async def show_reconnecting_message():
    """再接続中にメッセージを定期的に表示するタスク"""
    while True:
        print("再接続試行中...")
        await asyncio.sleep(5)


async def main():
    print("--- H808S Heart Rate Logger ---")
    
    # FR-S-01: デバイスのスキャン
    print("周辺のBLEデバイスをスキャンしています...(5秒間)")
    try:
        # return_adv=True にすることで、アドバタイズメントデータを取得
        devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
    except BleakError:
        # NR-EH-01: Bluetoothアダプタが無効
        print("\nエラー: Bluetoothアダプタを認識できません。PCのBluetoothが「オン」になっているか確認してください。")
        sys.exit(1)
        
    discoverd_devices = list(devices.values()) # デバイスのリストを取得
    
    if not discoverd_devices:
        # NR-EH-02: デバイス未検出
        print("\nエラー: 心拍計が見つかりませんでした。以下の3点を確認してください:")
        print("✅ センサーの電源は入っていますか？")
        print("✅ センサーはPCの近くにありますか？")
        print("✅ スマートフォン等、他の機器に接続されていませんか？")
        sys.exit(1)

    # FR-S-02: 対話的なデバイス選択 (詳細情報表示)
    print("\n--- 見つかったデバイス一覧 ---")
    for i, (device, adv_data) in enumerate(discoverd_devices):
        print(f"  [{i}]: {device.address}")
        # .name が None の場合は 'N/A' と表示
        print(f"    ├ Name: {device.name if device.name else 'N/A'}")
        # RSSI (電波強度) を表示。数値が0に近いほど近くにある
        print(f"    ├ RSSI: {adv_data.rssi} dBm")
        # アドバタイズしているサービスUUIDを表示
        service_uuids = adv_data.service_uuids
        print(f"    └ Services: {service_uuids}")
        
        # 心拍計サービス(180d)を持っているかチェックし、ユーザーにヒントを出す
        if any('0000180d' in s.lower() for s in service_uuids):
            print("      💓 [ヒント] このデバイスは心拍計の可能性が高いです！")
        print("-" * 30)

    while True:
        try:
            selection = int(input("\n接続するデバイスの番号を入力してください: "))
            if 0 <= selection < len(discoverd_devices):
                # ユーザーが選んだデバイス情報を取得
                selected_device, _ = discoverd_devices[selection]
                break
            else:
                print("無効な番号です。もう一度入力してください。")
        except ValueError:
            print("数値を入力してください。")
            
    # FR-O-02: CSVファイルの準備
    csv_filename = f"heart_rate_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        csv_writer = csv.writer(f)
        # ヘッダーを書き込み
        csv_writer.writerow(['timestamp', 'bpm', 'rr_interval_ms'])
        print(f"\nログファイル '{csv_filename}' を作成しました。")

        # NR-EH-04: 自動再接続ループ
        reconnecting_task = None
        
        # 切断を検知するためのコールバック
        def handle_disconnect(_: BleakClient):
            print(f"\n警告: {selected_device.name} との接続が切れました。")
            disconnected_event.set()

        while True:
            disconnected_event.clear()
            try:
                async with BleakClient(selected_device.address, disconnected_callback=handle_disconnect) as client:
                    if reconnecting_task:
                        reconnecting_task.cancel()
                        reconnecting_task = None
                    
                    # FR-S-03: 接続確立の通知
                    print(f"\n✅ '{client.address}' ({selected_device.name}) に接続しました。データ取得を開始します。")
                    print("プログラムを終了するには Ctrl+C を押してください。")
                    
                    # FR-D-03: 通知の購読
                    await client.start_notify(
                        HEART_RATE_MEASUREMENT_CHAR_UUID, 
                        lambda s, d: notification_handler(s, d, csv_writer)
                    )
                    
                    # 切断されるまで待機
                    await disconnected_event.wait()
                    
            except BleakError as e:
                # NR-EH-03: 接続失敗
                print(f"\n🔌 エラー: 心拍計への接続に失敗しました。 ({e})")
            except Exception as e:
                print(f"予期せぬエラーが発生しました: {e}")

            # NR-EH-04: 再接続処理
            if not reconnecting_task or reconnecting_task.done():
                 print("自動で再接続を試みます...")
                 reconnecting_task = asyncio.create_task(show_reconnecting_message())
            await asyncio.sleep(2) # 再接続試行までの待機時間


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # NR-P-01: プログラムの終了
        print("\n🛑 プログラムを終了します。デバイスとの接続は安全に解除されました。")
    except Exception as e:
        print(f"\n予期せぬエラーでプログラムが終了しました: {e}")
    finally:
        sys.exit(0)

