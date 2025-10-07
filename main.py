import sys
import json
import time
import cv2
import numpy as np
from rich import print



from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QGridLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# FR4: Matplotlib CanvasをPyQtウィジェットに組み込む
class MplCanvas(FigureCanvas):
    """MatplotlibのグラフをPyQtウィジェットとして扱うためのカスタムクラス"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.setStyleSheet("background-color: #000000;")

class VideoThread(QThread):
    """
    OpenCVによるカメラ映像取得を担うスレッド (FR6, 非機能要件: マルチスレッド戦略)
    """
    # メインスレッドにフレームデータを送信するシグナル
    change_pixmap_signal = pyqtSignal(np.ndarray)
    # カメラ接続エラーを通知するシグナル
    no_input_signal = pyqtSignal()

    def __init__(self, camera_id, fps_limit):
        super().__init__()
        self._run_flag = True
        self.camera_id = camera_id
        self.wait_time = 1.0 / fps_limit

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            # FR6, 非機能要件: カメラ接続エラー時の代替メッセージ
            self.no_input_signal.emit()
            return

        while self._run_flag:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)
            else:
                # FR6, 非機能要件: 実行中のカメラ切断
                self.no_input_signal.emit()
                break
            time.sleep(self.wait_time) # FPS制限
        cap.release()

    def stop(self):
        """スレッドを安全に停止させる"""
        self._run_flag = False
        self.wait()

class DataThread(QThread):
    """
    グラフ用データのランダム生成を担うスレッド (FR5, 非機能要件: マルチスレッド戦略)
    """
    # メインスレッドに新しいデータセットを送信するシグナル
    new_data_signal = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)

    def __init__(self, update_interval_ms, data_points):
        super().__init__()
        self._run_flag = True
        self.update_interval_sec = update_interval_ms / 1000.0
        self.data_points = data_points
        # 3種類のデータを保持する配列を初期化
        self.data_a = np.zeros(self.data_points)
        self.data_b = np.zeros(self.data_points)
        self.data_c = np.zeros(self.data_points)

    def run(self):
        while self._run_flag:
            # データを1つ左にスクロール
            self.data_a = np.roll(self.data_a, -1)
            self.data_b = np.roll(self.data_b, -1)
            self.data_c = np.roll(self.data_c, -1)

            # 最新のデータ点に乱数を設定
            self.data_a[-1] = np.random.rand()
            self.data_b[-1] = np.random.rand() * 0.8 + 0.1 # 値の範囲を少し変える
            self.data_c[-1] = np.random.rand() * 0.6 + 0.2

            self.new_data_signal.emit(self.data_a, self.data_b, self.data_c)
            time.sleep(self.update_interval_sec)

    def stop(self):
        """スレッドを安全に停止させる"""
        self._run_flag = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config

        self.setWindowTitle("AI Sports Viewer")
        window_size = self.config['window_size']
        self.setGeometry(100, 100, window_size[0], window_size[1]) # FR1: 16:9アスペクト比

        # メインウィジェットとレイアウト
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # FR1: 画面全体を4分割
        self.grid_layout = QGridLayout(central_widget)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
         # init_uiの前に画像データを読み込んでおく
        self.pixmap_a = QPixmap(self.config['image_a_path'])
        self.pixmap_b = QPixmap(self.config['image_b_path'])
        self.init_ui()
        self.init_threads()

    def init_ui(self):
        """各象限のUIウィジェットを初期化・配置"""
        # --- 象限I: 静的画像A (FR2) ---
        self.image_a_label = QLabel(self)
        self.image_a_label.setAlignment(Qt.AlignCenter)
        pixmap_a = QPixmap(self.config['image_a_path'])
        if pixmap_a.isNull():
            self.image_a_label.setText("Image A not found")
        else:
            self.image_a_label.setPixmap(pixmap_a.scaled(
                self.width() // 2, self.height() // 2, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.grid_layout.addWidget(self.image_a_label, 0, 0)

        # --- 象限II: 静的画像B (FR3) ---
        self.image_b_label = QLabel(self)
        self.image_b_label.setAlignment(Qt.AlignCenter)
        pixmap_b = QPixmap(self.config['image_b_path'])
        if pixmap_b.isNull():
            self.image_b_label.setText("Image B not found")
        else:
            self.image_b_label.setPixmap(pixmap_b.scaled(
                self.width() // 2, self.height() // 2, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.grid_layout.addWidget(self.image_b_label, 0, 1)

        # --- 象限III: 線グラフ (FR4) ---
        self.graph_canvas = MplCanvas(self)
        self.grid_layout.addWidget(self.graph_canvas, 1, 0)
        # 3本の線を初期プロット
        self.plot_ref_a = None
        self.plot_ref_b = None
        self.plot_ref_c = None

        # --- 象限IV: ライブ映像 (FR6) ---
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Connecting to camera...")
        self.video_label.setStyleSheet("background-color: #000; color: #FFF;")
        self.grid_layout.addWidget(self.video_label, 1, 1)

    def init_threads(self):
        """映像取得とデータ生成のスレッドを開始 (FR7, 非機能要件: マルチスレッド)"""
        # 映像スレッド
        self.video_thread = VideoThread(
            camera_id=self.config['camera_id'],
            fps_limit=self.config['video_fps_limit']
        )
        self.video_thread.change_pixmap_signal.connect(self.update_video_frame)
        self.video_thread.no_input_signal.connect(self.show_no_input_message)
        self.video_thread.start()

        # データスレッド
        self.data_thread = DataThread(
            update_interval_ms=self.config['graph_update_interval_ms'],
            data_points=self.config['graph_data_points']
        )
        self.data_thread.new_data_signal.connect(self.update_plot)
        self.data_thread.start()

    @pyqtSlot(np.ndarray)
    def update_video_frame(self, cv_img):
        """映像スレッドからフレームを受け取り、QLabelに表示するスロット"""
        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img.scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio))

    @pyqtSlot()
    def show_no_input_message(self):
        """カメラ入力がない場合にメッセージを表示するスロット"""
        self.video_label.setText("No Input")

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def update_plot(self, data_a, data_b, data_c):
        """データスレッドからデータを受け取り、グラフを更新するスロット"""
        # 初回描画時
        if self.plot_ref_a is None:
            self.graph_canvas.axes.cla() # 以前の描画をクリア
            self.plot_ref_a, = self.graph_canvas.axes.plot(data_a, label='Data A', color='r')
            self.plot_ref_b, = self.graph_canvas.axes.plot(data_b, label='Data B', color='g')
            self.plot_ref_c, = self.graph_canvas.axes.plot(data_c, label='Data C', color='b')
            self.graph_canvas.axes.set_ylim(0, 1.2) # Y軸のスケールを固定
            self.graph_canvas.axes.legend()
            self.graph_canvas.axes.set_facecolor('#111')
            self.graph_canvas.fig.patch.set_facecolor('#111')
            self.graph_canvas.axes.tick_params(axis='x', colors='white')
            self.graph_canvas.axes.tick_params(axis='y', colors='white')
        else: # 2回目以降はデータを更新して高速化 (非機能要件: パフォーマンス)
            self.plot_ref_a.set_ydata(data_a)
            self.plot_ref_b.set_ydata(data_b)
            self.plot_ref_c.set_ydata(data_c)
        
        self.graph_canvas.draw()

    def convert_cv_qt(self, cv_img):
        """OpenCVの画像をPyQtのQPixmapに変換"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format)

    def closeEvent(self, event):
        """ウィンドウが閉じられるときにスレッドを停止する"""
        self.video_thread.stop()
        self.data_thread.stop()
        event.accept()
        
    def resizeEvent(self, event):
        """ウィンドウサイズ変更時に画像のスケールを調整 (FR1)"""
        super().resizeEvent(event)
        # 静的画像のスケールを再計算
        if not QPixmap(self.config['image_a_path']).isNull():
            self.image_a_label.setPixmap(QPixmap(self.config['image_a_path']).scaled(
                self.image_a_label.width(), self.image_a_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if not QPixmap(self.config['image_b_path']).isNull():
            self.image_b_label.setPixmap(QPixmap(self.config['image_b_path']).scaled(
                self.image_b_label.width(), self.image_b_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


if __name__ == '__main__':
    # FR8: アプリケーション起動時に config.json ファイルを読み込む
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("エラー: config.json が見つかりません。") # 非機能要件: ロギング
        sys.exit(1)
    except json.JSONDecodeError:
        print("エラー: config.json の形式が正しくありません。") # 非機能要件: ロギング
        sys.exit(1)

    app = QApplication(sys.argv)
    main_window = MainWindow(config)
    main_window.show()
    sys.exit(app.exec_())