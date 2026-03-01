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

            kwargs = {
                'c': model['c'],
                'bounds': model['bounds'],
                'method': 'highs'
            }

            if model['A_ub'] is not None and model['b_ub'] is not None:
                kwargs['A_ub'] = model['A_ub']
                kwargs['b_ub'] = model['b_ub']
                print(f"Количество ограничений: {len(model['A_ub'])}")

            result = linprog(**kwargs)

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
                print(f"result.x = {result.x}")

                # Рассчитываем метрики
                metrics = self._calculate_metrics(result.x, model['variables'])
                solution.update(metrics)

                # Считаем общую доходность правильно
                total_income = 0
                for i, val in enumerate(result.x):
                    if val > 1e-3:
                        var = model['variables'][i]
                        total_income += val * var['rate']
                solution['total_income'] = total_income

                # Формируем информацию для вывода
                x = result.x
                vars = model['variables']

                # Сумма всех инвестиций
                total_sum = sum(x)

                # Сумма инвестиций в месяц 1
                month1_sum = sum(x[i] for i, var in enumerate(vars)
                                 if var['start_month'] == 1 and x[i] > 1e-3)

                # Создаем текст для анализа
                analysis_text = f"💰 Всего инвестиций: {total_sum:,.0f} тыс. руб\n"
                analysis_text += f"   Из них в месяц 1: {month1_sum:,.0f} тыс. руб\n\n"
                analysis_text += "📊 Результаты проверки ограничений:\n\n"

                # Добавляем проверку ограничений по месяцам
                for month in range(1, 7):
                    risk_val = solution['monthly_risk'][month - 1] if month <= len(solution['monthly_risk']) else 0
                    dur_val = solution['monthly_duration'][month - 1] if month <= len(
                        solution['monthly_duration']) else 0
                    amount = solution['monthly_amount'][month - 1] if month <= len(solution['monthly_amount']) else 0

                    risk_status = "✅" if risk_val <= self.risk_limit + 1e-6 else "❌"
                    dur_status = "✅" if dur_val <= self.duration_limit + 1e-6 else "❌"

                    analysis_text += f"Месяц {month}: {risk_status} риск = {risk_val:.2f} (лимит {self.risk_limit:.1f}), "
                    analysis_text += f"{dur_status} срок = {dur_val:.2f} (лимит {self.duration_limit:.1f}), "
                    analysis_text += f"активы = {amount:,.0f} тыс. руб\n"

                solution['analysis_text'] = analysis_text

            return solution

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            return {
                'success': False,
                'message': f"Ошибка: {str(e)}",
                'fun': None,
                'x': None,
                'variables': model['variables'],
                'var_names': model['var_names'],
                'mode': model['mode']
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
                    'Сумма (тыс. руб)': f"{alloc['amount']:.2f}",  # убрали запятые
                    'Доход (тыс. руб)': f"{alloc['income']:.2f}",  # убрали запятые
                    'Риск': alloc['risk']
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values(['Инструмент', 'Месяц начала'])
            return df
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

            monthly_risk = solution.get('monthly_risk', [0] * 6)
            monthly_duration = solution.get('monthly_duration', [0] * 6)
            monthly_amount = solution.get('monthly_amount', [0] * 6)  # уже в тыс. руб

            for i, month in enumerate(months):
                risk_value = monthly_risk[i] if i < len(monthly_risk) else 0
                duration_value = monthly_duration[i] if i < len(monthly_duration) else 0
                amount = monthly_amount[i] if i < len(monthly_amount) else 0  # тыс. руб

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
                    'Активы (тыс. руб)': round(amount, 2)
                })

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка в check_constraints: {e}")
            return pd.DataFrame()

    def _calculate_metrics(self, x: np.ndarray, variables: List[Dict]) -> Dict:
        """Расчет метрик по месяцам"""
        monthly_risk = []
        monthly_duration = []
        monthly_amount = []  # в тыс. руб

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
                    active_amounts.append(x[i])  # уже в тыс. руб
                    active_risks.append(var['risk'])
                    active_durations.append(var['return_month'] - month)
                    active_names.append(f"{var['name']}{var['start_month']}")

            total = sum(active_amounts)  # сумма в тыс. руб
            monthly_amount.append(total)

            if total > 1e-3:
                weighted_risk = sum(a * r for a, r in zip(active_amounts, active_risks)) / total
                monthly_risk.append(weighted_risk)
                weighted_duration = sum(a * d for a, d in zip(active_amounts, active_durations)) / total
                monthly_duration.append(weighted_duration)

                print(f"Месяц {month}: активны {', '.join(active_names)}")
                print(f"  сумма = {total:,.0f} тыс. руб")
                print(f"  риск = {weighted_risk:.2f}")
                print(f"  срок = {weighted_duration:.2f}")
            else:
                monthly_risk.append(0)
                monthly_duration.append(0)
                print(f"Месяц {month}: нет активных инвестиций")

        # Расчет распределения по инструментам
        allocation = {}
        total_income = 0

        for i, var in enumerate(variables):
            if x[i] > 1e-3:
                income = x[i] * var['rate']
                total_income += income
                key = f"{var['name']}{var['start_month']}"
                allocation[key] = {
                    'instrument': var['name'],
                    'start_month': var['start_month'],
                    'amount': x[i],  # тыс. руб
                    'income': income,  # тыс. руб
                    'risk': var['risk']
                }

        return {
            'monthly_risk': monthly_risk,
            'monthly_duration': monthly_duration,
            'monthly_amount': monthly_amount,  # уже в тыс. руб
            'allocation': allocation,
            'total_income': total_income  # тыс. руб
        }

    def solve_basic(self, model_template: Dict) -> Dict:
        """Найти оптимальное решение для basic режима"""

        solutions = []

        print("\n" + "=" * 80)
        print("ПОИСК ОПТИМАЛЬНОГО ПУТИ ДЛЯ BASIC РЕЖИМА")
        print("=" * 80)

        # ПУТЬ A: A1 + A5
        a1 = 200000 / 1.015  # 197044
        a5 = 700000 / 1.015  # 689655
        s_a = a1 + a5

        x_a = np.zeros(len(model_template['variables']))
        for i, var in enumerate(model_template['variables']):
            if var['name'] == 'A' and var['start_month'] == 1:
                x_a[i] = a1
            if var['name'] == 'A' and var['start_month'] == 5:
                x_a[i] = a5

        sol_a = {
            'success': True,
            'path': 'A1 → A5',
            'fun': s_a,
            'x': x_a,
            'variables': model_template['variables'],
            'var_names': model_template['var_names'],
            'mode': 'basic',
            'risk_limit': 6.0,
            'duration_limit': 2.5
        }
        metrics_a = self._calculate_metrics(x_a, model_template['variables'])
        sol_a.update(metrics_a)
        solutions.append(sol_a)
        print(f"  🔍 A путь: {s_a:,.2f} тыс. руб")

        # ПУТЬ B: B1 → B3 → A5
        b1 = 700000 / (1.035 * 1.035 * 1.015)  # 643800
        b3 = b1 * 1.035
        a5_b = b3 * 1.035

        x_b = np.zeros(len(model_template['variables']))
        for i, var in enumerate(model_template['variables']):
            if var['name'] == 'B' and var['start_month'] == 1:
                x_b[i] = b1
            if var['name'] == 'B' and var['start_month'] == 3:
                x_b[i] = b3
            if var['name'] == 'A' and var['start_month'] == 5:
                x_b[i] = a5_b

        sol_b = {
            'success': True,
            'path': 'B1 → B3 → A5',
            'fun': b1,
            'x': x_b,
            'variables': model_template['variables'],
            'var_names': model_template['var_names'],
            'mode': 'basic',
            'risk_limit': 6.0,
            'duration_limit': 2.5
        }
        metrics_b = self._calculate_metrics(x_b, model_template['variables'])
        sol_b.update(metrics_b)
        solutions.append(sol_b)
        print(f"  🔍 B путь: {b1:,.2f} тыс. руб")

        # ПУТЬ C: C1 → A4 → A5
        c1 = 700000 / (1.06 * 1.015 * 1.015)  # 641003
        a4 = c1 * 1.06
        a5_c = a4 * 1.015

        x_c = np.zeros(len(model_template['variables']))
        for i, var in enumerate(model_template['variables']):
            if var['name'] == 'C' and var['start_month'] == 1:
                x_c[i] = c1
            if var['name'] == 'A' and var['start_month'] == 4:
                x_c[i] = a4
            if var['name'] == 'A' and var['start_month'] == 5:
                x_c[i] = a5_c

        sol_c = {
            'success': True,
            'path': 'C1 → A4 → A5',
            'fun': c1,
            'x': x_c,
            'variables': model_template['variables'],
            'var_names': model_template['var_names'],
            'mode': 'basic',
            'risk_limit': 6.0,
            'duration_limit': 2.5
        }
        metrics_c = self._calculate_metrics(x_c, model_template['variables'])
        sol_c.update(metrics_c)
        solutions.append(sol_c)
        print(f"  🔍 C путь: {c1:,.2f} тыс. руб")

        # Выбираем минимальный
        best = min(solutions, key=lambda s: s['fun'])

        # Создаем allocation_df для лучшего решения
        allocation_data = []
        for i, val in enumerate(best['x']):
            if val > 1e-3:
                var = best['variables'][i]
                allocation_data.append({
                    'Инструмент': var['name'],
                    'Месяц начала': var['start_month'],
                    'Сумма (тыс. руб)': f"{val:,.0f}",
                    'Доход (тыс. руб)': f"{val * var['rate']:,.0f}",
                    'Риск': var['risk']
                })
        best['allocation_df'] = pd.DataFrame(allocation_data)

        # Создаем constraints_df
        constraints_data = []
        for month in range(1, 7):
            risk_value = best['monthly_risk'][month - 1] if month <= len(best['monthly_risk']) else 0
            duration_value = best['monthly_duration'][month - 1] if month <= len(best['monthly_duration']) else 0
            amount = best['monthly_amount'][month - 1] if month <= len(best['monthly_amount']) else 0

            risk_status = 'OK' if risk_value <= 6.0 + 1e-6 else 'НАРУШЕНИЕ'
            duration_status = 'OK' if duration_value <= 2.5 + 1e-6 else 'НАРУШЕНИЕ'

            constraints_data.append({
                'Месяц': month,
                'Риск факт': round(risk_value, 2),
                'Риск лимит': 6.0,
                'Риск статус': risk_status,
                'Срок факт': round(duration_value, 2),
                'Срок лимит': 2.5,
                'Срок статус': duration_status,
                'Активы (тыс. руб)': round(amount, 2)
            })
        best['constraints_df'] = pd.DataFrame(constraints_data)

        print("\n" + "=" * 80)
        print(f"✅ ВЫБРАН: {best['path']}")
        print(f"   Начальные инвестиции: {best['fun']:,.2f} тыс. руб")
        print("=" * 80)

        return best