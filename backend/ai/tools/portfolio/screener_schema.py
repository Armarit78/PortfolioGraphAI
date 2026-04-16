from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set, Any, Mapping, Iterable, FrozenSet


# =============================================================================
# Helpers
# =============================================================================

def merge_two_level_dicts(
    base: Mapping[str, Set[str]],
    overlay: Mapping[str, Set[str]],
) -> Dict[str, Set[str]]:
    """
    Merge de deux dicts {category -> set(fields)}.
    - Les catégories absentes de base sont ajoutées.
    - Les sets sont unis (union).
    - Retourne un nouveau dict de sets (pas de mutation des inputs).
    """
    out: Dict[str, Set[str]] = {k: set(v) for k, v in base.items()}
    for k, v in overlay.items():
        if k not in out:
            out[k] = set(v)
        else:
            out[k].update(v)
    return out


def _flatten(iterables: Iterable[Iterable[str]]) -> Set[str]:
    s: Set[str] = set()
    for it in iterables:
        s.update(it)
    return s


def yahoo_suffix_with_dot_from_mic(mic: str) -> str:
    """
    Retourne '.PA' etc à partir d'un MIC.
    (Compat avec l'ancienne map MIC->suffix sans point.)
    """
    suf = _MIC_TO_YAHOO_SUFFIX.get(mic, "")
    return f".{suf}" if suf else ""


# =============================================================================
# Dictionnaires bruts (repris de Yahoo Finance / yfinance)
# =============================================================================

fundamentals_keys = {
    "financials": [
        "TaxEffectOfUnusualItems", "TaxRateForCalcs", "NormalizedEBITDA", "NormalizedDilutedEPS",
        "NormalizedBasicEPS", "TotalUnusualItems", "TotalUnusualItemsExcludingGoodwill",
        "NetIncomeFromContinuingOperationNetMinorityInterest", "ReconciledDepreciation",
        "ReconciledCostOfRevenue", "EBITDA", "EBIT", "NetInterestIncome", "InterestExpense",
        "InterestIncome", "ContinuingAndDiscontinuedDilutedEPS", "ContinuingAndDiscontinuedBasicEPS",
        "NormalizedIncome", "NetIncomeFromContinuingAndDiscontinuedOperation", "TotalExpenses",
        "RentExpenseSupplemental", "ReportedNormalizedDilutedEPS", "ReportedNormalizedBasicEPS",
        "TotalOperatingIncomeAsReported", "DividendPerShare", "DilutedAverageShares", "BasicAverageShares",
        "DilutedEPS", "DilutedEPSOtherGainsLosses", "TaxLossCarryforwardDilutedEPS",
        "DilutedAccountingChange", "DilutedExtraordinary", "DilutedDiscontinuousOperations",
        "DilutedContinuousOperations", "BasicEPS", "BasicEPSOtherGainsLosses", "TaxLossCarryforwardBasicEPS",
        "BasicAccountingChange", "BasicExtraordinary", "BasicDiscontinuousOperations",
        "BasicContinuousOperations", "DilutedNIAvailtoComStockholders", "AverageDilutionEarnings",
        "NetIncomeCommonStockholders", "OtherunderPreferredStockDividend", "PreferredStockDividends",
        "NetIncome", "MinorityInterests", "NetIncomeIncludingNoncontrollingInterests",
        "NetIncomeFromTaxLossCarryforward", "NetIncomeExtraordinary", "NetIncomeDiscontinuousOperations",
        "NetIncomeContinuousOperations", "EarningsFromEquityInterestNetOfTax", "TaxProvision",
        "PretaxIncome", "OtherIncomeExpense", "OtherNonOperatingIncomeExpenses", "SpecialIncomeCharges",
        "GainOnSaleOfPPE", "GainOnSaleOfBusiness", "OtherSpecialCharges", "WriteOff",
        "ImpairmentOfCapitalAssets", "RestructuringAndMergernAcquisition", "SecuritiesAmortization",
        "EarningsFromEquityInterest", "GainOnSaleOfSecurity", "NetNonOperatingInterestIncomeExpense",
        "TotalOtherFinanceCost", "InterestExpenseNonOperating", "InterestIncomeNonOperating",
        "OperatingIncome", "OperatingExpense", "OtherOperatingExpenses", "OtherTaxes",
        "ProvisionForDoubtfulAccounts", "DepreciationAmortizationDepletionIncomeStatement",
        "DepletionIncomeStatement", "DepreciationAndAmortizationInIncomeStatement", "Amortization",
        "AmortizationOfIntangiblesIncomeStatement", "DepreciationIncomeStatement", "ResearchAndDevelopment",
        "SellingGeneralAndAdministration", "SellingAndMarketingExpense", "GeneralAndAdministrativeExpense",
        "OtherGandA", "InsuranceAndClaims", "RentExpenseSupplemental", "SalariesAndWages", "GrossProfit",
        "CostOfRevenue", "TotalRevenue",
    ],
    "balance-sheet": [
        "TreasurySharesNumber", "PreferredSharesNumber", "OrdinarySharesNumber", "ShareIssued", "NetDebt",
        "TotalDebt", "TangibleBookValue", "InvestedCapital", "WorkingCapital", "NetTangibleAssets",
        "CommonStockEquity", "PreferredStockEquity", "TotalCapitalization", "TotalEquityGrossMinorityInterest",
        "MinorityInterest", "StockholdersEquity", "RetainedEarnings", "AdditionalPaidInCapital",
        "TotalLiabilitiesNetMinorityInterest", "TotalNonCurrentLiabilitiesNetMinorityInterest",
        "CurrentLiabilities", "AccountsPayable", "TotalAssets", "TotalNonCurrentAssets",
        "CurrentAssets", "Inventory", "Receivables", "AccountsReceivable",
        "CashCashEquivalentsAndShortTermInvestments", "CashAndCashEquivalents",
    ],
    "cash-flow": [
        "FreeCashFlow", "RepurchaseOfCapitalStock", "RepaymentOfDebt", "IssuanceOfDebt",
        "IssuanceOfCapitalStock", "CapitalExpenditure", "EndCashPosition", "BeginningCashPosition",
        "ChangesInCash", "FinancingCashFlow", "InvestingCashFlow", "OperatingCashFlow",
        "ChangeInWorkingCapital", "StockBasedCompensation", "DepreciationAndAmortization",
        "NetIncomeFromContinuingOperations",
    ],
}

