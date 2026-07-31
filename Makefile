PYTHON ?= python3
GO ?= go

.PHONY: all
.PHONY: run-receptor run-emisor
.PHONY: test test-go test-receptor test-pruebas
.PHONY: simular simular-rapido graficas
.PHONY: clean

all:
	@echo "Comandos disponibles:"
	@echo "  make run-receptor"
	@echo "  make run-emisor"
	@echo "  make test"
	@echo "  make simular"
	@echo "  make graficas"

run-receptor:
	$(PYTHON) receptor/main.py

run-emisor:
	cd emisor && $(GO) run .

test-go:
	cd emisor && $(GO) test ./...

test-receptor:
	cd receptor && $(PYTHON) -m unittest -v

test-pruebas:
	cd pruebas && $(PYTHON) -m unittest -v

test: test-go test-receptor test-pruebas

simular:
	cd pruebas && $(PYTHON) simulacion.py

simular-rapido:
	cd pruebas && $(PYTHON) simulacion.py 200

graficas:
	cd pruebas && $(PYTHON) graficas.py

clean:
	cd emisor && $(GO) clean
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(ruta, ignore_errors=True) for ruta in pathlib.Path('.').rglob('__pycache__')]"