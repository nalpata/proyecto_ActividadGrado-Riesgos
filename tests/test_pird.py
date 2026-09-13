from src.risk.pird import PIRDInputs, calculate_pird, normalize, risk_level


def test_normalization_boundaries():
    assert normalize(1)==0
    assert normalize(5)==1


def test_score_requires_all_components():
    result=calculate_pird(PIRDInputs(5,4,None,None,5,4))
    assert result["score_status"]=="PENDIENTE_ENRIQUECIMIENTO"
    assert result["pird"] is None
    assert result["missing_components"]==["recurrence","persistence"]


def test_maximum_and_minimum_scores():
    assert calculate_pird(PIRDInputs(1,1,1,1,1,1))["pird"]==0
    assert calculate_pird(PIRDInputs(5,5,5,5,5,5))["pird"]==100


def test_score_is_monotonic_for_severity():
    low=calculate_pird(PIRDInputs(2,3,3,3,4,4))["pird"]
    high=calculate_pird(PIRDInputs(4,3,3,3,4,4))["pird"]
    assert high>low


def test_initial_risk_levels():
    assert risk_level(0)=="BAJO"
    assert risk_level(25)=="MEDIO"
    assert risk_level(50)=="ALTO"
    assert risk_level(75)=="CRITICO"
