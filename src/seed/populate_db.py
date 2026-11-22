import os
import hashlib
import random
from datetime import datetime, timedelta
import pandas as pd
from faker import Faker
from dotenv import load_dotenv
from src.config.database import get_mongo_db, get_neo4j_driver

load_dotenv()
fake = Faker("pt_BR")
Faker.seed(42)
random.seed(42)

MODO = os.getenv("MODO_OPERACAO", "HOMOLOGACAO")
SALT = os.getenv("ANON_SALT", "conexion_segredo_2026")

PROFESSORES = [
    {"id": "prof_01", "nome": "Minael", "idioma": "Espanhol", "especialidades": ["Negócios", "Conversação", "Cultura Latina"]},
    {"id": "prof_02", "nome": "Camila Morales", "idioma": "Espanhol", "especialidades": ["Viagens", "Gramática Avançada", "Preparatório DELE"]},
    {"id": "prof_03", "nome": "John Miller", "idioma": "Inglês", "especialidades": ["Negócios", "Entrevistas Tech", "Conversação"]},
    {"id": "prof_04", "nome": "Sarah Jenkins", "idioma": "Inglês", "especialidades": ["Viagens", "Cultura Pop", "Inglês Básico"]},
]

TOPICOS = [
    {"nome": "Presente de Indicativo", "idioma": "Espanhol", "nivel": "A1", "prerequisito": None},
    {"nome": "Pretérito Indefinido", "idioma": "Espanhol", "nivel": "A2", "prerequisito": "Presente de Indicativo"},
    {"nome": "Subjuntivo Presente", "idioma": "Espanhol", "nivel": "B1", "prerequisito": "Pretérito Indefinido"},
    {"nome": "Vocabulário de Negócios ES", "idioma": "Espanhol", "nivel": "B2", "prerequisito": "Subjuntivo Presente"},
    {"nome": "Simple Present & Routine", "idioma": "Inglês", "nivel": "A1", "prerequisito": None},
    {"nome": "Past Simple vs Present Perfect", "idioma": "Inglês", "nivel": "A2", "prerequisito": "Simple Present & Routine"},
    {"nome": "Phrasal Verbs Corporativos", "idioma": "Inglês", "nivel": "B1", "prerequisito": "Past Simple vs Present Perfect"},
]

INTERESSES = ["Negócios", "Viagens", "Cultura Latina", "Entrevistas Tech", "Cultura Pop"]

def anonimizar_id(valor_original: str, prefixo: str) -> str:
    hash_obj = hashlib.sha256(f"{SALT}_{valor_original}".encode())
    return f"{prefixo}_{hash_obj.hexdigest()[:8]}"

