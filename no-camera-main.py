import sys
import json
import time
import cv2
import numpy as np
from rich import print

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QGridLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QPixmap, QImage

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server

# ==============================================================================
# FR1: アプリケーションの統合 - Matplotlib, OSCのクラスを1つのファイルに集約
# ==============================================================================

class MplCanvas(FigureCanvas):
    """MatplotlibのグラフをPyQtウィジェットとして扱うためのカスタムクラス"""
    def __init__(self, parent=None):
        self.fig = Figure(facecolor='#111')
        self.axes = self.fig.add_subplot(111, facecolor='#111')
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.setStyleSheet("background-color: #111;")

# NFR1: 並行処理 - OSC受信をノンブロッキングで行うためのスレッド
class OSCListenerThread(QThread):
    """指定されたIPとポートでOSCデータを待ち受けるスレッド"""
    new_bpm_signal = pyqtSignal(int, float)

    def __init__(self, listener_config, listener_index):
        super().__init__()
        self.config = listener_config
        self.index = listener_index
        self.server = None
        self.last_bpm = 0.0

    def run(self):
        dispatcher = Dispatcher()
        dispatcher.map("/avatar/parameters/HeartRateBPM", self.bpm_handler)

        ip = self.config['ip']
        port = self.config['port']
        self.server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
        
        print(f"✅ [bold]OSCリスナー '{self.config['name']}' 起動[/bold] | "
              f"📫️ IP: [yellow]{ip}[/yellow], Port: [yellow]{port}[/yellow] で待機中...")
        
        self.server.serve_forever()

    def bpm_handler(self, address, *args):
        """BPMデータ受信時の処理 (0を受信した場合は最後の有効値を採用)"""
        current_bpm = args[0] if args else 0.0

        # 有効なBPM(>0)を受信した場合のみ、最後の値を更新する
        if current_bpm > 0.0:
            self.last_bpm = current_bpm

        # 最後の有効な値が0より大きい場合のみ、それを使って処理を行う
        if self.last_bpm > 0.0:
            print(f"🫀  [bold magenta]処理中 ({self.config['name']}):[/bold magenta] [cyan]{self.last_bpm:.2f}[/cyan] BPM❤️")
            self.new_bpm_signal.emit(self.index, float(self.last_bpm))

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config

        self.original_pixmap_a = QPixmap(self.config['image_a_path'])
        self.original_pixmap_b = QPixmap(self.config['image_b_path'])

        self.setWindowTitle("AI Sports Viewer")
        ws = self.config['window_size']
        self.setGeometry(100, 100, ws[0], ws[1])

        self.osc_threads = []
        self.graph_data_arrays = []
        self.plot_refs = []

        self.init_ui()
        self.init_graph_data()
        self.init_threads_and_timer()

    def init_ui(self):
        """UIウィジェットを初期化・配置"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        grid_layout = QGridLayout(central_widget)
        grid_layout.setSpacing(2)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # 象限I: 静的画像A
        self.image_a_label = self.create_image_label(self.original_pixmap_a, self.config['image_a_path'])
        grid_layout.addWidget(self.image_a_label, 0, 0)

        # 象限II: 静的画像B
        self.image_b_label = self.create_image_label(self.original_pixmap_b, self.config['image_b_path'])
        grid_layout.addWidget(self.image_b_label, 0, 1)

        # 下段: 線グラフ (2カラムにまたがる)
        self.graph_canvas = MplCanvas(self)
        # グラフを(行:1, 列:0)の位置に、1行分、2列分の大きさで配置
        grid_layout.addWidget(self.graph_canvas, 1, 0, 1, 2)

    def init_graph_data(self):
        """グラフ用のデータ配列とプロットを初期化"""
        data_points = self.config['graph_data_points']
        listeners = self.config['osc_listeners']

        self.graph_canvas.axes.set_ylim(0, 1.2)
        self.graph_canvas.axes.tick_params(axis='x', colors='white')
        self.graph_canvas.axes.tick_params(axis='y', colors='white')

        for i, listener in enumerate(listeners):
            self.graph_data_arrays.append(np.zeros(data_points))
            plot, = self.graph_canvas.axes.plot(
                self.graph_data_arrays[i],
                label=listener['name'],
                color=listener.get('color', 'white')
            )
            self.plot_refs.append(plot)

        self.graph_canvas.axes.legend(labelcolor='white', facecolor='#333')
        self.graph_canvas.fig.tight_layout()

    def init_threads_and_timer(self):
        """OSCリスナーのスレッドとグラフ更新タイマーを開始"""
        for i, listener_conf in enumerate(self.config['osc_listeners']):
            thread = OSCListenerThread(listener_conf, i)
            thread.new_bpm_signal.connect(self.update_bpm_data)
            self.osc_threads.append(thread)
            thread.start()
        
        self.graph_timer = QTimer()
        self.graph_timer.setInterval(self.config['graph_update_interval_ms'])
        self.graph_timer.timeout.connect(self.update_plot)
        self.graph_timer.start()

    @pyqtSlot(int, float)
    def update_bpm_data(self, listener_index, bpm):
        """OSCスレッドからBPMデータを受け取り、対応するデータ配列を更新"""
        normalized_bpm = bpm / self.config.get('graph_max_bpm', 150)
        
        self.graph_data_arrays[listener_index] = np.roll(self.graph_data_arrays[listener_index], -1)
        self.graph_data_arrays[listener_index][-1] = normalized_bpm

    @pyqtSlot()
    def update_plot(self):
        """タイマーに従ってグラフを再描画"""
        for i, plot_ref in enumerate(self.plot_refs):
            plot_ref.set_ydata(self.graph_data_arrays[i])
        self.graph_canvas.draw()

    def create_image_label(self, pixmap, error_path):
        """PixmapからQLabelを作成するヘルパー関数"""
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        if pixmap.isNull():
            label.setText(f"Image not found:\n{error_path}")
            label.setStyleSheet("color: #AAA;")
        return label
    
    def update_static_images(self):
        """静止画像を現在のラベルサイズに合わせて更新する"""
        if hasattr(self, 'image_a_label') and not self.original_pixmap_a.isNull():
            scaled_pixmap = self.original_pixmap_a.scaled(
                self.image_a_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_a_label.setPixmap(scaled_pixmap)

        if hasattr(self, 'image_b_label') and not self.original_pixmap_b.isNull():
            scaled_pixmap = self.original_pixmap_b.scaled(
                self.image_b_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_b_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """ウィンドウがリサイズされたときに呼ばれる"""
        super().resizeEvent(event)
        self.update_static_images()

    def showEvent(self, event):
        """ウィンドウが初めて表示されるときに呼ばれる"""
        super().showEvent(event)
        QTimer.singleShot(0, self.update_static_images)

    def closeEvent(self, event):
        """ウィンドウが閉じられるときに全てのスレッドを安全に停止"""
        print("\n[bold]アプリケーションを終了します...[/bold]")
        for thread in self.osc_threads:
            thread.stop()
        self.graph_timer.stop()
        print("✅ [green]すべてのスレッドが停止しました。[/green]")
        event.accept()

if __name__ == '__main__':
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("[bold red]エラー: config.json が見つかりません。[/bold red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[bold red]エラー: config.json の形式が正しくありません。: {e}[/bold red]")
        sys.exit(1)

    app = QApplication(sys.argv)
    main_window = MainWindow(config)
    main_window.show()
    sys.exit(app.exec_())