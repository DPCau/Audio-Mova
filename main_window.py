import sys, os, wave, logging, hashlib, math
from pathlib import Path
from pinyin import pinyin
from pydub import AudioSegment
from faster_whisper import WhisperModel

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QFileDialog, QProgressBar, QTreeWidget, QTreeWidgetItem,
    QSplitter, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QMenu, QSlider, QMessageBox
)
from PyQt5.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QKeySequence, QIcon)
from PyQt5.QtCore import (Qt, QRectF, QMimeData, QThread, pyqtSignal, QUrl, QTimer, QPointF)
from PyQt5.QtMultimedia import QMediaPlayer, QSoundEffect, QMediaContent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 自定义异常 ---
class ModelNotFoundError(Exception):
    """当模型文件在指定目录未找到时抛出此异常。"""
    pass

class AudioProcessor:
    def __init__(self, model_size: str = 'base', device: str = 'auto', compute_type: str = 'default'):
        if sys.platform == 'darwin':
            device = 'cpu'
            compute_type = 'int8'
            logger.info("macOS detected. Forcing device to 'cpu' for stability.")
        
        model_path = Path(resource_path("models"))
        model_path.mkdir(exist_ok=True)
        
        try:
            # 直接调用，如果模型不存在则会自动下载（在终端显示进度）
            self.model = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type, 
                download_root=str(model_path), 
                local_files_only=False, # 允许下载
            )
            logger.info(f"Loaded/Downloaded Whisper model: {model_size} on {device} from {model_path}")

        except Exception as e:
            logger.error(f"Fatal error loading model '{model_size}'. Error: {e}", exc_info=True)
            error_message = (
                f"加载或下载模型 '{model_size}' 时发生严重错误。\n\n"
                f"请检查您的网络连接和磁盘空间。\n\n错误详情: {e}"
            )
            raise ModelNotFoundError(error_message) from e
    
    def process_audio(self, input_path: str, output_dir: str = './temp', progress_callback=None):
        input_filename = Path(input_path).stem
        output_path = Path(output_dir) / input_filename
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Processing: {input_path}")
        
        segments, info = self.model.transcribe(input_path, word_timestamps=True, language='zh')
        logger.info(f"Transcribed: {info.language} ({info.language_probability:.2f})")
        
        audio = AudioSegment.from_file(input_path)
        processed_intervals = []
        words_to_process = []
        all_words = []
        [all_words.extend(s.words) for s in segments]
        
        sorted_words = sorted(all_words, key=lambda w: w.start)
        
        for word in sorted_words:
            start_ms, end_ms = int(word.start * 1000), int(word.end * 1000)
            if not any(p_start <= (start_ms + end_ms) / 2 <= p_end for p_start, p_end in processed_intervals) and word.word.strip():
                words_to_process.append(word)
                processed_intervals.append((start_ms, end_ms))
                
        logger.info(f"Found {len(words_to_process)} unique words. Slicing...")
        for i, word in enumerate(words_to_process):
            word_text = word.word.strip()
            start_ms, end_ms = int(word.start * 1000), int(word.end * 1000)
            hash_suffix = hashlib.md5(f"{word_text}_{start_ms}".encode()).hexdigest()[:6]
            output_filepath = output_path / f"{word_text}_{hash_suffix}.wav"
            audio[start_ms:end_ms].export(output_filepath, format='wav')
            if progress_callback:
                progress_callback(i + 1, len(words_to_process))
                
        logger.info(f"Finished processing. Generated {len(words_to_process)} clips.")
        return str(output_path)


class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(str)
    processing_error = pyqtSignal(str)

    def __init__(self, input_path, output_dir, model_size):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.model_size = model_size

    def run(self):
        try:
            input_filename = os.path.splitext(os.path.basename(self.input_path))[0]
            output_path = os.path.join(self.output_dir, input_filename)
            if os.path.exists(output_path) and any(f.endswith('.wav') for f in os.listdir(output_path)):
                self.processing_finished.emit(f"目录已存在，已加载: {output_path}")
                return
            
            # 这一步可能会因为下载而耗时
            processor = AudioProcessor(model_size=self.model_size)
            
            # 模型加载/下载完成后，发出提示
            self.processing_finished.emit("模型加载完成，开始处理音频...")
            
            def progress_callback(current, total):
                if total > 0:
                    self.progress_updated.emit(int((current / total) * 100))
            
            result_path = processor.process_audio(self.input_path, self.output_dir, progress_callback=progress_callback)
            self.processing_finished.emit(f"处理完成，结果保存在: {result_path}")
        
        except ModelNotFoundError as e:
            logger.error(f"模型文件加载/下载错误: {e}")
            self.processing_error.emit(str(e))
        except Exception as e:
            logger.error(f"处理错误: {e}", exc_info=True)
            self.processing_error.emit(f"处理错误: {str(e)}")

class MaterialLibrary(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setHeaderHidden(True); self.setDragEnabled(True)
    def mimeData(self, items):
        if not items: return None
        item = items[0]
        file_path = item.data(0, Qt.UserRole)
        if file_path:
            mime_data = QMimeData(); mime_data.setText(file_path); return mime_data
        return None

class AudioBlockItem(QGraphicsRectItem):
    def __init__(self, x, y, width, file_path, timeline_view, **kwargs):
        super().__init__(0, 0, width, 50, **kwargs)
        self.setPos(x, y)
        self.file_path = file_path
        self.timeline_view = timeline_view
        self.setBrush(QBrush(QColor(70, 130, 180)))
        self.setPen(QPen(Qt.black, 1))
        self.setFlags(self.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.drag_start_offset = QPointF(0, 0)
        self.drag_start_pos = QPointF(0, 0)
        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile(self.file_path))
        text = os.path.basename(file_path).split('_')[0]
        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setDefaultTextColor(Qt.white)
        font = QFont(); font.setPointSize(10)
        self.text_item.setFont(font)
        self.text_item.setPos(self.rect().topLeft() + QPointF(5, 5))

    def check_collision(self, target_rect):
        other_items = [item for item in self.scene().items()
                       if isinstance(item, AudioBlockItem) and item is not self]
        for item in other_items:
            if target_rect.intersects(item.sceneBoundingRect()):
                return True
        return False

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
            self.drag_start_offset = event.scenePos() - self.pos()
            self.drag_start_pos = self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        
        new_pos = event.scenePos() - self.drag_start_offset
        final_x = max(0, new_pos.x())
        max_y = self.timeline_view.TRACK_COUNT * self.timeline_view.TRACK_HEIGHT - self.rect().height()
        final_y = max(0, min(new_pos.y(), max_y))
        target_scene_rect = QRectF(QPointF(final_x, final_y), self.rect().size())

        if self.check_collision(target_scene_rect):
            self.setBrush(QBrush(QColor(255, 0, 0, 150)))
        else:
            self.setBrush(QBrush(QColor(70, 130, 180)))
            self.setPos(final_x, final_y)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mouseReleaseEvent(event)
        self.setCursor(Qt.OpenHandCursor)
        self.setBrush(QBrush(QColor(70, 130, 180)))
        current_pos = self.pos()
        current_scene_rect = QRectF(current_pos, self.rect().size())
        if self.check_collision(current_scene_rect):
            self.setPos(self.drag_start_pos)
            current_pos = self.drag_start_pos
        track_height = self.timeline_view.TRACK_HEIGHT
        track_index = int((current_pos.y() + self.rect().height() / 2) / track_height)
        clamped_track_index = max(0, min(track_index, self.timeline_view.TRACK_COUNT - 1))
        snapped_y = clamped_track_index * track_height + 5
        snapped_pos = QPointF(current_pos.x(), snapped_y)
        snapped_rect = QRectF(snapped_pos, self.rect().size())
        if self.check_collision(snapped_rect):
             final_pos = current_pos
        else:
             final_pos = snapped_pos
        self.setPos(final_pos)
        event.accept()
    
    def contextMenuEvent(self, event):
        menu = QMenu(); copy_action = menu.addAction("复制"); delete_action = menu.addAction("删除")
        action = menu.exec_(event.screenPos())
        if action == delete_action: self.scene().removeItem(self)
        elif action == copy_action:
            base_width = self.rect().width() / self.timeline_view.pixels_per_second * 100.0
            self.timeline_view.main_window.copied_block_data = {"file_path": self.file_path, "base_width": base_width}

    def mouseDoubleClickEvent(self, event):
        self.sound_effect.play()
        super().mouseDoubleClickEvent(event)

class RulerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedHeight(30)
        self.pixels_per_second = 100.0; self.scroll_offset = 0
    def set_view_properties(self, pps, offset):
        self.pixels_per_second = pps; self.scroll_offset = offset; self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(240, 240, 240)); painter.setPen(QColor(100, 100, 100))
        width = self.width(); pps = self.pixels_per_second; start_pixel = self.scroll_offset
        step = 1.0
        if pps < 30: step = 5.0
        elif pps < 15: step = 10.0
        elif pps > 200: step = 0.5
        elif pps > 400: step = 0.25
        current_sec_raw = start_pixel / pps; current_sec = int(current_sec_raw / step) * step
        while True:
            pixel_pos = current_sec * pps - start_pixel
            if pixel_pos > width: break
            if pixel_pos >= 0:
                mins, secs = divmod(current_sec, 60); time_str = f"{int(mins):02}:{int(secs):02}"
                painter.drawLine(int(pixel_pos), 15, int(pixel_pos), 30)
                painter.drawText(QPointF(pixel_pos + 4, 15), time_str)
            current_sec += step

