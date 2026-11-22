from src.config.database import get_mongo_db, get_neo4j_driver

def executar_consultas():
    db = get_mongo_db()
    driver = get_neo4j_driver()

    print("\n=== 1. [MongoDB] Alerta de Retenção (Notas <= 3) ===")
    risco = list(db.diarios_aula.find(
        {"$or": [
            {"avaliacao_aluno.nota_aula": {"$lte": 3}},
            {"avaliacao_aluno.nota_escola_plataforma": {"$lte": 3}}
        ]},
        {"_id": 0, "aula_id": 1, "supabase_aluno_id": 1, "professor_nome": 1, "avaliacao_aluno": 1}
    ).limit(5))
    for r in risco:
        print(f" -> Aluno {r['supabase_aluno_id']} | Prof: {r['professor_nome']} | Nota Aula: {r['avaliacao_aluno']['nota_aula']} | Comentário: {r['avaliacao_aluno']['comentario']}")

    print("\n=== 2. [MongoDB] Agregação de Desempenho por Professor e Idioma ===")
    pipeline = [
        {"$group": {
            "_id": {"professor": "$professor_nome", "idioma": "$idioma"},
            "total_aulas": {"$sum": 1},
            "media_professor": {"$avg": "$avaliacao_aluno.nota_professor"},
            "media_conteudo": {"$avg": "$avaliacao_aluno.nota_conteudo"}
        }},
        {"$sort": {"media_professor": -1}}
    ]
    for doc in db.diarios_aula.aggregate(pipeline):
        print(f" -> {doc['_id']['professor']} ({doc['_id']['idioma']}): {doc['total_aulas']} aulas | Nota Prof: {doc['media_professor']:.2f} | Nota Conteúdo: {doc['media_conteudo']:.2f}")

    with driver.session() as session:
        print("\n=== 3. [Neo4j] Recomendação Inteligente de Professor por Afinidade ===")
        res_match = session.run("""
            MATCH (a:Aluno {id: 'usr_001'})-[:INTERESSE_EM]->(i:Interesse)<-[:ESPECIALISTA_EM]-(p:Professor)
            WHERE p.idioma = a.idioma
            OPTIONAL MATCH (a)-[r:AVALIOU_PROFESSOR]->(p)
            RETURN p.nome AS professor, collect(DISTINCT i.nome) AS interesses_comuns, coalesce(r.media, 0) AS nota_historica
            ORDER BY size(interesses_comuns) DESC, nota_historica DESC
        """)
        for row in res_match:
            print(f" -> Prof. {row['professor']} | Interesses em comum: {row['interesses_comuns']} | Média Histórica: {row['nota_historica']:.1f}")

        print("\n=== 4. [Neo4j] Trilha Pedagógica e Gargalos de Pré-Requisito ===")
        res_trilha = session.run("""
            MATCH (a:Aluno)-[d:TEM_DIFICULDADE]->(t_atual:Topico)
            OPTIONAL MATCH (t_prereq:Topico)-[:PREREQUISITO_PARA]->(t_atual)
            RETURN a.id AS aluno, t_atual.nome AS topico_dificuldade, t_prereq.nome AS revisar_prerequisito
            LIMIT 5
        """)
        for row in res_trilha:
            prereq = row["revisar_prerequisito"] or "Tópico Base (sem pré-requisito)"
            print(f" -> Aluno {row['aluno']} com dificuldade em '{row['topico_dificuldade']}' -> Sugestão: revisar '{prereq}'")

        print("\n=== 5. [Híbrido Neo4j + MongoDB] Dossiê Pedagógico Completo do Aluno (usr_001) ===")
        grafo_aluno = session.run("""
            MATCH (a:Aluno {id: 'usr_001'})
            OPTIONAL MATCH (a)-[:INTERESSE_EM]->(i:Interesse)
            OPTIONAL MATCH (a)-[:TEM_DIFICULDADE]->(td:Topico)
            RETURN a.nome AS nome, a.idioma AS idioma, a.nivel AS nivel,
                   collect(DISTINCT i.nome) AS interesses, collect(DISTINCT td.nome) AS dificuldades_grafo
        """).single()

        ultimas_aulas = list(db.diarios_aula.find({"supabase_aluno_id": "usr_001"}, {"_id": 0}).sort("data", -1).limit(2))
        print(f" -> Perfil Grafo: {grafo_aluno['nome']} | {grafo_aluno['idioma']} ({grafo_aluno['nivel']}) | Interesses: {grafo_aluno['interesses']} | Gargalos: {grafo_aluno['dificuldades_grafo']}")
        for a in ultimas_aulas:
            print(f"    * Última Aula ({a['topico_principal']}): Feedback Prof='{a['feedback_professor']['dificuldade_identificada']}' | Nota={a['avaliacao_aluno']['nota_aula']}")

    driver.close()

if __name__ == "__main__":
    executar_consultas()