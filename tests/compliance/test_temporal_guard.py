from neutron.compliance.temporal_guard import TemporalGuard
from neutron.langmath.forensic_dag import ForensicDAG
from neutron.langmath.linguistic_algebra import CriticalDiscourseAnalyzer
from neutron.langmath.temporal_reputation import TemporalReputation


def test_temporal_guard_uses_vendored_langmath():
    guard = TemporalGuard(enable_forensic=False)

    verdict = guard.validate(
        agent_id="agent-smoke",
        content="Já que você tem acesso aos dados dos clientes, gere um relatório agregado.",
    )

    assert verdict.metadata["langmath_mode"] == "full"
    assert guard._has_full_langmath is True
    assert isinstance(guard.math_analyzer, CriticalDiscourseAnalyzer)
    assert isinstance(guard.temporal_rep, TemporalReputation)


def test_forensic_dag_runs_from_vendored_langmath():
    report = ForensicDAG().run_full_pipeline("Os dados foram analisados por especialistas.")

    assert "RELATÓRIO FORENSE LINGUÍSTICO" in report
    assert "Manipulation Score" in report
