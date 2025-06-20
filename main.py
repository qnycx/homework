# main.py
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QHBoxLayout, QCheckBox, QGroupBox, QSlider
)
from PyQt5.QtCore import QTimer, Qt
from memory_canvas import MemoryCanvas
from memory_model import MemoryManager
from job import Job
import sys
import json
import copy


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("内存分配模拟系统 - 带功能开关")

        # 1. 移除固定尺寸，改为设置最小尺寸和初始尺寸
        # self.setFixedSize(820, 680)  # 删除这一行
        self.setMinimumSize(600, 500)  # 设置最小尺寸
        self.resize(820, 680)  # 设置初始尺寸，但允许调整

        # 2. 创建可缩放的内存画布
        self.canvas = MemoryCanvas()

        self.strategy_select = QComboBox()
        # 删除了 'quick_fit', 'buddy', 'hash_fit'
        self.strategy_select.addItems(['first_fit', 'next_fit', 'best_fit', 'worst_fit'])

        # 新增：功能开关控件
        self.enable_merge_checkbox = QCheckBox("启用内存合并")
        self.enable_merge_checkbox.setChecked(True)  # 默认启用
        self.enable_merge_checkbox.stateChanged.connect(self.on_merge_checkbox_changed)

        self.enable_compact_checkbox = QCheckBox("启用内存紧凑")
        self.enable_compact_checkbox.setChecked(True)  # 默认启用
        self.enable_compact_checkbox.stateChanged.connect(self.on_compact_checkbox_changed)

        # 创建功能开关分组框
        switch_group = QGroupBox("功能开关")
        switch_layout = QHBoxLayout()
        switch_layout.addWidget(self.enable_merge_checkbox)
        switch_layout.addWidget(self.enable_compact_checkbox)
        switch_group.setLayout(switch_layout)

        # 新增：速度控制组件
        speed_group = QGroupBox("模拟速度")
        speed_layout = QHBoxLayout()

        # 速度滑块
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)  # 最慢：3秒一步
        self.speed_slider.setMaximum(10)  # 最快：0.1秒一步
        self.speed_slider.setValue(5)  # 默认：1秒一步
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)

        # 速度标签
        self.speed_label = QLabel("速度: 1.0x")
        self.speed_label.setMinimumWidth(80)

        # 预设速度按钮
        self.btn_slow = QPushButton("慢速")
        self.btn_normal = QPushButton("正常")
        self.btn_fast = QPushButton("快速")
        self.btn_ultra_fast = QPushButton("极速")

        self.btn_slow.clicked.connect(lambda: self.set_speed_preset(2))
        self.btn_normal.clicked.connect(lambda: self.set_speed_preset(5))
        self.btn_fast.clicked.connect(lambda: self.set_speed_preset(8))
        self.btn_ultra_fast.clicked.connect(lambda: self.set_speed_preset(10))

        speed_layout.addWidget(QLabel("慢"))
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(QLabel("快"))
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.btn_slow)
        speed_layout.addWidget(self.btn_normal)
        speed_layout.addWidget(self.btn_fast)
        speed_layout.addWidget(self.btn_ultra_fast)
        speed_group.setLayout(speed_layout)

        self.btn_reset = QPushButton("🔁 重置并开始调度")
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_resume = QPushButton("▶️ 继续")
        self.btn_step = QPushButton("⏭ 单步")
        self.btn_back = QPushButton("🔙 上一步")

        self.btn_back.clicked.connect(self.step_back)
        self.btn_reset.clicked.connect(self.start_simulation)
        self.btn_pause.clicked.connect(self.pause_simulation)
        self.btn_resume.clicked.connect(self.resume_simulation)
        self.btn_step.clicked.connect(self.step_once)

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("调度策略:"))
        control_layout.addWidget(self.strategy_select)
        control_layout.addWidget(self.btn_reset)
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_resume)
        control_layout.addWidget(self.btn_step)
        control_layout.addWidget(self.btn_back)

        self.input_job_id = QLineEdit()
        self.input_job_id.setPlaceholderText("作业ID")
        self.input_size = QLineEdit()
        self.input_size.setPlaceholderText("大小(MB)")
        self.input_arrival = QLineEdit()
        self.input_arrival.setPlaceholderText("到达时间")
        self.input_runtime = QLineEdit()
        self.input_runtime.setPlaceholderText("运行时间")

        self.btn_add_job = QPushButton("➕ 添加作业")
        self.btn_add_job.clicked.connect(self.add_job)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("添加作业:"))
        input_layout.addWidget(self.input_job_id)
        input_layout.addWidget(self.input_size)
        input_layout.addWidget(self.input_arrival)
        input_layout.addWidget(self.input_runtime)
        input_layout.addWidget(self.btn_add_job)

        self.job_table = QTableWidget()
        self.job_table.setColumnCount(6)
        self.job_table.setHorizontalHeaderLabels(["作业ID", "大小", "到达时间", "剩余时间", "状态", "完成时间"])
        self.job_table.verticalHeader().setVisible(False)
        self.job_table.setMinimumHeight(120)
        from PyQt5.QtWidgets import QSizePolicy
        self.job_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 让表格列宽自适应
        from PyQt5.QtWidgets import QHeaderView
        header = self.job_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 平均分配列宽

        self.status_label = QLabel("状态：未开始")
        self.status_label.setStyleSheet("font-weight: bold; color: darkblue;")

        # 新增：功能状态显示标签
        self.feature_status_label = QLabel("功能状态：内存合并 ✅ | 内存紧凑 ✅")
        self.feature_status_label.setStyleSheet("font-size: 10px; color: darkgreen;")

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(switch_group)  # 添加功能开关分组
        layout.addWidget(speed_group)  # 添加速度控制分组
        layout.addLayout(control_layout)
        layout.addLayout(input_layout)
        layout.addWidget(self.job_table)
        layout.addWidget(self.status_label)
        layout.addWidget(self.feature_status_label)  # 添加功能状态显示
        self.setLayout(layout)

        self.manager = None
        self.jobs = []
        self.timer = QTimer()
        self.history = []  # 用于保存历史记录
        self.timer.timeout.connect(self.step)
        self.current_time = 0

        # 初始化速度
        self.current_speed = 5
        self.update_speed_display()

    def on_merge_checkbox_changed(self, state):
        """内存合并开关变化处理"""
        enabled = state == 2  # 2 表示选中状态
        if self.manager:
            self.manager.set_merge_enabled(enabled)
        self.update_feature_status()

    def on_compact_checkbox_changed(self, state):
        """内存紧凑开关变化处理"""
        enabled = state == 2  # 2 表示选中状态
        if self.manager:
            self.manager.set_compact_enabled(enabled)
        self.update_feature_status()

    def on_speed_changed(self, value):
        """速度滑块变化处理"""
        self.current_speed = value
        self.update_speed_display()
        # 如果定时器正在运行，更新间隔
        if self.timer.isActive():
            self.timer.setInterval(self.get_timer_interval())

    def set_speed_preset(self, speed_value):
        """设置预设速度"""
        self.speed_slider.setValue(speed_value)
        self.current_speed = speed_value
        self.update_speed_display()
        if self.timer.isActive():
            self.timer.setInterval(self.get_timer_interval())

    def get_timer_interval(self):
        """根据速度值计算定时器间隔（毫秒）"""
        # 速度值1-10映射到3000ms-100ms
        # 使用指数映射让速度变化更平滑
        intervals = {
            1: 3000,  # 3秒 - 0.33x
            2: 2000,  # 2秒 - 0.5x
            3: 1500,  # 1.5秒 - 0.67x
            4: 1200,  # 1.2秒 - 0.83x
            5: 1000,  # 1秒 - 1.0x (默认)
            6: 800,  # 0.8秒 - 1.25x
            7: 600,  # 0.6秒 - 1.67x
            8: 400,  # 0.4秒 - 2.5x
            9: 200,  # 0.2秒 - 5.0x
            10: 100  # 0.1秒 - 10.0x
        }
        return intervals.get(self.current_speed, 1000)

    def get_speed_multiplier(self):
        """获取速度倍数用于显示"""
        speed_multipliers = {
            1: 0.33, 2: 0.5, 3: 0.67, 4: 0.83, 5: 1.0,
            6: 1.25, 7: 1.67, 8: 2.5, 9: 5.0, 10: 10.0
        }
        return speed_multipliers.get(self.current_speed, 1.0)

    def update_speed_display(self):
        """更新速度显示"""
        multiplier = self.get_speed_multiplier()
        self.speed_label.setText(f"速度: {multiplier}x")

        # 根据速度更新按钮样式
        buttons = [self.btn_slow, self.btn_normal, self.btn_fast, self.btn_ultra_fast]
        speeds = [2, 5, 8, 10]

        for i, (button, speed) in enumerate(zip(buttons, speeds)):
            if self.current_speed == speed:
                button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            else:
                button.setStyleSheet("")

    def update_feature_status(self):
        """更新功能状态显示"""
        merge_status = "✅" if self.enable_merge_checkbox.isChecked() else "❌"
        compact_status = "✅" if self.enable_compact_checkbox.isChecked() else "❌"
        self.feature_status_label.setText(f"功能状态：内存合并 {merge_status} | 内存紧凑 {compact_status}")

    def start_simulation(self):
        # 创建内存管理器时根据开关状态设置功能
        merge_enabled = self.enable_merge_checkbox.isChecked()
        compact_enabled = self.enable_compact_checkbox.isChecked()

        self.manager = MemoryManager(enable_merge=merge_enabled, enable_compact=compact_enabled)
        self.jobs = self.load_jobs()
        self.current_time = 0
        self.history = []  # 清空历史记录

        # 使用当前速度设置启动定时器
        interval = self.get_timer_interval()
        self.timer.start(interval)

        self.update_canvas()
        self.update_job_table()
        self.update_status_bar()

        multiplier = self.get_speed_multiplier()
        print("🎬 调度开始...", flush=True)
        print(f"🔧 内存合并: {'启用' if merge_enabled else '禁用'}")
        print(f"🔧 内存紧凑: {'启用' if compact_enabled else '禁用'}")
        print(f"⚡ 模拟速度: {multiplier}x ({self.get_timer_interval()}ms间隔)")

    def pause_simulation(self):
        self.timer.stop()
        multiplier = self.get_speed_multiplier()
        print(f"⏸ 模拟暂停 (当前速度: {multiplier}x)")

    def resume_simulation(self):
        # 使用当前速度设置重启定时器
        interval = self.get_timer_interval()
        self.timer.start(interval)
        multiplier = self.get_speed_multiplier()
        print(f"▶️ 模拟继续 (速度: {multiplier}x)")

    def step_once(self):
        self.step()
        print("⏭ 单步执行完成")

    def load_jobs(self):
        try:
            with open("job_data.json", "r", encoding="utf-8") as f:
                raw = json.load(f)
            return [Job(j["job_id"], j["size"], j["arrival_time"], j["run_time"]) for j in raw]
        except Exception as e:
            print(f"❌ 读取 job_data.json 出错：{e}")
            return []

    def add_job(self):
        try:
            job_id = self.input_job_id.text().strip()
            size = int(self.input_size.text())
            arrival = int(self.input_arrival.text())
            runtime = int(self.input_runtime.text())
            new_job = Job(job_id, size, arrival, runtime)
            self.jobs.append(new_job)
            self.update_job_table()
            self.input_job_id.clear()
            self.input_size.clear()
            self.input_arrival.clear()
            self.input_runtime.clear()
            print(f"➕ 添加作业: {job_id}, 大小: {size}MB, 到达时间: {arrival}s, 运行时间: {runtime}s")
        except Exception as e:
            print(f"❌ 添加作业失败：{e}")

    def step(self):
        # 保存快照（作业状态、内存块、当前时间）
        self.history.append({
            "jobs": copy.deepcopy(self.jobs),
            "blocks": copy.deepcopy(self.manager.blocks),
            "current_time": self.current_time
        })

        self.current_time += 1
        print(f"\n⏱ 当前时间: {self.current_time}")

        for job in self.jobs:
            if job.status == 'waiting' and job.arrival_time <= self.current_time:
                addr = self.manager.allocate(job.size, strategy=self.strategy_select.currentText(), job_id=job.job_id)
                if addr is not None:
                    job.status = 'running'
                    print(f"✅ 作业 {job.job_id} 进入内存，起始地址: {addr}MB")
                else:
                    print(f"🕓 作业 {job.job_id} 等待中，内存不足")

            elif job.status == 'running':
                job.remaining_time -= 1
                print(f"▶️ 作业 {job.job_id} 运行中，剩余时间: {job.remaining_time}s")
                if job.remaining_time <= 0:
                    job.status = 'finished'
                    job.finish_time = self.current_time
                    self.manager.recycle(job.job_id)
                    print(f"✅ 作业 {job.job_id} 已完成并释放内存")

        self.update_canvas()
        self.update_job_table()
        self.update_status_bar()

        if all(job.status == 'finished' for job in self.jobs):
            self.timer.stop()
            print("🎉 所有作业执行完毕！")

    def update_canvas(self):
        memory_state = []
        for block in self.manager.blocks:
            block_type = 'free' if block.status == 'free' else 'used'
            memory_state.append({
                'start': block.start,
                'size': block.size,
                'type': block_type,
                'job_id': block.job_id
            })
        self.canvas.update_blocks(memory_state)

    def update_job_table(self):
        status_order = {'running': 0, 'waiting': 1, 'finished': 2}
        self.jobs.sort(key=lambda j: (status_order.get(j.status, 3), j.arrival_time))

        self.job_table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            self.job_table.setItem(row, 0, QTableWidgetItem(str(job.job_id)))
            self.job_table.setItem(row, 1, QTableWidgetItem(str(job.size)))
            self.job_table.setItem(row, 2, QTableWidgetItem(str(job.arrival_time)))
            self.job_table.setItem(row, 3, QTableWidgetItem(str(job.remaining_time if job.status != 'finished' else 0)))
            status_item = QTableWidgetItem(str(job.status))
            if job.status == 'running':
                status_item.setBackground(QColor(0, 255, 0, 50))
            elif job.status == 'waiting':
                status_item.setBackground(QColor(128, 128, 128, 50))
            elif job.status == 'finished':
                status_item.setBackground(QColor(150, 150, 255, 50))
            self.job_table.setItem(row, 4, status_item)
            self.job_table.setItem(row, 5,
                                   QTableWidgetItem(str(job.finish_time) if job.finish_time is not None else ""))

    def update_status_bar(self):
        used = sum(b.size for b in self.manager.blocks if b.status == 'used')
        total = sum(b.size for b in self.manager.blocks)
        utilization = (used / total) * 100 if total else 0
        finished = sum(1 for job in self.jobs if job.status == 'finished')
        total_jobs = len(self.jobs)

        # 获取当前速度倍数
        speed_multiplier = self.get_speed_multiplier()

        self.status_label.setText(
            f"⏱ 当前时间: {self.current_time}s ｜ "
            f"📊 内存使用率: {utilization:.1f}% ({used}/{total}MB) ｜ "
            f"✅ 作业完成: {finished}/{total_jobs} ｜ "
            f"⚡ 速度: {speed_multiplier}x"
        )

    def step_back(self):
        if not self.history:
            print("❌ 无法回退，已是最初状态")
            return

        last_state = self.history.pop()
        self.jobs = copy.deepcopy(last_state["jobs"])
        self.manager.blocks = copy.deepcopy(last_state["blocks"])
        self.current_time = last_state["current_time"]

        self.update_canvas()
        self.update_job_table()
        self.update_status_bar()
        print(f"🔙 回退到时间: {self.current_time}s")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())