from json import JSONDecodeError

from yfinance import EquityQuery, screen
from yfinance.const import EQUITY_SCREENER_EQ_MAP
from yfinance.const import FUND_SCREENER_EQ_MAP
import json
import os
from .Filter import Filter

MAX_SIZE = 250

class EquityScreener:
    def __init__(self,constraints:list=[],filename=None, stringJson:str=None,dictJson:dict=None):
        if filename is not None:
            self.load_from_json(filename)
            return
        if stringJson is not None:
            self.load_from_string(stringJson)
            return
        if dictJson is not None:
            self.load_from_dict(dictJson)
            return

        #we write special attribute with a name starting by "__" all other attributes will be considered as constraints
        for constraint in constraints:
            if isinstance(constraint,Filter):
                #constructeur avec des contraintes déjà comme des filtres
                setattr(self,constraint.name,constraint)
            else:
                #constructeur annexe à partir d'un dictionnaire classique
                if "field" in constraint:
                    name = constraint["field"]
                else:
                    raise ValueError("Each constraint must have a field value")
                if "operator" in constraint and "values" in constraint:
                    filter = Filter(name,constraint["operator"],constraint["values"])
                    setattr(self, name,filter)

    def __str__(self):
        return f"Filtres actifs : \n{("\n").join([str(f) for name,f in vars(self).items() if not name.startswith("__")])}"

    def __repr__(self):
        return f"{("\n").join([repr(f) for name, f in vars(self).items()])}"

    def load_from_json(self,filename):
        try:
            with open(filename,"r",encoding='utf-8') as f:
                raw_data= json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"filter file not found : {filename}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"file {filename} is not a valid JSON file") from e
        #json must be on universe equity
        if raw_data["universe"] != 'equity':
            raise ValueError("JSON is not a set of constraints on equity universe, change the universe or use another constructor")
        else:
            if "constraints" in raw_data:
                self.__init__(constraints=raw_data["constraints"])

            else:
                raise ValueError("JSON file doesn't contain a constraints key")

    def load_from_string(self,stringJson:str):
        try:
            raw_data= json.loads(stringJson)
        except json.JSONDecodeError as e:
            raise ValueError(f"stringJson is not a valid JSON file") from e
        #json must be on universe equity
        if raw_data["universe"] != 'equity':
            raise ValueError("JSON is not a set of constraints on equity universe, change the universe or use another constructor")
        else:
            if "constraints" in raw_data:
                self.__init__(constraints=raw_data["constraints"])
            else:
                raise ValueError("JSON file doesn't contain a constraints key")

    def load_from_dict(self,dictJson:dict):
        try:
            raw_data= dictJson
        except json.JSONDecodeError as e:
            raise ValueError(f"stringJson is not a valid JSON file") from e
        #json must be on universe equity
        if raw_data["universe"] != 'equity':
            raise ValueError("JSON is not a set of constraints on equity universe, change the universe or use another constructor")
        else:
            if "constraints" in raw_data:
                self.__init__(constraints=raw_data["constraints"])
                print("initreussi")
            else:
                raise ValueError("JSON file doesn't contain a constraints key")

    #we assume that the list of constraints are linked by AND : ie each constraint is required
    def build_query(self):
        filters = []
        for name, filter in vars(self).items():
            if not name.startswith('__'):
                if isinstance(filter, Filter):
                    #we respect the norm required by yfinance lib
                    val=[filter.name]
                    if isinstance(filter.value,list):
                        val += filter.value
                    elif isinstance(filter.value,float) or isinstance(filter.value,int):
                        val.append(filter.value)
                    filters.append(EquityQuery(filter.operand,val))
                else:
                    raise ValueError("there is an attribute not starting by __ which value is not a Filter object")
        if len(filters) == 1:
            return filters[0]
        elif len(filters) == 0:
            raise ValueError("There are no filters")
        else:
            return EquityQuery("and",filters)


    def build_universe(self)->dict:
        query = self.build_query()
        try:
            data = screen(query,size=100,offset=0,sortField="bookvalueshare.lasttwelvemonths",sortAsc=False)
        except Exception as e:
            raise Exception(f"Erreur lors de la requête API de construction de l'univers : {str(e)}")

        res = {"quotes":[quote["symbol"] for quote in data["quotes"]]}
        #count = data["total"]
        #offset = 0
        #while offset<count:
            #we only keep quotes of equity in the universe
            #data["quotes"] += [quote["symbol"] for quote in screen(query,size=MAX_SIZE,offset=offset)["quotes"]]
            #offset += MAX_SIZE
        return res
