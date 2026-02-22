#!/usr/bin/env python3
"""
Точка входа в приложение
Инвестиционный оптимизатор - решение задачи Г. Альба
Вариант №10 курсовой работы по дисциплине "Методы оптимизации"
"""

import sys
from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow


def main():
    """Основная функция приложения"""
    app = QApplication(sys.argv)
    app.setApplicationName("Инвестиционный оптимизатор")
    app.setOrganizationName("КубГТУ")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()