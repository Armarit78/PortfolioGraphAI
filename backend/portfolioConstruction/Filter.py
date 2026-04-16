from dataclasses import dataclass
from typing import Any

from langgraph.channels import AnyValue


@dataclass
class Filter:
    name:str
    operand:str
    value:Any

    def __post_init__(self):
        if self.operand not in ["gte", "lte", "gt", "lt", "eq", "is-in", "btwn"]:
            raise ValueError("Operand must be either gte, lte, gt, lt, eq, is-in, btwn")

        if self.operand in ["gte", "lte", "gt", "lt", "eq"]:
            if isinstance(self.value, (int, float)):
                pass
            elif isinstance(self.value, list) and len(self.value) == 1 and isinstance(self.value[0], (int, float)):
                self.value = self.value[0]
            else:
                raise ValueError("With comparaison operand, value must be a float and 1 value must be present in the list")

        elif self.operand in ["is-in", "btwn"]:
            if not isinstance(self.value, list):
                raise ValueError("With include operand, value must be a list")


    def __str__(self):
        return f"filter name: {self.name} - operator: {self.operand} - value: {self.value}"

    def __repr__(self):
        return f"{self.name} - {self.operand} - {self.value}"
    #On surcharge l'opérateur = pour comparer des filtres. S'ils portent sur le même champ alors, ils sont dit égaux
    def __eq__(self, other:"Filter"):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    @staticmethod
    def invert_op(op:str):
        match op:
            case "lte":
                return "gt"
            case "lt":
                return "gte"
            case "gt":
                return "lte"
            case "gte":
                return "lt"
            case _ :
                raise ValueError("Operand not supported")


    def merge(self,f:"Filter"):
        def merge_aux(f1:Filter,f2:Filter):
            res = f1
            if f1.name != f2.name:
                raise ValueError("Impossible to merge two filter with different names")
            if (f1.operand in ["gte","lte","gt","lt","eq","btwn"] and f2.operand not in ["gte","lte","gt","lt","eq","btwn"]):
                raise ValueError("Impossible to merge two filter with different operator classification")
            elif f1.operand in ["gte","lte","gt","lt","eq","btwn"] and f2.operand in ["gte","lte","gt","lt","eq","btwn"]:
                match f1.operand:
                    case "gte":
                        match f2.operand:
                            case "gte":
                                res.value = max(f1.value,f2.value)
                            case "gt":
                                if f2.value >= f1.value:
                                    res.operand = "gt"
                                    res.value = f2.value
                            case "lte":
                                if f2.value==f1.value:
                                    res.operand = "eq"
                                elif f2.value < f1.value:
                                    raise ValueError("Merge will create empty solution")
                                else:
                                    res.operand = "btwn"
                                    res.value = [f1.value,f2.value]
                            case "lt":
                                if f2.value <= f1.value:
                                    raise ValueError("Merge will create empty solution")
                                else:
                                    res.operand = "btwn"
                                    res.value = [f1.value,f.value]
                            case "btwn":
                                if f1.value>max(f2.value):
                                    raise ValueError("Merge will create empty solution")
                                elif f1.value<=min(f2.value):
                                    res.operand = "btwn"
                                    res.value=f2.value
                                else:
                                    res.operand = "btwn"
                                    res.value=[f1.value,f2.value[1]]
                            case "eq":
                                if f2.value >= f1.value:
                                    res.operand = "eq"
                                    res.value = f2.value
                                else:
                                    raise ValueError("Merge will create empty solution")
                    case "gt":
                        match f2.operand:
                            case "gte":
                                res = merge_aux(f2,f1)
                            case "gt":
                                res.value = max(f1.value,f2.value)
                            case "lte"|"lt":
                                if res.value <= f1.value:
                                    raise ValueError("Merge will create empty solution")
                                else:
                                    #approximation avec le btwn qui passe à l'inégalité large
                                    res.operand = "btwn"
                                    res.value = [f1.value, f2.value]
                            case "btwn":
                                if res.value >= max(f2.value):
                                    raise ValueError("Merge will create empty solution")
                                elif f1.value < min(f2.value):
                                    res.operand = "btwn"
                                    res.value = f2.value
                                else:
                                    res.operand = "btwn"
                                    res.value = [f1.value, f2.value[1]]
                            case "eq":
                                if f2.value > f1.value:
                                    res.operand = "eq"
                                    res.value = f2.value
                                else:
                                    raise ValueError("Merge will create empty solution")

                    case "lte":
                        match f2.operand:
                            case "gte" | "gt":
                                res = merge_aux(f2,f1)
                            case "lte":
                                res.value = min(f1.value,f2.value)
                            case "lt":
                                if f1.value >= f2.value:
                                    res.operand = "lt"
                                    res.value = f2.value
                            case "btwn":
                                if f1.value == min(f2.value):
                                    res.operand = "eq"
                                elif f1.value <= min(f2.value):
                                    raise ValueError("Merge will create empty solution")
                                elif f1.value >= max(f2.value):
                                    res.value = f2.value
                                    res.operand = "btwn"
                                else:
                                    res.value=[f2.value[0],min(f1.value,f2.value[1])]
                                    res.operand = "btwn"
                            case "eq":
                                if f1.value >= f2.value:
                                    res.operand ="eq"
                                    res.value = f2.value
                    case "lt":
                        match f2.operand:
                            case "gte"|"gt"|"lte":
                                res = merge_aux(f2,f1)

                            case "lt":
                                res.value = min(f1.value,f2.value)
                            case "btwn":
                                if f1.value > max(f2.value):
                                    res.operand = "btwn"
                                    res.value = f2.value
                                elif f1.value <= min(f2.value):
                                    raise ValueError("Merge will create empty solution")
                                else:
                                    res.operand ="btwn"
                                    res.value = [f2.value[0],min(f2.value[1],f1.value)]
                            case "eq":
                                if f1.value>f2.value:
                                    res.operand = "eq"
                                    res.value = f2.value
                                else:
                                    raise ValueError("Merge will create empty solution")
                    case "btwn":
                        match f2.operand:
                            case "gte"|"gt"|"lte"|"lt":
                                res = merge_aux(f2,f1)
                            case "btwn":
                                if max(f1.value)<min(f2.value) or min(f1.value)>max(f2.value):
                                    raise ValueError("Merge will create empty solution")
                                elif max(f1.value)==min(f2.value):
                                    res.operand = "eq"
                                    res.value = f1.value[1]
                                elif min(f1.value)==max(f2.value):
                                    res.operand = "eq"
                                    res.value = f1.value[0]
                                else:
                                    res.value = [max(f1.value[0],f2.value[0]),min(f1.value[1],f2.value[1])]
                            case "eq":
                                if f2.value in f1.value:
                                    res.operand = "eq"
                                    res.value = f2.value
                                else :
                                    raise ValueError("Merge will create empty solution")
                    case "eq":
                        match f2.operand:
                            case "gte"|"gt"|"lte"|"lt"|"btwn":
                                res = merge_aux(f2,f1)
                            case "eq":
                                if f1.value != f2.value:
                                    raise ValueError("Merge will create empty solution")

            if f1.operand == "is-in" and f2.operand != "is-in":
                raise ValueError("Impossible to merge two filter with different operator classification")
            elif f1.operand == "is-in" and f2.operand == "is-in":
                items_selected=[]
                for it1 in f1.value:
                    for it2 in f2.value:
                        if(it1==it2):
                            items_selected.append(it1)

                if len(items_selected)==0:
                    raise ValueError("Merge will create empty solution")
                else:
                    res.value = items_selected

            return res
        return merge_aux(self,f)





