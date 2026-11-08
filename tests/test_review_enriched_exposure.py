import copy
import hashlib
import json

import pandas as pd
import pytest

from test_enrich_missing_exposure import fixture, response, CATALOG, QUOTE
from src.risk.enrich_missing_exposure import prepare_cases, apply_assessments
from src.risk.review_enriched_exposure import apply_quality_review, reconcile_checkpoint


def inputs():
    old, chunks = fixture()
    new, audit = apply_assessments(old, prepare_cases(old, chunks, CATALOG), response(), CATALOG)
    policy = {"policy": "TEST", "decisions": [{"item_id": "I1", "component": "severity",
        "review_reason": "Evidencia insuficiente para el impacto propuesto", "review_code": "QUARANTINED",
        "model_quote": QUOTE, "model_value": 4}]}
    snapshot = {"catalog_sha256": hashlib.sha256(json.dumps(CATALOG,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
    return old, new, audit, policy, CATALOG, snapshot


def test_quarantine_restores_missing_without_creating_an_alternative_level():
    args = inputs(); original = args[1].copy(deep=True)
    result, audit, snapshot = apply_quality_review(*args)
    assert pd.isna(result.iloc[0].severity) and pd.isna(result.iloc[0].pird)
    assert result.iloc[0].probability == 4
    assert audit.iloc[0].model_gate_accepted and not audit.iloc[0].accepted
    assert snapshot["method"]["expert_validation_of_new_values"] is False
    assert snapshot["projects"][0]["profile"]["signals_total"] == 1
    pd.testing.assert_frame_equal(args[1], original)


@pytest.mark.parametrize("mutation", ["duplicate", "quote", "existing", "value"])
def test_quarantine_must_match_unique_new_proposal(mutation):
    args=list(inputs());decision=args[3]["decisions"][0]
    if mutation=="duplicate":args[3]["decisions"].append(copy.deepcopy(decision))
    if mutation=="quote":decision["model_quote"]="Otra cita"
    if mutation=="existing":args[0].loc[0,"severity"]=3
    if mutation=="value":decision["model_value"]=5
    with pytest.raises(ValueError):apply_quality_review(*args)


def test_checkpoint_reconciliation_has_no_model_client_and_requires_all_ids(tmp_path):
    old,chunks=fixture();path=tmp_path/'checkpoint.jsonl'
    path.write_text(json.dumps({'ids':['I1'],'raw_response':json.dumps({'assessments':response()})})+'\n')
    new,audit=reconcile_checkpoint(old,chunks,CATALOG,path)
    assert new.iloc[0].severity==4 and audit.accepted.sum()==1
    path.write_text('')
    with pytest.raises(ValueError,match='incompleto'):reconcile_checkpoint(old,chunks,CATALOG,path)
