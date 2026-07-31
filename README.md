# Lab2 - Esquemas de detección y corrección de errores

# Laboratorio 2: Esquemas de detección y corrección de errores

## Integrantes
* Vianka 23201
* Ricardo 23247

## Descripción
Este proyecto simula la transmisión de mensajes entre un Cajero Automático (Emisor) y un Servidor Bancario (Receptor) a través de un canal ruidoso. Implementa una arquitectura por capas (Aplicación, Presentación, Enlace, Ruido y Transmisión).

## Requisitos
* Python 3.x
* Rust (Cargo)

## Ejecución
Para correr el proyecto, asegúrese de tener dos terminales abiertas.

1. En la primera terminal, inicie el receptor (servidor):
   ```bash
   make run-receptor