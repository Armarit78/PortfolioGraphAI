import time
import uuid
import pytest
import pytest_asyncio

from backend.ai.controller.AILocalController import LocalController

BENCHMARK = [

    # =========================
    # PRICE (20)
    # =========================
    {"text": "Donne-moi le prix de Apple", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AAPL"}},
    {"text": "Je veux le prix de Microsoft", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "MSFT"}},
    {"text": "Tu peux me donner le cours de Tesla ?", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "TSLA"}},
    {"text": "Montre-moi le prix de Nvidia", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "NVDA"}},
    {"text": "J’aimerais connaître le prix de Amazon", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AMZN"}},
    {"text": "Peux-tu me dire combien vaut Apple aujourd’hui ?", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AAPL"}},
    {"text": "Donne-moi le cours de Meta", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "META"}},
    {"text": "Je veux savoir combien cote alphabet", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "GOOGL"}},
    {"text": "Tu peux me sortir le prix de Tesla maintenant ?", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "TSLA"}},
    {"text": "Dis-moi le prix de Microsoft aujourd’hui", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "MSFT"}},
    {"text": "Apple ça vaut combien là ?", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AAPL"}},
    {"text": "Je veux le dernier prix de Nvidia", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "NVDA"}},
    {"text": "Montre-moi combien vaut Amazon en ce moment", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AMZN"}},
    {"text": "Tu peux me dire le cours de AAPL ?", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AAPL"}},
    {"text": "J’aimerais le prix de MSFT", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "MSFT"}},
    {"text": "Donne-moi le prix de GOOGL", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "GOOGL"}},
    {"text": "Je veux savoir le cours de NVDA", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "NVDA"}},
    {"text": "Peux-tu me donner le prix de Tesla en bourse ?", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "TSLA"}},
    {"text": "Montre-moi le cours de Meta aujourd’hui", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "META"}},
    {"text": "Dis-moi combien vaut Apple en bourse", "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AAPL"}},

    # =========================
    # STATS (20)
    # =========================
    {"text": "Je veux les stats de Apple sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AAPL", "period": "1y"}},
    {"text": "Donne-moi les statistiques de Microsoft sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "MSFT", "period": "1y"}},
    {"text": "J’aimerais la volatilité de Tesla sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "TSLA", "period": "1y"}},
    {"text": "Peux-tu me sortir les stats de Nvidia sur 6 mois ?", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "NVDA", "period": "6mo"}},
    {"text": "Je veux voir la performance de Amazon sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AMZN", "period": "1y"}},
    {"text": "Montre-moi les stats de Meta", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "META", "period": "1y"}},
    {"text": "Tu peux me donner le rendement de alphabet sur 1 an ?", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "GOOGL", "period": "1y"}},
    {"text": "Je veux la volatilité de Apple sur 6 mois", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AAPL", "period": "6mo"}},
    {"text": "Donne-moi les performances de Tesla sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "TSLA", "period": "1y"}},
    {"text": "J’aimerais les stats de MSFT sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "MSFT", "period": "1y"}},
    {"text": "Peux-tu me dire le Sharpe ratio de Nvidia ?", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "NVDA", "period": "1y"}},
    {"text": "Je veux les statistiques de Amazon sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AMZN", "period": "1y"}},
    {"text": "Montre-moi la performance de Meta sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "META", "period": "1y"}},
    {"text": "Tu peux me sortir les stats de GOOGL sur 6 mois ?", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "GOOGL", "period": "6mo"}},
    {"text": "Donne-moi le rendement annualisé de Tesla", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "TSLA", "period": "1y"}},
    {"text": "Je veux la volatilité de Microsoft", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "MSFT", "period": "1y"}},
    {"text": "J’aimerais les stats de Apple sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AAPL", "period": "1y"}},
    {"text": "Peux-tu me montrer la performance de Nvidia sur 1 an ?", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "NVDA", "period": "1y"}},
    {"text": "Je veux les indicateurs de Amazon sur 6 mois", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AMZN", "period": "6mo"}},
    {"text": "Dis-moi les stats de Tesla sur 1 an", "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "TSLA", "period": "1y"}},

    # =========================
    # COMPARE (20)
    # =========================
    {"text": "Compare Apple et Microsoft pour moi", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "MSFT", "period": "1y"}},
    {"text": "Je veux comparer Tesla et Nvidia", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "NVDA", "period": "1y"}},
    {"text": "Tu peux me faire une comparaison entre Amazon et alphabet ?", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "AMZN", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Montre-moi Apple vs Microsoft", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "MSFT", "period": "1y"}},
    {"text": "J’aimerais comparer Tesla à Nvidia sur 1 an", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "NVDA", "period": "1y"}},
    {"text": "Peux-tu comparer Meta et alphabet ?", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "META", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Je veux voir Microsoft contre Apple", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "MSFT", "symbol2": "AAPL", "period": "1y"}},
    {"text": "Fais-moi une comparaison entre Amazon et Meta", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AMZN", "symbol2": "META", "period": "1y"}},
    {"text": "Tu peux me dire entre Tesla et Microsoft lequel est meilleur ?", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "TSLA", "symbol2": "MSFT", "period": "1y"}},
    {"text": "Je veux comparer alphabet et Amazon sur 6 mois", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "GOOGL", "symbol2": "AMZN", "period": "6mo"}},
    {"text": "Montre-moi Apple ou Tesla", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "TSLA", "period": "1y"}},
    {"text": "J’aimerais une comparaison Amazon contre Apple", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AMZN", "symbol2": "AAPL", "period": "1y"}},
    {"text": "Peux-tu comparer Nvidia et Meta ?", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "NVDA", "symbol2": "META", "period": "1y"}},
    {"text": "Je veux savoir entre Apple et Microsoft lequel performe le mieux", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "AAPL", "symbol2": "MSFT", "period": "1y"}},
    {"text": "Dis-moi qui est meilleur entre Tesla et Nvidia sur 1 an", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "TSLA", "symbol2": "NVDA", "period": "1y"}},
    {"text": "Tu peux me faire Meta vs Microsoft ?", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "META", "symbol2": "MSFT", "period": "1y"}},
    {"text": "Je veux comparer alphabet et Meta", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "GOOGL", "symbol2": "META", "period": "1y"}},
    {"text": "Montre-moi Microsoft ou Amazon", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "MSFT", "symbol2": "AMZN", "period": "1y"}},
    {"text": "J’aimerais comparer Tesla et alphabet", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Entre Amazon et alphabet, lequel est le plus performant ?", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "AMZN", "symbol2": "GOOGL", "period": "1y"}},

    # =========================
    # SCREENER (20)
    # =========================
    {"text": "Je veux des actions européennes dans la santé", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions européennes dans la santé"}},
    {"text": "Donne-moi un portefeuille d’actions Europe secteur santé", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Donne-moi un portefeuille d’actions Europe secteur santé"}},
    {"text": "Je cherche des actions US dans la tech", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions US dans la tech"}},
    {"text": "Montre-moi des actions Europe avec faible volatilité", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions Europe avec faible volatilité"}},
    {"text": "J’aimerais un screener d’actions avec dividendes élevés", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "J’aimerais un screener d’actions avec dividendes élevés"}},
    {"text": "Peux-tu me trouver des actions santé en Europe ?", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Peux-tu me trouver des actions santé en Europe ?"}},
    {"text": "Je veux un portefeuille d’actions hors énergie", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille d’actions hors énergie"}},
    {"text": "Tu peux me sortir des actions américaines défensives ?", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Tu peux me sortir des actions américaines défensives ?"}},
    {"text": "Je cherche des actions monde avec rendement élevé", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions monde avec rendement élevé"}},
    {"text": "Montre-moi des actions européennes dans le luxe", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions européennes dans le luxe"}},
    {"text": "Je veux un screener d’actions industrielles en Europe", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je veux un screener d’actions industrielles en Europe"}},
    {"text": "Donne-moi des actions bancaires européennes", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Donne-moi des actions bancaires européennes"}},
    {"text": "Je veux des actions de croissance en Europe", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions de croissance en Europe"}},
    {"text": "Peux-tu filtrer des actions US hors technologie ?", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Peux-tu filtrer des actions US hors technologie ?"}},
    {"text": "Je cherche des actions santé avec dividendes", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions santé avec dividendes"}},
    {"text": "Montre-moi des actions à faible bêta", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions à faible bêta"}},
    {"text": "J’aimerais des actions monde dans la santé", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "J’aimerais des actions monde dans la santé"}},
    {"text": "Je veux un portefeuille d’actions défensives avec rendement", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille d’actions défensives avec rendement"}},
    {"text": "Tu peux me trouver des actions Europe hors finance ?", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Tu peux me trouver des actions Europe hors finance ?"}},
    {"text": "Je veux des actions internationales peu volatiles", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions internationales peu volatiles"}},

    # =========================
    # CHAT (20)
    # =========================
    {"text": "C’est quoi un ETF exactement ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi ce qu’est la volatilité", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Je veux comprendre ce qu’est un dividende", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Peux-tu m’expliquer le Sharpe ratio ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "J’aimerais comprendre la diversification", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Dis-moi simplement ce qu’est une action", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi la différence entre action et obligation", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Je veux comprendre le bêta en bourse", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Tu peux m’expliquer ce qu’est le PER ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "J’aimerais savoir ce qu’est un rendement annualisé", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Peux-tu m’expliquer la capitalisation boursière ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Je veux comprendre la différence entre ETF et action", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi ce qu’est un portefeuille défensif", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Dis-moi ce que veut dire drawdown", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Je veux une explication simple du risque en bourse", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Peux-tu m’expliquer ce qu’est un ETF distribuant ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "J’aimerais comprendre ce qu’est un ETF capitalisant", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi la différence entre croissance et value", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Je veux comprendre comment lire une performance sur un an", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Tu peux m’expliquer pourquoi une action monte ou baisse ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

]

BENCHMARK2 = [

    # =========================
    # PRICE (20)
    # =========================
    {"text": "Quel est le cours actuel de Apple ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "AAPL"}},
    {"text": "Montre-moi le prix actuel de Microsoft", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "MSFT"}},
    {"text": "Combien vaut Tesla en ce moment ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "TSLA"}},
    {"text": "Quel est le prix actuel de Nvidia ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "NVDA"}},
    {"text": "Je veux connaître le cours de Amazon", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "AMZN"}},
    {"text": "Peux-tu afficher le prix de Meta ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "META"}},
    {"text": "Quel est le dernier prix de Google ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "GOOGL"}},
    {"text": "Affiche-moi le cours de Tesla", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "TSLA"}},
    {"text": "Je voudrais voir le prix de Microsoft", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "MSFT"}},
    {"text": "Montre-moi combien vaut Nvidia", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "NVDA"}},
    {"text": "Quel est le cours de Meta en bourse ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "META"}},
    {"text": "Je veux voir combien vaut Apple", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "AAPL"}},
    {"text": "Donne-moi la valeur actuelle de Amazon", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "AMZN"}},
    {"text": "Quel prix pour Tesla aujourd'hui ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "TSLA"}},
    {"text": "Affiche le prix de Google", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "GOOGL"}},
    {"text": "Je veux le cours de Nvidia maintenant", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "NVDA"}},
    {"text": "Dis-moi le prix actuel de Apple", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "AAPL"}},
    {"text": "Combien vaut Amazon aujourd'hui ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "AMZN"}},
    {"text": "Quel est le cours de Microsoft en bourse ?", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "MSFT"}},
    {"text": "Donne-moi la cotation de Tesla", "expected_route": "tool", "expected_intent": "price",
     "expected_args": {"symbol": "TSLA"}},

    # =========================
    # STATS (20)
    # =========================
    {"text": "Quelle est la performance de Apple sur 5 ans ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "AAPL", "period": "5y"}},
    {"text": "Montre-moi la volatilité de Microsoft sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "MSFT", "period": "1y"}},
    {"text": "Quelle performance pour Tesla sur 6 mois ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "TSLA", "period": "6mo"}},
    {"text": "Je veux les stats de Nvidia sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "NVDA", "period": "1y"}},
    {"text": "Quel est le rendement de Amazon sur 5 ans ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "AMZN", "period": "5y"}},
    {"text": "Donne-moi la volatilité de Meta sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "META", "period": "1y"}},
    {"text": "Affiche les statistiques de Google sur 6 mois", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "GOOGL", "period": "6mo"}},
    {"text": "Quel est le Sharpe ratio de Tesla sur 1 an ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "TSLA", "period": "1y"}},
    {"text": "Montre-moi les performances de Nvidia sur 5 ans", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "NVDA", "period": "5y"}},
    {"text": "Je veux les indicateurs de Microsoft sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "MSFT", "period": "1y"}},
    {"text": "Quelle volatilité pour Apple sur 6 mois ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "AAPL", "period": "6mo"}},
    {"text": "Affiche les stats de Amazon sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "AMZN", "period": "1y"}},
    {"text": "Je veux voir la performance de Google sur 5 ans", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "GOOGL", "period": "5y"}},
    {"text": "Donne-moi le rendement de Tesla sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "TSLA", "period": "1y"}},
    {"text": "Quelle volatilité pour Nvidia sur 6 mois ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "NVDA", "period": "6mo"}},
    {"text": "Montre-moi les stats de Meta sur 5 ans", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "META", "period": "5y"}},
    {"text": "Je veux la performance de Apple sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "AAPL", "period": "1y"}},
    {"text": "Quel rendement pour Microsoft sur 5 ans ?", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "MSFT", "period": "5y"}},
    {"text": "Affiche les indicateurs de Tesla sur 6 mois", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "TSLA", "period": "6mo"}},
    {"text": "Je veux voir la volatilité de Amazon sur 1 an", "expected_route": "tool", "expected_intent": "stats",
     "expected_args": {"symbol": "AMZN", "period": "1y"}},

    # =========================
    # COMPARE (20)
    # =========================
    {"text": "Compare Apple et Tesla", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "TSLA", "period": "1y"}},
    {"text": "Quelle est la différence de performance entre Microsoft et Google ?", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "MSFT", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Compare Amazon et Nvidia sur 5 ans", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AMZN", "symbol2": "NVDA", "period": "5y"}},
    {"text": "Montre-moi la comparaison entre Apple et Meta", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "META", "period": "1y"}},
    {"text": "Entre Tesla et Microsoft lequel est le plus rentable ?", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "TSLA", "symbol2": "MSFT", "period": "1y"}},
    {"text": "Compare Nvidia et Google", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "NVDA", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Apple vs Amazon", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "AMZN", "period": "1y"}},
    {"text": "Tesla contre Nvidia", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "NVDA", "period": "1y"}},
    {"text": "Google ou Meta lequel est meilleur ?", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "GOOGL", "symbol2": "META", "period": "1y"}},
    {"text": "Je veux comparer Apple et Google", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Compare Microsoft et Nvidia sur 1 an", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "MSFT", "symbol2": "NVDA", "period": "1y"}},
    {"text": "Meta ou Amazon lequel performe le mieux ?", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "META", "symbol2": "AMZN", "period": "1y"}},
    {"text": "Fais-moi une comparaison entre Tesla et Google", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Compare Apple et Nvidia sur 1 an", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "NVDA", "period": "1y"}},
    {"text": "Amazon contre Google", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AMZN", "symbol2": "GOOGL", "period": "1y"}},
    {"text": "Compare Meta et Tesla", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "META", "symbol2": "TSLA", "period": "1y"}},
    {"text": "Microsoft ou Amazon lequel est le meilleur ?", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "MSFT", "symbol2": "AMZN", "period": "1y"}},
    {"text": "Compare Google et Tesla", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "GOOGL", "symbol2": "TSLA", "period": "1y"}},
    {"text": "Apple contre Meta", "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "META", "period": "1y"}},
    {"text": "Je veux voir la comparaison entre Amazon et Tesla", "expected_route": "tool",
     "expected_intent": "compare", "expected_args": {"symbol1": "AMZN", "symbol2": "TSLA", "period": "1y"}},

    # =========================
    # SCREENER (20)
    # =========================
    {"text": "Je cherche des actions technologiques en Europe", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions technologiques en Europe"}},
    {"text": "Trouve-moi des actions de santé aux États-Unis", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve-moi des actions de santé aux États-Unis"}},
    {"text": "Je veux un portefeuille d’actions européennes avec dividendes", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille d’actions européennes avec dividendes"}},
    {"text": "Montre-moi des actions américaines à faible volatilité", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions américaines à faible volatilité"}},
    {"text": "Je cherche des actions industrielles en Europe", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions industrielles en Europe"}},
    {"text": "Trouve des actions tech avec croissance élevée", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve des actions tech avec croissance élevée"}},
    {"text": "Je veux un screener d’actions défensives", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un screener d’actions défensives"}},
    {"text": "Montre-moi des actions européennes avec rendement élevé", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions européennes avec rendement élevé"}},
    {"text": "Je cherche des actions de croissance aux États-Unis", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions de croissance aux États-Unis"}},
    {"text": "Trouve des actions avec faible bêta en Europe", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve des actions avec faible bêta en Europe"}},
    {"text": "Je veux des actions de technologie sans énergie", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions de technologie sans énergie"}},
    {"text": "Montre-moi des actions de santé avec dividendes", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions de santé avec dividendes"}},
    {"text": "Je veux un portefeuille d’actions industrielles", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille d’actions industrielles"}},
    {"text": "Trouve des actions européennes dans la tech", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve des actions européennes dans la tech"}},
    {"text": "Je cherche des actions internationales défensives", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je cherche des actions internationales défensives"}},
    {"text": "Montre-moi des actions avec rendement et faible volatilité", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions avec rendement et faible volatilité"}},
    {"text": "Je veux des actions tech aux États-Unis", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions tech aux États-Unis"}},
    {"text": "Trouve des actions européennes à forte croissance", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Trouve des actions européennes à forte croissance"}},
    {"text": "Je veux filtrer des actions avec dividendes élevés", "expected_route": "tool",
     "expected_intent": "screener",
     "expected_args": {"description": "Je veux filtrer des actions avec dividendes élevés"}},
    {"text": "Montre-moi des actions de qualité en Europe", "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi des actions de qualité en Europe"}},

    # =========================
    # CHAT (20)
    # =========================
    {"text": "Qu'est-ce qu'un ETF ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi ce qu'est la volatilité en bourse", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Comment fonctionne le marché boursier ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "C'est quoi un dividende ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi la diversification en investissement", "expected_route": "chat",
     "expected_intent": "unknown", "expected_args": {}},
    {"text": "Quelle est la différence entre action et obligation ?", "expected_route": "chat",
     "expected_intent": "unknown", "expected_args": {}},
    {"text": "Peux-tu m'expliquer le ratio de Sharpe ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Qu'est-ce que la capitalisation boursière ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Pourquoi les actions montent et descendent ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Explique-moi ce qu'est un portefeuille équilibré", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Qu'est-ce que le risque en bourse ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Comment analyser une action ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Qu'est-ce que le bêta en finance ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Explique-moi la notion de rendement", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "C'est quoi un marché haussier ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "C'est quoi un marché baissier ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Comment fonctionne un indice boursier ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Qu'est-ce que le S&P 500 ?", "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
    {"text": "Explique-moi ce qu'est la gestion passive", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},
    {"text": "Pourquoi investir à long terme ?", "expected_route": "chat", "expected_intent": "unknown",
     "expected_args": {}},

]

BENCHMARK3 = [

    # =========================
    # PRICE COMPLEX (15)
    # =========================
    {"text": "Peux-tu me donner le dernier cours de Apple en bourse aujourd’hui ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AAPL"}},

    {"text": "Je veux savoir combien vaut Microsoft là maintenant",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "MSFT"}},

    {"text": "Donne-moi la cotation actuelle de Nvidia pour voir",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "NVDA"}},

    {"text": "Tesla ça cote combien en ce moment ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "TSLA"}},

    {"text": "Quel est le prix de Google aujourd’hui sur le marché ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "GOOGL"}},

    {"text": "Tu peux m’afficher le cours de Meta tout de suite ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "META"}},

    {"text": "Je veux le prix actuel de Amazon pour décider",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AMZN"}},

    {"text": "Montre-moi le cours de LVMH",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "MC.PA"}},

    {"text": "Quel est le prix de Air Liquide maintenant ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "AI.PA"}},

    {"text": "Donne-moi le cours de BNP Paribas",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "BNP.PA"}},

    {"text": "Je veux la valeur actuelle de ASML",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "ASML"}},

    {"text": "Affiche-moi le prix de SAP",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "SAP.DE"}},

    {"text": "Hermès vaut combien en bourse ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "RMS.PA"}},

    {"text": "Je veux connaître le prix de TotalEnergies",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "TTE.PA"}},

    {"text": "Peux-tu me sortir le cours de Société Générale ?",
     "expected_route": "tool", "expected_intent": "price", "expected_args": {"symbol": "GLE.PA"}},


    # =========================
    # STATS COMPLEX (15)
    # =========================
    {"text": "Je veux les stats complètes de Apple sur 5 ans",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AAPL", "period": "5y"}},

    {"text": "Montre-moi la volatilité de Microsoft sur 6 mois",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "MSFT", "period": "6mo"}},

    {"text": "Quel est le rendement de Nvidia sur 1 an ?",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "NVDA", "period": "1y"}},

    {"text": "Je veux la performance de Tesla sur 5 ans",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "TSLA", "period": "5y"}},

    {"text": "Affiche les indicateurs de Amazon sur 6 mois",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AMZN", "period": "6mo"}},

    {"text": "Peux-tu me donner le Sharpe ratio de Google sur 1 an ?",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "GOOGL", "period": "1y"}},

    {"text": "Je veux la volatilité de LVMH sur 1 an",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "MC.PA", "period": "1y"}},

    {"text": "Donne-moi les stats de Air Liquide sur 6 mois",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "AI.PA", "period": "6mo"}},

    {"text": "Je veux le rendement annualisé de BNP Paribas sur 5 ans",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "BNP.PA", "period": "5y"}},

    {"text": "Montre-moi les performances de ASML sur 1 an",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "ASML", "period": "1y"}},

    {"text": "Quelle volatilité pour SAP sur 6 mois ?",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "SAP.DE", "period": "6mo"}},

    {"text": "Je veux les statistiques de Hermès sur 5 ans",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "RMS.PA", "period": "5y"}},

    {"text": "Affiche les stats de TotalEnergies sur 1 an",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "TTE.PA", "period": "1y"}},

    {"text": "Donne-moi la performance de Société Générale sur 6 mois",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "GLE.PA", "period": "6mo"}},

    {"text": "Je veux voir les indicateurs de Nvidia sur 5 ans",
     "expected_route": "tool", "expected_intent": "stats", "expected_args": {"symbol": "NVDA", "period": "5y"}},


    # =========================
    # COMPARE COMPLEX (15)
    # =========================
    {"text": "Entre Apple et Microsoft, lequel a la meilleure performance sur 5 ans ?",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "MSFT", "period": "5y"}},

    {"text": "Compare Tesla et Nvidia sur 6 mois",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "NVDA", "period": "6mo"}},

    {"text": "Je veux une comparaison entre Amazon et Google sur 1 an",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AMZN", "symbol2": "GOOGL", "period": "1y"}},

    {"text": "Apple vs Meta sur 5 ans",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AAPL", "symbol2": "META", "period": "5y"}},

    {"text": "Microsoft ou Nvidia, lequel a le meilleur Sharpe sur 1 an ?",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "MSFT", "symbol2": "NVDA", "period": "1y"}},

    {"text": "Compare LVMH et Air Liquide sur 1 an",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "MC.PA", "symbol2": "AI.PA", "period": "1y"}},

    {"text": "Entre BNP Paribas et Société Générale, laquelle performe le mieux sur 5 ans ?",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "BNP.PA", "symbol2": "GLE.PA", "period": "5y"}},

    {"text": "ASML contre SAP sur 6 mois",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "ASML", "symbol2": "SAP.DE", "period": "6mo"}},

    {"text": "Compare TotalEnergies et Air Liquide sur 5 ans",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TTE.PA", "symbol2": "AI.PA", "period": "5y"}},

    {"text": "Air Liquide ou TotalEnergies, laquelle est la moins volatile sur 6 mois ?",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "AI.PA", "symbol2": "TTE.PA", "period": "6mo"}},

    {"text": "Hermès ou LVMH, lequel est le plus performant sur 1 an ?",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "RMS.PA", "symbol2": "MC.PA", "period": "1y"}},

    {"text": "Google contre Microsoft sur 6 mois",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "GOOGL", "symbol2": "MSFT", "period": "6mo"}},

    {"text": "Tesla ou Amazon, lequel a la meilleure perf sur 1 an ?",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "TSLA", "symbol2": "AMZN", "period": "1y"}},

    {"text": "Nvidia vs Apple sur 5 ans",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "NVDA", "symbol2": "AAPL", "period": "5y"}},

    {"text": "Je veux comparer BNP Paribas et ASML sur 1 an",
     "expected_route": "tool", "expected_intent": "compare",
     "expected_args": {"symbol1": "BNP.PA", "symbol2": "ASML", "period": "1y"}},


    # =========================
    # SCREENER COMPLEX (20)
    # =========================
    {"text": "Je veux un portefeuille d’actions européennes dans la santé sans la France",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille d’actions européennes dans la santé sans la France"}},

    {"text": "Construis-moi un screener d’actions US hors technologie avec faible volatilité",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Construis-moi un screener d’actions US hors technologie avec faible volatilité"}},

    {"text": "Je veux des actions asiatiques dans les semi-conducteurs",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions asiatiques dans les semi-conducteurs"}},

    {"text": "Trouve-moi des actions Europe santé et industrie mais sans banques",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve-moi des actions Europe santé et industrie mais sans banques"}},

    {"text": "Je veux un portefeuille actions monde hors États-Unis dans l’énergie",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille actions monde hors États-Unis dans l’énergie"}},

    {"text": "Donne-moi des actions européennes de qualité dans le luxe",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Donne-moi des actions européennes de qualité dans le luxe"}},

    {"text": "Je veux des actions US dans l’IA mais sans semiconducteurs",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions US dans l’IA mais sans semiconducteurs"}},

    {"text": "Montre-moi un screener d’actions Europe hors finance avec dividende élevé",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Montre-moi un screener d’actions Europe hors finance avec dividende élevé"}},

    {"text": "Je veux un portefeuille actions japonaises dans l’automobile",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille actions japonaises dans l’automobile"}},

    {"text": "Trouve des actions mondiales défensives sans technologie ni énergie",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve des actions mondiales défensives sans technologie ni énergie"}},

    {"text": "Je veux des actions européennes dans les banques et assurances",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions européennes dans les banques et assurances"}},

    {"text": "Construis-moi un screener d’actions USA santé avec market cap élevé",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Construis-moi un screener d’actions USA santé avec market cap élevé"}},

    {"text": "Je veux des actions Canada énergie sans pétrole",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions Canada énergie sans pétrole"}},

    {"text": "Trouve-moi des actions Asie hors Chine dans la tech",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve-moi des actions Asie hors Chine dans la tech"}},

    {"text": "Je veux un portefeuille actions Europe avec faible bêta hors France et hors Allemagne",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux un portefeuille actions Europe avec faible bêta hors France et hors Allemagne"}},

    {"text": "Portefeuille ETF bien classé avec performance rating de 4 ou 5 et risk rating de 1 ou 2",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Portefeuille ETF bien classé avec performance rating de 4 ou 5 et risk rating de 1 ou 2"}},

    {"text": "Je veux des ETF US avec bon rating et faible risque",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des ETF US avec bon rating et faible risque"}},

    {"text": "Trouve-moi des actions Europe santé sans biotech",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Trouve-moi des actions Europe santé sans biotech"}},

    {"text": "Je veux des actions américaines dans le cloud et la cybersécurité",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Je veux des actions américaines dans le cloud et la cybersécurité"}},

    {"text": "Construis un screener d’actions monde dans la défense et l’aéronautique",
     "expected_route": "tool", "expected_intent": "screener",
     "expected_args": {"description": "Construis un screener d’actions monde dans la défense et l’aéronautique"}},


    # =========================
    # CHAT / EXPLANATION / EDGE (15)
    # =========================
    {"text": "Explique-moi simplement ce qu’est la volatilité",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Quelle est la différence entre rendement et risque ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "C’est quoi un ETF capitalisant ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Explique-moi la différence entre action et ETF",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Comment lire une performance annualisée ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Je veux comprendre le ratio de Sharpe",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Pourquoi une action peut être plus volatile qu’une autre ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Explique-moi ce qu’est un portefeuille défensif",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Qu’est-ce qu’une diversification sectorielle ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Comment fonctionne un screener d’actions ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "C’est quoi la capitalisation boursière ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Explique-moi ce qu’est le bêta en finance",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Je voudrais comprendre la différence entre croissance et value",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Pourquoi investir à long terme change le risque ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},

    {"text": "Peux-tu m’expliquer comment comparer deux actions sans regarder seulement le prix ?",
     "expected_route": "chat", "expected_intent": "unknown", "expected_args": {}},
]

def args_exact_match(expected, predicted, intent=None):
    if not expected and not predicted:
        return True

    # Cas spécifique pour la comparaison
    if intent == "compare":
        e_pair = {expected.get("symbol1"), expected.get("symbol2")}
        p_pair = {predicted.get("symbol1"), predicted.get("symbol2")}
        return e_pair == p_pair and expected.get("period", "1y") == predicted.get("period", "1y")

    # Validation "Subset" : On vérifie que TOUT ce qui est attendu est là
    for key, value in expected.items():
        if predicted.get(key) != value:
            return False

    return True


@pytest_asyncio.fixture(scope="module")
async def ai_instance():
    ai = LocalController()
    await ai.initialize()
    return ai


@pytest_asyncio.fixture
async def session_id(ai_instance):
    sid = str(uuid.uuid4())[:8]
    await ai_instance.create_chat(sid)
    return sid


async def _run_router_case(ai_instance, session_id, sample):
    """
    Helper commun pour exécuter un cas benchmark.
    """
    response = await ai_instance.chat(session_id, sample["text"])
    time.sleep(2.0)

    if response.get("status") == "error":
        pytest.fail(f"Erreur API: {response.get('message')}")

    config = {"configurable": {"thread_id": session_id}}
    result_state = ai_instance.app.get_state(config)
    result = result_state.values

    pred_route = result.get("route")
    pred_intent = result.get("tool_intent")
    pred_args = result.get("tool_args", {})

    assert pred_route == sample["expected_route"], \
        f"Route incorrecte pour '{sample['text']}'"

    assert pred_intent == sample["expected_intent"], \
        f"Intention incorrecte pour '{sample['text']}'"

    assert args_exact_match(sample["expected_args"], pred_args, sample["expected_intent"]), \
        f"Arguments incorrects. Reçu: {pred_args}, Attendu: {sample['expected_args']}"


@pytest.mark.asyncio
@pytest.mark.parametrize("sample", BENCHMARK, ids=lambda s: s["text"])
async def test_semantic_router_case_benchmark1(ai_instance, session_id, sample):
    await _run_router_case(ai_instance, session_id, sample)


@pytest.mark.asyncio
@pytest.mark.parametrize("sample", BENCHMARK2, ids=lambda s: s["text"])
async def test_semantic_router_case_benchmark2(ai_instance, session_id, sample):
    await _run_router_case(ai_instance, session_id, sample)


@pytest.mark.asyncio
@pytest.mark.parametrize("sample", BENCHMARK3, ids=lambda s: s["text"])
async def test_semantic_router_case_benchmark3(ai_instance, session_id, sample):
    await _run_router_case(ai_instance, session_id, sample)