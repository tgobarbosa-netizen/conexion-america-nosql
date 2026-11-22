from datetime import datetime
from src.config.database import get_mongo_db, get_neo4j_driver

def registrar_aula_poliglota(aula_doc: dict):
    """CREATE: Insere diário no MongoDB e atualiza pesos/relações no Neo4j."""
    db = get_mongo_db()
    driver = get_neo4j_driver()

    db.diarios_aula.insert_one(aula_doc)

    av = aula_doc["avaliacao_aluno"]
    rel_tipo = "TEM_DIFICULDADE" if av["nota_conteudo"] <= 3 else "DOMINA"

    with driver.session() as session:
        session.run(f"""
            MATCH (a:Aluno {{id: $aluno_id}}), (p:Professor {{id: $prof_id}}), (t:Topico {{nome: $topico}}), (e:Escola {{nome: 'Conexión América'}})
            MERGE (a)-[rp:AVALIOU_PROFESSOR]->(p)
            ON CREATE SET rp.soma_notas = $nota_prof, rp.qtd = 1, rp.media = toFloat($nota_prof)
            ON MATCH SET rp.soma_notas = rp.soma_notas + $nota_prof, rp.qtd = rp.qtd + 1, rp.media = toFloat(rp.soma_notas + $nota_prof) / (rp.qtd + 1)

            MERGE (a)-[rt:{rel_tipo}]->(t)
            SET rt.ultima_nota_conteudo = $nota_conteudo

            MERGE (a)-[re:AVALIOU_ESCOLA]->(e)
            SET re.ultima_nota = $nota_escola
        """, aluno_id=aula_doc["supabase_aluno_id"], prof_id=aula_doc["supabase_prof_id"],
             topico=aula_doc["topico_principal"], nota_prof=av["nota_professor"],
             nota_conteudo=av["nota_conteudo"], nota_escola=av["nota_escola_plataforma"])
    print(f"[CREATE] Aula {aula_doc['aula_id']} registrada nos dois bancos.")

def buscar_historico_aluno(aluno_id: str, limite: int = 3):
    """READ: Busca os últimos diários do aluno no MongoDB."""
    db = get_mongo_db()
    aulas = list(db.diarios_aula.find({"supabase_aluno_id": aluno_id}, {"_id": 0}).sort("data", -1).limit(limite))
    print(f"[READ] {len(aulas)} diário(s) encontrado(s) para {aluno_id}.")
    return aulas

def atualizar_avaliacao_aula(aula_id: str, nova_nota_aula: int, novo_comentario: str):
    """UPDATE: Atualiza avaliação pós-aula no MongoDB."""
    db = get_mongo_db()
    res = db.diarios_aula.update_one(
        {"aula_id": aula_id},
        {"$set": {
            "avaliacao_aluno.nota_aula": nova_nota_aula,
            "avaliacao_aluno.comentario": novo_comentario,
            "atualizado_em": datetime.now()
        }}
    )
    print(f"[UPDATE] Aula {aula_id} atualizada (documentos modificados: {res.modified_count}).")

def remover_aula_teste(aula_id: str):
    """DELETE: Remove registro de teste no MongoDB."""
    db = get_mongo_db()
    res = db.diarios_aula.delete_one({"aula_id": aula_id})
    print(f"[DELETE] Aula {aula_id} removida (documentos excluídos: {res.deleted_count}).")

if __name__ == "__main__":
    teste_aula = {
        "aula_id": "AULA_TESTE_999",
        "supabase_aluno_id": "usr_001",
        "aluno_nome": "Aluno Teste CRUD",
        "supabase_prof_id": "prof_01",
        "professor_nome": "Minael",
        "idioma": "Espanhol",
        "data": datetime.now(),
        "topico_principal": "Subjuntivo Presente",
        "feedback_professor": {
            "desempenho_fala": 4,
            "dificuldade_identificada": "Concordância verbal",
            "proximo_foco": "Prática dirigida"
        },
        "avaliacao_aluno": {
            "nota_aula": 5,
            "nota_professor": 5,
            "nota_conteudo": 4,
            "nota_escola_plataforma": 5,
            "comentario": "Aula teste CRUD executada com sucesso."
        }
    }
    registrar_aula_poliglota(teste_aula)
    buscar_historico_aluno("usr_001", limite=2)
    atualizar_avaliacao_aula("AULA_TESTE_999", 5, "Comentário atualizado via CRUD.")
    remover_aula_teste("AULA_TESTE_999")