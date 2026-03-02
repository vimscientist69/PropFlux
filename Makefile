.PHONY: help build run run-property24 run-privateproperty run-test clean logs shell

# Default target
help:
	@echo "🏠 PropFlux - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make build              - Build the Docker image"
	@echo "  make run                - Run scraper (Property24, default)"
	@echo "  make run-property24     - Run Property24 scraper"
	@echo "  make run-privateproperty - Run Private Property scraper"
	@echo "  make run-test           - Run scraper with max 2 pages (testing)"
	@echo "  make logs               - View recent logs"
	@echo "  make shell              - Open shell in container"
	@echo "  make clean              - Remove Docker image"
	@echo ""

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker build -t propflux:latest .

# Run default scraper (Property24)
run: build
	@echo "🚀 Running Property24 scraper..."
	docker run --rm \
		-v "$$(pwd)/output:/app/output" \
		-v "$$(pwd)/logs:/app/logs" \
		propflux:latest --site property24 --verbose

# Run Property24 scraper
run-property24: build
	@echo "🚀 Running Property24 scraper..."
	docker run --rm \
		-v "$$(pwd)/output:/app/output" \
		-v "$$(pwd)/logs:/app/logs" \
		propflux:latest --site property24 --verbose

# Run Private Property scraper
run-privateproperty: build
	@echo "🚀 Running Private Property scraper..."
	docker run --rm \
		-v "$$(pwd)/output:/app/output" \
		-v "$$(pwd)/logs:/app/logs" \
		propflux:latest --site privateproperty --verbose

# Run test scrape (limited pages)
run-test: build
	@echo "🧪 Running test scrape (max 2 pages)..."
	docker run --rm \
		-v "$$(pwd)/output:/app/output" \
		-v "$$(pwd)/logs:/app/logs" \
		propflux:latest --site property24 --max-pages 2 --verbose

# View logs
logs:
	@echo "📋 Recent logs:"
	@tail -n 50 logs/scraper_*.log 2>/dev/null || echo "No logs found. Run 'make run' first."

# Open shell in container
shell: build
	@echo "🐚 Opening shell in container..."
	docker run --rm -it \
		-v "$$(pwd)/output:/app/output" \
		-v "$$(pwd)/logs:/app/logs" \
		--entrypoint /bin/bash \
		propflux:latest

# Clean up Docker image
clean:
	@echo "🧹 Removing Docker image..."
	docker rmi propflux:latest 2>/dev/null || echo "Image not found."