class TimelineView(QGraphicsView):
    TRACK_COUNT = 5; TRACK_HEIGHT = 60
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window; self.pixels_per_second = 100.0
        self._is_dragging_playhead = False
        self.scene = QGraphicsScene(self); self.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 3600 * self.pixels_per_second, self.TRACK_COUNT * self.TRACK_HEIGHT)
        self.setRenderHint(QPainter.Antialiasing); self.setAcceptDrops(True)
        self.playhead = self.scene.addLine(0, 0, 0, self.TRACK_COUNT * self.TRACK_HEIGHT, QPen(Qt.red, 2)); self.playhead.setZValue(10)
        self.setDragMode(QGraphicsView.NoDrag)
    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.save()
        track_area_rect = QRectF(rect.left(), 0, rect.width(), self.TRACK_COUNT * self.TRACK_HEIGHT)
        painter.setClipRect(track_area_rect)
        for i in range(self.TRACK_COUNT):
            if i % 2 == 1: painter.fillRect(QRectF(rect.left(), i * self.TRACK_HEIGHT, rect.width(), self.TRACK_HEIGHT), QColor(245, 245, 245))
        for i in range(1, self.TRACK_COUNT + 1):
            y = i * self.TRACK_HEIGHT; painter.setPen(QPen(QColor(210, 210, 210), 1)); painter.drawLine(int(rect.left()), y, int(rect.right()), y)
        pps = self.pixels_per_second; left = int(rect.left()); right = int(rect.right())
        minor_pen = QPen(QColor(220, 220, 220), 0.5); painter.setPen(minor_pen)
        minor_step = max(1, int(pps / 4))
        for x in range(left - (left % minor_step), right, minor_step): painter.drawLine(x, 0, x, self.TRACK_COUNT * self.TRACK_HEIGHT)
        major_pen = QPen(QColor(180, 180, 180), 1); painter.setPen(major_pen)
        major_step = max(1, int(pps))
        for x in range(left - (left % major_step), right, major_step): painter.drawLine(x, 0, x, self.TRACK_COUNT * self.TRACK_HEIGHT)
        painter.restore()
    def set_playhead_position(self, x):
        x = max(0, x); self.playhead.setX(x); self.main_window.update_time_label(x / self.pixels_per_second)
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None and event.button() == Qt.LeftButton:
            self._is_dragging_playhead = True
            scene_pos = self.mapToScene(event.pos())
            self.set_playhead_position(scene_pos.x())
        else:
            super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self._is_dragging_playhead:
            scene_pos = self.mapToScene(event.pos())
            self.set_playhead_position(scene_pos.x())
        else:
            super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if self._is_dragging_playhead:
            self._is_dragging_playhead = False
        super().mouseReleaseEvent(event)
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            if self.main_window.copied_block_data:
                data = self.main_window.copied_block_data; width = data['base_width'] * (self.pixels_per_second / 100.0)
                view_pos_y = self.mapFromScene(self.playhead.pos()).y()
                track_index = int(view_pos_y // self.TRACK_HEIGHT)
                if not (0 <= track_index < self.TRACK_COUNT): track_index = 0
                clamped_track_index = max(0, min(track_index, self.TRACK_COUNT - 1))
                snapped_y = clamped_track_index * self.TRACK_HEIGHT + 5
                block = AudioBlockItem(self.playhead.x(), snapped_y, width, data['file_path'], self)
                self.scene.addItem(block)
        else:
            super().keyPressEvent(event)
    def dragEnterEvent(self, event):
        if event.mimeData().hasText(): event.acceptProposedAction()
    def dragMoveEvent(self, event):
        if event.mimeData().hasText(): event.acceptProposedAction()
    def dropEvent(self, event):
        if not event.mimeData().hasText():
            super().dropEvent(event)
            return
        scene_pos = self.mapToScene(event.pos())
        track_index = int(scene_pos.y() // self.TRACK_HEIGHT)
        if not (0 <= track_index < self.TRACK_COUNT): return
        file_path = event.mimeData().text()
        try:
            with wave.open(file_path, 'rb') as wf:
                duration = wf.getnframes() / float(wf.getframerate())
            width = duration * self.pixels_per_second
        except Exception:
            width = self.pixels_per_second
        intended_x = scene_pos.x() - (width / 2)
        final_x = max(0, intended_x)
        y_pos = track_index * self.TRACK_HEIGHT + 5
        block = AudioBlockItem(final_x, y_pos, width, file_path, self)
        self.scene.addItem(block)
        event.acceptProposedAction()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Mova 活字乱刷术")
        self.setGeometry(100, 100, 1400, 800)
        self.copied_block_data = None
        self.setup_ui()
        self.setup_player()
        if sys.platform == 'darwin':
            self.setWindowIcon(QIcon(resource_path('icons/icon.icns')))
        else:
            self.setWindowIcon(QIcon(resource_path('icons/icon.png')))
        self.processing_thread = None

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.create_menu_bar()
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("输入文件:"))
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setReadOnly(True)
        param_layout.addWidget(self.input_path_edit)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_input_file)
        param_layout.addWidget(browse_btn)
        param_layout.addWidget(QLabel("模型大小:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText("base")
        param_layout.addWidget(self.model_combo)
        param_layout.addWidget(QLabel("输出目录:"))
        self.output_dir_edit = QLineEdit("./temp")
        self.output_dir_edit.setReadOnly(True)
        param_layout.addWidget(self.output_dir_edit)
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        param_layout.addWidget(output_browse_btn)
        btn_layout = QHBoxLayout()
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.start_processing)
        btn_layout.addWidget(self.process_btn)
        self.refresh_btn = QPushButton("刷新素材库")
        self.refresh_btn.clicked.connect(self.refresh_material_library)
        btn_layout.addWidget(self.refresh_btn)
        param_layout.addLayout(btn_layout)
        main_layout.addLayout(param_layout)
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        self.material_library = MaterialLibrary(self)
        splitter.addWidget(self.material_library)
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(0)
        control_layout = self.create_playback_controls()
        timeline_layout.addLayout(control_layout)
        self.ruler = RulerWidget(self)
        timeline_layout.addWidget(self.ruler)
        self.timeline_view = TimelineView(self)
        timeline_layout.addWidget(self.timeline_view)
        splitter.addWidget(timeline_container)
        self.timeline_view.horizontalScrollBar().valueChanged.connect(self.on_timeline_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 1100])
        self.statusBar().showMessage("就绪")
        self.refresh_material_library()

    def on_timeline_scroll(self):
        offset = self.timeline_view.horizontalScrollBar().value()
        pps = self.timeline_view.pixels_per_second
        self.ruler.set_view_properties(pps, offset)
        
    def create_playback_controls(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.clicked.connect(self.play_timeline)
        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(30, 30)
        self.stop_btn.clicked.connect(self.stop_timeline)
        self.time_label = QLabel("00:00.000")
        layout.addWidget(self.play_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.time_label)
        layout.addStretch()
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(30, 30)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(0, 100)
        self.zoom_slider.setValue(50)
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(30, 30)
        zoom_layout.addWidget(QLabel("缩放:"))
        zoom_layout.addWidget(zoom_out_btn)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(zoom_in_btn)
        zoom_out_btn.clicked.connect(lambda: self.zoom_slider.setValue(self.zoom_slider.value() - 10))
        zoom_in_btn.clicked.connect(lambda: self.zoom_slider.setValue(self.zoom_slider.value() + 10))
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        layout.addLayout(zoom_layout)
        return layout

    def on_zoom_changed(self, value):
        min_pps = 20
        max_pps = 800
        log_min = math.log(min_pps)
        log_max = math.log(max_pps)
        new_pps = math.exp(log_min + (log_max - log_min) * value / 100.0)
        current_pps = self.timeline_view.pixels_per_second
        if current_pps > 0:
             factor = new_pps / current_pps
             self.zoom(factor)

    def zoom(self, factor):
        view = self.timeline_view
        view_center_scene_pos = view.mapToScene(view.viewport().rect().center())
        old_pps = self.timeline_view.pixels_per_second
        new_pps = old_pps * factor
        self.timeline_view.pixels_per_second = new_pps
        for item in view.scene().items():
            if isinstance(item, AudioBlockItem):
                old_x = item.x()
                new_x = old_x * factor
                try:
                    with wave.open(item.file_path, 'rb') as wf:
                        duration = wf.getnframes() / float(wf.getframerate())
                    new_width = duration * new_pps
                    item.setRect(0, 0, new_width, item.rect().height())
                    item.setX(new_x)
                except Exception as e:
                    logger.warning(f"Could not update width/pos for {item.file_path}: {e}")
        self.playhead.setX(self.playhead.x() * factor)
        old_scene_rect = view.sceneRect()
        view.setSceneRect(0, old_scene_rect.y(), old_scene_rect.width() * factor, old_scene_rect.height())
        QTimer.singleShot(0, lambda: self.center_on(view_center_scene_pos))
        self.on_timeline_scroll()
    
    def center_on(self, scene_pos):
        self.timeline_view.centerOn(scene_pos)
        self.on_timeline_scroll()

    def synthesize_audio(self):
        all_blocks = [item for item in self.timeline_view.scene.items() if isinstance(item, AudioBlockItem)]
        if not all_blocks: return "时间轴为空", False
        try:
            max_x = max(item.x() + item.rect().width() for item in all_blocks) if all_blocks else 0
            total_duration_ms = int((max_x / self.timeline_view.pixels_per_second) * 1000) + 100
            output_audio = AudioSegment.silent(duration=total_duration_ms)
            for item in all_blocks:
                block_audio = AudioSegment.from_file(item.file_path, format="wav")
                start_pos_ms = int((item.x() / self.timeline_view.pixels_per_second) * 1000)
                output_audio = output_audio.overlay(block_audio, position=start_pos_ms)
            return output_audio, True
        except Exception as e:
            logger.error(f"合成音频时出错: {e}", exc_info=True)
            return f"合成失败: {str(e)}", False
            
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        import_action = file_menu.addAction("导入文件...")
        import_action.triggered.connect(self.browse_input_file)
        export_action = file_menu.addAction("导出音频...")
        export_action.triggered.connect(self.export_timeline)
        help_menu = menu_bar.addMenu("帮助")
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about_dialog) 
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)

    def export_timeline(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "导出音频", "", "MP3文件 (*.mp3);;WAV文件 (*.wav)")
        if not save_path: return
        self.statusBar().showMessage("正在导出音频...")
        QApplication.instance().processEvents()
        output_audio, status = self.synthesize_audio()
        if not status:
            self.statusBar().showMessage(f"导出失败: {output_audio}")
            return
        try:
            file_format = "mp3" if save_path.endswith(".mp3") else "wav"
            output_audio.export(save_path, format=file_format)
            self.statusBar().showMessage(f"导出成功: {save_path}")
        except Exception as e:
            self.statusBar().showMessage(f"导出错误: {e}")
            logger.error(f"导出错误: {e}", exc_info=True)

    def play_timeline(self):
        self.statusBar().showMessage("正在合成音频...")
        QApplication.instance().processEvents()
        output_audio, status = self.synthesize_audio()
        if not status:
            self.statusBar().showMessage(f"播放失败: {output_audio}")
            return
        temp_dir = Path("./temp")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / "_temp_playback.wav"
        try:
            output_audio.export(str(temp_file), format="wav")
        except Exception as e:
             self.statusBar().showMessage(f"创建播放文件失败: {e}")
             return
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(str(temp_file))))
        playhead_x = self.timeline_view.playhead.x()
        start_ms = int(playhead_x / self.timeline_view.pixels_per_second * 1000)
        self.media_player.setPosition(start_ms)
        self.media_player.play()
        self.playback_timer.start()
        self.statusBar().showMessage("播放中...")

    def setup_player(self):
        self.media_player = QMediaPlayer()
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(30)
        self.playback_timer.timeout.connect(self.update_playhead_on_playback)

    def stop_timeline(self):
        self.media_player.stop()
        self.playback_timer.stop()
        self.statusBar().showMessage("已停止")

    def update_playhead_on_playback(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            pos_x = (self.media_player.position() / 1000.0) * self.timeline_view.pixels_per_second
            self.timeline_view.set_playhead_position(pos_x)
        elif self.media_player.state() == QMediaPlayer.StoppedState and self.playback_timer.isActive():
            self.playback_timer.stop()
            if self.media_player.position() > 0 and self.media_player.position() >= self.media_player.duration() - 50:
                 self.statusBar().showMessage("播放完成")
                 end_pos_x = (self.media_player.duration() / 1000.0) * self.timeline_view.pixels_per_second
                 self.timeline_view.set_playhead_position(end_pos_x)

    def update_time_label(self, seconds):
        mins, secs = divmod(seconds, 60)
        msecs = (seconds - int(seconds)) * 1000
        self.time_label.setText(f"{int(mins):02d}:{int(secs):02d}.{int(msecs):03d}")

    def refresh_material_library(self):
        self.material_library.clear()
        base_dir = self.output_dir_edit.text()
        if not os.path.isdir(base_dir): return
        for project_name in sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]):
            project_item = QTreeWidgetItem(self.material_library, [project_name])
            project_path = os.path.join(base_dir, project_name)
            categorized = {}
            for filename in os.listdir(project_path):
                if filename.lower().endswith(".wav"):
                    word = filename.split('_')[0]
                    first_char = pinyin.get_initial(word[0], '').upper() if word else '#'
                    if not first_char.isalpha(): first_char = '#'
                    if first_char not in categorized: categorized[first_char] = []
                    categorized[first_char].append(filename)
            for letter in sorted(categorized.keys()):
                letter_item = QTreeWidgetItem(project_item, [letter])
                for filename in sorted(categorized[letter]):
                    file_item = QTreeWidgetItem(letter_item, [filename.split('_')[0]])
                    file_item.setData(0, Qt.UserRole, os.path.join(project_path, filename))
                    file_item.setToolTip(0, filename)
            project_item.setExpanded(True)
        self.statusBar().showMessage("素材库已刷新")

    def browse_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择音频/视频文件", "", "音视频文件 (*.mp3 *.wav *.m4a *.flac *.mp4 *.mov *.mkv *.avi)")
        if file_path:
            self.input_path_edit.setText(file_path)

    def browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", "./temp")
        if path:
            self.output_dir_edit.setText(path)

    def start_processing(self):
        input_path = self.input_path_edit.text()
        output_dir = self.output_dir_edit.text()
        model_size = self.model_combo.currentText()
        if not input_path or not os.path.exists(input_path):
            self.statusBar().showMessage("错误：请选择一个有效的输入文件。")
            return
        
        self.process_btn.setEnabled(False)
        self.statusBar().showMessage("正在准备处理，可能需要下载模型...")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

        self.processing_thread = ProcessingThread(
            input_path, 
            output_dir, 
            model_size
        )

        self.processing_thread.progress_updated.connect(self.progress_bar.setValue)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        self.processing_thread.processing_error.connect(self.show_error_message)
        self.processing_thread.finished.connect(lambda: self.process_btn.setEnabled(True))
        
        self.processing_thread.start()

    def processing_complete(self, message):
        self.statusBar().showMessage(message)
        if "处理完成" in message or "目录已存在" in message:
            self.progress_bar.setValue(100)
            self.refresh_material_library()
        else:
            self.progress_bar.setValue(0)


    def show_error_message(self, message):
        self.statusBar().showMessage("发生错误，请查看详情。")
        self.progress_bar.setValue(0)
        
        QMessageBox.critical(self, "错误", message)

    def show_about_dialog(self):
        """
        显示“关于”对话框。
        """
        about_text = """
            <h3>活字乱刷术 Audio Mova v1.0</h3>
            <p>
                一款借鉴“活字印刷术”思想的音频二次创作工具。<br>
                它可以智能切分语音，像排版一样组合声音。
            </p>
            <p>
                <a href='https://github.com/DPCau/Audio-Mova'>访问github项目主页</a>
                <a href='https://github.com/DPCau/Audio-Mova/releases'>访问项目发布页</a>
            </p>
        """
        QMessageBox.about(self, "关于 活字拼声", about_text)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())