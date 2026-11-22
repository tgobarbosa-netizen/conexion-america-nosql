# Relatório Técnico — Persistência Poliglota NoSQL & IA Generativa Aplicada à Educação Personalizada

**Projeto:** Conexión América — Ecossistema Híbrido de Gestão Pedagógica e Recomendação  
**Disciplina:** Banco de Dados NoSQL (3º Semestre — Ciência de Dados e Inteligência Artificial)  
**Instituição:** Centro Universitário Senac-RS  
**Repositório GitHub:** `https://github.com/tgobarbosa-netizen/conexion-america-nosql`  
**Data de Entrega:** 08 de Dezembro de 2026  

---

## 1. Contextualização e Problema de Negócio

A **Conexión América** é uma plataforma de ensino de idiomas focada em aulas particulares ao vivo (1-on-1) de Espanhol e Inglês com professores nativos. No ambiente operacional da escola, uma base relacional tradicional (PostgreSQL via Supabase) atende adequadamente ao controle transacional de cadastros, planos e agendamentos. Contudo, o crescimento do volume de sessões evidenciou duas limitações estruturais críticas:

1. **Rigidez de Schema nos Diários de Aula:** Cada aula gera registros pedagógicos heterogêneos (avaliação 360º do aluno, percepção do professor sobre ritmo e fala, dificuldades gramaticais específicas e recomendações de foco), cujo formato evolui continuamente sem justificar migrações constantes de tabelas relacionais.
2. **Ineficiência em Consultas de Afinidade e Trilhas Pedagógicas:** Recomendar o professor ideal com base em interesses pessoais em comum (*Negócios, Viagens, Cultura*) e navegar por cadeias de pré-requisitos gramaticais (*Presente de Indicativo* $\rightarrow$ *Pretérito Indefinido* $\rightarrow$ *Subjuntivo Presente*) exige múltiplos `JOIN` recursivos custosos em bancos relacionais.

Para solucionar esses gargalos, projetou-se uma arquitetura de **Persistência Poliglota** integrando **MongoDB Atlas** (documentos) e **Neo4j AuraDB** (grafos), enriquecida por uma camada de **IA Generativa (Google Gemini)** para síntese de planos de aula personalizados.

---

## 2. Engenharia de Requisitos

### 2.1 Requisitos Funcionais (RF)
* **RF01 — Ingestão Híbrida e Anonimizada:** O sistema deve extrair registros base em modo de homologação, anonimizando identificadores pessoais antes da carga simultânea no MongoDB Atlas e no Neo4j AuraDB.
* **RF02 — CRUD Poliglota Sincronizado:** O sistema deve permitir criar, consultar, atualizar e remover diários de aula no MongoDB enquanto atualiza pesos de avaliação e relações de domínio/dificuldade no grafo do Neo4j.
* **RF03 — Alerta Proativo de Retenção:** O sistema deve identificar aulas cuja nota da sessão ou da plataforma seja $\le 3$, expondo comentários qualitativos para intervenção pedagógica.
* **RF04 — Ranking de Desempenho Docente:** O sistema deve agregar métricas de volume de aulas e médias de avaliação por professor e idioma.
* **RF05 — Recomendação por Afinidade em Grafo:** O sistema deve cruzar interesses do aluno com especialidades dos professores no mesmo idioma, ordenando por afinidade e histórico de notas.
* **RF06 — Navegação de Pré-Requisitos Gramaticais:** O sistema deve identificar tópicos com dificuldade registrada e sugerir a revisão do tópico pré-requisito imediatamente anterior na trilha pedagógica.
* **RF07 — Dossiê Pedagógico Híbrido & Plano de Aula com IA:** O sistema deve consolidar o perfil relacional/grafo (Neo4j) com os últimos diários documentais (MongoDB) para gerar um plano de aula personalizado de 50 minutos via LLM.

### 2.2 Requisitos Não Funcionais (RNF) e Conformidade LGPD
* **RNF01 — Privacidade e Proteção de Dados (LGPD):** Nenhum dado pessoal identificável (PII) real de produção é exposto em ambientes de desenvolvimento/homologação. O pipeline aplica hash criptográfico determinístico (`SHA-256` truncado) aos IDs de origem e gera dados sintéticos realistas com a biblioteca `Faker` (`pt_BR`).
* **RNF02 — Segurança de Credenciais:** Todas as URIs, usuários e chaves de API são isolados em variáveis de ambiente (`.env`), estritamente bloqueadas no controle de versão via `.gitignore` (fornecendo-se apenas o molde `.env.example`).
* **RNF03 — Conectividade Cloud e TLS:** A comunicação com os clusters em nuvem (MongoDB Atlas e Neo4j AuraDB) utiliza transporte criptografado (`TLS/SSL` com cadeia de certificados validada via `certifi` e protocolo `neo4j+ssc://`).
* **RNF04 — Resiliência e Degradação Graciosa (*Graceful Degradation*):** Falhas temporárias ou sobrecarga (`503 UNAVAILABLE`) na API externa de IA Generativa não interrompem a operação; o sistema aciona cadeia de *fallback* entre modelos e contingência local baseada nos dados híbridos já recuperados.

---

## 3. Arquitetura Poliglota e Modelagem de Dados

### 3.1 Justificativa da Escolha dos Bancos
| Camada / Banco | Paradigma | Papel na Arquitetura | Justificativa Técnica |
| :--- | :--- | :--- | :--- |
| **Supabase (PostgreSQL)** | Relacional | Fonte Transacional Base | Integridade ACID para autenticação, contratos e agendamento de horários. |
| **MongoDB Atlas** | Documental (BSON/JSON) | Repositório de Diários (`diarios_aula`) | Schema flexível para feedbacks aninhados, leitura rápida do histórico cronológico e pipelines de agregação nativos. |
| **Neo4j AuraDB** | Grafo de Propriedades | Motor de Afinidade e Trilhas | Travessia em tempo constante ($O(1)$ por salto) entre alunos, interesses, professores e pré-requisitos curriculares. |

### 3.2 Modelo Documental (MongoDB Atlas — Coleção `diarios_aula`)
Cada documento encapsula o contexto completo de uma sessão sem fragmentação em tabelas auxiliares:

```json
{
  "aula_id": "AULA_001",
  "supabase_aluno_id": "usr_001",
  "aluno_nome": "Brenda Alves",
  "supabase_prof_id": "prof_01",
  "professor_nome": "Minael",
  "idioma": "Inglês",
  "data": "2026-11-20T19:00:00Z",
  "topico_principal": "Past Simple vs Present Perfect",
  "feedback_professor": {
    "desempenho_fala": 3,
    "dificuldade_identificada": "Dificuldade na estrutura gramatical e ritmo acelerado",
    "proximo_foco": "Prática contextualizada com vocabulário corporativo"
  },
  "avaliacao_aluno": {
    "nota_aula": 2,
    "nota_professor": 5,
    "nota_conteudo": 2,
    "nota_escola_plataforma": 5,
    "comentario": "Achei o conteúdo difícil de acompanhar nesta sessão."
  }
}