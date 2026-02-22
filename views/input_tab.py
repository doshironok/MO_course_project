"""
Модуль вкладки ввода данных
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from utils.constants import INVESTMENTS, PAYMENTS, RISK_LIMIT, DURATION_LIMIT


class InputTab(QWidget):
    """
    Вкладка для ввода исходных данных
    """

    # Сигналы
    calculationRequested = pyqtSignal(str)  # режим расчета

    def __init__(self):
        super().__init__()
        self.investments = INVESTMENTS.copy()
        self.payments = PAYMENTS.copy()
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout()

        # Группа параметров контракта
        contract_group = QGroupBox("Параметры контракта")
        contract_layout = QGridLayout()

        contract_layout.addWidget(QLabel("Платеж через 2 месяца:"), 0, 0)
        self.payment_2_edit = QLineEdit(str(self.payments[2]))
        self.payment_2_edit.setValidator(QDoubleValidator(0, 10000, 2))
        contract_layout.addWidget(self.payment_2_edit, 0, 1)
        contract_layout.addWidget(QLabel("тыс. руб"), 0, 2)

        contract_layout.addWidget(QLabel("Платеж через 6 месяцев:"), 1, 0)
        self.payment_6_edit = QLineEdit(str(self.payments[6]))
        self.payment_6_edit.setValidator(QDoubleValidator(0, 10000, 2))
        contract_layout.addWidget(self.payment_6_edit, 1, 1)
        contract_layout.addWidget(QLabel("тыс. руб"), 1, 2)

        contract_group.setLayout(contract_layout)
        layout.addWidget(contract_group)

        # Группа инвестиционных инструментов
        instruments_group = QGroupBox("Инвестиционные инструменты")
        instruments_layout = QVBoxLayout()

        # Таблица инструментов
        self.instruments_table = QTableWidget()
        self.instruments_table.setColumnCount(5)
        self.instruments_table.setHorizontalHeaderLabels(
            ["Инструмент", "Месяцы начала", "Срок (мес)", "Ставка (%)", "Риск"]
        )
        self.instruments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.update_instruments_table()
        instruments_layout.addWidget(self.instruments_table)

        # Кнопка сброса к значениям по умолчанию
        reset_btn = QPushButton("Сбросить к значениям по умолчанию")
        reset_btn.clicked.connect(self.reset_to_defaults)
        instruments_layout.addWidget(reset_btn)

        instruments_group.setLayout(instruments_layout)
        layout.addWidget(instruments_group)

        # Группа ограничений
        limits_group = QGroupBox("Ограничения")
        limits_layout = QGridLayout()

        limits_layout.addWidget(QLabel("Лимит по риску:"), 0, 0)
        self.risk_limit_edit = QLineEdit(str(RISK_LIMIT))
        self.risk_limit_edit.setValidator(QDoubleValidator(0, 100, 1))
        limits_layout.addWidget(self.risk_limit_edit, 0, 1)

        limits_layout.addWidget(QLabel("Лимит по сроку:"), 1, 0)
        self.duration_limit_edit = QLineEdit(str(DURATION_LIMIT))
        self.duration_limit_edit.setValidator(QDoubleValidator(0, 12, 1))
        limits_layout.addWidget(self.duration_limit_edit, 1, 1)
        limits_layout.addWidget(QLabel("месяцев"), 1, 2)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Группа кнопок управления
        buttons_group = QGroupBox("Управление расчетом")
        buttons_layout = QHBoxLayout()

        self.basic_btn = QPushButton("Расчет без ограничений")
        self.basic_btn.clicked.connect(lambda: self.calculationRequested.emit('basic'))
        buttons_layout.addWidget(self.basic_btn)

        self.risk_btn = QPushButton("Расчет с учетом риска")
        self.risk_btn.clicked.connect(lambda: self.calculationRequested.emit('risk'))
        buttons_layout.addWidget(self.risk_btn)

        self.full_btn = QPushButton("Полный расчет (риск + срок)")
        self.full_btn.clicked.connect(lambda: self.calculationRequested.emit('full'))
        buttons_layout.addWidget(self.full_btn)

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_inputs)
        buttons_layout.addWidget(self.clear_btn)

        buttons_group.setLayout(buttons_layout)
        layout.addWidget(buttons_group)

        # Индикатор состояния
        self.status_label = QLabel("Введите данные и выберите режим расчета")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def update_instruments_table(self):
        """Обновление таблицы инструментов"""
        self.instruments_table.setRowCount(len(self.investments))

        for i, inv in enumerate(self.investments):
            # Инструмент
            self.instruments_table.setItem(i, 0, QTableWidgetItem(inv['name']))

            # Месяцы начала
            months_str = ', '.join(str(m) for m in inv['start_months'])
            self.instruments_table.setItem(i, 1, QTableWidgetItem(months_str))

            # Срок
            self.instruments_table.setItem(i, 2, QTableWidgetItem(str(inv['duration'])))

            # Ставка
            self.instruments_table.setItem(i, 3, QTableWidgetItem(str(inv['rate'])))

            # Риск
            self.instruments_table.setItem(i, 4, QTableWidgetItem(str(inv['risk'])))

    def reset_to_defaults(self):
        """Сброс к значениям по умолчанию"""
        self.investments = INVESTMENTS.copy()
        self.payments = PAYMENTS.copy()
        self.risk_limit_edit.setText(str(RISK_LIMIT))
        self.duration_limit_edit.setText(str(DURATION_LIMIT))
        self.payment_2_edit.setText(str(PAYMENTS[2]))
        self.payment_6_edit.setText(str(PAYMENTS[6]))
        self.update_instruments_table()
        self.status_label.setText("Значения сброшены к исходным")

    def clear_inputs(self):
        """Очистка полей ввода"""
        self.payment_2_edit.clear()
        self.payment_6_edit.clear()
        self.risk_limit_edit.clear()
        self.duration_limit_edit.clear()
        self.status_label.setText("Поля очищены")

    def get_input_data(self) -> dict:
        """
        Получение введенных данных

        Returns:
            словарь с исходными данными
        """
        try:
            payments = {
                2: float(self.payment_2_edit.text() or '0'),
                6: float(self.payment_6_edit.text() or '0')
            }

            risk_limit = float(self.risk_limit_edit.text() or str(RISK_LIMIT))
            duration_limit = float(self.duration_limit_edit.text() or str(DURATION_LIMIT))

            return {
                'investments': self.investments,
                'payments': payments,
                'risk_limit': risk_limit,
                'duration_limit': duration_limit,
                'success': True
            }

        except ValueError as e:
            self.status_label.setText(f"Ошибка ввода: {str(e)}")
            return {'success': False, 'error': str(e)}

    def set_data(self, data: dict):
        """
        Установка данных из загруженного проекта

        Args:
            data: словарь с данными
        """
        try:
            if 'investments' in data:
                self.investments = data['investments']
                self.update_instruments_table()

            if 'payments' in data:
                self.payments = data['payments']
                self.payment_2_edit.setText(str(data['payments'].get(2, 200)))
                self.payment_6_edit.setText(str(data['payments'].get(6, 700)))

            if 'risk_limit' in data:
                self.risk_limit_edit.setText(str(data['risk_limit']))

            if 'duration_limit' in data:
                self.duration_limit_edit.setText(str(data['duration_limit']))

            self.status_label.setText("Данные загружены")

        except Exception as e:
            self.status_label.setText(f"Ошибка загрузки: {str(e)}")