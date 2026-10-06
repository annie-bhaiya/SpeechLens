.PHONY: setup models demo-data dataset-build dataset-validate test evaluate report demo-video release-check serve release
setup:
	uv sync --frozen --extra dev
	npm --prefix frontend ci
	npm --prefix frontend run build
models:
	uv run --frozen python -m scripts.download_models
demo-data:
	uv run --frozen python -m scripts.collect_sources
	uv run --frozen python -m scripts.build_dataset --demo
dataset-build:
	uv run --frozen python -m scripts.collect_sources
	uv run --frozen python -m scripts.build_dataset
dataset-validate:
	uv run --frozen python -m scripts.validate_dataset
test:
	uv run --frozen pytest tests/unit tests/integration -q
	npm --prefix frontend test
evaluate:
	uv run --frozen python -m scripts.run_evaluation
	uv run --frozen python -m scripts.stress_tests
report:
	uv run --frozen python -m scripts.finalize_evidence
	uv run --frozen python -m scripts.make_report
demo-video:
	uv run --frozen python -m scripts.make_video
release:
	uv run --frozen python -m scripts.make_release
release-check:
	uv run --frozen python -m scripts.release_check
serve:
	uv run --frozen python -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000
