"""
Модуль оптимизатора инвестиционного портфеля
Использование симплекс-метода (линейное программирование)
"""

import numpy as np
from scipy.optimize import linprog
import pandas as pd
from typing import Dict, List, Tuple
import traceback


class InvestmentOptimizer:
    def __init__(self):
        self.variables = []
        self.var_names = []
        self.investments = None
        self.payments = None
        self.risk_limit = None
        self.duration_limit = None
        self.simplex_iterations = []  # для хранения истории итераций

    def _log_iteration(self, iteration: int, phase: int, tableau: np.ndarray,
                       basis: List, entering: str, leaving: str, pivot: tuple,
                       objective_value: float = None):
        """Логирование итерации симплекс-метода"""
        self.simplex_iterations.append({
            'phase': phase,
            'iteration': iteration,
            'tableau': tableau.copy() if tableau is not None else None,
            'basis': basis.copy() if basis else [],
            'entering': entering,
            'leaving': leaving,
            'pivot': pivot,
            'objective_value': objective_value
        })

    def _generate_variables(self, investments: List[Dict]) -> List[Dict]:
        """Генерация всех возможных инвестиций с корректным временем возврата"""
        variables = []
        self.var_names = []

        for inv in investments:
            for month in inv['start_months']:
                # Возврат в начале месяца month + duration
                return_month = month + inv['duration']

                # Инвестиция имеет смысл если возврат не позже месяца 7
                # (платеж в конце месяца 6 требует средств в начале месяца 7)
                if return_month <= 7:
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

    def build_simplex_model(self, investments: List[Dict], payments: Dict,
                            risk_limit: float, duration_limit: float, mode: str) -> Dict:
        """
        Построение модели линейного программирования
        """

        print("\n" + "=" * 80)
        print("ПОСТРОЕНИЕ МОДЕЛИ ЛИНЕЙНОГО ПРОГРАММИРОВАНИЯ")
        print(f"Режим: {mode.upper()}")
        print("=" * 80)

        # Преобразуем платежи: платёж в конце месяца t -> потребность в начале t+1
        adjusted_payments = {}
        for month_end, amount in payments.items():
            adjusted_payments[month_end + 1] = amount

        # Генерируем все возможные инвестиции
        variables = self._generate_variables(investments)
        n_invest_vars = len(variables)

        print(f"\nСгенерированные инвестиции:")
        for i, var in enumerate(variables):
            print(f"  {self.var_names[i]}: старт м{var['start_month']} -> возврат м{var['return_month']}, "
                  f"ставка {var['rate'] * 100:.1f}%, риск {var['risk']}")

        # Переменные:
        # 1. Инвестиции x_i (n_invest_vars)
        # 2. Начальный фонд F (1)
        # 3. Остатки b_1..b_8 (8) — b_t = остаток на начало месяца t ДО инвестиций
        n_balance_vars = 8
        total_vars = n_invest_vars + 1 + n_balance_vars

        print(f"\nВсего переменных: {total_vars}")
        print(f"  Инвестиции: {n_invest_vars}")
        print(f"  Начальный фонд F: 1")
        print(f"  Балансовые b_1..b_8: {n_balance_vars}")

        # Целевая функция: минимизация F
        c = np.zeros(total_vars)
        c[n_invest_vars] = 1  # F

        # ============ ОГРАНИЧЕНИЯ ============
        A_eq = []
        b_eq = []
        A_ub = []
        b_ub = []

        # 1. F = b_1 (начальный фонд равен остатку в начале месяца 1)
        row_start = np.zeros(total_vars)
        row_start[n_invest_vars] = 1  # F
        row_start[n_invest_vars + 1] = -1  # -b_1
        A_eq.append(row_start)
        b_eq.append(0)
        print("\nОграничение 1: F = b_1")

        # 2. Балансовые ограничения для месяцев 1..7
        # b_t + возвраты_t = платеж_t + инвестиции_t + b_{t+1}

        print("\nБалансовые ограничения:")
        for t in range(1, 8):
            row = np.zeros(total_vars)

            # b_t (приход)
            row[n_invest_vars + t] = 1

            # Возвраты от инвестиций (приход)
            for i, var in enumerate(variables):
                if var['return_month'] == t:
                    row[i] = (1 + var['rate'])

            # Инвестиции в начале месяца t (расход)
            for i, var in enumerate(variables):
                if var['start_month'] == t:
                    row[i] -= 1

            # b_{t+1} (расход — остаток на следующий месяц)
            if t < 8:
                row[n_invest_vars + t + 1] = -1

            # Платеж
            payment = adjusted_payments.get(t, 0)

            A_eq.append(row)
            b_eq.append(payment)

            if payment > 0:
                print(f"  Мес{t}: b_{t} + возвраты = {payment} + инвестиции_{t} + b_{t + 1}")
            else:
                print(f"  Мес{t}: b_{t} + возвраты = инвестиции_{t} + b_{t + 1}")

        # 3. Ограничения по риску
        if mode in ['risk', 'full']:
            print("\nОГРАНИЧЕНИЯ ПО РИСКУ (средний взвешенный риск ≤ лимит)")

            for month in range(1, 8):
                row = np.zeros(total_vars)
                has_active = False

                for i, var in enumerate(variables):
                    if var['start_month'] <= month < var['return_month']:
                        row[i] = var['risk'] - risk_limit
                        has_active = True

                if has_active:
                    A_ub.append(row)
                    b_ub.append(0)
                    print(f"  Месяц {month}: Σ (risk_i - {risk_limit})·x_i ≤ 0")

        # 4. Ограничения по сроку погашения
        if mode == 'full':
            print("\nОГРАНИЧЕНИЯ ПО СРОКУ (средний оставшийся срок ≤ лимит)")

            for month in range(1, 8):
                row = np.zeros(total_vars)
                has_active = False

                for i, var in enumerate(variables):
                    if var['start_month'] <= month < var['return_month']:
                        remaining = var['return_month'] - month
                        row[i] = remaining - duration_limit
                        has_active = True

                if has_active:
                    A_ub.append(row)
                    b_ub.append(0)
                    print(f"  Месяц {month}: Σ (remaining_i - {duration_limit})·x_i ≤ 0")

        # 5. Все переменные неотрицательны
        bounds = [(0, None) for _ in range(total_vars)]

        print(f"\nВсего ограничений:")
        print(f"  Равенств: {len(A_eq)}")
        print(f"  Неравенств: {len(A_ub)}")

        model = {
            'c': c,
            'A_eq': np.array(A_eq) if A_eq else None,
            'b_eq': np.array(b_eq) if b_eq else None,
            'A_ub': np.array(A_ub) if A_ub else None,
            'b_ub': np.array(b_ub) if b_ub else None,
            'bounds': bounds,
            'variables': variables,
            'var_names': self.var_names,
            'n_invest_vars': n_invest_vars,
            'n_balance_vars': n_balance_vars,
            'mode': mode,
            'risk_limit': risk_limit,
            'duration_limit': duration_limit,
            'adjusted_payments': adjusted_payments
        }

        return model

    def _convert_to_standard_form(self, model: Dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Преобразование модели в стандартную форму для симплекс-метода:
        минимизация c^T x при ограничениях A x = b, x >= 0
        """
        # Собираем все ограничения
        A_list = []
        b_list = []

        # Ограничения-равенства
        if model['A_eq'] is not None:
            A_list.append(model['A_eq'])
            b_list.append(model['b_eq'])

        # Ограничения-неравенства (преобразуем в равенства добавлением slack-переменных)
        n_slack = 0
        if model['A_ub'] is not None:
            n_slack = model['A_ub'].shape[0]
            # Добавляем slack-переменные с коэффициентом 1
            A_ub_aug = np.hstack([model['A_ub'], np.eye(n_slack)])
            A_list.append(A_ub_aug)
            b_list.append(model['b_ub'])
        else:
            A_ub_aug = None

        # Объединяем все ограничения
        if len(A_list) > 1:
            # Добавляем нулевые столбцы для slack-переменных к A_eq
            if model['A_eq'] is not None:
                A_eq_aug = np.hstack([model['A_eq'], np.zeros((model['A_eq'].shape[0], n_slack))])
            else:
                A_eq_aug = None

            # Объединяем
            if A_eq_aug is not None and A_ub_aug is not None:
                A = np.vstack([A_eq_aug, A_ub_aug])
            elif A_eq_aug is not None:
                A = A_eq_aug
            else:
                A = A_ub_aug
            b = np.concatenate(b_list)
        elif len(A_list) == 1:
            A = A_list[0]
            b = b_list[0]
        else:
            A = np.array([])
            b = np.array([])

        # Целевая функция
        c_orig = model['c']
        if n_slack > 0:
            c = np.hstack([c_orig, np.zeros(n_slack)])
        else:
            c = c_orig

        return c, A, b, n_slack

    def _build_initial_tableau(self, c: np.ndarray, A: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, List[int], int]:
        """
        Построение начальной симплекс-таблицы с искусственными переменными (Фаза 1)
        """
        m, n = A.shape  # m - число ограничений, n - число исходных переменных

        # Добавляем искусственные переменные для каждого ограничения
        A_aug = np.hstack([A, np.eye(m)])

        # Целевая функция для Фазы 1: минимизация суммы искусственных переменных
        c_phase1 = np.hstack([np.zeros(n), np.ones(m)])

        # Начальный базис - искусственные переменные
        basis = list(range(n, n + m))

        # Построение таблицы
        tableau = np.zeros((m + 1, n + m + 1))
        tableau[:m, :n+m] = A_aug
        tableau[:m, -1] = b

        # Строка целевой функции Фазы 1
        tableau[-1, :n+m] = -c_phase1
        for i in range(m):
            tableau[-1, :] += tableau[i, :]

        return tableau, basis, m

    def _find_pivot(self, tableau: np.ndarray, phase: int) -> Tuple[int, int]:
        """
        Поиск ведущего элемента для симплекс-преобразования

        Returns:
            (row, col) - индексы ведущего элемента
        """
        m, n = tableau.shape
        n_vars = n - 1  # без RHS

        # Выбор ведущего столбца
        if phase == 1:
            # Фаза 1: ищем наибольший положительный коэффициент в строке W
            reduced_costs = tableau[-1, :-1]
            entering = np.argmax(reduced_costs)
            if reduced_costs[entering] <= 1e-10:
                return -1, -1  # оптимальное решение фазы 1
        else:
            # Фаза 2: ищем наименьший отрицательный коэффициент в строке Z
            reduced_costs = tableau[-1, :-1]
            entering = np.argmin(reduced_costs)
            if reduced_costs[entering] >= -1e-10:
                return -1, -1  # оптимальное решение фазы 2

        # Выбор ведущей строки (минимальное отношение RHS / коэффициент)
        ratios = []
        for i in range(m - 1):  # исключаем строку целевой функции
            if tableau[i, entering] > 1e-10:
                ratios.append(tableau[i, -1] / tableau[i, entering])
            else:
                ratios.append(np.inf)

        if all(np.isinf(ratios)):
            return -2, -2  # неограниченное решение

        leaving = np.argmin(ratios)

        return leaving, entering

    def _pivot_tableau(self, tableau: np.ndarray, pivot_row: int, pivot_col: int) -> np.ndarray:
        """
        Выполнение жорданова исключения (pivot operation)
        """
        pivot_value = tableau[pivot_row, pivot_col]

        # Делим ведущую строку на ведущий элемент
        tableau[pivot_row, :] /= pivot_value

        # Обнуляем остальные элементы в ведущем столбце
        for i in range(tableau.shape[0]):
            if i != pivot_row:
                tableau[i, :] -= tableau[i, pivot_col] * tableau[pivot_row, :]

        return tableau

    def _extract_solution_from_tableau(self, tableau: np.ndarray, basis: List[int],
                                        n_orig_vars: int, model: Dict) -> Dict:
        """
        Извлечение решения из финальной симплекс-таблицы
        """
        m = tableau.shape[0] - 1
        n = tableau.shape[1] - 1

        # Вектор решения
        x_full = np.zeros(n)
        for i in range(m):
            if basis[i] < n:
                x_full[basis[i]] = tableau[i, -1]

        # Извлекаем только исходные переменные
        x_orig = x_full[:n_orig_vars]
        x_invest = x_orig[:model['n_invest_vars']]
        initial_fund = x_orig[model['n_invest_vars']] if model['n_invest_vars'] < len(x_orig) else 0
        balances = x_orig[model['n_invest_vars'] + 1:model['n_invest_vars'] + 9]

        # Оптимальное значение целевой функции
        optimal_value = tableau[-1, -1]

        # Расчёт метрик
        metrics = self._calculate_metrics(x_invest, model['variables'])

        solution = {
            'success': True,
            'message': 'Оптимальное решение найдено симплекс-методом',
            'fun': initial_fund,
            'fun_thousand': initial_fund * 1000,
            'x': x_invest,
            'initial_fund': initial_fund,
            'balances': balances,
            'variables': model['variables'],
            'var_names': model['var_names'],
            'mode': model['mode'],
            'risk_limit': model['risk_limit'],
            'duration_limit': model['duration_limit'],
            **metrics
        }

        analysis_text = self._generate_analysis_text(solution)
        solution['analysis_text'] = analysis_text

        return solution

    def solve_simplex(self, model: Dict) -> Dict:
        """
        Решение задачи симплекс-методом с полным логированием итераций
        """
        self.simplex_iterations = []  # очищаем историю

        try:
            print("\n" + "=" * 80)
            print("РЕШЕНИЕ ЗАДАЧИ СИМПЛЕКС-МЕТОДОМ")
            print(f"Режим: {model['mode'].upper()}")
            print("=" * 80)

            # Преобразуем в стандартную форму
            c, A, b, n_slack = self._convert_to_standard_form(model)
            n_orig_vars = len(model['c'])

            print(f"\nСтандартная форма:")
            print(f"  Исходных переменных: {n_orig_vars}")
            print(f"  Slack-переменных: {n_slack}")
            print(f"  Всего переменных: {len(c)}")
            print(f"  Ограничений: {A.shape[0]}")

            # ========== ФАЗА 1: Поиск допустимого базиса ==========
            print("\n" + "=" * 60)
            print("ФАЗА 1: Поиск допустимого базиса")
            print("=" * 60)
            print("Вводим искусственные переменные a₁, a₂, ...")
            print("Цель: минимизировать W = Σ aᵢ → 0\n")

            tableau, basis, n_artificial = self._build_initial_tableau(c, A, b)
            m = tableau.shape[0] - 1

            # Логируем начальную таблицу
            self._log_iteration(0, 1, tableau,
                               [f"a{i+1}" for i in range(m)],
                               "", "", (0, 0),
                               self._calculate_phase1_objective(tableau))

            iteration = 0
            while True:
                iteration += 1
                pivot_row, pivot_col = self._find_pivot(tableau, 1)

                if pivot_row == -1 and pivot_col == -1:
                    print(f"\n✅ Фаза 1 завершена на итерации {iteration}")
                    print("   Допустимый базис найден!")
                    break
                elif pivot_row == -2:
                    print("\n❌ Задача не имеет допустимых решений")
                    return {'success': False, 'message': 'Нет допустимых решений',
                           'simplex_iterations': self.simplex_iterations}

                # Определяем имена переменных
                entering_name = self._get_variable_name(pivot_col, n_orig_vars, n_slack, m)
                leaving_name = self._get_variable_name(basis[pivot_row], n_orig_vars, n_slack, m)

                print(f"\nИтерация {iteration}:")
                print(f"  Вводим: {entering_name}")
                print(f"  Выводим: {leaving_name}")
                print(f"  Ведущий элемент: [{pivot_row}, {pivot_col}] = {tableau[pivot_row, pivot_col]:.4f}")

                # Выполняем жорданово исключение
                tableau = self._pivot_tableau(tableau, pivot_row, pivot_col)
                basis[pivot_row] = pivot_col

                # Логируем итерацию
                self._log_iteration(iteration, 1, tableau,
                                   [self._get_variable_name(b, n_orig_vars, n_slack, m) for b in basis],
                                   entering_name, leaving_name,
                                   (pivot_row, pivot_col),
                                   self._calculate_phase1_objective(tableau))

                # Выводим базис
                print(f"  Новый базис: {', '.join([self._get_variable_name(b, n_orig_vars, n_slack, m) for b in basis])}")
                print(f"  W = {tableau[-1, -1]:.4f}")

            # Проверяем, что все искусственные переменные выведены
            w_value = tableau[-1, -1]
            if abs(w_value) > 1e-8:
                print(f"\n❌ Фаза 1: W = {w_value:.6f} > 0")
                print("   Допустимого решения не существует")
                return {'success': False, 'message': 'Допустимого решения не существует',
                       'simplex_iterations': self.simplex_iterations}

            # ========== ФАЗА 2: Оптимизация ==========
            print("\n" + "=" * 60)
            print("ФАЗА 2: Оптимизация целевой функции")
            print("=" * 60)
            print("Удаляем искусственные переменные")
            print("Восстанавливаем исходную целевую функцию: min F\n")

            # Удаляем искусственные переменные из таблицы
            tableau = np.delete(tableau, np.s_[n_orig_vars + n_slack:n_orig_vars + n_slack + n_artificial], axis=1)
            n_total = n_orig_vars + n_slack

            # Корректируем базис
            basis = [b for b in basis if b < n_total]

            # Заменяем строку целевой функции на исходную
            tableau[-1, :] = 0
            # Для минимизации F коэффициенты c
            for j in range(n_orig_vars):
                tableau[-1, j] = model['c'][j]  # c_j (без минуса для минимизации)

            # Корректируем для текущего базиса
            for i in range(len(basis)):
                if basis[i] < n_orig_vars:
                    tableau[-1, :] -= model['c'][basis[i]] * tableau[i, :]

            # Логируем начальную таблицу Фазы 2
            self._log_iteration(0, 2, tableau,
                               [self._get_variable_name(b, n_orig_vars, n_slack, 0) for b in basis],
                               "", "", (0, 0),
                               tableau[-1, -1])

            iteration = 0
            while True:
                iteration += 1
                pivot_row, pivot_col = self._find_pivot(tableau, 2)

                if pivot_row == -1 and pivot_col == -1:
                    print(f"\n✅ Фаза 2 завершена на итерации {iteration}")
                    print("   Оптимальное решение найдено!")
                    break
                elif pivot_row == -2:
                    print("\n⚠️ Целевая функция неограничена")
                    break

                # Определяем имена переменных
                entering_name = self._get_variable_name(pivot_col, n_orig_vars, n_slack, 0)
                leaving_name = self._get_variable_name(basis[pivot_row], n_orig_vars, n_slack, 0)

                print(f"\nИтерация {iteration}:")
                print(f"  Вводим: {entering_name}")
                print(f"  Выводим: {leaving_name}")
                print(f"  Ведущий элемент: [{pivot_row}, {pivot_col}] = {tableau[pivot_row, pivot_col]:.4f}")

                # Выполняем жорданово исключение
                tableau = self._pivot_tableau(tableau, pivot_row, pivot_col)
                basis[pivot_row] = pivot_col

                # Логируем итерацию
                self._log_iteration(iteration, 2, tableau,
                                   [self._get_variable_name(b, n_orig_vars, n_slack, 0) for b in basis],
                                   entering_name, leaving_name,
                                   (pivot_row, pivot_col),
                                   tableau[-1, -1])

                print(f"  Новый базис: {', '.join([self._get_variable_name(b, n_orig_vars, n_slack, 0) for b in basis])}")
                print(f"  F = {tableau[-1, -1]:.4f}")

            # Извлекаем решение
            solution = self._extract_solution_from_tableau(tableau, basis, n_orig_vars, model)
            solution['simplex_iterations'] = self.simplex_iterations

            print("\n" + "=" * 80)
            print("РЕЗУЛЬТАТ ОПТИМИЗАЦИИ")
            print("=" * 80)
            print(f"Оптимальный начальный фонд: {solution['fun']:.2f} млн руб")
            print(f"Общая доходность: {solution['total_income']:.2f} млн руб")
            print(f"Количество инвестиций: {len(solution['allocation'])}")
            print(f"Итераций Фазы 1: {len([it for it in self.simplex_iterations if it['phase'] == 1])}")
            print(f"Итераций Фазы 2: {len([it for it in self.simplex_iterations if it['phase'] == 2])}")

            return solution

        except Exception as e:
            print(f"❌ ОШИБКА в симплекс-методе: {e}")
            traceback.print_exc()

            # Пробуем использовать scipy как fallback
            print("\nПопытка решения через scipy.linprog...")
            return self._solve_with_scipy(model)

    def _calculate_phase1_objective(self, tableau: np.ndarray) -> float:
        """Расчёт значения целевой функции Фазы 1"""
        return tableau[-1, -1]

    def _get_variable_name(self, idx: int, n_orig: int, n_slack: int, n_art: int) -> str:
        """Получение имени переменной по индексу"""
        if idx < n_orig:
            # Исходная переменная
            if idx < len(self.var_names):
                return self.var_names[idx]
            elif idx == len(self.var_names):
                return "F"
            else:
                bal_idx = idx - len(self.var_names) - 1
                return f"b{bal_idx + 1}"
        elif idx < n_orig + n_slack:
            # Slack-переменная
            slack_idx = idx - n_orig
            return f"s{slack_idx + 1}"
        else:
            # Искусственная переменная
            art_idx = idx - n_orig - n_slack
            return f"a{art_idx + 1}"

    def _solve_with_scipy(self, model: Dict) -> Dict:
        """Решение через scipy.linprog (fallback)"""
        try:
            kwargs = {
                'c': model['c'],
                'bounds': model['bounds'],
                'method': 'highs'
            }

            if model['A_eq'] is not None:
                kwargs['A_eq'] = model['A_eq']
                kwargs['b_eq'] = model['b_eq']

            if model['A_ub'] is not None:
                kwargs['A_ub'] = model['A_ub']
                kwargs['b_ub'] = model['b_ub']

            result = linprog(**kwargs)

            print(f"\nСтатус решения (scipy): {result.message}")
            print(f"Успешно: {result.success}")

            if result.success:
                print(f"\nОптимальный начальный фонд: {result.fun:.2f} млн руб")

                x_invest = result.x[:model['n_invest_vars']]
                initial_fund = result.x[model['n_invest_vars']]
                balances = result.x[model['n_invest_vars'] + 1:]

                metrics = self._calculate_metrics(x_invest, model['variables'])

                solution = {
                    'success': True,
                    'message': result.message,
                    'fun': result.fun,
                    'fun_thousand': result.fun * 1000,
                    'x': x_invest,
                    'initial_fund': initial_fund,
                    'balances': balances,
                    'variables': model['variables'],
                    'var_names': model['var_names'],
                    'mode': model['mode'],
                    'risk_limit': model['risk_limit'],
                    'duration_limit': model['duration_limit'],
                    **metrics
                }

                analysis_text = self._generate_analysis_text(solution)
                solution['analysis_text'] = analysis_text
                solution['simplex_iterations'] = self.simplex_iterations

                return solution
            else:
                return {
                    'success': False,
                    'message': result.message,
                    'fun': None,
                    'x': None,
                    'variables': model['variables'],
                    'var_names': model['var_names'],
                    'mode': model['mode'],
                    'simplex_iterations': self.simplex_iterations
                }

        except Exception as e:
            print(f"❌ ОШИБКА в scipy: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'message': f"Ошибка: {str(e)}",
                'fun': None,
                'x': None,
                'variables': model['variables'],
                'var_names': model['var_names'],
                'mode': model['mode'],
                'simplex_iterations': self.simplex_iterations
            }

    def _calculate_metrics(self, x: np.ndarray, variables: List[Dict]) -> Dict:
        """Расчет метрик по месяцам (1-7)"""
        monthly_risk = []
        monthly_duration = []
        monthly_amount = []

        for month in range(1, 7):
            active_amounts = []
            active_risks = []
            active_durations = []

            for i, var in enumerate(variables):
                if var['start_month'] <= month < var['return_month'] and x[i] > 1e-3:
                    active_amounts.append(x[i])
                    active_risks.append(var['risk'])
                    remaining = var['return_month'] - month
                    active_durations.append(remaining)

            total = sum(active_amounts)
            monthly_amount.append(total)

            if total > 1e-3:
                weighted_risk = sum(a * r for a, r in zip(active_amounts, active_risks)) / total
                monthly_risk.append(weighted_risk)
                weighted_duration = sum(a * d for a, d in zip(active_amounts, active_durations)) / total
                monthly_duration.append(weighted_duration)
            else:
                monthly_risk.append(0)
                monthly_duration.append(0)

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
                    'amount': x[i],
                    'income': income,
                    'risk': var['risk'],
                    'duration': var['duration']
                }

        return {
            'monthly_risk': monthly_risk,
            'monthly_duration': monthly_duration,
            'monthly_amount': monthly_amount,
            'allocation': allocation,
            'total_income': total_income
        }

    def _generate_analysis_text(self, solution: Dict) -> str:
        """Генерация текста анализа"""
        x = solution.get('x', [])
        if x is None:
            x = []

        total_sum = sum(x)
        month1_sum = sum(x[i] for i, var in enumerate(solution.get('variables', []))
                        if var['start_month'] == 1 and i < len(x) and x[i] > 1e-3)

        text = f"💰 Начальный фонд: {solution.get('fun', 0):.2f} млн руб\n"
        text += f"   Всего инвестиций: {total_sum:.2f} млн руб\n"
        text += f"   Из них в месяц 1: {month1_sum:.2f} млн руб\n\n"
        text += "📊 Результаты проверки ограничений:\n\n"

        risk_limit = solution.get('risk_limit', 6)
        duration_limit = solution.get('duration_limit', 2.5)

        for month in range(1, 7):
            risk_val = solution.get('monthly_risk', [0]*6)[month-1]
            dur_val = solution.get('monthly_duration', [0]*6)[month-1]
            amount = solution.get('monthly_amount', [0]*6)[month-1]

            risk_status = "✅" if risk_val <= risk_limit + 1e-6 else "❌"
            dur_status = "✅" if dur_val <= duration_limit + 1e-6 else "❌"

            text += f"Месяц {month}: {risk_status} риск = {risk_val:.2f} (лимит {risk_limit:.1f}), "
            text += f"{dur_status} срок = {dur_val:.2f} (лимит {duration_limit:.1f}), "
            text += f"активы = {amount:.2f} млн руб\n"

        return text

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
                    'Сумма (млн руб)': round(alloc['amount'], 2),
                    'Доход (млн руб)': round(alloc['income'], 2),
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
        """Проверка ограничений для отображения"""
        try:
            if not solution or not solution.get('success'):
                return pd.DataFrame()

            months = list(range(1, 7))
            data = []

            monthly_risk = solution.get('monthly_risk', [0] * 6)
            monthly_duration = solution.get('monthly_duration', [0] * 6)
            monthly_amount = solution.get('monthly_amount', [0] * 6)

            risk_limit = solution.get('risk_limit', 6)
            duration_limit = solution.get('duration_limit', 2.5)

            for i, month in enumerate(months):
                risk_value = monthly_risk[i] if i < len(monthly_risk) else 0
                duration_value = monthly_duration[i] if i < len(monthly_duration) else 0
                amount = monthly_amount[i] if i < len(monthly_amount) else 0

                risk_status = 'OK' if risk_value <= risk_limit + 1e-6 else 'НАРУШЕНИЕ'
                duration_status = 'OK' if duration_value <= duration_limit + 1e-6 else 'НАРУШЕНИЕ'

                data.append({
                    'Месяц': month,
                    'Риск факт': round(risk_value, 2),
                    'Риск лимит': risk_limit,
                    'Риск статус': risk_status,
                    'Срок факт': round(duration_value, 2),
                    'Срок лимит': duration_limit,
                    'Срок статус': duration_status,
                    'Активы (млн руб)': round(amount, 2)
                })

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка в check_constraints: {e}")
            return pd.DataFrame()