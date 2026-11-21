.PHONY: install run orchestrate dashboard test clean

# Install dependencies.
install:
	pip install -r requirements.txt

# Run the ETL pipeline directly (Extract -> Transform -> Load).
run:
	python -m etl.pipeline

# Run the pipeline through the orchestration DAG (with a data-quality gate).
orchestrate:
	python -m orchestration.flow

# Build the KPI dashboard (HTML) from the warehouse.
dashboard:
	python -m dashboard.build_dashboard

# Run the data-quality test suite.
test:
	pytest -v

# Remove generated outputs.
clean:
	rm -rf data/processed dashboard/dashboard.html __pycache__ **/__pycache__ .pytest_cache
