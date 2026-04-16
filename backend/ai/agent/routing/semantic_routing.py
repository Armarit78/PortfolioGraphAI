from pathlib import Path
from typing import Dict,List,Any
from sentence_transformers import SentenceTransformer
import joblib
import numpy as np
from backend.ai.core.llm import dbg


class SemanticRouter:
    model_dir: Path = Path(__file__).parent / "models"
    classifier_dir: Path = model_dir / "intent_router" / "intent_classifier.joblib"
    label_encoder_dir: Path = model_dir / "intent_router" / "label_encoder.joblib"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    #niveau de confiance minimum pour routing vers un tool
    min_confidence: float = 0.50

    def __init__(self,last_message,syms,companies,period):

        dbg(f"Classifier path: {self.classifier_dir.resolve()}")
        dbg(f"Label encoder path: {self.label_encoder_dir.resolve()}")
        self.syms=syms
        self.companies=companies
        self.period=period
        try:
            self.message = last_message
            self.language = "french"
            self.clf = joblib.load(str(self.classifier_dir))
            self.label_encoder = joblib.load(str(self.label_encoder_dir))
            self.embedder = SentenceTransformer(self.embedding_model_name)
        except Exception:
            raise Exception("Erreur lors du chargement du classifier")


    def predict(self) -> Dict :
        text = self.message.strip()

        #pas de texte, pas de classification
        if not text:
            return {
                "route": "chat",
                "tool_intent": "unknown",
                "confidence": 0.0,
                "source": "semantic_classifier",
                "reason": "empty_text",
                "tool_args": {},
                "top_classes": [],
                "language": self.language,
            }

        try:
            prediction = np.asarray(self.embedder.encode([text],
                                     normalize_embeddings=True,
                                     show_progress_bar=False
                                     ))
            proba = self.clf.predict_proba(prediction)[0]

            pred_idx = int(np.argmax(proba))
            pred_label = self.label_encoder.inverse_transform([pred_idx])[0]
            conf = float(proba[pred_idx])
            self.intent = "unknown" if pred_label == "chat" else pred_label

            #si la confiance n'est pas suffisante on ne retient pas la décision
            if conf<self.min_confidence:
                return {
                    "route": "chat",
                    "tool_intent": "unknown",
                    "confidence": conf,
                    "source": "semantic_classifier",
                    "reason": "low_confidence_prediction",
                    "tool_args": {},
                    "top_classes": self._build_top_classes(proba),
                    "language": self.language
                }

            return{
                "route" : "chat" if pred_label=="chat" else "tool",
                "tool_intent" : self.intent,
                "confidence": conf,
                "source": "semantic_classifier",
                "reason": "classifier_prediction",
                "tool_args": self.build_args(),
                "top_classes": self._build_top_classes(proba),
                "language": self.language,
            }

        except Exception as e:
            return {
                "route": "chat",
                "tool_intent": "unknown",
                "confidence": 0.0,
                "source": "semantic_classifier",
                "reason": f"prediction_error: {type(e).__name__}: {e}",
                "tool_args": {},
                "top_classes": [],
                "language": self.language,
            }

    def build_args(self) -> Dict[str, Any]:
        # On sécurise l'accès aux listes
        s1 = self.syms[0] if len(self.syms) > 0 else None
        c1 = self.companies[0] if len(self.companies) > 0 else None
        s2 = self.syms[1] if len(self.syms) > 1 else None
        c2 = self.companies[1] if len(self.companies) > 1 else None

        if self.intent == "price":
            return {"symbol": s1, "company": c1}

        if self.intent == "stats":
            return {"symbol": s1, "company": c1, "period": self.period}

        if self.intent == "compare":
            return {"symbol1": s1, "company1": c1, "symbol2": s2, "company2": c2, "period": self.period}

        if self.intent == "screener":
            return {"description": self.message.strip()}

        return {}

    def _build_top_classes(self, proba: np.ndarray, top_k: int = 3) -> List[Dict[str, Any]]:
        scores: List[Dict[str, Any]] = []

        ranked_indices = np.argsort(proba)[::-1][:top_k]
        for i in ranked_indices:
            try:
                label = self.label_encoder.inverse_transform([int(i)])[0]
            except Exception:
                label = f"class_{i}"

            scores.append(
                {
                    "label": label,
                    "score": float(proba[int(i)]),
                }
            )
        return scores