_PRICE_COLNAMES_ = {"Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"}

quote_summary_valid_modules = {
    "assetProfile", "balanceSheetHistory", "balanceSheetHistoryQuarterly", "calendarEvents",
    "cashflowStatementHistory", "cashflowStatementHistoryQuarterly", "defaultKeyStatistics",
    "earnings", "earningsHistory", "earningsTrend", "esgScores", "financialData",
    "fundOwnership", "fundPerformance", "fundProfile", "incomeStatementHistory",
    "incomeStatementHistoryQuarterly", "indexTrend", "industryTrend", "insiderHolders",
    "insiderTransactions", "institutionOwnership", "majorDirectHolders",
    "majorHoldersBreakdown", "netSharePurchaseActivity", "price", "quoteType",
    "recommendationTrend", "secFilings", "sectorTrend", "summaryDetail", "summaryProfile",
    "topHoldings", "upgradeDowngradeHistory", "pageViews",
}

# =============================================================================
# Mapping secteurs / industries (equity)
# =============================================================================
SECTOR_INDUSTRY_MAPPING = {
    'Basic Materials': {'Specialty Chemicals',
                        'Gold',
                        'Building Materials',
                        'Copper',
                        'Steel',
                        'Agricultural Inputs',
                        'Chemicals',
                        'Other Industrial Metals & Mining',
                        'Lumber & Wood Production',
                        'Aluminum',
                        'Other Precious Metals & Mining',
                        'Coking Coal',
                        'Paper & Paper Products',
                        'Silver'},
    'Communication Services': {'Advertising Agencies',
                                'Broadcasting',
                                'Electronic Gaming & Multimedia',
                                'Entertainment',
                                'Internet Content & Information',
                                'Publishing',
                                'Telecom Services'},
    'Consumer Cyclical': {'Apparel Manufacturing',
                            'Apparel Retail',
                            'Auto & Truck Dealerships',
                            'Auto Manufacturers',
                            'Auto Parts',
                            'Department Stores',
                            'Footwear & Accessories',
                            'Furnishings, Fixtures & Appliances',
                            'Gambling',
                            'Home Improvement Retail',
                            'Internet Retail',
                            'Leisure',
                            'Lodging',
                            'Luxury Goods',
                            'Packaging & Containers',
                            'Personal Services',
                            'Recreational Vehicles',
                            'Residential Construction',
                            'Resorts & Casinos',
                            'Restaurants',
                            'Specialty Retail',
                            'Textile Manufacturing',
                            'Travel Services'},
    'Consumer Defensive': {'Beverages—Brewers',
                            'Beverages—Non-Alcoholic',
                            'Beverages—Wineries & Distilleries',
                            'Confectioners',
                            'Discount Stores',
                            'Education & Training Services',
                            'Farm Products',
                            'Food Distribution',
                            'Grocery Stores',
                            'Household & Personal Products',
                            'Packaged Foods',
                            'Tobacco'},
    'Energy': {'Oil & Gas Drilling',
                'Oil & Gas E&P',
                'Oil & Gas Equipment & Services',
                'Oil & Gas Integrated',
                'Oil & Gas Midstream',
                'Oil & Gas Refining & Marketing',
                'Thermal Coal',
                'Uranium'},
    'Financial Services': {'Asset Management',
                            'Banks—Diversified',
                            'Banks—Regional',
                            'Capital Markets',
                            'Credit Services',
                            'Financial Conglomerates',
                            'Financial Data & Stock Exchanges',
                            'Insurance Brokers',
                            'Insurance—Diversified',
                            'Insurance—Life',
                            'Insurance—Property & Casualty',
                            'Insurance—Reinsurance',
                            'Insurance—Specialty',
                            'Mortgage Finance',
                            'Shell Companies'},
    'Healthcare': {'Biotechnology',
                    'Diagnostics & Research',
                    'Drug Manufacturers—General',
                    'Drug Manufacturers—Specialty & Generic',
                    'Health Information Services',
                    'Healthcare Plans',
                    'Medical Care Facilities',
                    'Medical Devices',
                    'Medical Instruments & Supplies',
                    'Medical Distribution',
                    'Pharmaceutical Retailers'},
    'Industrials': {'Aerospace & Defense',
                    'Airlines',
                    'Airports & Air Services',
                    'Building Products & Equipment',
                    'Business Equipment & Supplies',
                    'Conglomerates',
                    'Consulting Services',
                    'Electrical Equipment & Parts',
                    'Engineering & Construction',
                    'Farm & Heavy Construction Machinery',
                    'Industrial Distribution',
                    'Infrastructure Operations',
                    'Integrated Freight & Logistics',
                    'Marine Shipping',
                    'Metal Fabrication',
                    'Pollution & Treatment Controls',
                    'Railroads',
                    'Rental & Leasing Services',
                    'Security & Protection Services',
                    'Specialty Business Services',
                    'Specialty Industrial Machinery',
                    'Staffing & Employment Services',
                    'Tools & Accessories',
                    'Trucking',
                    'Waste Management'},
    'Real Estate': {'Real Estate—Development',
                    'Real Estate Services',
                    'Real Estate—Diversified',
                    'REIT—Healthcare Facilities',
                    'REIT—Hotel & Motel',
                    'REIT—Industrial',
                    'REIT—Office',
                    'REIT—Residential',
                    'REIT—Retail',
                    'REIT—Mortgage',
                    'REIT—Specialty',
                    'REIT—Diversified'},
    'Technology': {'Communication Equipment',
                    'Computer Hardware',
                    'Consumer Electronics',
                    'Electronic Components',
                    'Electronics & Computer Distribution',
                    'Information Technology Services',
                    'Scientific & Technical Instruments',
                    'Semiconductor Equipment & Materials',
                    'Semiconductors',
                    'Software—Application',
                    'Software—Infrastructure',
                    'Solar'},
    'Utilities': {'Utilities—Diversified',
                    'Utilities—Independent Power Producers',
                    'Utilities—Regulated Electric',
                    'Utilities—Regulated Gas',
                    'Utilities—Regulated Water',
                    'Utilities—Renewable'},
}

