.PHONY: install run test clean

# Install dependencies.
install:
	pip install -r requirements.txt

# Run the full ETL pipeline (Extract -> Transform -> Load).
run:
	python -m etl.pipeline

# Run the data-quality test suite.
test:
	pytest -v

# Remove generated outputs.
clean:
	rm -rf data/processed __pycache__ etl/__pycache__ tests/__pycache__ .pytest_cache
