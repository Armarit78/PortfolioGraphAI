from dataclasses import dataclass,field
from datetime import datetime
from backend.portfolioConstruction.Filter import Filter
from backend.portfolioConstruction.Weight import Weight
from typing import List,Dict,Any

@dataclass
class Portfolio:
    weights : List[Weight] = field(default_factory=list)
    constraints_llm : List[Filter] = field(default_factory=list)
    constraints_manu : Dict[str,Any] = field(default_factory=list)


    def __str__(self):
        return f"{('\n').join([f"{weight.name} : {weight.weight*100}%" for weight in self.weights])}"

    def investment_date(self)->str:
        #retourne la data d'achat la plus ancienne du portefeuille au format str : YYYY-MM-DD
        oldest_date:datetime=datetime.today()
        for weight in self.weights:
            for trade in weight.historic.keys():
                trade_date = datetime.strptime(trade,"%Y-%m-%d")
                if trade_date < oldest_date:
                    oldest_date = trade_date
        return datetime.strftime(oldest_date,"%Y-%m-%d")

    def find_reallocation_dates(self)->set[str]:
        #retourne toutes les dates où le portefeuille a eu un changement d'allocation
        realloc_dates:set[str]=set()
        for weight in self.weights:
            for trade in weight.historic.keys():
                realloc_dates.add(trade)
        return realloc_dates

    def find_weights(self,date:str)->dict[str,float]:
        #trouve les poids du portefeuille à une date au format str : %Y-%m-%d
        weights:dict[str,float]= {}
        date_selected = datetime.strptime(date,"%Y-%m-%d")
        for w in self.weights:
            histo_dates = [datetime.strptime(histo_date,"%Y-%m-%d") for histo_date in w.historic.keys() if datetime.strptime(histo_date,"%Y-%m-%d") <= date_selected]
            if len(histo_dates)>0:
                date_selected=max(histo_dates)
                weights[w.ticker]=w.historic[datetime.strftime(date_selected,"%Y-%m-%d")]
        return weights

    def calculate_portfolio_value(self,hp):
        def calculate_price(row):
            date = row.name.to_pydatetime().strftime("%Y-%m-%d")
            weights = self.find_weights(date)
            return sum(row[ticker]*weight for ticker,weight in weights.items())

        hp["portfolio"] = hp.apply(calculate_price,axis=1)
        return hp