# Lowercase mapping (utile pour matching flexible côté LLM)
SECTOR_INDUSTRY_MAPPING_LC: Dict[str, Set[str]] = {
    k.lower(): {x.lower() for x in v} for k, v in SECTOR_INDUSTRY_MAPPING.items()
}

# =============================================================================
# Mapping MIC -> suffix Yahoo (ANCIENNE MÉTHODE : SANS POINT)
# IMPORTANT : on garde la forme "PA", "AS", ... (pas ".PA") pour compat historique.
# =============================================================================

_MIC_TO_YAHOO_SUFFIX: Dict[str, str] = {
    "XCBT": "CBT", "XCME": "CME", "IFUS": "NYB", "CECS": "CMX", "XNYM": "NYM", "XNYS": "", "XNAS": "",
    "XBUE": "BA", "XVIE": "VI", "XASX": "AX", "XAUS": "XA", "XBRU": "BR", "BVMF": "SA",
    "CNSX": "CN", "NEOE": "NE", "XTSE": "TO", "XTSX": "V", "XSGO": "SN",
    "XSHG": "SS", "XSHE": "SZ", "XBOG": "CL", "XPRA": "PR", "XCSE": "CO", "XCAI": "CA", "XTAL": "TL",
    "CEUX": "XD", "XEUR": "NX", "XHEL": "HE", "XPAR": "PA",
    "XBER": "BE", "XBMS": "BM", "XDUS": "DU", "XFRA": "F", "XHAM": "HM", "XHAN": "HA", "XMUN": "MU",
    "XSTU": "SG", "XETR": "DE", "XATH": "AT", "XHKG": "HK", "XBUD": "BD", "XICE": "IC",
    "XBOM": "BO", "XNSE": "NS", "XIDX": "JK", "XDUB": "IR", "XTAE": "TA",
    "MTAA": "MI", "EUTL": "TI", "XTKS": "T", "XKFE": "KW", "XRIS": "RG", "XVIL": "VS", "XKLS": "KL",
    "XMEX": "MX", "XAMS": "AS", "XOSL": "OL", "XPHS": "PS", "XWAR": "WA", "XLIS": "LS", "XQAT": "QA",
    "XBSE": "RO", "XSES": "SI", "XJSE": "JO", "XKRX": "KS", "KQKS": "KQ", "BMEX": "MC", "XTAD": "SAU",
    "XSTO": "ST", "XSWX": "SW", "ROCO": "TWO", "XTAI": "TW", "XBKK": "BK", "XIST": "IS", "XDFM": "AE",
    "AQXE": "AQ", "XCHI": "XC", "XLON": "L", "ILSE": "IL", "XCAR": "CR", "XSTC": "VN",
}

