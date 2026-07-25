from pathlib import Path

from crypto_platform.production.orchestrator import PipelineOptions, ProductionOrchestrator
from crypto_platform.production.registry import ProductionStage


def test_selected_module_range_excludes_retired_module(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    options = PipelineOptions(
        repository_root=root,
        output_root=tmp_path,
        stages=(ProductionStage.CORE_ANALYTICS,),
        start_module=2,
        end_module=5,
        export_universal=False,
    )
    selected = [spec.number for spec in ProductionOrchestrator(options)._selected_modules()]
    assert selected == [2, 3, 5]


def test_run_id_is_stable_for_orchestrator_instance(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    orchestrator = ProductionOrchestrator(
        PipelineOptions(
            repository_root=root,
            output_root=tmp_path,
            export_universal=False,
        )
    )
    assert orchestrator.run_id
    assert orchestrator.run_directory.name == orchestrator.run_id
