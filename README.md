# Olist ETL Data Pipeline

Olist ETL – Data Engineering Project
Author: Lydia Meftah
Program: MSc Data Engineer – Applied AI (DSTI)

--------------------------------------------------

PROJECT DESCRIPTION

This project implements a data engineering ETL pipeline based on the Olist
Brazilian e-commerce dataset.

The objective is to process raw transactional data and transform it into a
clean and structured format suitable for analytics.

The project focuses on core data engineering principles:
- Extracting raw data
- Cleaning and transforming datasets
- Ensuring data quality
- Preparing data for analytical usage

--------------------------------------------------

PROJECT STRUCTURE

The repository is organized as follows:

- src/
  Contains the Python scripts implementing the ETL logic.

- sql/
  Contains SQL queries used for analytical purposes.

- tests/
  Contains automated tests related to data quality and validation.

- requirements.txt
  Lists the Python dependencies required to run the project.

- Makefile
  Provides standardized commands to execute the pipeline.

- README.txt
  Project documentation.

--------------------------------------------------

ETL LOGIC OVERVIEW

1. Extract
Raw data is loaded from source files without applying business logic.

2. Transform
The transformation step applies cleaning and normalization rules to ensure
data consistency and usability.

3. Load
The processed data is prepared for analytical consumption.

--------------------------------------------------

DATA QUALITY

Basic data quality checks are implemented through automated tests to ensure:
- Dataset integrity
- Consistency of values
- Presence of required fields

--------------------------------------------------

EXECUTION

Dependencies must be installed before running the project.

The ETL pipeline can be executed using the Makefile or directly via Python.

--------------------------------------------------

ACADEMIC CONTEXT

This project was developed as part of the MSc Data Engineer – Applied AI
program at DSTI.

It is intended as a standalone academic deliverable demonstrating data
engineering fundamentals.