# =============================================================================
# Screener maps (equity / fund)
# =============================================================================

# ---- EQUITY ----
# ✅ region = PAYS (clé "ar", "fr", "de", ...) — c'est ce qui rend "EUROPE sans FRANCE" possible.
# ✅ exchange = {pays -> set(exchanges Yahoo)} (ancienne méthode)
EQUITY_SCREENER_EQ_MAP: Dict[str, Any] = {
    "exchange": {
        "ar": {"BUE"},
        "at": {"VIE"},
        "au": {"ASX"},
        "be": {"BRU"},
        "br": {"SAO"},
        "ca": {"CNQ", "NEO", "TOR", "VAN"},
        "ch": {"EBS"},
        "cl": {"SGO"},
        "cn": {"SHH", "SHZ"},
        "co": {"BVC"},
        "cz": {"PRA"},
        "de": {"BER", "DUS", "FRA", "HAM", "GER", "MUN", "STU"},
        "dk": {"CPH"},
        "ee": {"TAL"},
        "eg": {"CAI"},
        "es": {"MCE"},
        "fi": {"HEL"},
        "fr": {"PAR"},
        "gb": {"AQS", "IOB", "LSE"},
        "gr": {"ATH"},
        "hk": {"HKG"},
        "hu": {"BUD"},
        "id": {"JKT"},
        "ie": {"ISE"},
        "il": {"TLV"},
        "in": {"BSE", "NSI"},
        "is": {"ICE"},
        "it": {"MIL"},
        "jp": {"FKA", "JPX", "SAP"},
        "kr": {"KOE", "KSC"},
        "kw": {"KUW"},
        "lk": set(),
        "lt": {"LIT"},
        "lv": {"RIS"},
        "mx": {"MEX"},
        "my": {"KLS"},
        "nl": {"AMS"},
        "no": {"OSL"},
        "nz": {"NZE"},
        "pe": set(),
        "ph": {"PHP", "PHS"},
        "pk": set(),
        "pl": {"WSE"},
        "pt": {"LIS"},
        "qa": {"DOH"},
        "ro": {"BVB"},
        "ru": set(),
        "sa": {"SAU"},
        "se": {"STO"},
        "sg": {"SES"},
        "sr": set(),
        "sw": {"EBS"},
        "th": {"SET"},
        "tr": {"IST"},
        "tw": {"TAI", "TWO"},
        "us": {"ASE", "BTS", "CXI", "NCM", "NGM", "NMS", "NYQ", "OEM", "OQB", "OQX", "PCX", "PNK", "YHD"},
        "ve": {"CCS"},
        "vn": set(),
        "za": {"JNB"},
    },
    "sector": set(SECTOR_INDUSTRY_MAPPING.keys()),
    "industry": SECTOR_INDUSTRY_MAPPING,
    "peer_group": set(),  # si tu l'utilises, remplis-le ici
}

