from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple, Set, Callable
import json
import re

from backend.ai.tools.portfolio.screener_schema import (
    # Equity
    ALLOWED_REGIONS,
    ALLOWED_SECTORS,
    ALLOWED_INDUSTRIES,
    ALLOWED_EQ_NUMERIC_FIELDS,
    ALLOWED_EQ_CATEGORICAL_FIELDS,
    ALLOWED_EQ_EXCHANGES,
    SECTOR_INDUSTRY_MAPPING,
    # Fund
    ALLOWED_FUND_NUMERIC_FIELDS,
    ALLOWED_FUND_CATEGORICAL_FIELDS,
    ALLOWED_FUND_EXCHANGES,
)


# ---------------------------------------------------------------------
# NEW (schema refacto): region groups (macro -> pays)
# ---------------------------------------------------------------------
try:
    from backend.ai.tools.portfolio.screener_schema import REGION_GROUPS, ALLOWED_REGION_GROUPS
except Exception:
    REGION_GROUPS: Dict[str, Set[str]] = {}
    ALLOWED_REGION_GROUPS: Set[str] = set()

ALLOWED_OPERATORS = {"gte", "lte", "gt", "lt", "eq", "is-in", "btwn"}
ALLOWED_UNIVERSES = {"equity", "fund"}

# ---- Normalisation (equity) : labels "humains" -> codes Yahoo screener
EQUITY_EXCHANGE_ALIASES: Dict[str, str] = {
    # US
    "nyse": "NYQ",
    "new york stock exchange": "NYQ",
    "nasdaq": "NMS",
    # Paris / Euronext
    "euronext paris": "PAR",
    "euronext": "PAR",
    "paris": "PAR",
    "xpar": "PAR",
    "par": "PAR",
    # London
    "london": "LON",
    "lse": "LON",
}

# Champs volume (equity) souvent hallucinés / surinterprétés
EQUITY_VOLUME_FIELDS = {"dayvolume", "eodvolume", "avgdailyvol3m"}

# Champs equity utiles (garde la logique existante)
EQUITY_MARKETCAP_FIELD = "lastclosemarketcap.lasttwelvemonths"
EQUITY_REVENUES_FIELD = "totalrevenues.lasttwelvemonths"

# ---------------------------------------------------------------------
# Europe candidates (pays) — SOURCE DE VÉRITÉ = schema REGION_GROUPS["EUROPE"]
# (utilisé pour exclusions "sans Europe" + fallback interne si besoin)
# ---------------------------------------------------------------------
_EUROPE_REGION_CANDIDATES: Set[str] = set(REGION_GROUPS.get("EUROPE", set()))

# Liste indicative “bourses européennes” (codes equity Yahoo) — conservée (guardrail/fallback notes)
_EUROPE_EQUITY_EXCHANGES_HINT: List[str] = [
    "PAR", "AMS", "BRU", "FRA", "GER", "DUS", "MUN", "STU",
    "MIL", "LON", "IOB", "AQS", "CPH", "STO", "HEL", "OSL",
    "LIS", "ISE", "ATH", "WSE", "PRA", "BUD", "EBS",
]

# --- Regex géo (strict + robust)
_RE_US = re.compile(r"\b(us|usa|u\.s\.a\.|u\.s\.|united\s+states)\b", re.IGNORECASE)
_RE_US_FR = re.compile(r"\b(etats?-unis|états?-unis)\b", re.IGNORECASE)

# optionnel
_RE_NORTH_AMERICA = re.compile(
    r"\b(north\s+america|am[eé]rique\s+du\s+nord)\b",
    re.IGNORECASE
)

_RE_NEG = re.compile(r"\b(sans|non|pas\s+de|pas\s+d['’]|hors|without|no)\b", re.IGNORECASE)

_RE_EUROPE = re.compile(
    r"\b("
    r"europe|european(?:s)?|europe[-\s]?based|"
    r"europ[ée]en(?:ne)?(?:s)?|"
    r"ue|e\.u\.|eu\b"
    r")\b",
    re.IGNORECASE,
)

# --- Macro-régions génériques (détection "macro → pays")
# IMPORTANT: ces macros ne doivent JAMAIS être output par le LLM en tant que values de "region".
# On s'en sert uniquement pour forcer une contrainte region déterministe côté postprocess.
_RE_ASIA = re.compile(r"\b(asie|asia|asiatique(?:s)?)\b", re.IGNORECASE)
_RE_LATAM = re.compile(r"\b(latam|am[eé]rique\s+latine|latin\s+america|latino[-\s]?am[eé]ricain(?:e)?(?:s)?)\b", re.IGNORECASE)
_RE_MIDDLE_EAST = re.compile(r"\b(moyen[-\s]?orient|middle\s+east|mena)\b", re.IGNORECASE)
_RE_AFRICA = re.compile(r"\b(afrique|africa|africain(?:e)?(?:s)?)\b", re.IGNORECASE)
_RE_AUSTRALIA = re.compile(r"\b(australie|australia|oceanie|oc[eé]anie|australasie)\b", re.IGNORECASE)
_RE_CANADA = re.compile(r"\b(canada|canadien(?:ne)?(?:s)?)\b", re.IGNORECASE)

# --- Négation (scope simple) : détecte "sans X", "non X", "hors X", "pas de X"
def _is_negated_keyword(text: str, keyword_regex: str) -> bool:
    t = (text or "").lower()
    try:
        return bool(re.search(
            rf"\b(sans|non|hors|pas\s+de|pas\s+d['’]|without|no)"
            rf"(?:\s+(?:la|le|les|l['’]|du|des|de|d['’]))*\s+({keyword_regex})\b",
            t,
            flags=re.IGNORECASE,
        ))
    except re.error:
        return False


def _detect_geo_macro(user_prompt: str) -> Optional[str]:
    raw = user_prompt or ""
    t = raw.lower()

    # 1) WORLD (mots entiers) + négation
    if re.search(r"\b(monde|mondial|global|world|worldwide|international)\b", t):
        if not _is_negated_keyword(raw, r"(monde|mondial|global|world|worldwide|international)"):
            if "WORLD" in set(ALLOWED_REGION_GROUPS) and "WORLD" in REGION_GROUPS:
                return "WORLD"

    def _macro(rx: re.Pattern, keyword_regex_for_neg: str, macro_name: str) -> Optional[str]:
        if rx.search(raw) and (not _is_negated_keyword(raw, keyword_regex_for_neg)):
            return macro_name
        return None

    for maybe in [
        _macro(_RE_EUROPE, r"(europe|european(?:s)?|europ[ée]en(?:ne)?(?:s)?|ue|eu\b)", "EUROPE"),
        _macro(_RE_US, r"(us|usa|u\.?s\.?a\.?|u\.?s\.?|united\s+states)", "USA"),
        _macro(_RE_US_FR, r"(états?-unis|etats?-unis)", "USA"),
        _macro(_RE_ASIA, r"(asie|asia|asiatique(?:s)?)", "ASIA"),
        _macro(_RE_LATAM, r"(latam|am[eé]rique\s+latine|latin\s+america)", "LATAM"),
        _macro(_RE_MIDDLE_EAST, r"(moyen[-\s]?orient|middle\s+east|mena)", "MIDDLE_EAST"),
        _macro(_RE_AFRICA, r"(afrique|africa)", "AFRICA"),
        _macro(_RE_AUSTRALIA, r"(australie|australia|oceanie|oc[eé]anie|australasie)", "AUSTRALIA"),
        _macro(_RE_CANADA, r"(canada|canadien(?:ne)?(?:s)?)", "CANADA"),
    ]:
        if maybe and maybe in set(ALLOWED_REGION_GROUPS) and maybe in REGION_GROUPS:
            return maybe

    return None

# --- Pays explicites -> region (ISO2)
_COUNTRY_KEYWORDS_TO_REGION: Dict[str, str] = {

    # -----------------
    # USA / Canada
    # -----------------
    "usa": "us",
    "us": "us",
    "united states": "us",
    "united states of america": "us",
    "etats-unis": "us",
    "états-unis": "us",

    "canada": "ca",

    # -----------------
    # EUROPE
    # -----------------

    # France
    "france": "fr",
    "francais": "fr",
    "français": "fr",
    "french": "fr",

    # Germany
    "allemagne": "de",
    "germany": "de",
    "deutschland": "de",

    # UK
    "royaume-uni": "gb",
    "united kingdom": "gb",
    "uk": "gb",
    "angleterre": "gb",
    "england": "gb",
    "britain": "gb",

    # Spain
    "espagne": "es",
    "spain": "es",

    # Italy
    "italie": "it",
    "italy": "it",

    # Switzerland
    "suisse": "ch",
    "switzerland": "ch",

    # Belgium
    "belgique": "be",
    "belgium": "be",

    # Netherlands
    "pays-bas": "nl",
    "netherlands": "nl",
    "hollande": "nl",

    # Austria
    "autriche": "at",
    "austria": "at",

    # Denmark
    "danemark": "dk",
    "denmark": "dk",

    # Sweden
    "suede": "se",
    "suède": "se",
    "sweden": "se",

    # Norway
    "norvege": "no",
    "norvège": "no",
    "norway": "no",

    # Finland
    "finlande": "fi",
    "finland": "fi",

    # Ireland
    "irlande": "ie",
    "ireland": "ie",

    # Iceland
    "islande": "is",
    "iceland": "is",

    # Portugal
    "portugal": "pt",

    # Greece
    "grece": "gr",
    "grèce": "gr",
    "greece": "gr",

    # Poland
    "pologne": "pl",
    "poland": "pl",

    # Czech
    "tchequie": "cz",
    "czech": "cz",
    "czech republic": "cz",

    # Hungary
    "hongrie": "hu",
    "hungary": "hu",

    # Romania
    "roumanie": "ro",
    "romania": "ro",

    # Lithuania
    "lituanie": "lt",
    "lithuania": "lt",

    # Latvia
    "lettonie": "lv",
    "latvia": "lv",

    # Estonia
    "estonie": "ee",
    "estonia": "ee",

    # Turkey
    "turquie": "tr",
    "turkey": "tr",

    # -----------------
    # ASIA
    # -----------------

    # China
    "chine": "cn",
    "china": "cn",

    # Hong Kong
    "hong kong": "hk",

    # Japon
    "japon": "jp",
    "japan": "jp",
    "japanese": "jp",

    # South Korea
    "coree": "kr",
    "corée": "kr",
    "south korea": "kr",
    "korea": "kr",

    # India
    "inde": "in",
    "india": "in",

    # Taiwan
    "taiwan": "tw",

    # Singapore
    "singapour": "sg",
    "singapore": "sg",

    # Thailand
    "thailande": "th",
    "thailand": "th",

    # Vietnam
    "vietnam": "vn",

    # Malaysia
    "malaisie": "my",
    "malaysia": "my",

    # Indonesia
    "indonesie": "id",
    "indonesia": "id",

    # Philippines
    "philippines": "ph",

    # -----------------
    # LATAM
    # -----------------

    "bresil": "br",
    "brésil": "br",
    "brazil": "br",

    "mexique": "mx",
    "mexico": "mx",

    "argentine": "ar",
    "argentina": "ar",

    "chili": "cl",
    "chile": "cl",

    "colombie": "co",
    "colombia": "co",

    "venezuela": "ve",

    "perou": "pe",
    "pérou": "pe",
    "peru": "pe",

    # -----------------
    # MIDDLE EAST
    # -----------------

    "israel": "il",

    "arabie saoudite": "sa",
    "saudi arabia": "sa",

    "qatar": "qa",

    "koweit": "kw",
    "kuwait": "kw",

    # -----------------
    # AFRICA
    # -----------------

    "afrique du sud": "za",
    "south africa": "za",

    "egypte": "eg",
    "egypt": "eg",

    # -----------------
    # AUSTRALIA / OCEANIA
    # -----------------

    "australie": "au",
    "australia": "au",

    "nouvelle zelande": "nz",
    "nouvelle-zélande": "nz",
    "new zealand": "nz",
}

def _extract_explicit_region_codes(user_prompt: str) -> Set[str]:
    t = (user_prompt or "").lower()
    wanted: Set[str] = set()
    allowed = set(ALLOWED_REGIONS)

    for k, code in _COUNTRY_KEYWORDS_TO_REGION.items():
        if code not in allowed:
            continue
        if re.search(rf"\b{re.escape(k)}\b", t, flags=re.IGNORECASE):
            wanted.add(code)

    for m in re.findall(r"\b([a-z]{2})\b", t):
        if m in allowed:
            wanted.add(m)

    return wanted


_SECTOR_SYNONYMS = {
    "Industrials": [r"\bindustrials?\b", r"\bindustriel(?:le)?s?\b", r"\bindustrie(?:l)?\b"],
    "Technology": [r"\btech\b", r"\btechnolog(?:y|ie|ique)s?\b"],
    "Healthcare": [r"\bhealthcare\b", r"\bsant[ée]\b", r"\bm[ée]dical\b", r"\bmedical\b"],
    "Financial Services": [r"\bfinancial\b", r"\bfinance\b", r"\bbanque(?:s)?\b", r"\bbank(?:s|ing)?\b", r"\bassurance(?:s)?\b", r"\binsurance\b"],
    "Energy": [r"\benergy\b", r"\b[ée]nergie\b", r"\boil\b", r"\bgas\b", r"\bp[ée]trol"],
    "Utilities": [r"\butilities\b", r"\bservices?\s+publics?\b"],
    "Real Estate": [r"\breal\s+estate\b", r"\bimmobilier\b", r"\breit(?:s)?\b"],
    "Consumer Cyclical": [r"\bconsumer\s+cyclical\b", r"\bcyclique\b"],
    "Consumer Defensive": [r"\bconsumer\s+defensive\b", r"\bd[ée]fensif\b"],
    "Basic Materials": [r"\bbasic\s+materials\b", r"\bmat[ée]riaux\b"],
    "Communication Services": [r"\bcommunication\s+services\b", r"\btel[eé]com\b", r"\bmedia\b"],
}

def _extract_explicit_sectors(user_prompt: str) -> List[str]:
    t = (user_prompt or "").lower()
    out: List[str] = []
    for sector, patterns in _SECTOR_SYNONYMS.items():
        if sector not in set(ALLOWED_SECTORS):
            continue
        if any(re.search(p, t) for p in patterns):
            out.append(sector)
    return out


# =============================================================================
# v9 FIX: rule-based industry extraction (to stabilize multi-industries prompts)
# =============================================================================
_KEYWORD_INDUSTRY_MAP: List[Tuple[str, List[str]]] = [

    (r"\b(pharma|pharmaceutique|pharmaceutiques|m[ée]dicament|m[ée]dicaments)\b",
     ["Drug Manufacturers—General", "Drug Manufacturers—Specialty & Generic"]),

    (r"\b(semi[- ]?conducteur|semi[- ]?conducteurs|semiconductors?|puces|chip|chips)\b",
     ["Semiconductors", "Semiconductor Equipment & Materials"]),

    (r"\b(auto|autos|automobile|automobiles|voiture|voitures)\b",
     ["Auto Manufacturers", "Auto Parts"]),

    (r"\b(d[ée]fense|defense|defence|armement|a[ée]ronautique)\b",
     ["Aerospace & Defense"]),

    (r"\b(luxe|luxury)\b",
     ["Luxury Goods"]),

    (r"\b(banque|banques|bank|banks|banking)\b",
     ["Banks—Diversified", "Banks—Regional"]),

    (r"\b(assurance|assurances|insurance|insurer|insurers)\b",
     ["Insurance—Diversified", "Insurance—Life", "Insurance—Property & Casualty", "Insurance—Reinsurance", "Insurance—Specialty"]),

    (r"\b(software|logiciel|logiciels|saas)\b",
     ["Software—Application", "Software—Infrastructure", "Technical & System Software"]),

    (r"\b(internet|plateforme|platform|platforms|web)\b",
     ["Internet Content & Information", "Internet Retail"]),

    (r"\b(renouvelable|renewable|solar|solaire)\b",
     ["Solar", "Utilities—Renewable"]),

    (r"\b(ai|ia|intelligence\s+artificielle|artificial\s+intelligence)\b",
     ["Software—Application", "Software—Infrastructure", "Semiconductors"]),

    (r"\b(cloud|cloud\s+computing)\b",
     ["Software—Infrastructure", "Information Technology Services"]),

    (r"\b(cyber|cybersecurity|cyber\s+security|cybers[ée]curit[ée])\b",
     ["Software—Infrastructure", "Information Technology Services"]),

    (r"\b(p[ée]trole|petrol|oil|gas|hydrocarbure|hydrocarbures)\b",
     ["Oil & Gas Integrated", "Oil & Gas E&P", "Oil & Gas Equipment & Services"]),

    (r"\b(sant[ée]|health|healthcare|m[ée]dical|medical)\b",
     ["Biotechnology", "Medical Devices", "Diagnostics & Research"]),
]

def _extract_keyword_industries(user_prompt: str) -> Set[str]:
    t = (user_prompt or "").lower()
    found: Set[str] = set()

    def _is_negated(rx: str) -> bool:
        # même logique que ton _neg_scope: autorise "sans le/la/du/des/de..."
        return bool(re.search(
            rf"\b(sans|non|hors|pas\s+de|pas\s+d['’]|without|no)"
            rf"(?:\s+(?:la|le|les|l['’]|du|des|de|d['’]))*\s+{rx}\b",
            t,
            flags=re.IGNORECASE,
        ))

    for pattern, industries in _KEYWORD_INDUSTRY_MAP:
        if re.search(pattern, t, flags=re.IGNORECASE):
            # si c'est "sans <mot>", on ne l'ajoute pas en inclusion
            if _is_negated(pattern):
                continue
            for ind in industries:
                if ind in set(ALLOWED_INDUSTRIES):
                    found.add(ind)

    return found

