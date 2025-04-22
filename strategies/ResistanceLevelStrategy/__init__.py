from jesse.strategies import Strategy
import jesse.indicators as ta
import numpy as np
from typing import Union


class ResistanceLevelStrategy(Strategy):
    """
    Стратегия торговли на основе уровней сопротивления
    Алгоритм:
    1. Отслеживаем цены и выявляем локальные максимумы
    2. Определяем уровни сопротивления, которые подтверждаются трижды
    3. Входим в сделку при приближении к уровню сопротивления с дисконтом 0.3%
    4. Устанавливаем TP 3.5% и SL 0.5%
    5. Перемещаем SL в безубыток при достижении 1.5% прибыли
    6. Пропускаем монету после двух последовательных неудачных сделок
    """

    def __init__(self):
        super().__init__()
        # Параметры стратегии
        self.discount_to_level = 0.003  # 0.3% скидка до уровня сопротивления для входа
        self.tp_percentage = 0.035  # 3.5% тейк-профит
        self.sl_percentage = 0.005  # 0.5% стоп-лосс
        self.breakeven_move = 0.015  # 1.5% прибыли для перемещения SL в безубыток
        self.level_confirmation = 3  # Количество подтверждений уровня
        self.price_tolerance = 0.001  # 0.1% допуск для уровней цены
        self.max_failed_trades = 2  # Максимальное количество неудачных сделок подряд

        # Внутренние переменные
        self.resistance_levels = []  # Список подтвержденных уровней сопротивления
        self.price_highs = []  # Список локальных максимумов
        self.consecutive_failures = 0  # Счетчик последовательных неудачных сделок
        self.entered_level = None  # Уровень, на котором мы вошли в сделку
        self.stop_moved_to_breakeven = False  # Флаг для отслеживания перемещения SL в безубыток

    def hyperparameters(self):
        """
        Определяет гиперпараметры для оптимизации
        """
        return [
            {'name': 'discount_to_level', 'type': float, 'min': 0.001, 'max': 0.005, 'default': 0.003},
            {'name': 'tp_percentage', 'type': float, 'min': 0.02, 'max': 0.05, 'default': 0.035},
            {'name': 'sl_percentage', 'type': float, 'min': 0.003, 'max': 0.01, 'default': 0.005},
            {'name': 'breakeven_move', 'type': float, 'min': 0.01, 'max': 0.02, 'default': 0.015},
            {'name': 'level_confirmation', 'type': int, 'min': 2, 'max': 4, 'default': 3}
        ]

    def before(self):
        """
        Вызывается перед каждой свечой
        """
        # Проверяем, не является ли текущая свеча локальным максимумом
        if self.is_local_high(10):  # Используем период 10 свечей для определения локального максимума
            self.update_price_highs(self.high)
            self.identify_resistance_levels()

    def should_long(self) -> bool:
        """
        Определяет, следует ли входить в длинную позицию
        """
        # Если слишком много неудачных сделок подряд, пропускаем
        if self.consecutive_failures >= self.max_failed_trades:
            return False

        # Проверяем, близка ли цена к уровню сопротивления с дисконтом
        for level in self.resistance_levels:
            discount_percentage = (level - self.close) / self.close
            if abs(discount_percentage - self.discount_to_level) < self.price_tolerance:
                self.entered_level = level
                return True

        return False

    def should_short(self) -> bool:
        """
        Эта стратегия не использует короткие позиции
        """
        return False

    def should_cancel_entry(self) -> bool:
        """
        Определяет, следует ли отменить вход в сделку
        """
        return False

    def go_long(self):
        """
        Выполняется при входе в длинную позицию
        """
        # Расчет размера позиции (используем фиксированный риск)
        entry_price = self.price
        stop_price = entry_price * (1 - self.sl_percentage)
        take_profit = entry_price * (1 + self.tp_percentage)

        # Вход в позицию с риском 2% от капитала
        qty = self.position_size_to_qty(self.capital * 0.02, entry_price, stop_price)
        self.buy = qty

        # Установка стоп-лосса и тейк-профита
        self.stop_loss = stop_price
        self.take_profit = take_profit

        # Сбрасываем флаг перемещения стопа в безубыток
        self.stop_moved_to_breakeven = False

    def update_position(self):
        """
        Выполняется на каждой свече, когда есть открытая позиция
        """
        # Проверяем, достигла ли прибыль уровня для перемещения стопа в безубыток
        if not self.stop_moved_to_breakeven and self.position.pnl_percentage >= self.breakeven_move * 100:
            # Перемещаем стоп в безубыток (чуть выше, чтобы покрыть комиссии)
            self.stop_loss = self.position.entry_price * 1.001
            self.stop_moved_to_breakeven = True

    def on_stop_loss(self, order):
        """
        Выполняется при срабатывании стоп-лосса
        """
        self.consecutive_failures += 1
        # Здесь можно добавить логирование или уведомления

    def on_take_profit(self, order):
        """
        Выполняется при достижении тейк-профита
        """
        self.consecutive_failures = 0
        # Здесь можно добавить логирование или уведомления

    def is_local_high(self, period: int) -> bool:
        """
        Определяет, является ли текущая свеча локальным максимумом
        """
        if self.index < period:
            return False

        current_high = self.high
        for i in range(1, period + 1):
            if self.candles[-i, 2] > current_high:
                return False

        return True

    def update_price_highs(self, price: float):
        """
        Добавляет новый локальный максимум в список
        """
        self.price_highs.append(price)

        # Ограничиваем длину списка, чтобы не хранить слишком много данных
        if len(self.price_highs) > 100:
            self.price_highs = self.price_highs[-100:]

    def identify_resistance_levels(self):
        """
        Выявляет уровни сопротивления на основе локальных максимумов
        """
        potential_levels = []

        # Группируем ценовые максимумы, которые находятся в пределах допуска
        for price_high in self.price_highs:
            found_group = False

            for i, level in enumerate(potential_levels):
                if abs(price_high - level["price"]) / level["price"] <= self.price_tolerance:
                    # Обновляем потенциальный уровень и увеличиваем счетчик касаний
                    avg_price = (level["price"] * level["touches"] + price_high) / (level["touches"] + 1)
                    potential_levels[i]["price"] = avg_price
                    potential_levels[i]["touches"] += 1
                    found_group = True
                    break

            if not found_group:
                potential_levels.append({"price": price_high, "touches": 1})

        # Добавляем подтвержденные уровни в список
        for level in potential_levels:
            if level["touches"] >= self.level_confirmation and level["price"] not in self.resistance_levels:
                self.resistance_levels.append(level["price"])

        # Сортируем уровни по возрастанию цены
        self.resistance_levels.sort()

    def position_size_to_qty(self, position_size, entry_price, stop_price) -> float:
        """
        Конвертирует размер позиции (в валюте депозита) в размер позиции (в единицах торгуемого актива)
        """
        risk_per_qty = abs(entry_price - stop_price)
        if risk_per_qty == 0:
            return 0

        return position_size / risk_per_qty

    def terminate(self):
        """
        Выполняется по завершении бэктеста
        """
        pass