from backend.ai.core.llm import dbg
from backend.portfolioConstruction.Filter import Filter


def merge_constraints(oldF:list[Filter],newC:list[dict]):
    if newC is None:
        if oldF is not None:
            return oldF
        else:
            return []

    mergedC:list[Filter] = []
    #conversion des nouvelles contraintes en filtres
    newF = []
    for nc in newC:
        try:
            nf = Filter(nc.get("field"), nc.get("operator"), nc.get("values"))
        except Exception as e:
            return {"success": False, "message": f"impossible de définir une contraintes : {str(e)}"}

        newF.append(nf)
    #si pas encore de contraintes on retourne seulement les nouvelles
    if oldF is None or len(oldF) == 0:
        return newF
    #ajout des anciens paramètres
    for of in oldF:
        for nf in newF:
            if of == nf:
                try:
                    of = of.merge(nf)
                except Exception as e:
                    dbg("Erreur lors de la fusion des filtres : ",str(e))
                    of = None

        if of is not None:
            mergedC.append(of)
    #ajout des nouveaux paramètres qui ne nécessitent pas de fusion
    for nf in newF:
        if nf not in mergedC:
            mergedC.append(nf)

    return mergedC
