"""
Модуль для работы с файлами проектов
"""

import json
import os
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox
from datetime import datetime


class FileManager:
    """
    Класс для сохранения и загрузки проектов
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.current_file = None

    def save_project(self, data: Dict[str, Any], filename: str) -> bool:
        """
        Сохранение проекта в файл

        Args:
            data: данные проекта
            filename: имя файла

        Returns:
            True если успешно, False иначе
        """
        try:
            # Добавление метаданных
            data['metadata'] = {
                'saved_at': datetime.now().isoformat(),
                'version': '1.0.0'
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.current_file = filename
            return True

        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка",
                                 f"Не удалось сохранить проект: {str(e)}")
            return False

    def load_project(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Загрузка проекта из файла

        Args:
            filename: имя файла

        Returns:
            данные проекта или None при ошибке
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_file = filename
            return data

        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка",
                                 f"Не удалось загрузить проект: {str(e)}")
            return None

    def export_to_json(self, data: Dict[str, Any], filename: str) -> bool:
        """
        Экспорт данных в JSON (без метаданных)

        Args:
            data: данные для экспорта
            filename: имя файла

        Returns:
            True если успешно
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(self.parent, "Ошибка",
                                 f"Не удалось экспортировать: {str(e)}")
            return False