def popular_bancos(qtd_alunos=15, qtd_aulas=45):
    print(f"Iniciando carga em modo: {MODO}...")
    db = get_mongo_db()
    driver = get_neo4j_driver()

    # Limpa apenas a coleção do projeto atual
    db.diarios_aula.delete_many({})

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        # 1. Cria Escola, Professores, Interesses e Tópicos no Neo4j
        session.run("CREATE (:Escola {nome: 'Conexión América'})")

        for prof in PROFESSORES:
            session.run("""
                CREATE (p:Professor {id: $id, nome: $nome, idioma: $idioma})
                WITH p
                UNWIND $especialidades AS esp
                MERGE (i:Interesse {nome: esp})
                MERGE (p)-[:ESPECIALISTA_EM]->(i)
            """, **prof)

        for top in TOPICOS:
            session.run("""
                MERGE (t:Topico {nome: $nome, idioma: $idioma, nivel: $nivel})
            """, **top)
            if top["prerequisito"]:
                session.run("""
                    MATCH (t1:Topico {nome: $prereq}), (t2:Topico {nome: $nome})
                    MERGE (t1)-[:PREREQUISITO_PARA]->(t2)
                """, prereq=top["prerequisito"], nome=top["nome"])

        # 2. Gera Alunos (simulando IDs anonimizados vindos do Supabase)
        alunos = []
        for idx in range(1, qtd_alunos + 1):
            idioma = random.choice(["Espanhol", "Inglês"])
            aluno_id = anonimizar_id(f"supabase_real_id_{idx}", "usr") if idx > 1 else "usr_001"
            aluno = {
                "id": aluno_id,
                "nome": fake.name(),
                "idioma": idioma,
                "nivel": random.choice(["A1", "A2", "B1", "B2"]),
                "interesses": random.sample(INTERESSES, 2)
            }
            alunos.append(aluno)
            session.run("""
                CREATE (a:Aluno {id: $id, nome: $nome, idioma: $idioma, nivel: $nivel})
                WITH a
                UNWIND $interesses AS int_nome
                MERGE (i:Interesse {nome: int_nome})
                MERGE (a)-[:INTERESSE_EM]->(i)
            """, **aluno)

        # 3. Gera 45 Diários de Aula (MongoDB) + Relacionamentos de Avaliação (Neo4j)
        documentos_mongo = []
        for idx in range(1, qtd_aulas + 1):
            aluno = random.choice(alunos)
            profs_idioma = [p for p in PROFESSORES if p["idioma"] == aluno["idioma"]]
            prof = random.choice(profs_idioma)
            topicos_idioma = [t for t in TOPICOS if t["idioma"] == aluno["idioma"]]
            topico = random.choice(topicos_idioma)

            # Simula cenário de risco de churn no aluno usr_001 para validar a Consulta 1
            if aluno["id"] == "usr_001":
                nota_aula, nota_prof, nota_conteudo, nota_escola = 2, 3, 2, 2
                dificuldade = "Dificuldade na estrutura gramatical e ritmo acelerado"
                comentario_aluno = "Achei o conteúdo difícil de acompanhar nesta sessão."
            else:
                nota_aula = random.choice([4, 5, 5])
                nota_prof = random.choice([4, 5, 5])
                nota_conteudo = random.choice([3, 4, 5])
                nota_escola = random.choice([4, 5, 5])
                dificuldade = random.choice(["Pronúncia de vogais", "Uso de preposições", "Nenhuma dificuldade crítica"])
                comentario_aluno = random.choice([
                    "Aula muito dinâmica e prática!",
                    "Excelente didática do professor.",
                    "Bom conteúdo, gostaria de mais exercícios de escuta."
                ])

            data_aula = datetime.now() - timedelta(days=random.randint(1, 60))
            aula_doc = {
                "aula_id": f"AULA_{idx:04d}",
                "supabase_aluno_id": aluno["id"],
                "aluno_nome": aluno["nome"],
                "supabase_prof_id": prof["id"],
                "professor_nome": prof["nome"],
                "idioma": aluno["idioma"],
                "data": data_aula,
                "topico_principal": topico["nome"],
                "feedback_professor": {
                    "desempenho_fala": random.randint(3, 5),
                    "dificuldade_identificada": dificuldade,
                    "proximo_foco": f"Revisar {topico['nome']} em contexto prático"
                },
                "avaliacao_aluno": {
                    "nota_aula": nota_aula,
                    "nota_professor": nota_prof,
                    "nota_conteudo": nota_conteudo,
                    "nota_escola_plataforma": nota_escola,
                    "comentario": comentario_aluno
                }
            }
            documentos_mongo.append(aula_doc)

            rel_tipo = "TEM_DIFICULDADE" if nota_conteudo <= 3 else "DOMINA"
            session.run(f"""
                MATCH (a:Aluno {{id: $aluno_id}}), (p:Professor {{id: $prof_id}}), (t:Topico {{nome: $topico}}), (e:Escola {{nome: 'Conexión América'}})
                MERGE (a)-[rp:AVALIOU_PROFESSOR]->(p)
                ON CREATE SET rp.soma_notas = $nota_prof, rp.qtd = 1, rp.media = toFloat($nota_prof)
                ON MATCH SET rp.soma_notas = rp.soma_notas + $nota_prof, rp.qtd = rp.qtd + 1, rp.media = toFloat(rp.soma_notas + $nota_prof) / (rp.qtd + 1)

                MERGE (a)-[rt:{rel_tipo}]->(t)
                SET rt.ultima_nota_conteudo = $nota_conteudo

                MERGE (a)-[re:AVALIOU_ESCOLA]->(e)
                SET re.ultima_nota = $nota_escola
            """, aluno_id=aluno["id"], prof_id=prof["id"], topico=topico["nome"],
                 nota_prof=nota_prof, nota_conteudo=nota_conteudo, nota_escola=nota_escola)

        db.diarios_aula.insert_many(documentos_mongo)
        print(f"Concluído! {len(documentos_mongo)} registros inseridos no MongoDB Atlas e grafo populado no Neo4j AuraDB.")
    driver.close()

if __name__ == "__main__":
    popular_bancos()