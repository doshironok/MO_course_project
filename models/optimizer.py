"""
Модуль оптимизатора инвестиционного портфеля
"""

import numpy as np
from scipy.optimize import linprog
import pandas as pd
from typing import Dict, List
import sys
import traceback


class InvestmentOptimizer:
    def __init__(self):
        self.variables = []
        self.var_names = []
        self.investments = None
        self.payments = None
        self.risk_limit = None
        self.duration_limit = None

    def _generate_variables(self, investments: List[Dict]) -> List[Dict]:
        """Генерация переменных"""
        variables = []
        self.var_names = []

        for inv in investments:
            for month in inv['start_months']:
                return_month = month + inv['duration']

                var_info = {
                    'name': inv['name'],
                    'start_month': month,
                    'duration': inv['duration'],
                    'rate': inv['rate'] / 100,
                    'risk': inv['risk'],
                    'return_month': return_month,
                }
                variables.append(var_info)
                self.var_names.append(f"{inv['name']}{month}")

        return variables

    def build_model(self, investments: List[Dict], payments: Dict,
                    risk_limit: float, duration_limit: float, mode: str = 'full') -> Dict:
        """Построение математической модели"""

        self.investments = investments
        self.payments = payments
        self.risk_limit = risk_limit
        self.duration_limit = duration_limit

        self.variables = self._generate_variables(investments)
        n_vars = len(self.variables)

        print("\n" + "=" * 80)
        print("СГЕНЕРИРОВАННЫЕ ПЕРЕМЕННЫЕ")
        print("=" * 80)
        for i, var in enumerate(self.variables):
            print(f"  {self.var_names[i]:4}: старт={var['start_month']}, "
                  f"возврат в начале мес.{var['return_month']}, "
                  f"ставка={var['rate'] * 100:.1f}%, риск={var['risk']}")

        # Целевая функция: минимизация суммы ВСЕХ инвестиций (а не только месяца 1)
        c = np.ones(n_vars)  # Все инвестиции имеют вес 1

        print(f"\nЦелевая функция: минимизировать сумму всех инвестиций")

        A_ub = []
        b_ub = []

        # 1. ПЛАТЕЖ В МЕСЯЦЕ 2
        row_payment2 = np.zeros(n_vars)
        for i, var in enumerate(self.variables):
            if var['return_month'] == 2:
                row_payment2[i] = (1 + var['rate'])

        A_ub.append(-row_payment2)
        b_ub.append(-payments[2])
        print(f"\nПлатеж месяц 2: инвестиции с return_month=2 ≥ {payments[2]:,} тыс. руб")

        # 2. ПЛАТЕЖ В МЕСЯЦЕ 6
        row_payment6 = np.zeros(n_vars)
        for i, var in enumerate(self.variables):
            if var['return_month'] == 6:
                row_payment6[i] = (1 + var['rate'])

        A_ub.append(-row_payment6)
        b_ub.append(-payments[6])
        print(f"Платеж месяц 6: инвестиции с return_month=6 ≥ {payments[6]:,} тыс. руб")

        # 3. БАЛАНСОВЫЕ ОГРАНИЧЕНИЯ - УБИРАЕМ ПОЛНОСТЬЮ!
        # Деньги могут просто лежать, не обязательно их реинвестировать

        # 4. ОГРАНИЧЕНИЯ ПО РИСКУ
        if mode in ['risk', 'full']:
            print("\n" + "=" * 80)
            print("ОГРАНИЧЕНИЯ ПО РИСКУ")
            print("=" * 80)

            for month in range(1, 7):
                row = np.zeros(n_vars)
                active_vars = []

                for i, var in enumerate(self.variables):
                    if var['start_month'] <= month < var['return_month']:
                        active_vars.append((i, var))

                if active_vars:
                    constraint_parts = []
                    for i, var in active_vars:
                        coef = var['risk'] - risk_limit
                        row[i] = coef
                        constraint_parts.append(f"{coef:+.1f}·{self.var_names[i]}")

                    A_ub.append(row)
                    b_ub.append(0)
                    print(f"Месяц {month}: {' '.join(constraint_parts)} ≤ 0")

        # 5. ОГРАНИЧЕНИЯ ПО СРОКУ ПОГАШЕНИЯ
        if mode == 'full':
            print("\n" + "=" * 80)
            print("ОГРАНИЧЕНИЯ ПО СРОКУ ПОГАШЕНИЯ")
            print("=" * 80)

            for month in range(1, 7):
                row = np.zeros(n_vars)
                active_vars = []

                for i, var in enumerate(self.variables):
                    if var['start_month'] <= month < var['return_month']:
                        active_vars.append((i, var))

                if active_vars:
                    constraint_parts = []
                    for i, var in active_vars:
                        remaining = var['return_month'] - month
                        coef = remaining - duration_limit
                        row[i] = coef
                        constraint_parts.append(f"{coef:+.1f}·{self.var_names[i]}")

                    A_ub.append(row)
                    b_ub.append(0)
                    print(f"Месяц {month}: {' '.join(constraint_parts)} ≤ 0")

        bounds = [(0, None) for _ in range(n_vars)]

        print(f"\nВсего ограничений: {len(A_ub)}")

        model = {
            'c': c,
            'A_ub': np.array(A_ub) if A_ub else None,
            'b_ub': np.array(b_ub) if b_ub else None,
            'bounds': bounds,
            'variables': self.variables,
            'var_names': self.var_names,
            'n_vars': n_vars,
            'mode': mode
        }

        return model

    def solve(self, model: Dict) -> Dict:
        """Решение задачи"""
        try:
            print("\n" + "=" * 80)
            print("РЕШЕНИЕ ЗАДАЧИ")
            print("=" * 80)

            print(f"model.keys() = {model.keys()}")
            print(f"model['c'] = {model['c']}")
            print(f"model['c'].shape = {model['c'].shape}")

            if model['A_ub'] is not None:
                print(f"model['A_ub'].shape = {model['A_ub'].shape}")
                print(f"model['b_ub'].shape = {model['b_ub'].shape}")

            kwargs = {
                'c': model['c'],
                'bounds': model['bounds'],
                'method': 'highs'
            }

            if model['A_ub'] is not None and model['b_ub'] is not None:
                kwargs['A_ub'] = model['A_ub']
                kwargs['b_ub'] = model['b_ub']
                print(f"Количество ограничений: {len(model['A_ub'])}")

            print("Вызов linprog...")
            sys.stdout.flush()

            result = linprog(**kwargs)

            print(f"linprog выполнен")
            print(f"result.success = {result.success}")
            print(f"result.message = {result.message}")
            sys.stdout.flush()

            solution = {
                'success': result.success,
                'message': result.message,
                'fun': result.fun if result.success else None,
                'x': result.x if result.success else None,
                'variables': model['variables'],
                'var_names': model['var_names'],
                'mode': model['mode'],
                'risk_limit': self.risk_limit,
                'duration_limit': self.duration_limit
            }

            if result.success:
                print("Решение успешно, рассчитываем метрики...")
                print(f"result.x = {result.x}")
                sys.stdout.flush()

                # РАСЧЕТ МЕТРИК - включаем обратно!
                metrics = self._calculate_metrics(result.x, model['variables'])
                solution.update(metrics)

                # Также добавим простую аллокацию для надежности
                if 'allocation' not in solution or not solution['allocation']:
                    solution['allocation'] = {}
                    solution['total_income'] = 0
                    for i, val in enumerate(result.x):
                        if val > 1e-3:
                            var = model['variables'][i]
                            key = f"{var['name']}{var['start_month']}"
                            solution['allocation'][key] = {
                                'instrument': var['name'],
                                'start_month': var['start_month'],
                                'amount': val,
                                'income': val * var['rate'],
                                'risk': var['risk']
                            }
                            solution['total_income'] += val * var['rate']

            print("Возвращаем решение")
            sys.stdout.flush()

            return solution

        except Exception as e:
            print(f"❌ ОШИБКА В SOLVE: {e}")
            traceback.print_exc()
            sys.stdout.flush()
            return {
                'success': False,
                'message': f"Ошибка: {str(e)}",
                'fun': None,
                'x': None,
                'variables': model['variables'] if model else [],
                'var_names': model['var_names'] if model else [],
                'mode': model['mode'] if model else 'unknown'
            }

    def get_allocation_dataframe(self, solution: Dict) -> pd.DataFrame:
        """Таблица распределения"""
        try:
            if not solution or not solution.get('success'):
                return pd.DataFrame()

            data = []
            allocation = solution.get('allocation', {})
            for key, alloc in allocation.items():
                data.append({
                    'Инструмент': alloc['instrument'],
                    'Месяц начала': alloc['start_month'],
                    'Сумма (тыс. руб)': f"{alloc['amount']:,.0f}",
                    'Сумма (млн руб)': f"{alloc['amount']/1000:,.2f}",
                    'Доход (тыс. руб)': f"{alloc['income']:,.0f}",
                    'Доход (млн руб)': f"{alloc['income']/1000:,.2f}",
                    'Риск': alloc['risk']
                })

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка в get_allocation_dataframe: {e}")
            return pd.DataFrame()

    def check_constraints(self, solution: Dict) -> pd.DataFrame:
        """Проверка ограничений"""
        try:
            if not solution or not solution.get('success'):
                return pd.DataFrame()

            months = list(range(1, 7))
            data = []

            monthly_risk = solution.get('monthly_risk', [0]*6)
            monthly_duration = solution.get('monthly_duration', [0]*6)
            monthly_amount = solution.get('monthly_amount', [0]*6)

            for i, month in enumerate(months):
                risk_value = monthly_risk[i] if i < len(monthly_risk) else 0
                duration_value = monthly_duration[i] if i < len(monthly_duration) else 0
                amount = monthly_amount[i] / 1000 if i < len(monthly_amount) else 0

                risk_status = 'OK' if risk_value <= solution.get('risk_limit', 6) + 1e-6 else 'НАРУШЕНИЕ'
                duration_status = 'OK' if duration_value <= solution.get('duration_limit', 2.5) + 1e-6 else 'НАРУШЕНИЕ'

                data.append({
                    'Месяц': month,
                    'Риск факт': round(risk_value, 2),
                    'Риск лимит': solution.get('risk_limit', 6),
                    'Риск статус': risk_status,
                    'Срок факт': round(duration_value, 2),
                    'Срок лимит': solution.get('duration_limit', 2.5),
                    'Срок статус': duration_status,
                    'Активы (млн руб)': round(amount, 2)
                })

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка в check_constraints: {e}")
            return pd.DataFrame()

    def _calculate_metrics(self, x: np.ndarray, variables: List[Dict]) -> Dict:
        """Расчет метрик по месяцам"""
        monthly_risk = []
        monthly_duration = []
        monthly_amount = []

        print("\n" + "=" * 80)
        print("РАСЧЕТ МЕТРИК ПО МЕСЯЦАМ")
        print("=" * 80)

        for month in range(1, 7):
            active_amounts = []
            active_risks = []
            active_durations = []
            active_names = []

            for i, var in enumerate(variables):
                if var['start_month'] <= month < var['return_month'] and x[i] > 1e-3:
                    active_amounts.append(x[i])
                    active_risks.append(var['risk'])
                    active_durations.append(var['return_month'] - month)
                    active_names.append(f"{var['name']}{var['start_month']}")

            total = sum(active_amounts)
            monthly_amount.append(total)

            if total > 1e-3:
                weighted_risk = sum(a * r for a, r in zip(active_amounts, active_risks)) / total
                monthly_risk.append(weighted_risk)
                weighted_duration = sum(a * d for a, d in zip(active_amounts, active_durations)) / total
                monthly_duration.append(weighted_duration)

                print(f"Месяц {month}: активны {', '.join(active_names)}")
                print(f"  сумма = {total / 1000:.2f} млн руб")
                print(f"  риск = {weighted_risk:.2f}")
                print(f"  срок = {weighted_duration:.2f}")
            else:
                monthly_risk.append(0)
                monthly_duration.append(0)
                print(f"Месяц {month}: нет активных инвестиций")

        return {
            'monthly_risk': monthly_risk,
            'monthly_duration': monthly_duration,
            'monthly_amount': monthly_amount
        }

    def solve_basic(self, model_template: Dict) -> Dict:
        """Найти оптимальное решение для basic режима"""

        import copy
        solutions = []

        print("\n" + "=" * 80)
        print("ПОИСК ОПТИМАЛЬНОГО ПУТИ ДЛЯ BASIC РЕЖИМА")
        print("=" * 80)

        # Для каждого пути создаем свою целевую функцию

        # ПУТЬ 1: Только A (A1 + A5)
        print("\n🔍 Пробуем путь A1 → A5...")
        model1 = copy.deepcopy(model_template)

        # МЕНЯЕМ целевую функцию: минимизируем только начальные инвестиции
        c1 = np.zeros(len(model1['variables']))
        for i, var in enumerate(model1['variables']):
            if var['start_month'] == 1:  # только инвестиции в месяц 1
                c1[i] = 1.0
        model1['c'] = c1

        # Запрещаем B, C, O
        for i, var in enumerate(model1['variables']):
            if var['name'] in ['B', 'C', 'O']:
                model1['bounds'][i] = (0, 0)
            if var['name'] == 'A' and var['start_month'] not in [1, 5]:
                model1['bounds'][i] = (0, 0)

        sol1 = self.solve(model1)
        if sol1['success']:
            # Считаем только начальные инвестиции
            initial = sum(sol1['x'][i] for i, var in enumerate(model1['variables'])
                          if var['start_month'] == 1 and sol1['x'][i] > 1e-3)
            sol1['path'] = 'A1 → A5'
            sol1['initial'] = initial
            solutions.append(sol1)
            print(f"  ✅ Найдено: {initial:,.2f} тыс. руб")

        # ПУТЬ 2: B путь (B1 → B3 → A5)
        print("\n🔍 Пробуем путь B1 → B3 → A5...")
        model2 = copy.deepcopy(model_template)

        # МЕНЯЕМ целевую функцию
        c2 = np.zeros(len(model2['variables']))
        for i, var in enumerate(model2['variables']):
            if var['start_month'] == 1:
                c2[i] = 1.0
        model2['c'] = c2

        # Запрещаем лишнее
        for i, var in enumerate(model2['variables']):
            if var['name'] in ['C', 'O']:
                model2['bounds'][i] = (0, 0)
            if var['name'] == 'A' and var['start_month'] == 1:
                model2['bounds'][i] = (0, 0)
            if var['name'] == 'A' and var['start_month'] not in [5]:
                model2['bounds'][i] = (0, 0)
            if var['name'] == 'B' and var['start_month'] not in [1, 3]:
                model2['bounds'][i] = (0, 0)

        sol2 = self.solve(model2)
        if sol2['success']:
            initial = sum(sol2['x'][i] for i, var in enumerate(model2['variables'])
                          if var['start_month'] == 1 and sol2['x'][i] > 1e-3)
            sol2['path'] = 'B1 → B3 → A5'
            sol2['initial'] = initial
            solutions.append(sol2)
            print(f"  ✅ Найдено: {initial:,.2f} тыс. руб")

        # ПУТЬ 3: C путь (C1 → A4 → A5)
        print("\n🔍 Пробуем путь C1 → A4 → A5...")
        model3 = copy.deepcopy(model_template)

        # МЕНЯЕМ целевую функцию
        c3 = np.zeros(len(model3['variables']))
        for i, var in enumerate(model3['variables']):
            if var['start_month'] == 1:
                c3[i] = 1.0
        model3['c'] = c3

        # Запрещаем лишнее
        for i, var in enumerate(model3['variables']):
            if var['name'] in ['B', 'O']:
                model3['bounds'][i] = (0, 0)
            if var['name'] == 'A' and var['start_month'] == 1:
                model3['bounds'][i] = (0, 0)
            if var['name'] == 'A' and var['start_month'] not in [4, 5]:
                model3['bounds'][i] = (0, 0)
            if var['name'] == 'C' and var['start_month'] != 1:
                model3['bounds'][i] = (0, 0)

        sol3 = self.solve(model3)
        if sol3['success']:
            initial = sum(sol3['x'][i] for i, var in enumerate(model3['variables'])
                          if var['start_month'] == 1 and sol3['x'][i] > 1e-3)
            sol3['path'] = 'C1 → A4 → A5'
            sol3['initial'] = initial
            solutions.append(sol3)
            print(f"  ✅ Найдено: {initial:,.2f} тыс. руб")

        # Выбираем лучшее
        if solutions:
            best = min(solutions, key=lambda s: s['initial'])
            print("\n" + "=" * 80)
            print(f"✅ ВЫБРАН ОПТИМАЛЬНЫЙ ПУТЬ: {best['path']}")
            print(f"   Начальные инвестиции: {best['initial']:,.2f} тыс. руб")
            print("=" * 80)
            return best

        return {'success': False, 'message': 'Нет решений'}