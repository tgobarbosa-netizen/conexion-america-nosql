# Conexión América — Arquitetura Poliglota NoSQL & IA Generativa

Projeto final da disciplina de **Banco de Dados NoSQL** (3º Semestre — Ciência de Dados e Inteligência Artificial), aplicando persistência poliglota ao ecossistema real da escola de idiomas **Conexión América**.

## Arquitetura Poliglota
* **Supabase (Relacional Base):** Fonte transacional de usuários e agendamentos (anonimizada via `SHA-256` + `Faker` no pipeline de homologação).
* **MongoDB Atlas (Documental — `diarios_aula`):** Armazena diários de aula com schema flexível, feedback do professor e avaliação 360º do aluno.
* **Neo4j AuraDB (Grafos):** Modela a rede de afinidade entre `Aluno`, `Professor`, `Topico`, `Interesse` e `Escola`, permitindo recomendação por interesses e navegação em pré-requisitos gramaticais.
* **IA Generativa (Google Gemini):** Consome o dossiê híbrido (MongoDB + Neo4j) para gerar planos de aula personalizados de 50 minutos.

## Como Executar
1. Clone o repositório e crie o ambiente virtual:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt