import json
import pickle
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import List, Literal
import pandas as pd
import torch
from pydantic import BaseModel,Field
from sentence_transformers import SentenceTransformer, util

from backend.ai.core.llm import general_llm, dbg

_PERIOD_DICT = {
    "1 jour":"1d",
    "5 jours":"5d",
    "1 mois" : "1mo",
    "3 mois" : "3mo",
    "6 mois" : "6mo",
    "1 an": "1y",
    "2 ans" :"2y",
    "5 ans":"5y",
    "depuis le début de l'année":"ytd",
    "depuis toujours":"max"
}
_THRESHOLD_ECART = 0.1
_TOP_SCORE_LOW = 0.35
_TOP_SCORE_HIGH = 0.80
_GAP_SCORE_HIGH = 0.15
_DOMINANT_TOP_SCORE = 0.55
_DOMINANT_GAP_SCORE = 0.07
_DOMINANT_VOLUME_RATIO = 2.8
_STRUCTURED_DIRECT_CONFIDENCE = 0.99
_STRUCTURED_AMBIGUOUS_CONFIDENCE = 0.35
_SEMANTIC_TOP_K = 3
_TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
_TEXT_TOKEN_PATTERN = re.compile(r"(?<![\w.\-])([A-Za-z0-9][A-Za-z0-9.\-]{0,14})(?![\w.\-])")
_LEADING_ARTICLES = {"l", "the"}
_TRAILING_LEGAL_TOKENS = {
    "inc",
    "corp",
    "corporation",
    "company",
    "co",
    "limited",
    "ltd",
    "plc",
    "sa",
    "se",
    "ag",
    "nv",
    "spa",
    "as",
    "asa",
    "ab",
    "group",
    "holding",
    "holdings",
}
_TRAILING_LEGAL_PHRASES = [
    ("societe", "en", "commandite", "par", "actions"),
    ("societe", "europeenne"),
    ("societe", "anonyme"),
]
_MAX_DERIVED_FORM_TOKENS = 3
_FRENCH_ELISION_CLITICS = {"j", "l", "d", "c", "t", "s", "n", "m", "qu"}
_MAX_TEXT_ENTITY_NGRAM = 6
_LOW_SIGNAL_TEXT_TOKENS = {
    "a", "an", "and", "au", "aux", "bourse", "combien", "compare", "comparer", "connaître", "connaitre",
    "cours", "de", "des", "du", "en", "entre", "et", "je", "la", "le", "les", "ou", "par", "pour",
    "prix", "quel", "quelle", "rendement", "stat", "stats", "statistique", "statistiques", "sur", "un",
    "une", "vaut", "vs",
}


#on définit ce que doit renvoyer le LLM
class CompanyExtraction(BaseModel):
    companies: List[str] = Field(
        default=[],
        description="Liste des noms d'entreprises mentionnés dans le texte.",

    )

class PeriodExtraction(BaseModel):
    period: Literal["1 jour","5 jours","1 mois","3 mois","6 mois","1 an","2 ans","5 ans","depuis le début de l'année","depuis toujours"] = Field(
        default="1 an",
        description="trouve la correspondance la période la plus proche de celle mentionnée dans le texte, si aucune période n'est mentionnée on suppose la valeur par défaut de 1 an"
    )

class RegexClass:
    def __init__(self):
        self.universe = self.load_tickers()
        self._prepare_resolution_universe()
        self.external_alias_records = self.load_external_aliases()
        self._build_resolution_indexes()
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = self.load_embedding()
        self.last_symbol_resolution = []

    @staticmethod
    def _normalize_score(value: float, low: float, high: float) -> float:
        if high <= low:
            return 0.0

        normalized = (value - low) / (high - low)
        return max(0.0, min(normalized, 1.0))

    @classmethod
    def _compute_entity_confidence(
        cls,
        top_score: float,
        score_gap: float,
        multiple_matches: bool,
        used_volume_fallback: bool,
    ) -> float:
        # Base confidence combines:
        # - absolute semantic quality of the best match (top_score)
        # - separation from the second-best candidate (score_gap)
        normalized_top = cls._normalize_score(top_score, _TOP_SCORE_LOW, _TOP_SCORE_HIGH)
        normalized_gap = cls._normalize_score(score_gap, 0.0, _GAP_SCORE_HIGH)
        base_confidence = 0.7 * normalized_top + 0.3 * normalized_gap

        if multiple_matches:
            base_confidence -= 0.15

        if used_volume_fallback:
            base_confidence -= 0.10

        return max(0.0, min(base_confidence, 1.0))

    @staticmethod
    def _to_float(value: object) -> float:
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _has_dominant_top_candidate(
        cls,
        top_score: float,
        score_gap: float,
        semantic_top_row: pd.Series,
        top_candidate_rows: pd.DataFrame,
    ) -> bool:
        if top_score < _DOMINANT_TOP_SCORE or score_gap < _DOMINANT_GAP_SCORE:
            return False

        semantic_top_volume = cls._to_float(semantic_top_row.get("avgvolume3m"))
        if semantic_top_volume <= 0.0:
            return False

        runner_up_rows = top_candidate_rows.iloc[1:]
        if runner_up_rows.empty:
            return True

        runner_up_volume = max(cls._to_float(row.get("avgvolume3m")) for _, row in runner_up_rows.iterrows())
        if runner_up_volume <= 0.0:
            return True

        return semantic_top_volume >= runner_up_volume * _DOMINANT_VOLUME_RATIO

    @staticmethod
    def _normalize_entity_label(value: object) -> str:
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _canonicalize_company_name(cls, value: object) -> str:
        normalized = cls._normalize_entity_label(value)
        if not normalized:
            return ""

        tokens = normalized.split()
        while len(tokens) > 1 and tokens[0] in _LEADING_ARTICLES:
            tokens = tokens[1:]

        changed = True
        while len(tokens) > 1 and changed:
            changed = False
            for phrase in _TRAILING_LEGAL_PHRASES:
                if len(tokens) > len(phrase) and tuple(tokens[-len(phrase):]) == phrase:
                    tokens = tokens[:-len(phrase)]
                    changed = True
                    break

        while len(tokens) > 1 and tokens[-1] in _TRAILING_LEGAL_TOKENS:
            tokens = tokens[:-1]

        return " ".join(tokens).strip()

    @staticmethod
    def _safe_series(series: pd.Series) -> pd.Series:
        return series.fillna("").astype(str)

    @classmethod
    def _normalize_symbol_token(cls, value: object) -> str:
        return str(value or "").strip().upper()

    @classmethod
    def _is_french_elision_fragment(cls, text: str, candidate: object) -> bool:
        normalized_candidate = cls._normalize_entity_label(candidate)
        if normalized_candidate not in _FRENCH_ELISION_CLITICS:
            return False

        raw_text = str(text or "").replace("’", "'")
        if not raw_text:
            return False

        candidate_pattern = re.escape(str(candidate or "").strip())
        if not candidate_pattern:
            return False

        return re.search(rf"(?i)(?<!\w){candidate_pattern}'", raw_text) is not None

    @classmethod
    def _is_explicit_symbol_form(cls, value: object) -> bool:
        raw = str(value or "").strip()
        if not raw or " " in raw:
            return False

        token = cls._normalize_symbol_token(raw)
        if not _TICKER_PATTERN.match(token):
            return False

        has_digit = any(ch.isdigit() for ch in raw)
        has_separator = any(ch in ".-" for ch in raw)
        is_all_upper_alpha = any(ch.isalpha() for ch in raw) and raw == raw.upper()
        return has_digit or has_separator or is_all_upper_alpha

    @classmethod
    def _is_ticker_like(cls, value: object) -> bool:
        token = cls._normalize_symbol_token(value)
        if not token or " " in token:
            return False
        if not _TICKER_PATTERN.match(token):
            return False

        has_digit = any(ch.isdigit() for ch in token)
        has_separator = any(ch in ".-" for ch in token)
        is_upperish = token == token.upper()
        return is_upperish or has_digit or has_separator

    @classmethod
    def _is_legal_suffix_token(cls, value: object) -> bool:
        normalized = cls._normalize_entity_label(value)
        return normalized in _TRAILING_LEGAL_TOKENS

    def _prepare_resolution_universe(self) -> None:
        if self.universe.empty:
            self.universe = pd.DataFrame()
            return

        self.universe = self.universe.reset_index(drop=True).copy()
        self.universe["ticker"] = self._safe_series(self.universe.get("ticker", pd.Series(dtype=str)))
        self.universe["shortTicker"] = self._safe_series(self.universe.get("shortTicker", pd.Series(dtype=str)))
        self.universe["longName"] = self._safe_series(self.universe.get("longName", pd.Series(dtype=str)))
        self.universe["shortName"] = self._safe_series(self.universe.get("shortName", pd.Series(dtype=str)))
        self.universe["avgvolume3m"] = pd.to_numeric(self.universe.get("avgvolume3m"), errors="coerce").fillna(0.0)
        self.universe["tickerKey"] = self.universe["ticker"].map(self._normalize_symbol_token)
        self.universe["shortTickerKey"] = self.universe["shortTicker"].map(self._normalize_symbol_token)
        self.universe["normalizedLongName"] = self.universe["longName"].map(self._normalize_entity_label)
        self.universe["normalizedShortName"] = self.universe["shortName"].map(self._normalize_entity_label)
        self.universe["canonicalLongName"] = self.universe["longName"].map(self._canonicalize_company_name)
        self.universe["canonicalShortName"] = self.universe["shortName"].map(self._canonicalize_company_name)

    def _build_resolution_indexes(self) -> None:
        self._ticker_to_indices: dict[str, list[int]] = defaultdict(list)
        self._short_ticker_to_indices: dict[str, list[int]] = defaultdict(list)
        self._normalized_name_to_indices: dict[str, list[int]] = defaultdict(list)
        self._canonical_name_to_indices: dict[str, list[int]] = defaultdict(list)
        self._external_alias_to_indices: dict[str, list[int]] = defaultdict(list)
        self._derived_form_to_indices: dict[str, list[int]] = defaultdict(list)

        if self.universe.empty:
            return

        for index, row in self.universe.iterrows():
            ticker_key = row.get("tickerKey")
            short_ticker_key = row.get("shortTickerKey")
            normalized_long = row.get("normalizedLongName")
            normalized_short = row.get("normalizedShortName")
            canonical_long = row.get("canonicalLongName")
            canonical_short = row.get("canonicalShortName")

            if ticker_key:
                self._ticker_to_indices[ticker_key].append(index)
            if short_ticker_key:
                self._short_ticker_to_indices[short_ticker_key].append(index)
            for key in {normalized_long, normalized_short}:
                if key:
                    self._normalized_name_to_indices[key].append(index)
            if canonical_long:
                self._canonical_name_to_indices[canonical_long].append(index)
            for form in self._generate_derived_forms(row):
                self._derived_form_to_indices[form].append(index)

        for alias_record in self.external_alias_records:
            alias_key = self._normalize_entity_label(alias_record.get("alias"))
            if not alias_key:
                continue

            for ticker in alias_record.get("tickers", []):
                ticker_key = self._normalize_symbol_token(ticker)
                for index in self._ticker_to_indices.get(ticker_key, []):
                    self._external_alias_to_indices[alias_key].append(index)

    def _generate_derived_forms(self, row: pd.Series) -> set[str]:
        forms: set[str] = set()
        for field_name in ("canonicalLongName",):
            value = row.get(field_name)
            if not value:
                continue

            tokens = str(value).split()
            if len(tokens) < 2:
                continue

            max_prefix_len = min(len(tokens) - 1, _MAX_DERIVED_FORM_TOKENS)
            for prefix_len in range(1, max_prefix_len + 1):
                form = " ".join(tokens[:prefix_len]).strip()
                if len(form) >= 4:
                    forms.add(form)

        normalized_long = row.get("normalizedLongName")
        normalized_short = row.get("normalizedShortName")
        canonical_long = row.get("canonicalLongName")
        canonical_short = row.get("canonicalShortName")
        for form in {normalized_long, normalized_short, canonical_long, canonical_short}:
            if form:
                forms.discard(form)

        return forms

    def _rows_from_indices(self, indices: list[int]) -> pd.DataFrame:
        if not indices:
            return self.universe.iloc[0:0].copy()

        unique_indices = list(dict.fromkeys(indices))
        return self.universe.iloc[unique_indices].copy()

    def _rows_for_lookup(self, mapping: dict[str, list[int]], key: str) -> pd.DataFrame:
        return self._rows_from_indices(mapping.get(key, []))

    @staticmethod
    def _count_distinct_tickers(rows: pd.DataFrame) -> int:
        if rows.empty or "ticker" not in rows:
            return 0
        return rows["ticker"].astype(str).nunique()

    def _deduplicate_rows(self, rows: pd.DataFrame) -> pd.DataFrame:
        if rows.empty:
            return rows

        deduped = rows.copy()
        deduped["__priority_order"] = range(len(deduped))
        deduped = deduped.drop_duplicates(subset=["ticker"], keep="first")
        deduped = deduped.drop(columns=["__priority_order"])
        return deduped

    @classmethod
    def _find_candidate_token_span(cls, normalized_tokens: list[str], normalized_candidate: str) -> tuple[int | None, int | None]:
        candidate_tokens = normalized_candidate.split()
        if not candidate_tokens:
            return None, None

        max_start = len(normalized_tokens) - len(candidate_tokens)
        for start in range(max_start + 1):
            if normalized_tokens[start:start + len(candidate_tokens)] == candidate_tokens:
                return start, start + len(candidate_tokens)

        return None, None

    @staticmethod
    def _raw_text_entity_tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9.\-]+", str(text or ""))

    @classmethod
    def _looks_like_entity_token_in_text(cls, raw_token: str) -> bool:
        token = str(raw_token or "").strip()
        if not token:
            return False
        if any(ch.isdigit() for ch in token):
            return True
        if token == token.upper() and any(ch.isalpha() for ch in token):
            return True
        first_alpha = next((ch for ch in token if ch.isalpha()), "")
        return bool(first_alpha and first_alpha.isupper())

    def _has_structured_name_match(self, normalized_value: str) -> bool:
        if not normalized_value:
            return False

        return any(
            normalized_value in mapping
            for mapping in (
                self._normalized_name_to_indices,
                self._canonical_name_to_indices,
                self._external_alias_to_indices,
                self._derived_form_to_indices,
            )
        )

    def _extract_structured_entity_candidates(self, text: str) -> list[dict]:
        normalized_text = self._normalize_entity_label(text)
        tokens = normalized_text.split()
        raw_tokens = self._raw_text_entity_tokens(text)
        if not tokens:
            return []

        candidates: list[dict] = []
        seen = set()
        max_ngram = min(_MAX_TEXT_ENTITY_NGRAM, len(tokens))
        for size in range(max_ngram, 0, -1):
            for start in range(0, len(tokens) - size + 1):
                candidate = " ".join(tokens[start:start + size]).strip()
                if not candidate or candidate in seen:
                    continue
                if self._is_legal_suffix_token(candidate):
                    continue
                if size == 1 and len(candidate) <= 1:
                    continue
                if size == 1 and candidate in _LOW_SIGNAL_TEXT_TOKENS:
                    continue
                raw_span_tokens = raw_tokens[start:start + size]
                if raw_span_tokens and not any(self._looks_like_entity_token_in_text(token) for token in raw_span_tokens):
                    continue
                if not self._has_structured_name_match(candidate):
                    continue

                seen.add(candidate)
                candidates.append(
                    {
                        "value": candidate,
                        "normalized": candidate,
                        "source": "structured_span",
                        "start": start,
                        "end": start + size,
                    }
                )

        return candidates

    def _build_candidate_record(
        self,
        text: str,
        candidate: object,
        *,
        source: str,
    ) -> dict | None:
        value = str(candidate or "").strip()
        normalized = self._normalize_entity_label(value)
        if not value or not normalized:
            return None
        if self._is_french_elision_fragment(text, value):
            return None

        normalized_tokens = self._normalize_entity_label(text).split()
        start, end = self._find_candidate_token_span(normalized_tokens, normalized)
        return {
            "value": value,
            "normalized": normalized,
            "source": source,
            "start": start,
            "end": end,
        }

    def _structured_preview_resolution(self, candidate: dict) -> dict | None:
        if candidate["source"] == "explicit_ticker":
            return self._resolve_exact_ticker(candidate["value"])

        structured_name = self._resolve_structured_name(candidate["value"])
        if structured_name is not None:
            return structured_name

        if candidate["source"] != "structured_span":
            return self._resolve_exact_ticker(candidate["value"])

        return None

    @staticmethod
    def _candidate_source_rank(source: str) -> int:
        ranks = {
            "explicit_ticker": 0,
            "llm": 1,
            "structured_span": 2,
        }
        return ranks.get(source, 9)

    def _consolidate_candidate_records(self, text: str, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []

        unique_candidates: list[dict] = []
        by_normalized: dict[str, dict] = {}
        for candidate in candidates:
            current = by_normalized.get(candidate["normalized"])
            if current is None:
                by_normalized[candidate["normalized"]] = candidate
                continue

            current_rank = self._candidate_source_rank(current["source"])
            candidate_rank = self._candidate_source_rank(candidate["source"])
            if candidate_rank < current_rank:
                by_normalized[candidate["normalized"]] = candidate
                continue
            if candidate_rank == current_rank and len(candidate["normalized"]) > len(current["normalized"]):
                by_normalized[candidate["normalized"]] = candidate

        unique_candidates = list(by_normalized.values())
        for candidate in unique_candidates:
            candidate["preview_resolution"] = self._structured_preview_resolution(candidate)

        kept: list[dict] = []
        for candidate in sorted(
            unique_candidates,
            key=lambda item: (
                item["start"] if item["start"] is not None else 10_000,
                -(item["end"] - item["start"]) if item["start"] is not None and item["end"] is not None else 0,
                self._candidate_source_rank(item["source"]),
            ),
        ):
            dominated = False
            for other in unique_candidates:
                if other is candidate:
                    continue
                if other["start"] is None or candidate["start"] is None:
                    continue
                if other["start"] > candidate["start"] or other["end"] < candidate["end"]:
                    continue
                if other["normalized"] == candidate["normalized"]:
                    continue
                if len(other["normalized"]) <= len(candidate["normalized"]):
                    continue

                same_ticker = (
                    candidate.get("preview_resolution") is not None
                    and other.get("preview_resolution") is not None
                    and candidate["preview_resolution"].get("selected_ticker") == other["preview_resolution"].get("selected_ticker")
                )
                short_name_fragment = (
                    len(candidate["normalized"].split()) == 1
                    and len(candidate["normalized"]) <= 4
                    and candidate["source"] != "explicit_ticker"
                )
                if same_ticker or short_name_fragment:
                    dominated = True
                    break

            if not dominated:
                kept.append(candidate)

        kept.sort(
            key=lambda item: (
                self._candidate_source_rank(item["source"]),
                item["start"] if item["start"] is not None else 10_000,
                -(item["end"] - item["start"]) if item["start"] is not None and item["end"] is not None else -len(item["normalized"]),
            )
        )
        return kept

    def _compute_structured_row_score(self, query: str, row: pd.Series) -> int:
        normalized_query = self._normalize_entity_label(query)
        symbol_query = self._normalize_symbol_token(query)
        score = 0

        if symbol_query and row.get("tickerKey") == symbol_query:
            score += 100
        if symbol_query and row.get("shortTickerKey") == symbol_query:
            score += 90
        if normalized_query in self._external_alias_to_indices and row.name in self._external_alias_to_indices[normalized_query]:
            score += 80
        if normalized_query and row.get("canonicalLongName") == normalized_query:
            score += 70
        if normalized_query and (
            row.get("normalizedLongName") == normalized_query
            or row.get("normalizedShortName") == normalized_query
        ):
            score += 60
        if normalized_query in self._derived_form_to_indices and row.name in self._derived_form_to_indices[normalized_query]:
            score += 20

        return score

    def _sort_structured_rows(self, query: str, rows: pd.DataFrame) -> pd.DataFrame:
        if rows.empty:
            return rows

        ranked = rows.copy()
        ranked["__match_score"] = ranked.apply(lambda row: self._compute_structured_row_score(query, row), axis=1)
        ranked = ranked.sort_values(by=["__match_score", "avgvolume3m", "ticker"], ascending=[False, False, True])
        ranked = ranked.drop(columns=["__match_score"])
        return ranked

    def _build_resolution_result(
        self,
        query: str,
        rows: pd.DataFrame,
        *,
        source: str,
        multiple_matches: bool,
        used_volume_fallback: bool,
        entity_confidence: float,
    ) -> dict | None:
        if rows.empty:
            return None

        ranked_rows = self._deduplicate_rows(self._sort_structured_rows(query, rows))
        selected_row = ranked_rows.iloc[0]
        return {
            "query": query,
            "selected_company": selected_row.get("longName"),
            "selected_ticker": selected_row.get("ticker"),
            "multiple_matches": multiple_matches,
            "used_volume_fallback": used_volume_fallback,
            "entity_confidence": entity_confidence,
            "top_score": entity_confidence,
            "score_gap": 1.0 if not multiple_matches else 0.0,
            "candidates": self._serialize_candidates(ranked_rows.head(_SEMANTIC_TOP_K)),
            "resolution_source": source,
        }

    def _resolve_exact_ticker(self, query: str) -> dict | None:
        if not self._is_explicit_symbol_form(query):
            return None

        symbol_key = self._normalize_symbol_token(query)
        ticker_rows = self._rows_for_lookup(self._ticker_to_indices, symbol_key)
        if len(ticker_rows) == 1:
            return self._build_resolution_result(
                query,
                ticker_rows,
                source="exact_ticker",
                multiple_matches=False,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_DIRECT_CONFIDENCE,
            )
        if len(ticker_rows) > 1:
            return self._build_resolution_result(
                query,
                ticker_rows,
                source="ambiguous_exact_ticker",
                multiple_matches=True,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
            )

        short_ticker_rows = self._rows_for_lookup(self._short_ticker_to_indices, symbol_key)
        if len(short_ticker_rows) == 1:
            return self._build_resolution_result(
                query,
                short_ticker_rows,
                source="exact_short_ticker",
                multiple_matches=False,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_DIRECT_CONFIDENCE,
            )
        if len(short_ticker_rows) > 1:
            return self._build_resolution_result(
                query,
                short_ticker_rows,
                source="ambiguous_exact_short_ticker",
                multiple_matches=True,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
            )

        return None

    def _build_name_family_rows(
        self,
        normalized_query: str,
        *,
        include_exact_name: bool = True,
        include_canonical: bool = True,
        include_alias: bool = False,
        include_derived: bool = True,
    ) -> pd.DataFrame:
        family_parts = []
        if include_exact_name:
            family_parts.append(self._rows_for_lookup(self._normalized_name_to_indices, normalized_query))
        if include_canonical:
            family_parts.append(self._rows_for_lookup(self._canonical_name_to_indices, normalized_query))
        if include_alias:
            family_parts.append(self._rows_for_lookup(self._external_alias_to_indices, normalized_query))
        if include_derived:
            family_parts.append(self._rows_for_lookup(self._derived_form_to_indices, normalized_query))

        non_empty_parts = [part for part in family_parts if not part.empty]
        if not non_empty_parts:
            return self.universe.iloc[0:0].copy()

        combined = pd.concat(non_empty_parts, ignore_index=False)
        return self._deduplicate_rows(combined)

    def _resolve_structured_name(self, query: str) -> dict | None:
        normalized_query = self._normalize_entity_label(query)
        if not normalized_query:
            return None

        exact_name_rows = self._rows_for_lookup(self._normalized_name_to_indices, normalized_query)
        if len(exact_name_rows) == 1:
            family_rows = self._build_name_family_rows(
                normalized_query,
                include_derived=" " not in normalized_query,
            )
            if self._count_distinct_tickers(family_rows) > 1:
                return self._build_resolution_result(
                    query,
                    family_rows,
                    source="ambiguous_exact_name_family",
                    multiple_matches=True,
                    used_volume_fallback=False,
                    entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
                )
            return self._build_resolution_result(
                query,
                exact_name_rows,
                source="exact_name",
                multiple_matches=False,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_DIRECT_CONFIDENCE,
            )
        if len(exact_name_rows) > 1:
            return self._build_resolution_result(
                query,
                exact_name_rows,
                source="ambiguous_exact_name",
                multiple_matches=True,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
            )

        canonical_rows = self._rows_for_lookup(self._canonical_name_to_indices, normalized_query)
        if len(canonical_rows) == 1:
            family_rows = self._build_name_family_rows(
                normalized_query,
                include_derived=False,
            )
            if self._count_distinct_tickers(family_rows) > 1:
                return self._build_resolution_result(
                    query,
                    family_rows,
                    source="ambiguous_canonical_name_family",
                    multiple_matches=True,
                    used_volume_fallback=False,
                    entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
                )
            return self._build_resolution_result(
                query,
                canonical_rows,
                source="canonical_name_exact",
                multiple_matches=False,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_DIRECT_CONFIDENCE,
            )
        if len(canonical_rows) > 1:
            return self._build_resolution_result(
                query,
                canonical_rows,
                source="ambiguous_canonical_name_exact",
                multiple_matches=True,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
            )

        alias_rows = self._rows_for_lookup(self._external_alias_to_indices, normalized_query)
        if len(alias_rows) == 1:
            return self._build_resolution_result(
                query,
                alias_rows,
                source="external_alias_exact",
                multiple_matches=False,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_DIRECT_CONFIDENCE,
            )
        if len(alias_rows) > 1:
            return self._build_resolution_result(
                query,
                alias_rows,
                source="ambiguous_external_alias_exact",
                multiple_matches=True,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
            )

        derived_form_rows = self._rows_for_lookup(self._derived_form_to_indices, normalized_query)
        if len(derived_form_rows) == 1:
            family_rows = self._build_name_family_rows(
                normalized_query,
                include_exact_name=False,
                include_canonical=True,
                include_derived=True,
            )
            if self._count_distinct_tickers(family_rows) > 1:
                return self._build_resolution_result(
                    query,
                    family_rows,
                    source="ambiguous_derived_form_family",
                    multiple_matches=True,
                    used_volume_fallback=False,
                    entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
                )
            return self._build_resolution_result(
                query,
                derived_form_rows,
                source="derived_form_exact",
                multiple_matches=False,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_DIRECT_CONFIDENCE,
            )
        if len(derived_form_rows) > 1:
            return self._build_resolution_result(
                query,
                derived_form_rows,
                source="ambiguous_derived_form_exact",
                multiple_matches=True,
                used_volume_fallback=False,
                entity_confidence=_STRUCTURED_AMBIGUOUS_CONFIDENCE,
            )

        return None

    def _resolve_semantic(self, query: str) -> dict | None:
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, self.embeddings)[0]
        best_score_val, best_idx = torch.topk(cosine_scores, k=_SEMANTIC_TOP_K)
        dbg("BEST_SCORES : ", best_score_val.tolist(), "BEST_IDX : ", best_idx.tolist())
        top_scores = best_score_val.tolist()
        score_gap = top_scores[0] - top_scores[1]
        top_score = top_scores[0]
        multiple_matches = score_gap < _THRESHOLD_ECART
        top_candidate_rows = self.universe.iloc[best_idx.tolist()].copy()
        semantic_top_row = self.universe.iloc[best_idx.tolist()[0]]
        if multiple_matches and self._has_dominant_top_candidate(
            top_score=top_score,
            score_gap=score_gap,
            semantic_top_row=semantic_top_row,
            top_candidate_rows=top_candidate_rows,
        ):
            # Avoid over-triggering clarifications when the semantic winner is
            # already clearly dominant and much more liquid than alternatives.
            multiple_matches = False
        #si le premier se détache on le garde, sinon on compare les volumes de trading sur 3 mois
        if not multiple_matches:
            selected_row = semantic_top_row
            used_volume_fallback = False
        else:
            if self._should_keep_semantic_top(query, semantic_top_row, top_candidate_rows):
                selected_row = semantic_top_row
                multiple_matches = False
                used_volume_fallback = False
            else:
                res = top_candidate_rows.sort_values(by=["avgvolume3m"], ascending=[False])
                dbg("CANDIDATS : ", res[["longName", "avgvolume3m"]])
                selected_row = res.iloc[0]
                used_volume_fallback = selected_row["ticker"] != semantic_top_row["ticker"]

        entity_confidence = self._compute_entity_confidence(
            top_score=top_score,
            score_gap=score_gap,
            multiple_matches=multiple_matches,
            used_volume_fallback=used_volume_fallback,
        )
        dbg("ENTITY CONFIDENCE:", {
            "top_score": top_score,
            "gap": score_gap,
            "confidence": entity_confidence,
            "multiple_matches": multiple_matches,
            "fallback": used_volume_fallback
        })

        return {
            "query": query,
            "selected_company": selected_row["longName"],
            "selected_ticker": selected_row["ticker"],
            "multiple_matches": multiple_matches,
            "used_volume_fallback": used_volume_fallback,
            "entity_confidence": entity_confidence,
            "top_score": top_score,
            "score_gap": score_gap,
            "candidates": self._serialize_candidates(top_candidate_rows),
            "resolution_source": "semantic",
        }

    def _resolve_candidate(self, query: str) -> dict | None:
        if self._is_explicit_symbol_form(query):
            structured_symbol = self._resolve_exact_ticker(query)
            if structured_symbol is not None:
                return structured_symbol

        structured_name = self._resolve_structured_name(query)
        if structured_name is not None:
            return structured_name

        if not self._is_explicit_symbol_form(query):
            structured_symbol = self._resolve_exact_ticker(query)
            if structured_symbol is not None:
                return structured_symbol

        return self._resolve_semantic(query)

    def _extract_explicit_ticker_candidates(self, text: str) -> list[str]:
        candidates: list[str] = []
        for raw_token in _TEXT_TOKEN_PATTERN.findall(text or ""):
            token = raw_token.strip("()[]{}<>,;:!?\"'")
            if not self._is_ticker_like(token):
                continue

            has_digit = any(ch.isdigit() for ch in raw_token)
            has_separator = any(ch in ".-" for ch in raw_token)
            has_alpha = any(ch.isalpha() for ch in raw_token)
            is_explicit_symbol_form = (has_alpha and raw_token == raw_token.upper()) or has_digit or has_separator
            if not is_explicit_symbol_form:
                continue

            if self._is_legal_suffix_token(token) and not has_digit and not has_separator:
                continue
            if self._is_french_elision_fragment(text, token):
                continue

            token_key = self._normalize_symbol_token(token)
            if token_key in self._ticker_to_indices or token_key in self._short_ticker_to_indices:
                candidates.append(token)

        return list(dict.fromkeys(candidates))

    @classmethod
    def _query_matches_row_name(cls, query: str, row: pd.Series) -> bool:
        normalized_query = cls._normalize_entity_label(query)
        normalized_name = cls._normalize_entity_label(row.get("longName"))

        if not normalized_query or not normalized_name:
            return False

        return normalized_query in normalized_name

    @classmethod
    def _should_keep_semantic_top(
        cls,
        query: str,
        semantic_top_row: pd.Series,
        top_candidate_rows: pd.DataFrame,
    ) -> bool:
        if not cls._query_matches_row_name(query, semantic_top_row):
            return False

        runner_up_rows = top_candidate_rows.iloc[1:]
        matching_runner_ups = [
            row for _, row in runner_up_rows.iterrows()
            if cls._query_matches_row_name(query, row)
        ]
        return len(matching_runner_ups) == 0

    def load_embedding(self):
        script_dir = Path(__file__).parent
        path = script_dir / "company_embeddings.pt"

        if not path.exists():
            raise Exception("false path for embedding file")

        # Détection propre du device
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

        with path.open("rb") as f:
            obj = torch.load(f, map_location=device)

        if isinstance(obj, torch.Tensor):
            obj = obj.to(device)

        return obj

    def load_tickers(self):
        script_dir = Path(__file__).parent
        path = script_dir / "company_enriched.pickle"

        if not path.exists():
            return pd.DataFrame()

        with path.open("rb") as f:
            df = pickle.load(f)
            df = df.reset_index(drop=True)
            return df

    def load_external_aliases(self) -> list[dict]:
        script_dir = Path(__file__).parent
        path = script_dir / "company_aliases.json"

        if not path.exists():
            return []

        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        raw_aliases = payload.get("aliases", payload) if isinstance(payload, dict) else payload
        aliases: list[dict] = []
        for entry in raw_aliases:
            if not isinstance(entry, dict):
                continue

            alias = entry.get("alias")
            tickers = entry.get("tickers", [])
            if isinstance(tickers, str):
                tickers = [tickers]

            normalized_tickers = []
            for ticker in tickers:
                ticker_key = self._normalize_symbol_token(ticker)
                if ticker_key:
                    normalized_tickers.append(ticker_key)

            if not alias or not normalized_tickers:
                continue

            aliases.append(
                {
                    "alias": alias,
                    "tickers": normalized_tickers,
                    "source": entry.get("source", "external_alias_table"),
                    "notes": entry.get("notes"),
                }
            )

        return aliases

    @staticmethod
    def _serialize_candidates(rows: pd.DataFrame) -> list[dict]:
        return [
            {
                "longName": row.get("longName"),
                "ticker": row.get("ticker"),
                "avgvolume3m": row.get("avgvolume3m"),
            }
            for _, row in rows.iterrows()
        ]


    def extract_symbols(self,text: str):
        self.last_symbol_resolution = []

        extractor = general_llm.with_structured_output(CompanyExtraction)
        prompt = f"Extrais uniquement les noms d'entreprises ou les tickers boursiers de ce message utilisateur : {text}"
        result = extractor.invoke(prompt)
        if result:
            llm_candidates = result.companies
        else:
            llm_candidates = []

        candidate_records: list[dict] = []
        for candidate in self._extract_explicit_ticker_candidates(text):
            record = self._build_candidate_record(text, candidate, source="explicit_ticker")
            if record is not None:
                candidate_records.append(record)

        for candidate in llm_candidates:
            record = self._build_candidate_record(text, candidate, source="llm")
            if record is not None:
                candidate_records.append(record)

        structured_fallback_candidates = self._extract_structured_entity_candidates(text)
        for record in structured_fallback_candidates:
            candidate_records.append(record)

        consolidated_candidates = self._consolidate_candidate_records(text, candidate_records)
        candidates = [candidate["value"] for candidate in consolidated_candidates]

        dbg("candidates found by LLM", candidates)
        candidates_selected = []
        tickers = []
        seen_tickers = set()
        for candidate in candidates :
            resolution = self._resolve_candidate(candidate)
            if resolution is None:
                continue
            selected_ticker = resolution["selected_ticker"]
            if selected_ticker in seen_tickers:
                continue

            candidates_selected.append(resolution["selected_company"])
            tickers.append(selected_ticker)
            self.last_symbol_resolution.append(resolution)
            seen_tickers.add(selected_ticker)

        return tickers,candidates_selected

    def extract_period(self, text: str) -> str:
        extractor = general_llm.with_structured_output(PeriodExtraction)
        prompt = f"Extrais la période que tu juges la plus proche parfois celles possibles dans ce message utilisateur : {text}"
        result = extractor.invoke(prompt)
        period = result.period
        if period:
            return _PERIOD_DICT[period]
        else:
            return ""