# ✅ region matérialisée comme liste des pays (comme avant)
EQUITY_SCREENER_EQ_MAP["region"] = list(EQUITY_SCREENER_EQ_MAP["exchange"].keys())

# Optionnel : garder "region" en premier
ordered_keys = ["region"] + [k for k in EQUITY_SCREENER_EQ_MAP.keys() if k != "region"]
EQUITY_SCREENER_EQ_MAP = {k: EQUITY_SCREENER_EQ_MAP[k] for k in ordered_keys}

# ---- MACRO GROUPES (NOUVEAU, SANS CASSER) ----
# Utilisé par ton builder/LLM : "EUROPE" -> liste de pays -> contraintes region is-in [...]
REGION_GROUPS: Dict[str, Set[str]] = {
    "USA": {"us"},
    "CANADA": {"ca"},
    "EUROPE": {
        "at", "be", "ch", "cz", "de", "dk", "ee", "es", "fi", "fr", "gb", "gr", "ie", "is",
        "it", "lt", "lv", "nl", "no", "pl", "pt", "ro", "se", "tr",
    },
    "ASIA": {"cn", "hk", "id", "in", "jp", "kr", "my", "ph", "sg", "th", "tw", "vn"},
    "LATAM": {"ar", "br", "cl", "co", "mx", "ve", "pe"},
    "MIDDLE_EAST": {"il", "sa", "qa", "kw"},
    "AFRICA": {"eg", "za"},
    "AUSTRALIA": {"au", "nz"},
}

ALLOWED_REGION_GROUPS = sorted(REGION_GROUPS.keys())

# ---- FUND ----
# Ici tu peux garder ta logique macro (Yahoo FundQuery aime bien les regroupements).
FUND_SCREENER_EQ_MAP: Dict[str, Any] = {
    "exchange": {
        "USA": {"NAS", "NYS"},
        "EUROPE": {"EUR"},
        "ASIA": {"ASI"},
        "LATAM": {"LAM"},
        "CANADA": {"CAN"},
        "AUSTRALIA": {"AUS"},
        "MIDDLE_EAST": set(),
        "AFRICA": set(),
    }
}

# =============================================================================
# Screener fields (COMMON / EQUITY / FUND)
# =============================================================================
COMMON_SCREENER_FIELDS = {
    "price":{
        "eodprice",
        "intradaypricechange",
        "intradayprice"
    },
    "eq_fields": {
        "exchange"},
}

