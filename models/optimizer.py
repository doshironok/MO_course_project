"""
Модуль оптимизатора инвестиционного портфеля
Реализует математическую модель и алгоритмы решения задачи линейного программирования
"""

import numpy as np
from scipy.optimize import linprog
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any


class InvestmentOptimizer:
    """
    Класс для оптимизации инвестиционного портфеля
    """

    def __init__(self):
        """Инициализация оптимизатора"""
        self.variables = []  # Список переменных решения
        self.investments = None
        self.payments = None
        self.risk_limit = None
        self.duration_limit = None

    def _generate_variables(self, investments: List[Dict]) -> List[Dict]:
        """
        Генерация списка переменных решения

        Args:
            investments: список характеристик инвестиционных инструментов

        Returns:
            список словарей с переменными
        """
        variables = []
        for inv in investments:
            for month in inv['start_months']:
                variables.append({
                    'name': inv['name'],
                    'start_month': month,
                    'duration': inv['duration'],
                    'rate': inv['rate'] / 100,  # перевод в доли
                    'risk': inv['risk'],
                    'end_month': month + inv['duration']
                })
        return variables

    def build_model(self, investments: List[Dict], payments: Dict,
                    risk_limit: float, duration_limit: float, mode: str = 'full') -> Dict:
        """
        Построение математической модели задачи линейного программирования

        Args:
            investments: список инвестиционных инструментов
            payments: словарь платежей {месяц: сумма}
            risk_limit: лимит по риску
            duration_limit: лимит по сроку погашения
            mode: режим расчета ('basic', 'risk', 'full')

        Returns:
            словарь с компонентами модели
        """
        self.investments = investments
        self.payments = payments
        self.risk_limit = risk_limit
        self.duration_limit = duration_limit

        # Генерация переменных
        self.variables = self._generate_variables(investments)
        n_vars = len(self.variables)

        # Целевая функция (минимизация суммы всех инвестиций)
        c = np.ones(n_vars)

        # Инициализация матриц ограничений
        A_eq = []
        b_eq = []
        A_ub = []
        b_ub = []

        # 1. Ограничения по платежам (равенства)
        for month in sorted(payments.keys()):
            row = np.zeros(n_vars)
            for i, var in enumerate(self.variables):
                if var['end_month'] == month:
                    # Коэффициент с учетом процентов (отрицательный для канонической формы)
                    row[i] = -(1 + var['rate'])
            A_eq.append(row)
            b_eq.append(-payments[month])

        # 2. Ограничения по риску (если требуется)
        if mode in ['risk', 'full']:
            for month in range(1, 7):
                for i, var in enumerate(self.variables):
                    if var['start_month'] <= month < var['end_month']:
                        row = np.zeros(n_vars)
                        row[i] = var['risk'] - risk_limit
                        A_ub.append(row)
                        b_ub.append(0)

        # 3. Ограничения по сроку погашения (если требуется)
        if mode == 'full':
            for month in range(1, 7):
                for i, var in enumerate(self.variables):
                    if var['start_month'] <= month < var['end_month']:
                        row = np.zeros(n_vars)
                        remaining_time = var['end_month'] - month
                        row[i] = remaining_time - duration_limit
                        A_ub.append(row)
                        b_ub.append(0)

        # Границы переменных (x >= 0)
        bounds = [(0, None) for _ in range(n_vars)]

        # Преобразование в массивы numpy
        model = {
            'c': c,
            'A_eq': np.array(A_eq) if A_eq else None,
            'b_eq': np.array(b_eq) if b_eq else None,
            'A_ub': np.array(A_ub) if A_ub else None,
            'b_ub': np.array(b_ub) if b_ub else None,
            'bounds': bounds,
            'variables': self.variables,
            'n_vars': n_vars,
            'mode': mode
        }

        return model

    def solve(self, model: Dict) -> Dict:
        """
        Решение задачи линейного программирования

        Args:
            model: словарь с компонентами модели

        Returns:
            словарь с результатами решения
        """
        try:
            # Подготовка параметров для linprog
            kwargs = {
                'c': model['c'],
                'bounds': model['bounds'],
                'method': 'highs'
            }

            # Добавление ограничений, если они есть
            if model['A_eq'] is not None and model['b_eq'] is not None:
                kwargs['A_eq'] = model['A_eq']
                kwargs['b_eq'] = model['b_eq']

            if model['A_ub'] is not None and model['b_ub'] is not None:
                kwargs['A_ub'] = model['A_ub']
                kwargs['b_ub'] = model['b_ub']

            # Решение
            result = linprog(**kwargs)

            # Формирование результата
            solution = {
                'success': result.success,
                'message': result.message,
                'fun': result.fun if result.success else None,
                'x': result.x if result.success else None,
                'variables': model['variables'],
                'mode': model['mode'],
                'risk_limit': self.risk_limit,
                'duration_limit': self.duration_limit
            }

            # Если решение успешно, рассчитываем дополнительные показатели
            if result.success:
                solution.update(self._calculate_metrics(result.x, model['variables']))

            return solution

        except Exception as e:
            return {
                'success': False,
                'message': f"Ошибка при решении: {str(e)}",
                'fun': None,
                'x': None,
                'variables': model['variables'],
                'mode': model['mode']
            }

    def _calculate_metrics(self, x: np.ndarray, variables: List[Dict]) -> Dict:
        """
        Расчет дополнительных показателей по месяцам

        Args:
            x: оптимальные значения переменных
            variables: список переменных

        Returns:
            словарь с показателями
        """
        monthly_risk = []
        monthly_duration = []
        monthly_amount = []

        for month in range(1, 7):
            # Находим активные инвестиции в текущем месяце
            active_indices = []
            active_amounts = []
            active_risks = []
            active_durations = []

            for i, var in enumerate(variables):
                if var['start_month'] <= month < var['end_month'] and x[i] > 1e-6:
                    active_indices.append(i)
                    active_amounts.append(x[i])
                    active_risks.append(var['risk'])
                    active_durations.append(var['end_month'] - month)

            total_amount = sum(active_amounts)
            monthly_amount.append(total_amount)

            if total_amount > 1e-6:
                # Средневзвешенный риск
                weighted_risk = sum(a * r for a, r in zip(active_amounts, active_risks)) / total_amount
                monthly_risk.append(weighted_risk)

                # Средневзвешенный срок
                weighted_duration = sum(a * d for a, d in zip(active_amounts, active_durations)) / total_amount
                monthly_duration.append(weighted_duration)
            else:
                monthly_risk.append(0)
                monthly_duration.append(0)

        # Расчет распределения по инструментам
        allocation = {}
        for i, var in enumerate(variables):
            if x[i] > 1e-6:
                key = f"{var['name']}_{var['start_month']}"
                allocation[key] = {
                    'instrument': var['name'],
                    'start_month': var['start_month'],
                    'amount': x[i],
                    'income': x[i] * var['rate'],
                    'risk': var['risk']
                }

        return {
            'monthly_risk': monthly_risk,
            'monthly_duration': monthly_duration,
            'monthly_amount': monthly_amount,
            'allocation': allocation,
            'total_income': sum(v['income'] for v in allocation.values())
        }

    def check_constraints(self, solution: Dict) -> pd.DataFrame:
        """
        Проверка соблюдения ограничений

        Args:
            solution: словарь с результатами решения

        Returns:
            DataFrame с отчетом о соблюдении ограничений
        """
        if not solution['success']:
            return pd.DataFrame()

        months = list(range(1, 7))
        data = []

        for i, month in enumerate(months):
            risk_value = solution['monthly_risk'][i]
            duration_value = solution['monthly_duration'][i]

            risk_status = 'OK' if risk_value <= solution['risk_limit'] else 'Нарушение'
            duration_status = 'OK' if duration_value <= solution['duration_limit'] else 'Нарушение'

            data.append({
                'Месяц': month,
                'Риск факт': round(risk_value, 2),
                'Риск лимит': solution['risk_limit'],
                'Риск статус': risk_status,
                'Срок факт': round(duration_value, 2),
                'Срок лимит': solution['duration_limit'],
                'Срок статус': duration_status,
                'Сумма активов': round(solution['monthly_amount'][i], 2)
            })

        return pd.DataFrame(data)

    def get_allocation_dataframe(self, solution: Dict) -> pd.DataFrame:
        """
        Получение таблицы распределения инвестиций

        Args:
            solution: словарь с результатами решения

        Returns:
            DataFrame с распределением
        """
        if not solution['success']:
            return pd.DataFrame()

        data = []
        for key, alloc in solution['allocation'].items():
            data.append({
                'Инструмент': alloc['instrument'],
                'Месяц начала': alloc['start_month'],
                'Сумма (млн руб)': round(alloc['amount'], 2),
                'Доход (млн руб)': round(alloc['income'], 2),
                'Риск': alloc['risk']
            })

        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values(['Инструмент', 'Месяц начала'])

        return df