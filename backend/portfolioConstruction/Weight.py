from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class Weight:
    ticker:str
    name:str
    weight:float
    historic: Dict[str,float]


    def __str__(self):
        return f"{self.ticker} : {self.weight*100}% \n Prix : {self.historic}"