.PHONY: help install test verify benchmark-etl benchmark-latency cli docker-build docker-up docker-down clean

help:
	@echo "Datheon Forward Deployed Engineering (FDE) Platform"
	@echo "====================================================="
	@echo "make install           - Install project dependencies"
	@echo "make test              - Run all 25 unit, integration, and security tests"
	@echo "make verify            - Run comprehensive 3-pass audit suite"
	@echo "make benchmark-etl     - Run batch vector ingestion throughput benchmark"
	@echo "make benchmark-latency - Run microservice latency benchmark"
	@echo "make cli               - Launch interactive CLI demonstrator"
	@echo "make docker-build      - Build hardened VPC Docker container"
	@echo "make docker-up         - Start platform via Docker Compose"
	@echo "make docker-down       - Stop Docker Compose services"
	@echo "make clean             - Remove cache artifacts and temporary logs"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

verify:
	python scripts/verify_all.py

benchmark-etl:
	python scripts/run_etl_benchmark.py

benchmark-latency:
	python scripts/run_latency_benchmark.py

cli:
	python scripts/interactive_cli.py

docker-build:
	docker build -t datheon-fde-service:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf *.log
