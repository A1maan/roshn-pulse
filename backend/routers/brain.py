from fastapi import APIRouter, HTTPException
from typing import Dict, List, Tuple
from pathlib import Path
import json
import pickle
import numpy as np

try:
    import joblib  # type: ignore
except ImportError:  # pragma: no cover
    joblib = None

from core.config import settings
from core.schemas import (
    BrainPredictIn, BrainPredictOut, RiskContributor,
    BrainWhatIfIn, BrainWhatIfOut
)

router = APIRouter()

# === Load model & schema lazily ===
_model = None
_schema = None  # {"features": [{"name": "...", "type": "float"}], ...}

def _lazy_load():
    global _model, _schema
    if _model is None:
        model_path: Path = settings.brain_model_path
        if not model_path.exists():
            raise RuntimeError(f"Brain model not found at {model_path}")
        try:
            with open(model_path, "rb") as f:
                _model = pickle.load(f)
        except Exception as pickle_error:
            if not joblib:
                raise RuntimeError(
                    f"Failed to load model with pickle ({pickle_error}) and joblib unavailable."
                ) from pickle_error
            try:
                loaded = joblib.load(model_path)
            except Exception as joblib_error:  # pragma: no cover - rare
                raise RuntimeError(
                    f"Failed to load model from {model_path}: {joblib_error}"
                ) from joblib_error
            else:
                # Some exports wrap the estimator inside a dict (e.g. {"calibrated_model": ...})
                if isinstance(loaded, dict):
                    for key in ("calibrated_model", "model", "estimator"):
                        if key in loaded:
                            _model = loaded[key]
                            break
                else:
                    _model = loaded

        if _model is None:
            raise RuntimeError(
                f"Brain model artifact at {model_path} could not be interpreted. "
                "Ensure the export contains an estimator under 'calibrated_model' or 'model'."
            )
    if _schema is None:
        schema_path: Path = settings.brain_schema_path
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                _schema = json.load(f)
        else:
            # Fallback: infer from input at runtime
            _schema = None


def _vectorize(features: Dict[str, float]) -> np.ndarray:
    """
    Converts feature dict into a fixed ordering vector based on preprocess_schema.json.
    If schema is missing, we sort keys for deterministic order.
    """
    if _schema and "features" in _schema:
        names: List[str] = [f["name"] for f in _schema["features"]]
    else:
        names = sorted(features.keys())

    x = np.array([float(features.get(n, 0.0)) for n in names], dtype=float).reshape(1, -1)
    return x


def _band(score: float) -> str:
    if score < 0.34:
        return "Low"
    if score < 0.67:
        return "Medium"
    return "High"


def _unwrap_for_contributors(model) -> Tuple[object, str]:
    """
    Return an estimator that exposes coefficients/importances and a label describing the source.
    """
    if hasattr(model, "coef_") or hasattr(model, "feature_importances_"):
        return model, "model"

    # CalibratedClassifierCV keeps per-fold calibrators with .estimator
    calibrators = getattr(model, "calibrated_classifiers_", None)
    if calibrators:
        for calibrator in calibrators:
            est = getattr(calibrator, "estimator", None)
            if est is not None and (hasattr(est, "coef_") or hasattr(est, "feature_importances_")):
                return est, "calibrator"

    base = getattr(model, "base_estimator", None)
    if base is not None and (hasattr(base, "coef_") or hasattr(base, "feature_importances_")):
        return base, "base_estimator"

    return model, "model"


def _top_contributors_from_model(x: np.ndarray, features_order: List[str]) -> List[RiskContributor]:
    """
    Heuristic: if model exposes feature_importances_ or coef_, use that.
    Otherwise, return empty list.
    """
    contribs: List[RiskContributor] = []
    try:
        estimator, _ = _unwrap_for_contributors(_model)
        if hasattr(estimator, "feature_importances_"):
            importances = np.asarray(estimator.feature_importances_)
            idx = np.argsort(-np.abs(importances))[:5]
            for i in idx:
                contribs.append(RiskContributor(feature=features_order[i], impact=float(importances[i])))
        elif hasattr(estimator, "coef_"):
            coef = np.asarray(getattr(estimator, "coef_"))
            if coef.ndim > 1:
                coef = coef[0]
            idx = np.argsort(-np.abs(coef))[:5]
            for i in idx:
                contribs.append(RiskContributor(feature=features_order[i], impact=float(coef[i])))
    except Exception:
        pass
    return contribs


@router.post("/predict-delay", response_model=BrainPredictOut)
def predict_delay(payload: BrainPredictIn):
    _lazy_load()

    # Prepare vector and order
    if _schema and "features" in _schema:
        order = [f["name"] for f in _schema["features"]]
    else:
        order = sorted(payload.features.keys())

    x = _vectorize(payload.features)

    # Predict probability if available; else decision_function → sigmoid
    try:
        if hasattr(_model, "predict_proba"):
            p = float(_model.predict_proba(x)[0, 1])
        else:
            # decision function to probability
            from math import exp
            d = float(_model.decision_function(x)[0])
            p = 1.0 / (1.0 + np.exp(-d))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Model inference failed: {e}")

    contributors = _top_contributors_from_model(x, order)
    return BrainPredictOut(
        risk_score=round(p, 4),
        risk_band=_band(p),
        top_contributors=contributors,
    )


@router.post("/what-if", response_model=BrainWhatIfOut)
def what_if(payload: BrainWhatIfIn):
    _lazy_load()

    base = predict_delay(BrainPredictIn(features=payload.features))

    # Apply deltas
    scenario_features = dict(payload.features)
    for k, dv in payload.deltas.items():
        try:
            scenario_features[k] = float(scenario_features.get(k, 0.0)) + float(dv)
        except Exception:
            scenario_features[k] = scenario_features.get(k, 0.0)

    scen = predict_delay(BrainPredictIn(features=scenario_features))
    return BrainWhatIfOut(baseline=base, scenario=scen)
