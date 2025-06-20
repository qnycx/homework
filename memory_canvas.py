# memory_canvas.py

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsSimpleTextItem
from PyQt5.QtGui import QColor, QBrush, QFont, QPen

class MemoryCanvas(QGraphicsView):
    def __init__(self, total_size=400, parent=None):
        super().__init__(parent)
        self.total_size = total_size

        # 3. 移除固定尺寸，设置最小尺寸和尺寸策略
        self.setMinimumSize(400, 80)  # 设置最小尺寸
        self.setMaximumHeight(120)  # 限制最大高度，保持比例

        # 4. 设置尺寸策略，让组件可以随窗口缩放
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setScene(QGraphicsScene(self))
        self.draw_background()

    def draw_background(self):
        """绘制背景和图例 - 自适应版本"""
        self.scene().clear()

        # 5. 获取当前视图的实际宽度
        view_width = self.viewport().width() - 10  # 留出边距
        if view_width <= 0:
            view_width = 400  # 默认宽度

        # 背景条 - 使用动态宽度
        bg = QGraphicsRectItem(0, 0, view_width, 40)
        bg.setBrush(QBrush(QColor(220, 220, 220)))
        self.scene().addItem(bg)

        # 图例文字
        legend = QGraphicsSimpleTextItem("🟩 空闲区  🟥 已用区")
        legend.setPos(5, 45)
        legend.setBrush(QColor(0, 0, 0))
        legend.setFont(QFont("Arial", 9))
        self.scene().addItem(legend)

        # 6. 更新场景矩形
        self.setSceneRect(0, 0, view_width, 70)

    def update_blocks(self, memory_blocks):
        """绘制每个内存块 - 自适应版本"""
        self.draw_background()

        # 7. 获取当前可用宽度
        view_width = self.viewport().width() - 10
        if view_width <= 0:
            view_width = 400

        for block in memory_blocks:
            # 根据当前视图宽度计算位置和大小
            x = block['start'] / self.total_size * view_width
            w = block['size'] / self.total_size * view_width

            # 动态颜色逻辑保持不变
            if block.get('flash', False):
                color = QColor(255, 255, 100)
            elif block['type'] == 'free':
                color = QColor(0, 200, 0)
            else:
                color = QColor(200, 0, 0)

            rect = QGraphicsRectItem(x, 0, w, 40)
            rect.setBrush(QBrush(color))

            # 添加黑色边框
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(1)
            rect.setPen(pen)

            # 鼠标悬浮提示
            tooltip = f"起始地址: {block['start']}MB\n大小: {block['size']}MB"
            if block['type'] == 'used' and 'job_id' in block:
                tooltip += f"\n作业ID: {block['job_id']}"
            rect.setToolTip(tooltip)
            self.scene().addItem(rect)

            # 8. 智能标签显示 - 根据宽度决定是否显示标签
            min_width_for_label = 25  # 最小宽度才显示标签
            if w >= min_width_for_label:
                # 大小标签
                label = QGraphicsSimpleTextItem(f"{block['size']}MB")
                font_size = max(6, min(8, int(w / 8)))  # 根据宽度调整字体大小
                label.setFont(QFont("Arial", font_size))
                label.setBrush(QColor(255, 255, 255))
                label.setPos(x + w / 2 - label.boundingRect().width() / 2, 10)
                self.scene().addItem(label)

                # 作业ID标签
                if block['type'] == 'used' and 'job_id' in block:
                    job_label = QGraphicsSimpleTextItem(str(block['job_id']))
                    job_label.setFont(QFont("Arial", font_size - 1))
                    job_label.setBrush(QColor(255, 255, 255))
                    job_label.setPos(x + w / 2 - job_label.boundingRect().width() / 2, 24)
                    self.scene().addItem(job_label)

    def resizeEvent(self, event):
        """9. 窗口大小改变时重新绘制"""
        super().resizeEvent(event)
        # 延迟更新，避免频繁重绘
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        else:
            from PyQt5.QtCore import QTimer
            self._resize_timer = QTimer()
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._delayed_update)
        self._resize_timer.start(100)  # 100ms后更新

    def _delayed_update(self):
        """延迟更新画布"""
        if hasattr(self, 'parent') and hasattr(self.parent(), 'manager'):
            # 重新绘制当前的内存状态
            self.draw_background()