def _extract_positive_sectors(user_prompt: str) -> List[str]:
    """
    Renvoie les secteurs explicitement mentionnés DANS LE SENS POSITIF
    (ex: 'energy' => Energy ; 'sans technologie' => ne renvoie PAS Technology).
    """
    text = user_prompt or ""
    t = text.lower()

    # map regex -> secteur Yahoo
    candidates: List[Tuple[str, str]] = [
        (r"\b(technology|technologie|tech)\b", "Technology"),

        (r"\b(energy|energie|énergie)\b", "Energy"),
        (r"\b(oil\s*&\s*gas)\b", "Energy"),

        (r"\b(health|healthcare|sant[ée]|m[ée]dical)\b", "Healthcare"),
        (r"\b(industrials?|industriel(?:s)?)\b", "Industrials"),
        (r"\b(financial|financials|finance|banque|banques|assurance|assurances)\b", "Financial Services"),
        (r"\b(utilities?|services\s+publics?)\b", "Utilities"),
        (r"\b(real\s+estate|immobilier)\b", "Real Estate"),
        (r"\b(communication\s+services|telecom|t[ée]l[ée]com)\b", "Communication Services"),
        (r"\b(consumer\s+cyclical|conso\s+cyclique)\b", "Consumer Cyclical"),
        (r"\b(consumer\s+defensive|conso\s+d[ée]fensive)\b", "Consumer Defensive"),
        (r"\b(basic\s+materials|mat[ée]riaux)\b", "Basic Materials"),
    ]

    out: List[str] = []
    allowed = set(ALLOWED_SECTORS)

    for rx, sector in candidates:
        if sector not in allowed:
            continue
        # secteur présent ET pas sous négation ("sans ...")
        if re.search(rx, t, flags=re.IGNORECASE) and not _is_negated_keyword(text, rx):
            out.append(sector)

    # dédupe en gardant l'ordre
    seen: Set[str] = set()
    uniq: List[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq

def _drop_invalid_industries(constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    allowed = set(ALLOWED_INDUSTRIES)
    out = []
    for c in constraints:
        if str(c.get("field", "")).lower() == "industry" and str(c.get("operator", "")).lower() == "is-in":
            vals = [v for v in _flatten_values(c.get("values", [])) if isinstance(v, str)]
            vals2 = [v for v in vals if v in allowed]
            if vals2:
                c2 = dict(c)
                c2["values"] = vals2
                out.append(c2)
            # sinon: on drop la contrainte industry
        else:
            out.append(c)
    return out

def _restrict_industry_to_sector(cleaned: List[Dict[str, Any]], notes: str) -> Tuple[List[Dict[str, Any]], str]:
    sectors = []
    industries = []
    for c in cleaned:
        if c.get("field") == "sector" and str(c.get("operator", "")).lower() == "is-in":
            sectors = [v for v in _flatten_values(c.get("values", [])) if isinstance(v, str)]
        if c.get("field") == "industry" and str(c.get("operator", "")).lower() == "is-in":
            industries = [v for v in _flatten_values(c.get("values", [])) if isinstance(v, str)]
    if not sectors or not industries:
        return cleaned, notes
    allowed = set()
    for s in sectors:
        allowed |= set(SECTOR_INDUSTRY_MAPPING.get(s, set()))
    if not allowed:
        return cleaned, notes
    filtered = [i for i in industries if i in allowed]
    if filtered and len(filtered) != len(industries):
        out = []
        for c in cleaned:
            if c.get("field") == "industry":
                c2 = dict(c)
                c2["values"] = filtered
                out.append(c2)
            else:
                out.append(c)
        notes = (notes + " | " if notes else "") + "industries recadrées sur le(s) secteur(s) demandé(s)."
        return out, notes
    return cleaned, notes

# =============================================================================
# Exclusions
# =============================================================================
def _extract_exclusions(user_prompt: str) -> Dict[str, Any]:
    """
    Extrait des exclusions (sans / hors / non / without / no) depuis le texte utilisateur.

    Retourne:
      - excluded_regions: set[str] (codes pays ex: {"us","fr"} + sentinel "europe")
      - excluded_sectors: set[str]
      - excluded_industries: set[str]
      - excluded_topics: list[str] (non représentable -> notes)
    """
    t = (user_prompt or "").lower()

    excluded_regions: Set[str] = set()
    excluded_sectors: Set[str] = set()
    excluded_industries: Set[str] = set()
    excluded_topics: List[str] = []

    def _neg_scope(rx: str) -> bool:
        return bool(
            #Reponse : c’est dans un regex de négation : tu autorises des articles (“sans le/la/les/du/des…”) entre “sans” et le mot-clé. C’est normal en FR.
            re.search(
                rf"\b(sans|non|hors|pas\s+de|pas\s+d['’]|without|no)(?:\s+(?:la|le|les|l['’]|du|des|de|d['’]))*\s+{rx}\b",
                t,
                flags=re.IGNORECASE,
            )
        )

    # Regions (US / Europe / pays)
    if _neg_scope(r"(us|usa|u\.s\.|u\.s\.a\.|united\s+states|[ée]tats?-unis|etats?-unis|am[eé]rique|america)"):
        excluded_regions.add("us")
    if _neg_scope(r"(europe|european(?:s)?|europ[ée]en(?:ne)?(?:s)?|ue|eu\b)"):
        excluded_regions.add("europe")
    if _neg_scope(r"(asie|asia|asiatique(?:s)?)"):
        excluded_regions.add("asia")
    if _neg_scope(r"(latam|am[eé]rique\s+latine|latin\s+america)"):
        excluded_regions.add("latam")
    if _neg_scope(r"(afrique|africa)"):
        excluded_regions.add("africa")
    if _neg_scope(r"(moyen[-\s]?orient|middle\s+east|mena)"):
        excluded_regions.add("middle_east")
    if _neg_scope(r"(monde|mondial|global|world|worldwide|international)"):
        excluded_regions.add("world")


    allowed_regions_set = set(ALLOWED_REGIONS)

    # pays communs (mots clés)
    for k, code in _COUNTRY_KEYWORDS_TO_REGION.items():
        if code not in allowed_regions_set:
            continue

        if _neg_scope(re.escape(k)):
            excluded_regions.add(code)

    # ---------------- PATCH ISO2 (NEGATIF) ----------------
    # permet "sans jp", "sans fr", "sans us"
    iso2_neg = re.findall(r"\b(?:sans|hors|non|without|no)(?:\s+(?:la|le|les|l['’]|du|des|de|d['’]))*\s+([a-z]{2})\b", t, flags=re.I,)

    for code in iso2_neg:
        code = code.lower()
        if code in allowed_regions_set:
            excluded_regions.add(code)
    # -----------------------------------------------------

    # Sectors
    if _neg_scope(r"(tech|technologie|technology)") and "Technology" in set(ALLOWED_SECTORS):
        excluded_sectors.add("Technology")

    if _neg_scope(r"(énergie|energie|energy)\b") and "Energy" in set(ALLOWED_SECTORS):
        excluded_sectors.add("Energy")

    # Industries

    # software / SaaS
    if _neg_scope(r"(software|logiciel|logiciels|saas)"):
        for v in ["Software—Application", "Software—Infrastructure", "Technical & System Software"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    if _neg_scope(r"(auto|autos|automobile|automobiles|voiture|voitures)"):
        for v in ["Auto Manufacturers", "Auto Parts"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    if _neg_scope(r"(semi[- ]?conducteur|semi[- ]?conducteurs|semiconductors?|puces|chip|chips)"):
        for v in ["Semiconductors", "Semiconductor Equipment & Materials"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    if _neg_scope(r"(pharma|pharmaceutique|m[ée]dicament|drug\s+manufacturers?)"):
        for v in ["Drug Manufacturers—General", "Drug Manufacturers—Specialty & Generic"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    if _neg_scope(r"(luxe|luxury)"):
        if "Luxury Goods" in set(ALLOWED_INDUSTRIES):
            excluded_industries.add("Luxury Goods")

    if _neg_scope(r"(d[ée]fense|defense|defence|armement|a[ée]ronautique)"):
        if "Aerospace & Defense" in set(ALLOWED_INDUSTRIES):
            excluded_industries.add("Aerospace & Defense")

    # banques
    if _neg_scope(r"(banque|banques|bank|banks|banking)"):
        for v in ["Banks—Diversified", "Banks—Regional"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    # assurances
    if _neg_scope(r"(assurance|assurances|insurance|insurer|insurers)"):
        for v in [
            "Insurance—Diversified", "Insurance—Life", "Insurance—Property & Casualty",
            "Insurance—Reinsurance", "Insurance—Specialty"
        ]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    # pétrole/gas
    if _neg_scope(r"(p[ée]trole|petrol|oil|gas|hydrocarbure|hydrocarbures)"):
        for v in ["Oil & Gas Integrated", "Oil & Gas E&P", "Oil & Gas Equipment & Services"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    # santé (large)
    if _neg_scope(r"(sant[ée]|health|healthcare|m[ée]dical|medical)"):
        for v in ["Biotechnology", "Medical Devices", "Diagnostics & Research"]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    # Industries: oil/gas (ne PAS mapper ça au secteur Energy)
    if _neg_scope(r"(p[ée]trol|p[ée]troli[eè]r|oil|crude|brent|wti|gas|gaz|hydrocarbure|hydrocarbures)"):
        for v in [
            "Oil & Gas Drilling",
            "Oil & Gas E&P",
            "Oil & Gas Equipment & Services",
            "Oil & Gas Integrated",
            "Oil & Gas Midstream",
            "Oil & Gas Refining & Marketing",
        ]:
            if v in set(ALLOWED_INDUSTRIES):
                excluded_industries.add(v)

    # Topics Difficilement représentables sur yahou (notes)
    if _neg_scope(r"(militaire|armement|weapons?)"):
        excluded_topics.append("militaire/armement (approx: pas toujours représentable via industries Yahoo)")

    return {
        "excluded_regions": excluded_regions,
        "excluded_sectors": excluded_sectors,
        "excluded_industries": excluded_industries,
        "excluded_topics": excluded_topics,
    }


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================
def _build_common_header() -> str:
    return """Tu es un traducteur de requêtes d'investissement vers des contraintes Yahoo Finance.

Ta réponse doit être STRICTEMENT un JSON valide (sans texte autour) au format :

{
  "universe": "equity" | "fund",
  "constraints": [
    {
      "field": string,
      "operator": "gte" | "lte" | "gt" | "lt" | "eq" | "is-in" | "btwn",
      "values": [ ... ]
    }
  ],
  "notes": string
}

Règles générales :
- Tu ne renvoies AUCUN texte en dehors du JSON.
- Operators autorisés : ["gte","lte","gt","lt","eq","is-in","btwn"].
- "constraints" est une liste.
- "values" est toujours une liste.
- Tu n'utilises JAMAIS un mot du langage naturel comme nom de champ (field).
- Si une contrainte n’est pas représentable avec les champs autorisés, mets l’info dans "notes" (n’invente pas).
- Pour les champs catégoriels, préfère "is-in" (même pour une seule valeur).
"""

def _build_equity_system_prompt() -> str:
    # ✅ IMPORTANT: region attend des PAYS (ISO2) côté screener (et non plus des "buckets macro").
    # On donne aussi les groupes macro comme "aide" conceptuelle (le LLM ne doit pas les output).
    rg = sorted(list(ALLOWED_REGION_GROUPS)) if isinstance(ALLOWED_REGION_GROUPS, (set, list, tuple)) else []
    rg_hint = f"\nGroupes macro disponibles (NE PAS utiliser comme valeurs de 'region', c'est juste un hint): {rg}\n" if rg else "\n"
    return (
        _build_common_header()
        + f"""
MODE: EQUITY
- "universe" DOIT être "equity".
- IMPORTANT : ETF / UCITS / tracker => "fund" (pas equity) dans ce projet.

Champs catégoriels autorisés (equity) :
- region (pays ISO2) : {ALLOWED_REGIONS}
{rg_hint}
- sector : {ALLOWED_SECTORS}
- industry : {ALLOWED_INDUSTRIES}
- exchange : {ALLOWED_EQ_EXCHANGES}
- autres : {sorted(list(ALLOWED_EQ_CATEGORICAL_FIELDS))}

Champs numériques autorisés (equity) :
{ALLOWED_EQ_NUMERIC_FIELDS}

Règles (equity) :
- Dividende / yield => forward_dividend_yield
- Capitalisation / market cap => {EQUITY_MARKETCAP_FIELD}
- Ne jamais inventer de champs.
- Ne JAMAIS confondre volatilité avec volume.
- "US/USA/United States/États-Unis" => region "us" (si dispo)
- "Europe/européen/european" => region = liste de pays européens (pas exchange).
"""
    )


def _build_fund_system_prompt() -> str:
    return (
        _build_common_header()
        + f"""
MODE: FUND
- "universe" DOIT être "fund".
- IMPORTANT : ETF / UCITS / tracker => "fund" dans ce projet.

Champs catégoriels autorisés (fund / FundQuery) :
- exchange (valeurs autorisées) : {ALLOWED_FUND_EXCHANGES}
- categoryname : texte libre (si incertain => notes)

Champs numériques autorisés (fund) :
{ALLOWED_FUND_NUMERIC_FIELDS}

Rappels FundQuery (anti-invention) :
- Pas de sector/industry/marketcap/dividend_yield en fund.
  Si l'utilisateur les demande => notes uniquement.
- "bien classé / top / rank" => annualreturnnavy1categoryrank < 50 (uniquement si demandé).
- Ratings :
  - performanceratingoverall : 1..5
  - riskratingoverall : 1..5
- Ne crée JAMAIS de filtre "exchange" si l’utilisateur n’a pas explicitement demandé une place/échange,
  sauf si l'utilisateur demande explicitement "US" (car seul exchange possible dans ce projet).
"""
    )


# =============================================================================
# PARSING & NORMALISATION
# =============================================================================
def _parse_json_safely(raw: str) -> Dict[str, Any]:
    import ast
    raw = (raw or "").strip()

    # 0) enlever code fences
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw)

    # 1) extraire le premier objet {...} via "brace balancing"
    start = raw.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", raw, 0)

    s = raw[start:]
    depth = 0
    end = None
    in_str = False
    esc = False
    quote = ""

    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

    candidate = s if end is None else s[:end]

    def _as_dict(obj: Any) -> Dict[str, Any]:
        if isinstance(obj, dict):
            return obj
        return {"data": obj}

    # 2) essai JSON direct
    try:
        return _as_dict(json.loads(candidate))
    except Exception:
        pass

    # 3) réparations LLM-friendly
    repaired = candidate
    repaired = repaired.replace("“", "\"").replace("”", "\"").replace("’", "'")
    repaired = re.sub(r"\bTrue\b", "true", repaired)
    repaired = re.sub(r"\bFalse\b", "false", repaired)
    repaired = re.sub(r"\bNone\b", "null", repaired)
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)  # trailing commas

    # virgules manquantes entre tokens (les 2 patterns clés)
    repaired = re.sub(r'("|\]|\})\s*(")', r"\1,\2", repaired)       #  "x" "y"  ]"k"  }"k"
    repaired = re.sub(r'(\}|\])\s*(\{|\[)', r"\1,\2", repaired)     #  }{  ]{  }[  ][

    # 4) essai JSON après réparations
    try:
        return _as_dict(json.loads(repaired))
    except Exception:
        pass

    # 5) fallback Python-literal (gère: quotes simples, dict python, etc.)
    # re-map vers Python (literal_eval comprend True/False/None, pas true/false/null)
    py_like = repaired
    py_like = re.sub(r"\btrue\b", "True", py_like, flags=re.IGNORECASE)
    py_like = re.sub(r"\bfalse\b", "False", py_like, flags=re.IGNORECASE)
    py_like = re.sub(r"\bnull\b", "None", py_like, flags=re.IGNORECASE)

    obj = ast.literal_eval(py_like)  # safe for literals only
    return _as_dict(obj)


#certains LLM sortent "values": [[...]] au lieu de "values": [...]. Cette fonction évite que ta validation casse.
def _flatten_values(values: Any) -> List[Any]:
    if not isinstance(values, list):
        return []
    if len(values) == 1 and isinstance(values[0], list):
        return list(values[0])
    out: List[Any] = []
    for v in values:
        if isinstance(v, list):
            out.extend(v)
        else:
            out.append(v)
    return out


def _validate_operator_values(operator: str, values: List[Any], idx: int) -> None:
    if operator == "btwn":
        if len(values) != 2:
            raise ValueError(f"Contrainte {idx} : operator 'btwn' attend exactement 2 valeurs")
    elif operator in {"gt", "gte", "lt", "lte", "eq"}:
        if len(values) != 1:
            raise ValueError(f"Contrainte {idx} : operator {operator!r} attend exactement 1 valeur")
    elif operator == "is-in":
        if len(values) < 1:
            raise ValueError(f"Contrainte {idx} : operator 'is-in' attend au moins 1 valeur")


def _normalize_equity_exchange_values(values: List[Any]) -> List[Any]:
    out: List[Any] = []
    for v in values:
        if not isinstance(v, str):
            out.append(v)
            continue
        key = v.strip().lower()
        out.append(EQUITY_EXCHANGE_ALIASES.get(key, v))
    return out


# =============================================================================
# VALIDATION
# =============================================================================
def validate_constraints(payload: Dict[str, Any]) -> Dict[str, Any]:
    universe = payload.get("universe")
    if universe not in ALLOWED_UNIVERSES:
        raise ValueError(f"universe doit être dans {sorted(ALLOWED_UNIVERSES)}, reçu : {universe!r}")

    constraints = payload.get("constraints", [])
    if not isinstance(constraints, list):
        raise ValueError("'constraints' doit être une liste")

    if universe == "equity":
        allowed_cat = set(ALLOWED_EQ_CATEGORICAL_FIELDS)
        allowed_num = set(ALLOWED_EQ_NUMERIC_FIELDS)
    else:
        allowed_cat = set(ALLOWED_FUND_CATEGORICAL_FIELDS)
        allowed_num = set(ALLOWED_FUND_NUMERIC_FIELDS)

    for idx, c in enumerate(constraints):
        if not isinstance(c, dict):
            raise ValueError(f"Chaque contrainte doit être un dict (index {idx})")

        field = c.get("field")
        operator = c.get("operator")
        values = _flatten_values(c.get("values"))
        c["values"] = values

        if not isinstance(field, str) or not field:
            raise ValueError(f"Contrainte {idx} : 'field' doit être une chaîne non vide")

        if not isinstance(operator, str) or operator not in ALLOWED_OPERATORS:
            raise ValueError(
                f"Contrainte {idx} : opérateur invalide {operator!r}. "
                f"Autorisés : {sorted(ALLOWED_OPERATORS)}"
            )

        _validate_operator_values(operator, values, idx)

        # Normalisation exchange (equity)
        if universe == "equity" and field == "exchange":
            c["values"] = _normalize_equity_exchange_values(values)

        # Garde-fou dividende equity
        if universe == "equity":
            f = field.lower()
            if ("dividend" in f or "dividende" in f) and field != "forward_dividend_yield":
                raise ValueError(
                    f"Contrainte {idx} : pour le dividende, utilise uniquement "
                    f"'forward_dividend_yield' (pas {field!r})."
                )

        # Champs autorisés
        if not (field in allowed_cat or field in allowed_num):
            raise ValueError(
                f"Contrainte {idx} : champ non autorisé {field!r} pour universe={universe!r}."
            )

        # Validation exchange (fund)
        if universe == "fund" and field == "exchange":
            for v in c["values"]:
                if isinstance(v, str) and v not in ALLOWED_FUND_EXCHANGES:
                    raise ValueError(
                        f"Contrainte {idx} : valeur exchange invalide {v!r}. "
                        f"Autorisés : {ALLOWED_FUND_EXCHANGES}"
                    )

        # Validation exchange (equity)
        if universe == "equity" and field == "exchange":
            for v in c["values"]:
                if isinstance(v, str) and v not in ALLOWED_EQ_EXCHANGES:
                    raise ValueError(
                        f"Contrainte {idx} : valeur exchange invalide {v!r}. "
                        f"Autorisés : {ALLOWED_EQ_EXCHANGES}"
                    )

        # Validation industry (equity)
        if universe == "equity" and field == "industry":
            for v in c["values"]:
                if isinstance(v, str) and v not in ALLOWED_INDUSTRIES:
                    raise ValueError(f"Contrainte {idx} : industry invalide {v!r}.")

        # Validation region (equity)
        if universe == "equity" and field == "region":
            for v in c["values"]:
                if isinstance(v, str) and v not in set(ALLOWED_REGIONS):
                    raise ValueError(
                        f"Contrainte {idx} : region invalide {v!r}. "
                        f"Autorisés : {ALLOWED_REGIONS}"
                    )

    notes = payload.get("notes", "")
    payload["notes"] = notes if isinstance(notes, str) else str(notes)
    return payload


# =============================================================================
# PROMPT NORMALIZATION
# =============================================================================
def _normalize_user_prompt(user_prompt: str) -> str:
    t = (user_prompt or "").strip()
    t = re.sub(r"\s+", " ", t)

    replacements = {
        "portfeuil": "portefeuille",
        "portfeuille": "portefeuille",
        "porte feuille": "portefeuille",
        "sante": "santé",
        "energies": "énergies",
        "energie": "énergie",
        "enérgies": "énergies",
        "énérgies": "énergies",
        "petroliere": "pétrolière",
        "petrolieres": "pétrolières",
        "petrolières": "pétrolières",
        "amerique": "amérique",
        "etats unis": "états-unis",
        "usa ": "usa ",
    }
    low = t.lower()
    for k, v in replacements.items():
        if k in low:
            t = re.sub(re.escape(k), v, t, flags=re.IGNORECASE)
            low = t.lower()
    return t


# =============================================================================
# FR/EN scale fix: "milliard" (FR) / "billion" (EN-US) = 1e9 ; "trillion" = 1e12
# -----------------------------------------------------------------------------
_FR_SMALL_NUM = {
    "zéro": 0, "zero": 0,
    "un": 1, "une": 1,
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
}

#Extract number requested by the user (e.g. "3 stocks", "top 5 ETF", "deux actions")
#Used to set the screener result limit deterministically instead of relying on the LLM.
def _parse_leading_number(token: str) -> Optional[float]:
    tok = (token or "").strip().lower()
    if not tok:
        return None
    if tok in _FR_SMALL_NUM:
        return float(_FR_SMALL_NUM[tok])
    # 1,5 / 1.5 / 1 500
    tok = tok.replace(" ", "").replace("\u202f", "")
    tok = tok.replace(",", ".")
    try:
        return float(tok)
    except ValueError:
        return None

def _extract_scale_requests(user_prompt: str) -> List[Tuple[float, str]]:
    """Extrait des mentions comme '1 milliard', '2.5 billion', '3 trillion'."""
    t = (user_prompt or "").lower()
    out: List[Tuple[float, str]] = []
    # capture: (nombre) (unité)
    for m in re.finditer(r"\b([\w.,\u202f ]+)\s*(milliard(?:s)?|billion(?:s)?|trillion(?:s)?)\b", t):
        num_raw = (m.group(1) or "").strip()
        unit = (m.group(2) or "").strip().lower()
        # on ne prend que le dernier token du nombre (évite 'plus de 1' etc.)
        num_token = num_raw.split()[-1] if num_raw else ""
        n = _parse_leading_number(num_token)
        if n is None:
            continue
        out.append((n, unit))
    return out

def _is_monetary_scale_field(field: str) -> bool:
    f = (field or "").lower()
    return any(k in f for k in [
        "marketcap", "revenue", "revenu", "sales", "debt", "assets", "equity", "cash",
        "freecashflow", "ebitda", "netincome",
    ])

def _fix_billion_milliard_scaling(
    user_prompt: str,
    constraints: List[Dict[str, Any]],
    notes: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Corrige les confusions 1e9 vs 1e12 quand l'utilisateur dit 'milliard'/'billion'.

    Cas visé (observé): l'utilisateur demande '1 milliard' (1e9) et le LLM produit 1e12.
    On corrige si la valeur semble exactement *1000* trop grande par rapport au (n, unité) détecté.
    """
    reqs = _extract_scale_requests(user_prompt)
    if not reqs:
        return constraints, notes

    # on ne corrige que si le prompt ne mentionne pas explicitement 'mille milliards' / 'trillion' etc.
    t = (user_prompt or "").lower()
    if re.search(r"\bmille\s+milliard", t) or "trillion" in t:
        return constraints, notes

    # on prend la première mention (souvent unique)
    n, unit = reqs[0]

    if unit.startswith("trillion"):
        expected = n * 1e12
    else:
        # ✅ milliard (FR) = 1e9 ; ✅ billion (EN-US) = 1e9
        expected = n * 1e9

    if expected <= 0:
        return constraints, notes

    changed = False
    out: List[Dict[str, Any]] = []

    # Quand l'utilisateur écrit "1 milliard" / "1 billion", le LLM peut parfois produire
    # une valeur 1000 fois trop grande (ex: 1e12 au lieu de 1e9).
    # Cette fonction vérifie les valeurs numériques dans les contraintes et les
    # ramène à la bonne échelle si elles semblent exactement 1000x trop grandes.
    # Ce n'est pas redondant avec les fonctions au-dessus :
    # - _parse_leading_number() lit les nombres dans le prompt utilisateur
    # - _extract_scale_requests() détecte "milliard/billion/trillion"
    # - ici on corrige la sortie du LLM si elle est mal scalée.
    def _fix_val(v: Any) -> Any:
        nonlocal changed
        if not isinstance(v, (int, float)):
            return v
        # si la valeur est ~1000x trop grande, on ramène à l'échelle attendue
        target = expected * 1000.0
        # tolérance relative (2%) + absolue (1e6) pour éviter les faux positifs
        tol = max(1e6, 0.02 * target)
        if abs(float(v) - target) <= tol:
            changed = True
            return expected
        return v

    for c in constraints:
        c2 = dict(c)
        field = str(c2.get("field", ""))
        if not _is_monetary_scale_field(field):
            out.append(c2)
            continue

        vals = _flatten_values(c2.get("values", []))
        c2["values"] = [_fix_val(v) for v in vals]
        out.append(c2)

    if changed:
        notes = (notes + " | " if notes else "") + (
            "échelle corrigée automatiquement: 'milliard/billion' interprété comme 1e9 (pas 1e12)."
        )
    return out, notes


def _guess_universe(user_prompt: str) -> str:
    t = (user_prompt or "").lower()
    if any(k in t for k in ["etf", "tracker", "ucits", "fonds indiciel", "fonds coté", "fonds cote", "index fund"]):
        return "fund"
    if any(k in t for k in ["mutual fund", "sicav", "fcp", "fonds commun", "opcvm", "fund"]):
        return "fund"
    if "fonds" in t:
        return "fund"
    return "equity"


def _invoke_llm(
    llm: object,
    system_prompt: str,
    user_prompt: str,
    correction: Optional[str] = None,
) -> str:
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if correction:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Tu as produit un JSON invalide. Corrige-le STRICTEMENT.\n"
                    f"Erreur: {correction}\n"
                    "Rappels:\n"
                    "- JSON seulement\n"
                    "- operators/values cohérents\n"
                    "- champs autorisés uniquement\n"
                ),
            }
        )
    messages.append({"role": "user", "content": user_prompt})
    response = llm.invoke(messages)
    return getattr(response, "content", None) or ""


# =============================================================================
# Intent flags
# =============================================================================
def _intent_flags(user_prompt: str) -> Dict[str, Any]:
    t = (user_prompt or "").lower()

    # Heuristique rapide pour décider si on produit des notes en FR :
    # - présence de caractères accentués
    # - ou quelques mots très fréquents en FR
    force_french = bool(re.search(r"[àâçéèêëîïôûùüÿœ]", t)) or any(
        w in t
        for w in [
            "portefeuille", "actions", "sans", "hors", "non",
            "europe", "europé", "santé", "technologie",
            "dividende", "capitalisation", "volatilité", "risque",
            "je veux", "construis", "fais",
        ]
    )

    # Heuristique “place financière / exchange”
    exchange_words = [
        "nasdaq", "nyse", "euronext", "paris", "xpar", "lse", "london",
        "amsterdam", "xams", "frankfurt", "xfra", "milan", "xmil",
    ]
    wants_exchange = any(w in t for w in exchange_words) or ("coté" in t) or ("cote" in t) or ("listed" in t)

    raw_prompt = user_prompt or ""

    # Détection négations (ex: "sans US", "hors Europe", etc.)
    neg_us = _is_negated_keyword(
        raw_prompt,
        r"(us|usa|u\.s\.|u\.s\.a\.|united\s+states|états?-unis|etats?-unis|am[eé]rique|america)"
    )
    neg_eu = _is_negated_keyword(raw_prompt, r"(europe|european(?:s)?|europ[ée]en(?:ne)?(?:s)?|ue|eu\b)")
    neg_asia = _is_negated_keyword(raw_prompt, r"(asia|asian|asie|asiatique(?:s)?)")
    neg_middle_east = _is_negated_keyword(raw_prompt, r"(middle\s?east|moyen[- ]?orient)")
    neg_africa = _is_negated_keyword(raw_prompt, r"(africa|afrique|african)")
    neg_latam = _is_negated_keyword(raw_prompt, r"(latam|latin\s?america|am[eé]rique\s?latine)")

    # Détection intentions positives (non négatées)
    wants_us = (bool(_RE_US.search(raw_prompt)) or bool(_RE_US_FR.search(raw_prompt))) and (not neg_us)
    wants_europe = bool(_RE_EUROPE.search(raw_prompt)) and (not neg_eu)
    wants_asia = bool(re.search(r"\b(asia|asie|asian|asiatique(?:s)?)\b", t)) and (not neg_asia)
    wants_middle_east = bool(re.search(r"\b(middle\s?east|moyen[- ]?orient)\b", t)) and (not neg_middle_east)
    wants_africa = bool(re.search(r"\b(africa|afrique|african)\b", t)) and (not neg_africa)
    wants_latam = bool(re.search(r"\b(latam|latin\s?america|am[eé]rique\s?latine)\b", t)) and (not neg_latam)

    wants_categoryname = any(k in t for k in ["category", "catégorie", "categorie", "categoryname"])

    # 1) On extrait les exclusions TÔT
    excl = _extract_exclusions(raw_prompt)

    # 2) On normalise "excluded_regions" en set local (interne) pour manipuler proprement
    excluded_regions = set(excl.get("excluded_regions") or [])

    # Si tu veux modéliser les négations macro comme "exclusions macro" (selon ton pipeline)
    if neg_asia:
        excluded_regions.add("asia")
    if neg_middle_east:
        excluded_regions.add("middle_east")
    if neg_africa:
        excluded_regions.add("africa")
    if neg_latam:
        excluded_regions.add("latam")

    # 3) Pays explicitement cités (ISO2) puis on retire ceux qui ne sont cités que dans l'exclusion
    wants_country_regions = _extract_explicit_region_codes(raw_prompt)

    # ✅ IMPORTANT: ne pas considérer comme "pays voulu" un pays cité uniquement dans une exclusion ("sans france")
    wants_country_regions = [r for r in wants_country_regions if r not in excluded_regions]
    wants_country = len(wants_country_regions) > 0

    # 4) Détection macro-géo (ex: "asie", "europe", "world", etc.)
    geo_macro = _detect_geo_macro(raw_prompt)

    # 4bis) Fallback exclusions-only geo :
    # ex: "sans asie" => on veut implicitement "WORLD - ASIA"
    has_geo_exclusions = any(
        r in {"asia", "europe", "latam", "africa", "middle_east", "world", "usa", "north_america", "canada", "australia"}
        for r in excluded_regions
    )
    has_geo_positive = bool(geo_macro) or wants_country or wants_us or wants_europe or wants_asia or wants_latam or wants_africa or wants_middle_east

    if (not geo_macro) and has_geo_exclusions and (not has_geo_positive):
        geo_macro = "WORLD"

    # 5) On remet des types JSON-friendly dans excl
    excl["excluded_regions"] = sorted(excluded_regions)

    return {
        "force_french": force_french,

        # Exclusions (JSON-friendly)
        "excluded_regions": excl.get("excluded_regions") or [],
        "excluded_sectors": sorted(list(excl.get("excluded_sectors") or [])),
        "excluded_industries": sorted(list(excl.get("excluded_industries") or [])),
        "excluded_topics": list(excl.get("excluded_topics") or []),

        # Geo macro
        "geo_macro": geo_macro,
        "wants_geo_macro": bool(geo_macro),

        # Autres intents
        "wants_etf": any(k in t for k in ["etf", "tracker", "ucits", "fonds indiciel", "index fund"]),
        "wants_dividend": any(k in t for k in ["dividende", "dividendes", "dividend", "yield", "coupon"]),
        "wants_marketcap": any(k in t for k in ["capitalisation", "market cap", "cap", "grosse cap", "large cap"]),
        "wants_volume": any(
            k in t
            for k in [
                "volume", "volumes", "liquidité", "liquidite", "liquide", "liquidity",
                "trading volume", "volume échangé", "volume echange", "volume journalier"
            ]
        ),
        "wants_volatility": any(k in t for k in ["volatilité", "volatilite", "volatility", "volatile"]),
        "wants_beta": "beta" in t,
        "wants_low_risk": any(k in t for k in ["stable", "peu risqué", "peu risque", "low risk", "defensif", "défensif"]),
        "wants_exchange": wants_exchange,

        "wants_sector": ("secteur" in t or "sector" in t) or any(s.lower() in t for s in [x.lower() for x in ALLOWED_SECTORS]),
        "wants_industry": ("industrie" in t or "industry" in t) or any(
            k in t for k in ["pharma", "pharmaceut", "semi", "conducteur", "automobile", "auto", "luxe", "défense", "defense", "assurance", "banque"]
        ),

        # Geo flags
        "wants_us": wants_us,
        "wants_europe": wants_europe,
        "wants_asia": wants_asia,
        "wants_middle_east": wants_middle_east,
        "wants_africa": wants_africa,
        "wants_latam": wants_latam,

        # Neg flags
        "neg_us": neg_us,
        "neg_eu": neg_eu,
        "neg_asia": neg_asia,
        "neg_middle_east": neg_middle_east,
        "neg_africa": neg_africa,
        "neg_latam": neg_latam,

        # Country (ISO2)
        "wants_country": wants_country,
        "wants_country_regions": sorted(list(wants_country_regions)),

        "wants_categoryname": wants_categoryname,

        # Fund-related
        "fund_wants_rank": any(
            k in t for k in [
                "bien classé", "bien classe", "top", "meilleur", "meilleurs",
                "rank", "classement", "dans sa catégorie", "dans sa categorie"
            ]
        ),
        "fund_wants_perf_rating": any(k in t for k in ["performance rating", "performancerating"]),
        "fund_wants_risk_rating": any(k in t for k in ["risk rating", "riskrating"]),

        # Price / change
        "wants_price": any(k in t for k in ["prix", "price", "nav"]),
        "wants_intraday_change": any(k in t for k in ["variation", "change", "intraday", "hausse", "baisse"]),
    }


# =============================================================================
# Post-processing helpers
# =============================================================================
def _hashable_key(v: Any) -> str:
    try:
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    except TypeError:
        return str(v)


def _dedupe_constraints(constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for c in constraints:
        k = _hashable_key({"field": c.get("field"), "operator": c.get("operator"), "values": c.get("values")})
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out


def _coerce_industry_sector(c: Dict[str, Any], notes: str) -> Tuple[Dict[str, Any], str]:
    if c.get("field") != "industry":
        return c, notes
    vals = c.get("values", [])
    if not isinstance(vals, list) or not vals:
        return c, notes
    if not all(isinstance(v, str) for v in vals):
        return c, notes
    if all(v in ALLOWED_SECTORS for v in vals):
        c2 = dict(c)
        c2["field"] = "sector"
        notes = (notes + " | " if notes else "") + "industry→sector corrigé automatiquement (valeur de secteur détectée)."
        return c2, notes
    return c, notes


def _extract_rating_set(segment: str) -> List[int]:
    nums = [int(x) for x in re.findall(r"\b(\d)\b", segment or "")]
    return sorted({n for n in nums if 1 <= n <= 5})


def _extract_ratings_by_context(user_prompt: str) -> Tuple[List[int], List[int]]:
    t = (user_prompt or "").lower()
    perf_nums: List[int] = []
    risk_nums: List[int] = []

    m_perf = re.search(r"(performance\s*rating|performancerating)[^0-9]{0,30}(.+?)(?:,|;|\.|$)", t)
    if m_perf:
        seg = m_perf.group(2)
        seg = re.split(r"\b(risk|risque)\b", seg, maxsplit=1)[0]
        perf_nums = _extract_rating_set(seg)

    m_risk = re.search(r"(risk\s*rating|riskrating)[^0-9]{0,30}(.+?)(?:,|;|\.|$)", t)
    if m_risk:
        seg = m_risk.group(2)
        seg = re.split(r"\b(performance)\b", seg, maxsplit=1)[0]
        risk_nums = _extract_rating_set(seg)

    return perf_nums, risk_nums

def _apply_fund_rating_overrides(user_prompt: str, constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    perf_nums, risk_nums = _extract_ratings_by_context(user_prompt)
    if not perf_nums and not risk_nums:
        return constraints

    out = [dict(c) for c in constraints]

    if perf_nums:
        out = [c for c in out if c.get("field") != "performanceratingoverall"]
        out.append({"field": "performanceratingoverall", "operator": "is-in", "values": perf_nums})

    if risk_nums:
        out = [c for c in out if c.get("field") != "riskratingoverall"]
        out.append({"field": "riskratingoverall", "operator": "is-in", "values": risk_nums})

    return out

def _merge_constraints(constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_field: Dict[str, List[Dict[str, Any]]] = {}
    for c in constraints:
        f = c.get("field")
        if isinstance(f, str) and f:
            by_field.setdefault(f, []).append(c)

    merged: List[Dict[str, Any]] = []
    for field, group in by_field.items():
        eq_vals: List[Any] = []
        other: List[Dict[str, Any]] = []

        for c in group:
            op = c.get("operator")
            vals = _flatten_values(c.get("values", []))
            c2 = dict(c)
            c2["values"] = vals
            if op in {"eq", "is-in"}:
                eq_vals.extend(vals)
            else:
                other.append(c2)

        merged.extend(other)

        if eq_vals:
            uniq: List[Any] = []
            seen: set[str] = set()
            for v in eq_vals:
                k = _hashable_key(v)
                if k not in seen:
                    seen.add(k)
                    uniq.append(v)
            merged.append({"field": field, "operator": "is-in", "values": uniq})

    merged.sort(key=lambda x: str(x.get("field", "")))
    return merged

def _prune_noise_constraints(
    flags: Dict[str, Any],
    constraints: List[Dict[str, Any]],
    notes: str,
) -> Tuple[List[Dict[str, Any]], str]:
    if not constraints:
        return constraints, notes

    excluded_sectors = set(flags.get("excluded_sectors") or [])
    excluded_industries = set(flags.get("excluded_industries") or [])

    out = []
    for c in constraints:
        if not isinstance(c, dict):
            continue
        f = c.get("field")
        if f == "sector" and (not flags.get("wants_sector")) and (not excluded_sectors):
            vals = _flatten_values(c.get("values", []))
            if len([v for v in vals if isinstance(v, str)]) >= len(ALLOWED_SECTORS) * 0.8:
                continue
        if f == "industry" and (not flags.get("wants_industry")) and (not excluded_industries):
            vals = _flatten_values(c.get("values", []))
            if len([v for v in vals if isinstance(v, str)]) >= len(ALLOWED_INDUSTRIES) * 0.8:
                continue
        out.append(c)

    return out, notes


def _coerce_revenues_to_marketcap_if_requested(
    user_prompt: str,
    constraints: List[Dict[str, Any]],
    notes: str,
) -> Tuple[List[Dict[str, Any]], str]:
    t = (user_prompt or "").lower()
    wants_cap = any(k in t for k in ["capitalisation", "market cap", "cap", "large cap", "grosse cap"])
    if not wants_cap:
        return constraints, notes

    out: List[Dict[str, Any]] = []
    changed = False
    for c in constraints:
        if c.get("field") == EQUITY_REVENUES_FIELD:
            c2 = dict(c)
            c2["field"] = EQUITY_MARKETCAP_FIELD
            out.append(c2)
            changed = True
        else:
            out.append(c)

    if changed:
        notes = (notes + " | " if notes else "") + "revenus→market cap corrigé automatiquement (cap détectée dans la demande)."
    return out, notes


def _handle_volatility_wording(flags: Dict[str, Any], notes: str) -> str:
    if flags.get("wants_volatility") and not flags.get("wants_beta"):
        notes = (notes + " | " if notes else "") + (
            "Demande de volatilité : pas de filtre de volatilité directe ici ; "
            "attention à ne pas confondre avec le volume."
        )
    if flags.get("wants_volatility") and flags.get("wants_beta"):
        notes = (notes + " | " if notes else "") + (
            "Demande de volatilité : beta utilisé comme proxy (la volatilité historique n'est pas filtrable ici)."
        )
    return notes


def _drop_exchange_if_not_explicit(
    flags: Dict[str, Any],
    c: Dict[str, Any],
    notes: str,
    universe: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    if c.get("field") != "exchange":
        return c, notes
    if flags.get("wants_exchange"):
        return c, notes
    notes = (notes + " | " if notes else "") + f"filtre exchange supprimé ({universe}) : non demandé explicitement."
    return None, notes


def _drop_fund_irrelevant_numeric(flags: Dict[str, Any], c: Dict[str, Any], notes: str) -> Tuple[Optional[Dict[str, Any]], str]:
    f = str(c.get("field", "")).lower()
    if f in {"eodprice", "price", "nav", "navprice"} and not flags.get("wants_price"):
        notes = (notes + " | " if notes else "") + "filtre prix supprimé (fund) : non demandé explicitement."
        return None, notes
    if "intraday" in f or "pricechange" in f or "change" in f:
        if not flags.get("wants_intraday_change"):
            notes = (notes + " | " if notes else "") + "filtre variation supprimé (fund) : non demandé explicitement."
            return None, notes
    return c, notes


def _prefer_isin_for_categorical(universe: str, c: Dict[str, Any]) -> Dict[str, Any]:
    field = c.get("field")
    op = c.get("operator")
    if not isinstance(field, str) or not isinstance(op, str):
        return c

    if universe == "equity":
        allowed_cat = set(ALLOWED_EQ_CATEGORICAL_FIELDS)
    else:
        allowed_cat = set(ALLOWED_FUND_CATEGORICAL_FIELDS)

    if field in allowed_cat and op == "eq":
        c2 = dict(c)
        c2["operator"] = "is-in"
        return c2
    return c


# ---------------------------------------------------------------------
# ✅ NEW: macro-group expansion helpers
# ---------------------------------------------------------------------
def _group_key(s: str) -> str:
    return (s or "").strip().upper().replace("-", "_").replace(" ", "_")


def _expand_region_groups(values: List[Any]) -> List[str]:
    """
    Expand macro region groups (EUROPE/USA/...) into country codes (fr,de,...).
    Also accepts common aliases: "eu", "europe", "us", "usa".
    """
    allowed = set(ALLOWED_REGIONS)
    out: List[str] = []

    def _add_many(xs: Set[str]) -> None:
        for x in sorted(xs):
            if x in allowed and x not in out:
                out.append(x)

    for v in values:
        if not isinstance(v, str):
            continue
        vv = v.strip().lower()
        k = _group_key(vv)

        # common aliases
        if vv in {"eu", "europe", "european", "ue"}:
            k = "EUROPE"
        if vv in {"us", "usa", "united states", "états-unis", "etats-unis", "america", "amérique"}:
            k = "USA"

        if REGION_GROUPS and k in REGION_GROUPS:
            _add_many(set(REGION_GROUPS[k]))
            continue

        # if already a country code
        if vv in allowed and vv not in out:
            out.append(vv)

        # allow "gb"/"uk"
        if vv == "uk" and "gb" in allowed and "gb" not in out:
            out.append("gb")

    return out


def _normalize_equity_region_values(values: List[Any]) -> List[str]:
    expanded = _expand_region_groups(values)
    # unique stable order already handled in _expand_region_groups
    return expanded

def _normalize_str_list(values: Any) -> List[str]:
    """
    Utilisé pour traiter les valeurs venant du LLM.
    """
    vals = _flatten_values(values if values is not None else [])
    out: List[str] = []

    for v in vals:
        if isinstance(v, str):
            s = v.strip()
            if s:
                out.append(s)

    return out

def _rewrite_neq_to_exclusions(
    constraints: list[dict[str, Any]],
    excluded: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """
    On le réécrit en exclusions (sinon la validation échoue car 'neq' n'est pas supporté).
    """
    out: list[dict[str, Any]] = []
    for c in constraints:
        op = str(c.get("operator", "")).lower().strip()
        if op not in {"neq", "not-in"}:
            out.append(c)
            continue

        field = str(c.get("field", "")).strip()
        vals = _normalize_str_list(c.get("values", []))

        # Cas secteur
        if field.lower() in {"sector", "sectorname"} and vals:
            excluded.setdefault("excluded_sectors", set()).update(vals)
            continue  # on supprime cette contrainte (remplacée par exclusion)

        # Cas industrie
        if field.lower() in {"industry", "industryname"} and vals:
            excluded.setdefault("excluded_industries", set()).update(vals)
            continue

        # Fallback: on ne sait pas inverser ce champ => on drop pour éviter de casser
        # (ou tu peux lever une erreur explicite si tu préfères)
        continue
    return out


def _force_macro_equity_geo(
    cleaned: List[Dict[str, Any]],
    notes: str,
    macro: str,
) -> Tuple[List[Dict[str, Any]], str]:
    macro_key = _group_key(macro)
    cleaned2: List[Dict[str, Any]] = [c for c in cleaned if c.get("field") != "region"]

    allowed_regions = set(ALLOWED_REGIONS)

    # ✅ fallback WORLD: monde = tous les pays autorisés
    if macro_key == "WORLD":
        vals = sorted(list(allowed_regions))
        if vals:
            cleaned2.append({"field": "region", "operator": "is-in", "values": vals})
            return cleaned2, notes
        notes = (notes + " | " if notes else "") + "WORLD demandé mais ALLOWED_REGIONS est vide."
        return cleaned2, notes

    if not REGION_GROUPS or macro_key not in REGION_GROUPS:
        notes = (notes + " | " if notes else "") + f"macro-région {macro_key!r} détectée mais absente de REGION_GROUPS."
        return cleaned2, notes

    vals = sorted(list(set(REGION_GROUPS[macro_key]) & allowed_regions))
    if not vals:
        notes = (notes + " | " if notes else "") + (
            f"macro-région {macro_key!r} détectée mais aucun pays de ce groupe n'est disponible dans ALLOWED_REGIONS."
        )
        return cleaned2, notes

    cleaned2.append({"field": "region", "operator": "is-in", "values": vals})
    return cleaned2, notes


def _force_europe_equity_geo(cleaned: List[Dict[str, Any]], notes: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    ✅ Europe déterministe (equity):
    - Supprime toute contrainte region existante
    - Ajoute region=[pays Europe] via REGION_GROUPS["EUROPE"] (sinon fallback candidates ∩ allowed)
    """
    cleaned2: List[Dict[str, Any]] = [c for c in cleaned if c.get("field") != "region"]

    allowed_regions = set(ALLOWED_REGIONS)

    europe = set(REGION_GROUPS.get("EUROPE", set()) or _EUROPE_REGION_CANDIDATES)

    europe_regions = sorted(list(europe & allowed_regions))

    if europe_regions:
        cleaned2.append({"field": "region", "operator": "is-in", "values": europe_regions})
        return cleaned2, notes

    # If region not available, keep note (no exchange fallback anymore)
    notes = (notes + " | " if notes else "") + (
        "Europe demandée mais aucun pays Europe n'est disponible dans ALLOWED_REGIONS ; "
        "impossible d'appliquer region."
    )
    return cleaned2, notes


def _ensure_equity_geo(flags: Dict[str, Any], cleaned: List[Dict[str, Any]], notes: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Ajoute la géo en equity si demandée et absente.
    - US => region via REGION_GROUPS["USA"] (souvent {"us"})
    - pays explicites => region=ces pays
    - Europe => gérée ailleurs via _force_europe_equity_geo
    """
    existing_fields = {c.get("field") for c in cleaned if isinstance(c, dict)}
    has_region = "region" in existing_fields

    if has_region:
        return cleaned, notes

    allowed = set(ALLOWED_REGIONS)

    # Country explicit
    if flags.get("wants_country"):
        wanted = set(flags.get("wants_country_regions") or [])
        vals = sorted([x for x in wanted if x in allowed])
        if vals:
            cleaned.append({"field": "region", "operator": "is-in", "values": vals})
            return cleaned, notes

    # US
    if flags.get("wants_us"):
        us_vals: List[str] = []
        if REGION_GROUPS and "USA" in REGION_GROUPS:
            us_vals = sorted([x for x in set(REGION_GROUPS["USA"]) if x in allowed])
        else:
            if "us" in allowed:
                us_vals = ["us"]
        if us_vals:
            cleaned.append({"field": "region", "operator": "is-in", "values": us_vals})
        else:
            notes = (notes + " | " if notes else "") + "US demandés mais 'us' n'est pas dans ALLOWED_REGIONS."
    return cleaned, notes


def _ensure_fund_geo(flags: Dict[str, Any], cleaned: List[Dict[str, Any]], notes: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Ajoute la géo en fund si demandée et absente.
    - FundQuery utilise exchange comme proxy geo (USA/EUROPE/ASIA/LATAM/...)
    """
    existing_fields = {c.get("field") for c in cleaned if isinstance(c, dict)}
    has_exchange = "exchange" in existing_fields

    if has_exchange:
        return cleaned, notes

    # pas de macro fund automatique ici (guardrail): seulement si user demande "US"/"Europe"/etc.
    if flags.get("wants_us"):
        if "NAS" in set(ALLOWED_FUND_EXCHANGES) or "NYS" in set(ALLOWED_FUND_EXCHANGES):
            cleaned.append({"field": "exchange", "operator": "is-in", "values": ["NAS", "NYS"]})
            return cleaned, notes
        notes = (notes + " | " if notes else "") + "US demandés (fund) mais aucun exchange US n'est autorisé."
        return cleaned, notes

    if flags.get("wants_europe"):
        if "EUR" in set(ALLOWED_FUND_EXCHANGES):
            cleaned.append({"field": "exchange", "operator": "is-in", "values": ["EUR"]})
            return cleaned, notes
        notes = (notes + " | " if notes else "") + "Europe demandée (fund) mais 'EUR' n'est pas autorisé."
        return cleaned, notes

    return cleaned, notes


def _apply_exclusions_to_constraints(
    flags: Dict[str, Any],
    cleaned: List[Dict[str, Any]],
    notes: str,
    universe: str,
) -> Tuple[List[Dict[str, Any]], str]:
    excluded_regions = set(flags.get("excluded_regions") or [])
    excluded_sectors = set(flags.get("excluded_sectors") or [])
    excluded_industries = set(flags.get("excluded_industries") or [])
    excluded_topics = list(flags.get("excluded_topics") or [])

    if excluded_topics:
        notes = (notes + " | " if notes else "") + "Exclusions non représentables: " + "; ".join(excluded_topics)

    if universe == "equity":
        # exclusions region (pays + macros)
        if excluded_regions:
            # 1) Construire un set d'ISO2 à exclure (en expansant les macros via REGION_GROUPS)
            excl_iso2: set[str] = set()

            for r in list(excluded_regions):
                if not isinstance(r, str):
                    continue
                r0 = r.strip().lower()

                # ISO2 direct
                if len(r0) == 2:
                    excl_iso2.add(r0)
                    continue

                # Macro -> expand (asia/europe/latam/...)
                key = r0.upper()
                if key in REGION_GROUPS:
                    grp = REGION_GROUPS.get(key) or []
                    excl_iso2 |= set(map(str.lower, grp))

            out: List[Dict[str, Any]] = []
            for c in cleaned:
                if c.get("field") == "region":
                    vals = [v.lower() for v in _flatten_values(c.get("values", [])) if isinstance(v, str)]
                    vals2 = [v for v in vals if v not in excl_iso2]
                    if vals2:
                        c2 = dict(c)
                        c2["values"] = vals2
                        out.append(c2)
                    else:
                        notes = (notes + " | " if notes else "") + "filtre region supprimé (tout exclu)."
                else:
                    out.append(c)
            cleaned = out

        # exclusions industry
        if excluded_industries:
            # 0) guard: sans secteur, ne pas fabriquer une whitelist gigantesque
            sector_vals: List[str] = []
            for c in cleaned:
                if c.get("field") == "sector" and str(c.get("operator", "")).strip().lower() in {"eq", "is-in"}:
                    sector_vals = [v for v in _flatten_values(c.get("values", [])) if isinstance(v, str)]
                    break

            if not sector_vals:
                notes = (notes + " | " if notes else "") + (
                    "exclusion industry ignorée (pas de secteur de référence ; Yahoo ne supporte pas 'not-in'). "
                    "Ex: 'Europe + Technology sans semiconducteurs' ou 'Europe + Industrials sans défense'."
                )
            else:
                # 1) Construire whitelist industries du/des secteurs - exclusions
                allowed_inds: set[str] = set()
                for s in sector_vals:
                    allowed_inds |= set(SECTOR_INDUSTRY_MAPPING.get(s, set()))

                allowed_inds -= set(excluded_industries)

                if allowed_inds:
                    out2: List[Dict[str, Any]] = []
                    replaced = False
                    for c in cleaned:
                        if c.get("field") == "industry":
                            c2 = dict(c)
                            c2["operator"] = "is-in"
                            c2["values"] = sorted(list(allowed_inds))
                            out2.append(c2)
                            replaced = True
                        else:
                            out2.append(c)

                    if not replaced:
                        out2.append({"field": "industry", "operator": "is-in", "values": sorted(list(allowed_inds))})

                    cleaned = out2
                else:
                    notes = (notes + " | " if notes else "") + (
                        "exclusion industry impossible (aucune industry restante dans le secteur)."
                    )

        return cleaned, notes

    # fund: exclusions sector/industry non supportées ; region = exchange macro (pas ici)
    if excluded_regions or excluded_sectors or excluded_industries:
        notes = (notes + " | " if notes else "") + (
            "Exclusions demandées non supportées en fund (sauf cas US/EUR gérés via exchange)."
        )
    return cleaned, notes


def _clean_notes_by_intent(notes: str, flags: Dict[str, Any]) -> str:
    # Si l'utilisateur ne demande pas quelque chose, ne spam pas les notes.
    # (garde les notes utiles)
    return notes.strip()


def _force_french_notes(notes: str, flags: Dict[str, Any]) -> str:
    # ici on peut ajouter une traduction/enrichissement si besoin
    return notes.strip()


def _verbose_debug_notes(
    user_prompt: str,
    universe: str,
    flags: Dict[str, Any],
    constraints: List[Dict[str, Any]],
    notes: str,
) -> str:
    """
    Notes verbeuses pour debug: objectif = rendre le résultat "explicable" à partir
    UNIQUEMENT de (prompt, universe, flags, constraints, notes) sans modifier le pipeline.

    Principe:
    - afficher ce qui a été détecté (signaux)
    - afficher ce qui a été demandé explicitement (inclusions/exclusions)
    - expliquer la décision "probable" (heuristique) qui relie signaux -> contraintes
    - signaler contradictions / cas limites
    - résumer les contraintes finales avec tailles + échantillons
    """
    parts: List[str] = []

    # -------- 0) notes existantes --------
    notes = (notes or "").strip()
    if notes:
        parts.append(f"Notes pipeline: {notes}")

    # -------- 1) prompt / universe --------
    parts.append(f"Prompt: {user_prompt!r}")
    parts.append(f"Universe: {universe}")

    # -------- 2) signaux détectés --------
    pos_sectors = _extract_positive_sectors(user_prompt or "")
    parts.append(f"Secteurs détectés (sens positif): {pos_sectors or '0'}")

    wants_us = bool(flags.get("wants_us"))
    wants_eu = bool(flags.get("wants_europe"))
    wants_asia = bool(flags.get("wants_asia"))
    wants_latam = bool(flags.get("wants_latam"))
    wants_africa = bool(flags.get("wants_africa"))
    wants_me = bool(flags.get("wants_middle_east"))
    wants_country = bool(flags.get("wants_country"))
    wants_geo_macro = bool(flags.get("wants_geo_macro"))
    geo_macro = flags.get("geo_macro")

    excluded_regions = flags.get("excluded_regions") or []
    excluded_sectors = flags.get("excluded_sectors") or []
    excluded_industries = flags.get("excluded_industries") or []
    excluded_topics = flags.get("excluded_topics") or []

    wants_country_regions = flags.get("wants_country_regions") or []

    parts.append(
        "Intent geo: "
        f"wants_us={wants_us}, "
        f"wants_europe={wants_eu}, "
        f"wants_asia={wants_asia}, "
        f"wants_latam={wants_latam}, "
        f"wants_africa={wants_africa}, "
        f"wants_middle_east={wants_me}, "
        f"wants_country={wants_country}, "
        f"wants_geo_macro={wants_geo_macro}"
    )
    parts.append(f"geo_macro={geo_macro!r}")

    excl = set(map(lambda x: str(x).lower(), excluded_regions or []))

    neg_us = "us" in excl
    neg_eu = "europe" in excl
    neg_asia = "asia" in excl
    neg_latam = "latam" in excl
    neg_middle_east = ("middle_east" in excl) or ("middle east" in excl)
    neg_africa = "africa" in excl

    parts.append(
        f"neg_eu={neg_eu}, neg_asia={neg_asia}, neg_us={neg_us}, "
        f"neg_latam={neg_latam}, neg_middle_east={neg_middle_east}, neg_africa={neg_africa}"
    )

    parts.append(f"Pays détectés (ISO2)={wants_country_regions or '0'}")

    parts.append(
        "Exclusions demandées: "
        f"regions={excluded_regions}, "
        f"sectors={excluded_sectors}, "
        f"industries={excluded_industries}, "
        f"topics={excluded_topics}"
    )

    # -------- 3) explication "probable" (sans modifier le code) --------
    # Objectif: dire "d'où vient la géo" (macro vs pays vs complément exclusions-only vs rien),
    # et pourquoi un filtre region apparaît ou pas.
    geo_expl: List[str] = []

    # 3.1) Source geo probable
    if wants_country and wants_country_regions:
        geo_expl.append("Décision geo: basée sur pays explicites (wants_country=True).")
    elif wants_geo_macro and geo_macro:
        geo_expl.append(f"Décision geo: basée sur macro-région (geo_macro={geo_macro!r}).")
    elif excluded_regions and not any([wants_us, wants_eu, wants_asia, wants_latam, wants_africa, wants_me, wants_country]):
        geo_expl.append("Décision geo: prompt uniquement négatif (exclusions-only) → construction probable d'un complément (monde − exclusions).")
    else:
        geo_expl.append("Décision geo: aucune intention geo claire → soit pas de filtre geo, soit fallback du pipeline.")

    # 3.2) Détection présence/absence du filtre region dans les contraintes finales
    region_constraints = [
        c for c in (constraints or [])
        if str(c.get("field", "")).strip().lower() == "region"
    ]
    if not constraints:
        geo_expl.append("Résultat: aucune contrainte finale (tout a été élagué ou rien n'était applicable).")
    else:
        if region_constraints:
            # On décrit le(s) filtre(s) region
            for rc in region_constraints:
                op = rc.get("operator", "")
                vals = _flatten_values(rc.get("values", []))
                geo_expl.append(f"Résultat: filtre region présent ({op}), n={len(vals)}.")
        else:
            # Pas de filtre region
            if any([wants_us, wants_eu, wants_asia, wants_latam, wants_africa, wants_me, wants_country, wants_geo_macro]) or excluded_regions:
                geo_expl.append("Résultat: pas de filtre region malgré signaux/exclusions → probablement supprimé (vide après exclusions) ou non applicable.")
            else:
                geo_expl.append("Résultat: pas de filtre region (aucune demande geo détectée).")

    parts.append("Explication (heuristique): " + " ".join(geo_expl))

    # -------- 4) warnings / contradictions / cas limites --------
    warnings: List[str] = []

    # 4.1) Contradictions geo
    if geo_macro is not None:
        try:
            geo_norm = str(geo_macro).strip().lower()
            macro_to_excl = {
                "usa": "us",
                "us": "us",
                "europe": "europe",
                "asia": "asia",
                "latam": "latam",
                "africa": "africa",
                "middle_east": "middle_east",
                "world": "world",
            }
            geo_norm = macro_to_excl.get(geo_norm, geo_norm)

            excl_norm = set(map(lambda x: str(x).strip().lower(), excluded_regions or []))
            if geo_norm in excl_norm:
                warnings.append(f"Contradiction: geo_macro={geo_macro!r} est aussi exclu.")
        except Exception:
            pass

    # 4.2) Secteurs inclus & exclus
    if pos_sectors and excluded_sectors:
        try:
            overlap = sorted(set(map(str.lower, pos_sectors)) & set(map(str.lower, excluded_sectors)))
            if overlap:
                warnings.append(f"Contradiction: secteurs à la fois inclus & exclus: {overlap}.")
        except Exception:
            pass

    # 4.3) Filtre region vide / suspect (ex: n=0)
    for rc in region_constraints:
        vals = _flatten_values(rc.get("values", []))
        if len(vals) == 0:
            warnings.append("Anomalie: contrainte 'region' présente mais liste vide (sera souvent supprimée plus tard).")

    # 4.4) Exclusion de pays sans base geo claire (souvent déclenche un complément)
    if excluded_regions and not (wants_country or wants_geo_macro or wants_us or wants_eu or wants_asia or wants_latam or wants_africa or wants_me):
        warnings.append("Info: exclusions geo sans inclusion explicite → attendu: complément (monde − exclusions).")

    # 4.5) Contradiction / info sur macros exclues
    excl_set = set(map(lambda x: str(x).lower(), excluded_regions or []))

    neg_rx_map = {
        "europe": r"(europe|european(?:s)?|europ[ée]en(?:ne)?(?:s)?|ue|eu\b)",
        "asia": r"(asie|asia|asiatique(?:s)?)",
        "latam": r"(latam|am[eé]rique\s+latine|latin\s+america)",
        "africa": r"(afrique|africa)",
        "middle_east": r"(moyen[-\s]?orient|middle\s+east|mena)",
        "world": r"(monde|mondial|global|world|worldwide|international)",
        "usa": r"(us|usa|u\.?s\.?a\.?|u\.?s\.?|united\s+states|états?-unis|etats?-unis)",
        "north_america": r"(north\s+america|am[eé]rique\s+du\s+nord)",
        "canada": r"(canada|canadien(?:ne)?(?:s)?)",
        "australia": r"(australie|australia|oceanie|oc[eé]anie|australasie)",
    }

    for macro_key, kw_rx in neg_rx_map.items():
        if macro_key not in excl_set:
            continue

        # Si le prompt dit explicitement "sans X", ce n'est pas une contradiction
        if _is_negated_keyword(user_prompt or "", kw_rx):
            # si tu ne veux PAS de "Info", commente la ligne suivante
            continue
        else:
            warnings.append(f"Contradiction: macro '{macro_key}' mentionnée mais aussi exclue.")

    if warnings:
        parts.append("Warnings: " + " ; ".join(dict.fromkeys(warnings)))

    # -------- 5) contraintes finales --------
    if not constraints:
        parts.append("Contraintes finales:  (aucun filtre applicable / tout a été élagué).")
        return " | ".join(parts)

    # aide: region = ISO2
    if region_constraints:
        parts.append("Note région: le champ 'region' utilise des codes ISO2.")

    parts.append(f"Contraintes finales ({len(constraints)}):")
    for i, c in enumerate(constraints, 1):
        field = c.get("field", "")
        op = c.get("operator", "")
        vals = _flatten_values(c.get("values", []))

        # sample stable si possible (tri), sinon ordre naturel
        try:
            vals2 = sorted(vals)
        except Exception:
            vals2 = vals

        sample = vals2[:12]
        more = "" if len(vals2) <= 12 else f" (+{len(vals2)-12} autres)"
        parts.append(f"{i}. {field} {op} -> n={len(vals2)} sample={sample}{more}")

    return " | ".join(parts)


# =============================================================================
# Postprocess main
# =============================================================================
def _postprocess_constraints(user_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    universe = payload.get("universe", "equity")
    constraints: List[Dict[str, Any]] = payload.get("constraints", [])
    notes = payload.get("notes", "")
    notes = notes if isinstance(notes, str) else str(notes)

    flags = _intent_flags(user_prompt)

    # LLM peut générer operator="neq"
    excluded = {
        "excluded_regions": set(flags.get("excluded_regions") or []),
        "excluded_sectors": set(flags.get("excluded_sectors") or []),
        "excluded_industries": set(flags.get("excluded_industries") or []),
    }

    # rewrite neq -> exclusions
    constraints = _rewrite_neq_to_exclusions(constraints, excluded)

    # réinjecte exclusions mises à jour
    flags["excluded_regions"] = sorted(list(excluded["excluded_regions"]))
    flags["excluded_sectors"] = sorted(list(excluded["excluded_sectors"]))
    flags["excluded_industries"] = sorted(list(excluded["excluded_industries"]))

    t = (user_prompt or "").lower()
    positive_sectors = _extract_positive_sectors(user_prompt)

    # --- intent négatif / base intent ---
    has_neg_word = bool(re.search(r"\b(sans|hors|non|without|no)\b", t))

    has_base_intent = any([
        bool(positive_sectors),
        flags.get("wants_us"),
        flags.get("wants_europe"),
        flags.get("wants_asia"),
        flags.get("wants_middle_east"),
        flags.get("wants_africa"),
        flags.get("wants_latam"),
        flags.get("wants_country"),
        flags.get("wants_exchange"),
        flags.get("wants_geo_macro"),
    ])

    has_any_exclusion = any([
        flags.get("excluded_regions"),
        flags.get("excluded_sectors"),
        flags.get("excluded_industries"),
    ]) or bool(flags.get("excluded_topics"))

    # IMPORTANT: drapeau pour éviter de repasser derrière et re-modifier la base reconstruite
    built_base = False

    # prompt uniquement négatif : si c'est juste "sans <secteur>" OU "sans <region>",
    # on construit une base "is-in" par complément (car Yahoo ne supporte pas NOT IN).
    if has_neg_word and has_any_exclusion and not has_base_intent:
        excl_sec = set(flags.get("excluded_sectors") or [])
        excl_reg = set(flags.get("excluded_regions") or [])
        excl_ind = set(flags.get("excluded_industries") or [])

        # -------------------------
        # CAS 1 : uniquement exclusions sector -> base sector = complément
        # -------------------------
        if excl_sec and not excl_reg and not excl_ind:
            allowed = [s for s in ALLOWED_SECTORS if s not in excl_sec]
            if not allowed:
                notes = (notes + " | " if notes else "") + "exclusion sector impossible (tout exclu)."
                return {"universe": universe, "constraints": [], "notes": notes}

            # on supprime toute contrainte sector existante puis on met le complément
            constraints = [
                c for c in constraints
                if str(c.get("field", "")).strip().lower() not in {"sector", "sectorname"}
            ]
            constraints.append({"field": "sector", "operator": "is-in", "values": allowed})
            notes = (notes + " | " if notes else "") + "base sector construite automatiquement (complément)."

        # -------------------------
        # CAS 2 : uniquement exclusions region -> base region = complément
        # -------------------------
        elif excl_reg and not excl_sec and not excl_ind:
            expanded_excl = set()
            for r in excl_reg:
                r_norm = str(r).strip().lower()

                # macros éventuelles
                if r_norm in {"europe", "eu"}:
                    expanded_excl |= set(REGION_GROUPS.get("EUROPE", set()))
                elif r_norm in {"asia", "asie"}:
                    expanded_excl |= set(REGION_GROUPS.get("ASIA", set()))
                elif r_norm in {"latam"}:
                    expanded_excl |= set(REGION_GROUPS.get("LATAM", set()))
                elif r_norm in {"africa", "afrique"}:
                    expanded_excl |= set(REGION_GROUPS.get("AFRICA", set()))
                elif r_norm in {"middle_east", "moyen_orient", "moyen-orient", "mena"}:
                    expanded_excl |= set(REGION_GROUPS.get("MIDDLE_EAST", set()))
                else:
                    # sinon on suppose que c'est déjà un code pays (us/fr/de/jp/...)
                    expanded_excl.add(r_norm)

            allowed_regions = [x for x in ALLOWED_REGIONS if x not in expanded_excl]
            if not allowed_regions:
                notes = (notes + " | " if notes else "") + "exclusion region impossible (tout exclu)."
                return {"universe": universe, "constraints": [], "notes": notes}

            # on a reconstruit une base => ne pas repasser derrière dans d'autres patches
            built_base = True

            # IMPORTANT: ne pas laisser plus tard le code supprimer region "non demandée"
            flags["wants_geo_macro"] = True

            # IMPORTANT: éviter l'étape "wants_country" qui intersecte / supprime
            flags["wants_country"] = False
            flags["wants_country_regions"] = list(allowed_regions)

            # on supprime toute contrainte region existante puis on met le complément
            constraints = [
                c for c in constraints
                if str(c.get("field", "")).strip().lower() != "region"
            ]
            constraints.append({"field": "region", "operator": "is-in", "values": allowed_regions})

            notes = (notes + " | " if notes else "") + "base region construite automatiquement (complément)."

        # -------------------------
        # CAS non représentable facilement (mix exclusions sector+region+industry, etc.)
        # -------------------------
        else:
            notes = (notes + " | " if notes else "") + (
                "Exclusion demandée mais aucun critère positif (région/secteur) n'est fourni : "
                "précise une base, ex: 'Europe sans défense' ou 'Industrials sans défense'."
            )
            return {"universe": universe, "constraints": [], "notes": notes}

    # -------- PATCH : exclusions sector (ne PAS repasser si on vient de reconstruire une base) --------
    excluded_sectors = set(flags.get("excluded_sectors") or [])
    if excluded_sectors and not built_base:
        sector_fields = {"sector", "sectorname"}

        sector_constraints = [
            c for c in constraints
            if str(c.get("field", "")).strip().lower() in sector_fields
        ]

        if not sector_constraints:
            allowed = [s for s in ALLOWED_SECTORS if s not in excluded_sectors]
            if allowed:
                constraints.append({"field": "sector", "operator": "is-in", "values": allowed})
        else:
            for c in sector_constraints:
                if str(c.get("operator", "")).lower() == "is-in":
                    vals = _normalize_str_list(c.get("values", []))
                    c["values"] = [v for v in vals if v not in excluded_sectors]

    # -------- PATCH : verrouillage secteur explicite --------
    explicit_sectors = positive_sectors
    if explicit_sectors:
        constraints = [
            c for c in constraints
            if str(c.get("field", "")).strip().lower() not in {"sector", "sectorname"}
        ]
        constraints.append({"field": "sector", "operator": "is-in", "values": explicit_sectors})

    # -------- PATCH : ignorer "sans software" hors tech --------
    excluded_industries = set(flags.get("excluded_industries") or [])

    software_inds = {
        "Software—Application",
        "Software—Infrastructure",
        "Technical & System Software"
    }

    if explicit_sectors and "Technology" not in explicit_sectors and (excluded_industries & software_inds):
        excluded_industries -= software_inds
        flags["excluded_industries"] = sorted(list(excluded_industries))
        notes = (notes + " | " if notes else "") + "exclusion 'software' ignorée (hors secteur Technology)."

    # -------- PATCH : nettoyage industries --------
    if excluded_industries:
        industry_fields = {"industry", "industryname"}

        industry_constraints = [
            c for c in constraints
            if str(c.get("field", "")).strip().lower() in industry_fields
        ]

        for c in industry_constraints:
            if str(c.get("operator", "")).lower() == "is-in":
                vals = _normalize_str_list(c.get("values", []))
                c["values"] = [v for v in vals if v not in excluded_industries]

        constraints2 = []

        for c in constraints:
            if str(c.get("field", "")).lower() in industry_fields:
                vals = _normalize_str_list(c.get("values", []))
                if not vals:
                    notes = (notes + " | " if notes else "") + "filtre industry supprimé (tout exclu)."
                    continue
            constraints2.append(c)

        constraints = constraints2

    # -------- stabilizer industries --------
    keyword_inds = _extract_keyword_industries(user_prompt)

    # -------------------
    # FUND
    # -------------------
    if universe == "fund":
        notes = ""  # on ignore les notes brutes du LLM (souvent bruit)
        cleaned: List[Dict[str, Any]] = []

        for c in constraints:
            c = dict(c)
            field = c.get("field", "")
            c["values"] = _flatten_values(c.get("values", []))

            # exchange : normalise + drop si pas demandé explicitement (sauf cas US dans system prompt)
            if field == "exchange":
                c2, notes = _drop_exchange_if_not_explicit(flags, c, notes, universe="fund")
                if c2 is None:
                    continue
                c = c2

            # numeric filters irrelevant for fund -> drop
            c, notes = _drop_fund_irrelevant_numeric(flags, c, notes)
            if c is None:
                continue

            # categoryname : drop si ressemble à de la géo / bourse / etc (guardrail)
            if field == "categoryname" and isinstance(c.get("values"), list):
                if len(c["values"]) == 1 and isinstance(c["values"][0], str):
                    blob = c["values"][0].lower()
                    if any(k in blob for k in ["etf", "ucits", "paris", "euronext", "nasdaq", "nyse", "us", "fr", "europe", "european"]):
                        notes = (notes + " | " if notes else "") + "categoryname non fiable => déplacé en notes."
                        continue

                blob = " ".join([str(v).lower() for v in c["values"]])
                if any(k in blob for k in ["etf", "ucits", "paris", "euronext", "nasdaq", "nyse", "us", "fr", "europe", "european"]):
                    notes = (notes + " | " if notes else "") + "categoryname non fiable => déplacé en notes."
                    continue

            c = _prefer_isin_for_categorical("fund", c)
            cleaned.append(c)

        if flags["fund_wants_rank"]:
            if not any(c.get("field") == "annualreturnnavy1categoryrank" for c in cleaned):
                cleaned.append({"field": "annualreturnnavy1categoryrank", "operator": "lt", "values": [50]})

        cleaned = _apply_fund_rating_overrides(user_prompt, cleaned)
        cleaned, notes = _ensure_fund_geo(flags, cleaned, notes)

        cleaned = _merge_constraints(cleaned)
        cleaned = _dedupe_constraints(cleaned)

        if not cleaned:
            wants_quality_fallback = bool(flags.get("wants_etf")) and (
                bool(flags.get("wants_europe")) or bool(flags.get("wants_dividend"))
            )
            if wants_quality_fallback:
                cleaned = [
                    {"field": "performanceratingoverall", "operator": "gt", "values": [3]},
                    {"field": "riskratingoverall", "operator": "lte", "values": [5]},
                ]
                notes = (notes + " | " if notes else "") + (
                    "Fallback qualité (fund) appliqué : performanceratingoverall>3 et riskratingoverall<=5 "
                    "(car critères demandés non filtrables en fund)."
                )

        notes = _clean_notes_by_intent(notes, flags)
        notes = _verbose_debug_notes(user_prompt, universe, flags, cleaned, notes)

        payload["constraints"] = cleaned
        payload["notes"] = notes
        return payload

    # -------------------
    # EQUITY
    # -------------------
    notes = ""  # on ignore les notes brutes du LLM (souvent bruit)
    cleaned: List[Dict[str, Any]] = []

    if keyword_inds:
        constraints = list(constraints) if constraints else []
        constraints.append({"field": "industry", "operator": "is-in", "values": keyword_inds})

    # PATCH : supprimer les industries invalides générées par le LLM
    constraints = _drop_invalid_industries(constraints)

    for c in constraints:
        c = dict(c)
        field = c.get("field", "")
        c["values"] = _flatten_values(c.get("values", []))

        # exchange : normalise + drop si pas demandé
        if field == "exchange":
            c["values"] = _normalize_equity_exchange_values(c.get("values", []))
            c2, notes = _drop_exchange_if_not_explicit(flags, c, notes, universe="equity")
            if c2 is None:
                continue
            c = c2

        # region : normalise + macro expansion
        if field == "region":
            c["values"] = _normalize_equity_region_values(c.get("values", []))
            if not c["values"]:
                continue

            # si l'utilisateur n'a demandé aucune géo, on drop
            if not (flags.get("wants_us") or flags.get("wants_europe") or flags.get("wants_country") or flags.get("wants_geo_macro")):
                notes = (notes + " | " if notes else "") + "filtre region supprimé (non demandé explicitement)."
                continue

            # si pays explicit demandé: on intersecte
            if flags.get("wants_country") and not (flags.get("wants_us") or flags.get("wants_europe")):
                wanted = set(flags.get("wants_country_regions") or [])
                c["values"] = [v for v in c["values"] if v in wanted]
                if not c["values"]:
                    notes = (notes + " | " if notes else "") + "filtre region supprimé (géo demandée mais non résolue proprement)."
                    continue

        # industry->sector si nécessaire
        if field == "industry":
            c, notes = _coerce_industry_sector(c, notes)
            field = c.get("field", "")

        # --- PATCH : si le LLM a sorti une contrainte industry qui ne contient QUE des industries exclues
        # (ex: "energy sans oil" et il met industry = Oil&Gas...), on ignore cette contrainte.
        if field == "industry" and flags.get("excluded_industries"):
            vals = [v for v in _flatten_values(c.get("values", [])) if isinstance(v, str)]
            excl = set(flags.get("excluded_industries") or [])
            if vals and all(v in excl for v in vals):
                notes = (notes + " | " if notes else "") + "filtre industry ignoré (semblait exprimer les exclusions)."
                continue

        # volume non demandé -> drop
        if isinstance(field, str) and field in EQUITY_VOLUME_FIELDS and not flags["wants_volume"]:
            notes = (notes + " | " if notes else "") + "filtre volume supprimé (non demandé explicitement)."
            continue

        # dividend non demandé -> drop
        if field == "forward_dividend_yield" and not flags["wants_dividend"]:
            notes = (notes + " | " if notes else "") + "filtre dividende supprimé (non demandé explicitement)."
            continue

        # marketcap non demandé -> drop
        if field == EQUITY_MARKETCAP_FIELD and not flags["wants_marketcap"]:
            notes = (notes + " | " if notes else "") + "filtre capitalisation supprimé (non demandé explicitement)."
            continue

        # beta uniquement si demandé ou faible risque
        if field == "beta" and not (flags.get("wants_beta") or flags.get("wants_low_risk")):
            notes = (notes + " | " if notes else "") + "filtre beta supprimé (non demandé explicitement)."
            continue

        c = _prefer_isin_for_categorical("equity", c)
        cleaned.append(c)

    # Macro geo (ASIA/LATAM/...) : override déterministe (macro -> pays)
    if flags.get("wants_geo_macro") and flags.get("geo_macro"):
        cleaned, notes = _force_macro_equity_geo(cleaned, notes, flags["geo_macro"])

    #  Europe: override déterministe via region (macro->pays)
    if flags.get("wants_europe"):
        cleaned, notes = _force_europe_equity_geo(cleaned, notes)

    #  Country -> region (plus de country->exchange)
    cleaned, notes = _ensure_equity_geo(flags, cleaned, notes)

    cleaned, notes = _coerce_revenues_to_marketcap_if_requested(user_prompt, cleaned, notes)

    # Fix 'milliard/billion' (1e9) vs confusion 1e12
    cleaned, notes = _fix_billion_milliard_scaling(user_prompt, cleaned, notes)

    cleaned, notes = _restrict_industry_to_sector(cleaned, notes)

    cleaned, notes = _apply_exclusions_to_constraints(flags, cleaned, notes, universe="equity")

    cleaned = _merge_constraints(cleaned)
    cleaned = _dedupe_constraints(cleaned)

    cleaned, notes = _prune_noise_constraints(flags, cleaned, notes)

    notes = _clean_notes_by_intent(notes, flags)
    notes = _verbose_debug_notes(user_prompt, universe, flags, cleaned, notes)

    payload["constraints"] = cleaned
    payload["notes"] = notes
    return payload


# =============================================================================
# Point d'entrée public
# =============================================================================

def _interpret(
    user_prompt: str,
    llm: object,
    correction: Optional[str] = None,
) -> Dict[str, Any]:
    """Appelle le LLM et retourne le JSON brut parsé."""
    universe      = _guess_universe(user_prompt)
    system_prompt = _build_fund_system_prompt() if universe == "fund" else _build_equity_system_prompt()
    content       = _invoke_llm(llm, system_prompt, user_prompt, correction=correction)
    raw           = _parse_json_safely(content)
    raw.setdefault("universe", universe)
    raw.setdefault("constraints", [])
    raw.setdefault("notes", "")
    raw["universe"] = universe
    return raw


def build_constraints_from_prompt(
    user_prompt: str,
    llm: object,
) -> Dict[str, Any]:
    """
    Point d'entrée principal.
    Appelle le LLM, postprocess les contraintes, valide, et retourne le payload.
    Réessaie jusqu'à 3 fois en cas de JSON invalide ou de contrainte mal formée.
    """
    user_prompt = _normalize_user_prompt(user_prompt)
    correction: Optional[str] = None

    for _ in range(3):
        try:
            raw = _interpret(user_prompt, llm, correction=correction)
        except Exception as e:
            correction = f"JSON parsing failed: {e}"
            continue

        raw = _postprocess_constraints(user_prompt, raw)

        try:
            return validate_constraints(raw)
        except Exception as e:
            correction = str(e)

    # Après 3 échecs : retourne un payload vide plutôt que de planter
    return {"universe": _guess_universe(user_prompt), "constraints": [], "notes": "Échec après 3 tentatives."}