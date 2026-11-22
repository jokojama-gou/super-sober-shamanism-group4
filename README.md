# super-sober-shamanism-group4

複数の BLE 心拍センサー（Coospo 等）から取得した心拍数（BPM）・RR 間隔データを UDP / OSC で集約し、カメラ映像とリアルタイムグラフを統合表示するマルチモーダル・ビジュアライゼーションシステムです。

## システム構成

- **`coospo-connector.py`**: `bleak` を用いて BLE Heart Rate Service (`0x180D` / Characteristic `0x2A37`) に接続し、BPM（UINT8/UINT16）および RR 間隔（1/1024秒単位）をパースして記録・配信
- **`udp-forwarder.py` / `udp-listenner.py` / `udp-listnnerfrom-forwarder.py`**: 各センサー接続端末からメイン端末へ心拍ストリームを UDP 転送・集約
- **`main.py`**: `PyQt5` GUI 上に `OpenCV` カメラ映像スレッド、`Matplotlib` リアルタイム波形キャンバス、`python-osc` サーバーを統合表示

## 技術スタック

- Python 3
- `bleak` (Bluetooth Low Energy GATT クライアント)
- `PyQt5` + `matplotlib` + `opencv-python` (リアルタイム GUI・映像・グラフ描画)
- `python-osc` / UDP Sockets (デバイス間リアルタイム通信)

## セットアップ

```bash
pipenv install
pipenv run python main.py
```

---

## Author

横山 豪 (Go Yokoyama) / 慶應義塾大学 SFC / [@jokojama-gou](https://github.com/jokojama-gou)