FUND_SCREENER_FIELDS: Dict[str, Set[str]] = {
    "price": {
        "ytdreturn",
        "oneyearreturn",
        "threeyearreturn",
        "fiveyearreturn",
        "tenyearreturn",
        "alpha3y",
        "alpha5y",
        "alpha10y",
        "beta3y",
        "beta5y",
        "beta10y",
        "meanannualreturn3y",
        "meanannualreturn5y",
        "meanannualreturn10y",
        "annualholdingsTurnover",
        "morningstarOverallRating",
        "morningstarRiskRating",
        "morningstarRatingOverall",
        "morningstarRiskRatingOverall",
        "maxfrontload",
        "maxdeferredload",
        "annualreportexpense",
        "annualreportgrossexpense",
        "annualreportnetexpense",
        "annualreporttotalannualoperatingexpense",
        "categoryname",
        "riskratingoverall",
        "performanceratingoverall",
        "initialinvestment",
        "annualreturnnavy1categoryrank",
    }
}
EQUITY_SCREENER_FIELDS = {
    "eq_fields": {
        "region",
        "sector",
        "peer_group",
        "industry"},
    "price":{
        "lastclosemarketcap.lasttwelvemonths",
        "percentchange",
        "lastclose52weekhigh.lasttwelvemonths",
        "fiftytwowkpercentchange",
        "lastclose52weeklow.lasttwelvemonths",
        "intradaymarketcap"},
    "trading":{
        "beta",
        "avgdailyvol3m",
        "pctheldinsider",
        "pctheldinst",
        "dayvolume",
        "eodvolume"},
    "short_interest":{
        "short_percentage_of_shares_outstanding.value",
        "short_interest.value",
        "short_percentage_of_float.value",
        "days_to_cover_short.value",
        "short_interest_percentage_change.value"},
    "valuation":{
        "bookvalueshare.lasttwelvemonths",
        "lastclosemarketcaptotalrevenue.lasttwelvemonths",
        "lastclosetevtotalrevenue.lasttwelvemonths",
        "pricebookratio.quarterly",
        "peratio.lasttwelvemonths",
        "lastclosepricetangiblebookvalue.lasttwelvemonths",
        "lastclosepriceearnings.lasttwelvemonths",
        "pegratio_5y"},
    "profitability":{
        "consecutive_years_of_dividend_growth_count",
        "returnonassets.lasttwelvemonths",
        "returnonequity.lasttwelvemonths",
        "forward_dividend_per_share",
        "forward_dividend_yield",
        "returnontotalcapital.lasttwelvemonths"},
    "leverage":{
        "lastclosetevebit.lasttwelvemonths",
        "netdebtebitda.lasttwelvemonths",
        "totaldebtequity.lasttwelvemonths",
        "ltdebtequity.lasttwelvemonths",
        "ebitinterestexpense.lasttwelvemonths",
        "ebitdainterestexpense.lasttwelvemonths",
        "lastclosetevebitda.lasttwelvemonths",
        "totaldebtebitda.lasttwelvemonths"},
    "liquidity":{
        "quickratio.lasttwelvemonths",
        "altmanzscoreusingtheaveragestockinformationforaperiod.lasttwelvemonths",
        "currentratio.lasttwelvemonths",
        "operatingcashflowtocurrentliabilities.lasttwelvemonths"},
    "income_statement":{
        "totalrevenues.lasttwelvemonths",
        "netincomemargin.lasttwelvemonths",
        "grossprofit.lasttwelvemonths",
        "ebitda1yrgrowth.lasttwelvemonths",
        "dilutedepscontinuingoperations.lasttwelvemonths",
        "quarterlyrevenuegrowth.quarterly",
        "epsgrowth.lasttwelvemonths",
        "netincomeis.lasttwelvemonths",
        "ebitda.lasttwelvemonths",
        "dilutedeps1yrgrowth.lasttwelvemonths",
        "totalrevenues1yrgrowth.lasttwelvemonths",
        "operatingincome.lasttwelvemonths",
        "netincome1yrgrowth.lasttwelvemonths",
        "grossprofitmargin.lasttwelvemonths",
        "ebitdamargin.lasttwelvemonths",
        "ebit.lasttwelvemonths",
        "basicepscontinuingoperations.lasttwelvemonths",
        "netepsbasic.lasttwelvemonths"
        "netepsdiluted.lasttwelvemonths"},
    "balance_sheet":{
        "totalassets.lasttwelvemonths",
        "totalcommonsharesoutstanding.lasttwelvemonths",
        "totaldebt.lasttwelvemonths",
        "totalequity.lasttwelvemonths",
        "totalcurrentassets.lasttwelvemonths",
        "totalcashandshortterminvestments.lasttwelvemonths",
        "totalcommonequity.lasttwelvemonths",
        "totalcurrentliabilities.lasttwelvemonths",
        "totalsharesoutstanding"},
    "cash_flow":{
        "forward_dividend_yield",
        "leveredfreecashflow.lasttwelvemonths",
        "capitalexpenditure.lasttwelvemonths",
        "cashfromoperations.lasttwelvemonths",
        "leveredfreecashflow1yrgrowth.lasttwelvemonths",
        "unleveredfreecashflow.lasttwelvemonths",
        "cashfromoperations1yrgrowth.lasttwelvemonths"},
    "esg":{
        "esg_score",
        "environmental_score",
        "governance_score",
        "social_score",
        "highest_controversy"}
}
# Important: COMMON fields fusionnés dans EQUITY (comme avant)
EQUITY_SCREENER_FIELDS = merge_two_level_dicts(EQUITY_SCREENER_FIELDS, COMMON_SCREENER_FIELDS)

