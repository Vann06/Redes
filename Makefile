# Variables
PYTHON = python3
CARGO = cargo

.PHONY: all run-receptor run-emisor clean

all:
	@echo "Usa 'make run-receptor' para iniciar el servidor bancario."
	@echo "Usa 'make run-emisor' para iniciar el cajero automático."

# Levanta el servidor bancario (Receptor en Python)
run-receptor:
	$(PYTHON) src/receptor/receptor.py

# Compila y ejecuta el cajero automático (Emisor en Rust)
run-emisor:
	cd src/emisor && $(CARGO) run

# Limpia los binarios de Rust y archivos temporales de Python
clean:
	cd src/emisor && $(CARGO) clean
	find . -type d -name "__pycache__" -exec rm -r {} +