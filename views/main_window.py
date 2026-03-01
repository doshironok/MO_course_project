"""
Модуль главного окна приложения
"""
import traceback
from turtle import pd

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from views.input_tab import InputTab
from views.results_tab import ResultsTab
from views.charts_tab import ChartsTab
from views.analysis_tab import AnalysisTab
from models.optimizer import InvestmentOptimizer
from controllers.file_manager import FileManager
from controllers.export_manager import ExportManager
from utils.constants import APP_NAME, APP_WIDTH, APP_HEIGHT


class MainWindow(QMainWindow):
    """
    Главное окно приложения
    """

    def __init__(self):
        super().__init__()
        self.optimizer = InvestmentOptimizer()
        self.file_manager = FileManager(self)
        self.export_manager = ExportManager(self)
        self.current_solution = None
        self.current_constraints_df = None
        self.current_allocation_df = None

        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, APP_WIDTH, APP_HEIGHT)

        # Создание центрального виджета с вкладками
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Создание вкладок
        self.input_tab = InputTab()
        self.results_tab = ResultsTab()
        self.charts_tab = ChartsTab()
        self.analysis_tab = AnalysisTab()

        # Подключение сигналов
        self.input_tab.calculationRequested.connect(self.run_calculation)

        # Добавление вкладок
        self.tab_widget.addTab(self.input_tab, "Ввод данных")
        self.tab_widget.addTab(self.results_tab, "Результаты")
        self.tab_widget.addTab(self.charts_tab, "Графики")
        self.tab_widget.addTab(self.analysis_tab, "Анализ")

        # Создание меню
        self.create_menu()

        # Создание панели инструментов
        self.create_toolbar()

        # Строка состояния
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

    def create_menu(self):
        """Создание меню приложения"""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        new_action = QAction("Новый расчет", self)
        new_action.triggered.connect(self.new_calculation)
        file_menu.addAction(new_action)

        open_action = QAction("Открыть проект", self)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить проект", self)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_pdf_action = QAction("Экспорт в PDF", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        file_menu.addAction(export_pdf_action)

        export_excel_action = QAction("Экспорт в Excel", self)
        export_excel_action.triggered.connect(self.export_excel)
        file_menu.addAction(export_excel_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Расчет
        calc_menu = menubar.addMenu("Расчет")

        basic_action = QAction("Без ограничений", self)
        basic_action.triggered.connect(lambda: self.run_calculation('basic'))
        calc_menu.addAction(basic_action)

        risk_action = QAction("С учетом риска", self)
        risk_action.triggered.connect(lambda: self.run_calculation('risk'))
        calc_menu.addAction(risk_action)

        full_action = QAction("Полный расчет", self)
        full_action.triggered.connect(lambda: self.run_calculation('full'))
        calc_menu.addAction(full_action)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        guide_action = QAction("Руководство пользователя", self)
        guide_action.triggered.connect(self.show_guide)
        help_menu.addAction(guide_action)

    def create_toolbar(self):
        """Создание панели инструментов"""
        toolbar = self.addToolBar("Инструменты")

        # Кнопки быстрого доступа
        basic_btn = QAction("Без ограничений", self)
        basic_btn.triggered.connect(lambda: self.run_calculation('basic'))
        toolbar.addAction(basic_btn)

        risk_btn = QAction("С риском", self)
        risk_btn.triggered.connect(lambda: self.run_calculation('risk'))
        toolbar.addAction(risk_btn)

        full_btn = QAction("Полный", self)
        full_btn.triggered.connect(lambda: self.run_calculation('full'))
        toolbar.addAction(full_btn)

        toolbar.addSeparator()

        save_btn = QAction("Сохранить", self)
        save_btn.triggered.connect(self.save_project)
        toolbar.addAction(save_btn)

        export_btn = QAction("Экспорт", self)
        export_btn.triggered.connect(self.export_excel)
        toolbar.addAction(export_btn)

    def run_calculation(self, mode: str):
        """
        Запуск расчета в выбранном режиме
        """
        try:
            self.status_bar.showMessage(f"Выполняется расчет ({mode})...")
            QApplication.processEvents()

            # Получение исходных данных
            input_data = self.input_tab.get_input_data()

            if not input_data['success']:
                QMessageBox.warning(self, "Ошибка ввода", input_data.get('error', 'Неизвестная ошибка'))
                self.status_bar.showMessage("Ошибка ввода данных")
                return

            print(f"\n🔴 ЗАПУСК РАСЧЕТА В РЕЖИМЕ: {mode}")

            # Построение модели
            model = self.optimizer.build_model(
                investments=input_data['investments'],
                payments=input_data['payments'],
                risk_limit=input_data['risk_limit'],
                duration_limit=input_data['duration_limit'],
                mode=mode
            )

            # Решение в зависимости от режима
            if mode == 'basic':
                # Для basic используем специальный метод поиска оптимального пути
                solution = self.optimizer.solve_basic(model)
            else:
                # Для risk и full используем обычный solve
                solution = self.optimizer.solve(model)

            # Сохранение результатов
            self.current_solution = solution

            # Получение таблиц для отображения
            self.current_constraints_df = self.optimizer.check_constraints(solution)
            self.current_allocation_df = self.optimizer.get_allocation_dataframe(solution)

            # Обновление вкладок
            self.results_tab.display_results(solution, self.current_constraints_df, self.current_allocation_df)
            self.charts_tab.set_solution(solution)
            self.analysis_tab.set_data(solution, self.current_constraints_df, self.current_allocation_df)

            # Переключение на вкладку результатов
            self.tab_widget.setCurrentIndex(1)

            mode_names = {'basic': 'без ограничений', 'risk': 'с риском', 'full': 'полный'}
            if solution['success']:
                self.status_bar.showMessage(f"✅ Расчет ({mode_names[mode]}) выполнен успешно")
            else:
                self.status_bar.showMessage(f"❌ Ошибка при расчете: {solution['message']}")

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Критическая ошибка: {str(e)}")

    def new_calculation(self):
        """Начать новый расчет"""
        reply = QMessageBox.question(self, "Новый расчет",
                                    "Начать новый расчет? Все несохраненные данные будут потеряны.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.input_tab.reset_to_defaults()
            self.results_tab.clear()
            self.charts_tab.set_solution(None)
            self.analysis_tab.set_data(None, None, None)
            self.current_solution = None
            self.tab_widget.setCurrentIndex(0)
            self.status_bar.showMessage("Новый расчет")

    def save_project(self):
        """Сохранение проекта"""
        if not self.current_solution:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект", "", "JSON файлы (*.json)")

        if filename:
            # Подготовка данных для сохранения
            input_data = self.input_tab.get_input_data()
            data = {
                'input': input_data,
                'solution': {
                    'fun': float(self.current_solution['fun']) if self.current_solution['fun'] else None,
                    'mode': self.current_solution['mode'],
                    'success': self.current_solution['success'],
                    'message': self.current_solution['message']
                }
            }

            if self.file_manager.save_project(data, filename):
                self.status_bar.showMessage(f"Проект сохранен: {filename}")

    def open_project(self):
        """Загрузка проекта"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "", "JSON файлы (*.json)")

        if filename:
            data = self.file_manager.load_project(filename)
            if data:
                # Восстановление данных ввода
                if 'input' in data:
                    self.input_tab.set_data(data['input'])

                self.status_bar.showMessage(f"Проект загружен: {filename}")

    def export_pdf(self):
        """Экспорт в PDF"""
        if not self.current_solution or not self.current_solution.get('success'):
            QMessageBox.warning(self, "Предупреждение", "Нет успешного решения для экспорта")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в PDF", "", "PDF файлы (*.pdf)")

        if filename:
            if self.export_manager.export_to_pdf(
                self.current_solution,
                self.current_constraints_df,
                self.current_allocation_df,
                filename
            ):
                self.status_bar.showMessage(f"Отчет сохранен: {filename}")

    def export_excel(self):
        """Экспорт в Excel"""
        if not self.current_solution or not self.current_solution.get('success'):
            QMessageBox.warning(self, "Предупреждение", "Нет успешного решения для экспорта")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в Excel", "", "Excel файлы (*.xlsx)")

        if filename:
            if self.export_manager.export_to_excel(
                self.current_solution,
                self.current_constraints_df,
                self.current_allocation_df,
                filename
            ):
                self.status_bar.showMessage(f"Отчет сохранен: {filename}")

    def show_about(self):
        """Отображение информации о программе"""
        dialog = AboutDialog(self)
        dialog.exec()

    def show_guide(self):
        """Отображение руководства пользователя"""
        dialog = GuideDialog(self)
        dialog.exec()


class AboutDialog(QDialog):
    """Диалоговое окно 'О программе'"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.resize(1000, 600)  # Используем resize вместо setMinimumWidth

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        # Текст с информацией
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <div style='text-align: center; font-family: Segoe UI, Arial, sans-serif;'>
            <h2 style='color: #1560BD; margin: 20px 0; font-size: 24px;'>Инвестиционный оптимизатор</h2>
            <p style='font-size: 18px; color: #666; margin: 15px 0;'>Версия 1.0.0</p>
            <hr style='border: 2px solid #1560BD; width: 95%; margin: 25px auto;'>

            <div style='text-align: left; margin: 25px 35px;'>
                <p style='margin: 20px 0; font-size: 12px; line-height: 1.8;'><b>Назначение:</b> Решение задачи оптимизации инвестиционного портфеля
                (вариант №10 курсовой работы по дисциплине 'Методы оптимизации')</p>

                <p style='margin: 20px 0; font-size: 12px; line-height: 1.8;'><b>Суть программы:</b> Минимизация начального целевого фонда для выполнения
                платежей по контракту (200 млн руб через 2 месяца и 700 млн руб через 6 месяцев)
                путем оптимального распределения инвестиций между четырьмя типами инструментов
                (A, B, C, O) с учетом ограничений по риску и сроку погашения.</p>
            </div>

            <div style='background-color: #F0F4FA; padding: 25px; border-radius: 10px; margin: 25px 35px; text-align: left;'>
                <p style='margin: 15px 0; font-size: 12px;'><b>Разработчик:</b> Зубенко Диана Сергеевна</p>
                <p style='margin: 15px 0; font-size: 12px;'><b>Учебное заведение:</b> ФГБОУ ВО «Кубанский государственный технологический университет» (КубГТУ)</p>
                <p style='margin: 15px 0; font-size: 12px;'><b>Факультет:</b> Компьютерных систем и информационной безопасности (КСИБ)</p>
                <p style='margin: 15px 0; font-size: 12px;'><b>Кафедра:</b> Информационных систем и программирования (ИСП)</p>
                <p style='margin: 15px 0; font-size: 12px;'><b>Курс:</b> 3</p>
                <p style='margin: 15px 0; font-size: 12px;'><b>Группа:</b> 23-КБ-ПР1</p>
                <p style='margin: 15px 0; font-size: 12px;'><b>Год разработки:</b> 2026</p>
            </div>

            <p style='color: #666; font-style: italic; margin: 25px 0; font-size: 12px;'>
                Руководитель: канд. техн. наук, доц. М.В. Янаева
            </p>

            <hr style='border: 2px solid #1560BD; width: 95%; margin: 25px auto;'>
            <p style='color: #999; margin: 20px 0; font-size: 16px;'>© 2026 КубГТУ, кафедра ИСП</p>
        </div>
        """)

        layout.addWidget(text_edit)

        # Кнопка закрытия
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)


class GuideDialog(QDialog):
    """Диалоговое окно 'Руководство пользователя' с увеличенным размером"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Руководство пользователя")
        # Увеличиваем размер в 2 раза
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        # Текст с руководством
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Segoe UI", 12))
        text_edit.setHtml("""
        <div style='font-family: Segoe UI, Arial, sans-serif; margin: 20px;'>
            <h2 style='color: #1560BD; text-align: center; margin: 25px 0 35px 0; font-size: 28px;'>📖 Руководство пользователя</h2>

            <div style='margin: 35px 30px;'>
                <h3 style='color: #1560BD; margin: 25px 0 20px 0; font-size: 22px;'>1. Ввод исходных данных</h3>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• Заполните параметры контракта (суммы платежей через 2 и 6 месяцев)</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• Просмотрите характеристики инвестиционных инструментов (можно сбросить к значениям по умолчанию)</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• Укажите ограничения по риску и сроку погашения</p>
            </div>

            <div style='margin: 35px 30px;'>
                <h3 style='color: #1560BD; margin: 25px 0 20px 0; font-size: 22px;'>2. Выбор режима расчета</h3>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Без ограничений</b> - минимизация начального фонда без учета риска и срока</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>С учетом риска</b> - с ограничением средневзвешенного риска ≤ 6</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Полный расчет</b> - с ограничениями по риску и сроку погашения ≤ 2.5 месяца</p>
            </div>

            <div style='margin: 35px 30px;'>
                <h3 style='color: #1560BD; margin: 25px 0 20px 0; font-size: 22px;'>3. Просмотр результатов</h3>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Вкладка "Результаты"</b> - табличные данные и анализ ограничений</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Вкладка "Графики"</b> - визуализация структуры портфеля и динамики показателей</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Вкладка "Анализ"</b> - детальная информация и ответы на вопросы задания</p>
            </div>

            <div style='margin: 35px 30px;'>
                <h3 style='color: #1560BD; margin: 25px 0 20px 0; font-size: 22px;'>4. Сохранение и экспорт</h3>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Сохранить проект (JSON)</b> - для последующей загрузки</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Экспорт в Excel</b> - полный отчет с несколькими листами</p>
                <p style='margin: 12px 0 12px 35px; font-size: 14px; line-height: 1.8;'>• <b>Экспорт в PDF</b> - форматированный отчет для печати</p>
            </div>

            <div style='background-color: #F0F4FA; padding: 30px; border-radius: 10px; margin: 35px 30px;'>
                <h3 style='color: #1560BD; margin: 0 0 20px 0; font-size: 22px;'>❓ Ответы на вопросы задания</h3>
                <p style='margin: 15px 0; font-size: 18px;'>Программа автоматически формирует ответы на все вопросы варианта №10:</p>
                <p style='margin: 10px 0 10px 35px; font-size: 14px;'>- размер целевого фонда без ограничений</p>
                <p style='margin: 10px 0 10px 35px; font-size: 14px;'>- необходимость инвестиций вида А в месяце 1</p>
                <p style='margin: 10px 0 10px 35px; font-size: 14px;'>- размер фонда с учетом риска</p>
                <p style='margin: 10px 0 10px 35px; font-size: 14px;'>- размер фонда с учетом всех ограничений</p>
            </div>

            <p style='text-align: center; color: #666; margin: 35px 0 25px 0; font-size: 16px;'>
                Для получения дополнительной информации обратитесь к разработчику
            </p>
        </div>
        """)

        layout.addWidget(text_edit)

        # Кнопка закрытия
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Закрыть")
        ok_button.setMinimumWidth(150)
        ok_button.setMinimumHeight(40)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)