# =============================================================================
# POO: Schema + Whitelists (sans casser les constantes module-level)
# =============================================================================

@dataclass(frozen=True)
class ScreenerWhitelists:
    # Equity
    allowed_eq_categorical_fields: FrozenSet[str]
    allowed_eq_numeric_fields: FrozenSet[str]
    allowed_regions: FrozenSet[str]           # pays (ar, fr, de...)
    allowed_region_groups: FrozenSet[str]     # macro (EUROPE, USA...)
    allowed_sectors: FrozenSet[str]
    allowed_industries: FrozenSet[str]
    allowed_eq_exchanges: FrozenSet[str]

    # Fund
    allowed_fund_categorical_fields: FrozenSet[str]
    allowed_fund_numeric_fields: FrozenSet[str]
    allowed_fund_exchanges: FrozenSet[str]
    allowed_fund_regions: FrozenSet[str]


@dataclass(frozen=True)
class ScreenerSchema:
    """
    Conteneur POO pour rendre explicites les sources de vérité.
    """
    equity_map: Mapping[str, Any]
    fund_map: Mapping[str, Any]
    equity_fields: Mapping[str, Set[str]]
    fund_fields: Mapping[str, Set[str]]
    sector_industry_mapping: Mapping[str, Set[str]]
    region_groups: Mapping[str, Set[str]]

    def build_whitelists(self) -> ScreenerWhitelists:
        # --- EQUITY ---
        allowed_eq_categorical_fields = frozenset({"region", "exchange", "sector", "industry", "peer_group"})

        # ✅ "region" = pays
        allowed_regions = frozenset(sorted(list(self.equity_map["region"])))
        allowed_region_groups = frozenset(sorted(list(self.region_groups.keys())))

        allowed_sectors = frozenset(sorted(list(self.equity_map["sector"])))
        allowed_industries = frozenset(
            sorted({ind for inds in self.sector_industry_mapping.values() for ind in inds})
        )

        eq_numeric = set()
        for k in (
            "price",
            "trading",
            "short_interest",
            "valuation",
            "profitability",
            "leverage",
            "liquidity",
            "income_statement",
            "balance_sheet",
            "cash_flow",
            "esg",
        ):
            eq_numeric |= set(self.equity_fields.get(k, set()))
        allowed_eq_numeric_fields = frozenset(sorted(eq_numeric))

        # Exchanges equity: union des codes sur toutes les régions/pays
        ex_union = {ex for ex_set in self.equity_map["exchange"].values() for ex in ex_set}
        allowed_eq_exchanges = frozenset(sorted(ex_union))

        # --- FUND ---
        allowed_fund_categorical_fields = frozenset({"exchange", "categoryname"})

        fund_numeric = {
            "performanceratingoverall",
            "initialinvestment",
            "annualreturnnavy1categoryrank",
            "riskratingoverall",
        } | set(self.fund_fields.get("price", set()))
        allowed_fund_numeric_fields = frozenset(sorted(fund_numeric))

        fund_ex_union = {ex for ex_set in self.fund_map["exchange"].values() for ex in ex_set}
        allowed_fund_exchanges = frozenset(sorted(fund_ex_union))

        allowed_fund_regions = frozenset(sorted(list(self.fund_map["exchange"].keys())))

        return ScreenerWhitelists(
            # equity
            allowed_eq_categorical_fields=allowed_eq_categorical_fields,
            allowed_eq_numeric_fields=allowed_eq_numeric_fields,
            allowed_regions=allowed_regions,
            allowed_region_groups=allowed_region_groups,
            allowed_sectors=allowed_sectors,
            allowed_industries=allowed_industries,
            allowed_eq_exchanges=allowed_eq_exchanges,
            # fund
            allowed_fund_categorical_fields=allowed_fund_categorical_fields,
            allowed_fund_numeric_fields=allowed_fund_numeric_fields,
            allowed_fund_exchanges=allowed_fund_exchanges,
            allowed_fund_regions=allowed_fund_regions,
        )


