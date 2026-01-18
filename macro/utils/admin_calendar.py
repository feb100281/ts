# macro/utils/admin_calendar.py
from calendar import HTMLCalendar
from datetime import date


class WorkingCalendar(HTMLCalendar):
    """
    Календарь, который подсвечивает рабочие/нерабочие дни.
    working_days_map: dict {date: CalendarExceptions}
    """

    def __init__(self, working_days_map, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.working_days_map = working_days_map
        self._year = None
        self._month = None

    def formatmonth(self, year, month, withyear=True):
        # запоминаем год/месяц, чтобы использовать в formatday
        self._year = year
        self._month = month
        return super().formatmonth(year, month, withyear)

    def formatday(self, day, weekday):
        if day == 0:
            # пустая ячейка (дни из соседних месяцев)
            return '<td class="noday">&nbsp;</td>'

        d = date(self._year, self._month, day)
        obj = self.working_days_map.get(d)

        classes = []
        if obj is not None:
            if obj.is_working_day:
                classes.append("working")
            else:
                classes.append("nonworking")

        # сегодняшний день
        if d == date.today():
            classes.append("today")

        class_attr = f' class="{" ".join(classes)}"' if classes else ""
        return f"<td{class_attr}>{day}</td>"
