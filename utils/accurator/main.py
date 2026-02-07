import pandas as pd
import numpy as np


#основной класс для работы с массивами дат
class DatesContext:
    def __init__(self, end_date=None):
        end_date = pd.Timestamp(end_date).normalize() if end_date else pd.Timestamp.now().normalize()

        d = pd.date_range(
            start="2024-01-01",
            end=end_date,
            freq="D"
        )

        self.timeline = d.to_numpy(dtype="datetime64[D]")
        self.n = self.timeline.size
        self.zero = np.zeros(self.n)



def get_ctx(end_date=None):
    return (DatesContext(end_date))