DEFAULT_SCHEMA = ScreenerSchema(
    equity_map=EQUITY_SCREENER_EQ_MAP,
    fund_map=FUND_SCREENER_EQ_MAP,
    equity_fields=EQUITY_SCREENER_FIELDS,
    fund_fields=FUND_SCREENER_FIELDS,
    sector_industry_mapping=SECTOR_INDUSTRY_MAPPING,
    region_groups=REGION_GROUPS,
)

DEFAULT_WHITELISTS = DEFAULT_SCHEMA.build_whitelists()

# =============================================================================
# Constantes dérivées (whitelists) — COMPAT STRICTE AVEC L'EXISTANT
# =============================================================================

# --- EQUITY ---
ALLOWED_EQ_CATEGORICAL_FIELDS = set(DEFAULT_WHITELISTS.allowed_eq_categorical_fields)

ALLOWED_REGIONS = sorted(list(DEFAULT_WHITELISTS.allowed_regions))            # pays
ALLOWED_REGION_GROUPS = sorted(list(DEFAULT_WHITELISTS.allowed_region_groups))# macro
ALLOWED_SECTORS = sorted(list(DEFAULT_WHITELISTS.allowed_sectors))
ALLOWED_INDUSTRIES = sorted(list(DEFAULT_WHITELISTS.allowed_industries))

ALLOWED_EQ_NUMERIC_FIELDS = sorted(list(DEFAULT_WHITELISTS.allowed_eq_numeric_fields))
ALLOWED_EQ_EXCHANGES = sorted(list(DEFAULT_WHITELISTS.allowed_eq_exchanges))

# --- FUND (FundQuery) ---
ALLOWED_FUND_CATEGORICAL_FIELDS = set(DEFAULT_WHITELISTS.allowed_fund_categorical_fields)
ALLOWED_FUND_NUMERIC_FIELDS = sorted(list(DEFAULT_WHITELISTS.allowed_fund_numeric_fields))
ALLOWED_FUND_EXCHANGES = sorted(list(DEFAULT_WHITELISTS.allowed_fund_exchanges))
ALLOWED_FUND_REGIONS = sorted(list(DEFAULT_WHITELISTS.allowed_fund_regions))

# =============================================================================
# Exports (compat)
# =============================================================================

__all__ = [
    # raw stuff
    "fundamentals_keys",
    "_PRICE_COLNAMES_",
    "quote_summary_valid_modules",
    "SECTOR_INDUSTRY_MAPPING",
    "SECTOR_INDUSTRY_MAPPING_LC",
    "_MIC_TO_YAHOO_SUFFIX",
    # helpers
    "merge_two_level_dicts",
    "_flatten",
    "yahoo_suffix_with_dot_from_mic",
    # maps / fields
    "EQUITY_SCREENER_EQ_MAP",
    "FUND_SCREENER_EQ_MAP",
    "COMMON_SCREENER_FIELDS",
    "EQUITY_SCREENER_FIELDS",
    "FUND_SCREENER_FIELDS",
    # macro groups (nouveau, sans casser)
    "REGION_GROUPS",
    "ALLOWED_REGION_GROUPS",
    # POO
    "ScreenerSchema",
    "ScreenerWhitelists",
    "DEFAULT_SCHEMA",
    "DEFAULT_WHITELISTS",
    # whitelists (importées par screener_llm)
    "ALLOWED_EQ_CATEGORICAL_FIELDS",
    "ALLOWED_EQ_NUMERIC_FIELDS",
    "ALLOWED_REGIONS",
    "ALLOWED_SECTORS",
    "ALLOWED_INDUSTRIES",
    "ALLOWED_EQ_EXCHANGES",
    "ALLOWED_FUND_CATEGORICAL_FIELDS",
    "ALLOWED_FUND_NUMERIC_FIELDS",
    "ALLOWED_FUND_EXCHANGES",
    "ALLOWED_FUND_REGIONS",
]