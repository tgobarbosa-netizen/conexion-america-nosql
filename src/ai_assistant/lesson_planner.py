import os
from dotenv import load_dotenv
from google import genai
from src.config.database import get_mongo_db, get_neo4j_driver

load_dotenv()

def gerar_plano_aula_ia(aluno_id: str = "usr_001"):
    db = get_mongo_db()
    driver = get_neo4j_driver()

    with driver.session() as session:
        perfil = session.run("""
            MATCH (a:Aluno {id: $id})
            OPTIONAL MATCH (a)-[:INTERESSE_EM]->(i:Interesse)
            OPTIONAL MATCH (a)-[:TEM_DIFICULDADE]->(td:Topico)
            OPTIONAL MATCH (prereq:Topico)-[:PREREQUISITO_PARA]->(td)
            RETURN a.nome AS nome, a.idioma AS idioma, a.nivel AS nivel,
                   collect(DISTINCT i.nome) AS interesses,
                   collect(DISTINCT td.nome) AS dificuldades,
                   collect(DISTINCT prereq.nome) AS prerequisitos
        """, id=aluno_id).single()
    driver.close()

    diarios = list(db.diarios_aula.find({"supabase_aluno_id": aluno_id}, {"_id": 0}).sort("data", -1).limit(3))

    contexto = f"""
    Aluno: {perfil['nome']} | Idioma: {perfil['idioma']} | Nível CEFR: {perfil['nivel']}
    Interesses (Neo4j): {', '.join(perfil['interesses'])}
    Tópicos com dificuldade (Neo4j): {', '.join(perfil['dificuldades'])}
    Pré-requisitos recomendados (Neo4j): {', '.join(perfil['prerequisitos'])}
    Histórico recente de diários (MongoDB):
    """
    for d in diarios:
        contexto += f"- Tópico: {d['topico_principal']} | Obs. Prof: {d['feedback_professor']['dificuldade_identificada']} | Nota Aluno: {d['avaliacao_aluno']['nota_aula']} ({d['avaliacao_aluno']['comentario']})\n"

    prompt = f"""
    Você é o Coordenador Pedagógico da escola de idiomas Conexión América.
    Com base nos dados reais extraídos da nossa arquitetura híbrida (Neo4j + MongoDB) abaixo, elabore um Plano de Aula de 50 minutos altamente personalizado e engajador para recuperar a confiança deste aluno, conectando os tópicos gramaticais difíceis aos seus interesses pessoais:
    {contexto}
    """

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or "sua_chave" in api_key:
        print("\n[AVISO] GEMINI_API_KEY não configurada no .env. Exibindo prompt estruturado:\n")
        print(prompt)
        return

    client = genai.Client(api_key=api_key)
    modelos = ["gemini-3.8-flash", "gemini-3.8-pro"]

    for modelo in modelos:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
            )
            print(f"\n=== PLANO DE AULA GERADO PELA IA ({modelo} + MONGODB + NEO4J) ===\n")
            print(response.text)
            return
        except Exception as e:
            print(f"[AVISO] Modelo {modelo} temporariamente indisponível ({e.args[0] if e.args else e}). Tentando alternativa...")

    print("\n=== PLANO DE AULA PERSONALIZADO (MODO CONTINGÊNCIA — CONTEXTO HÍBRIDO) ===\n")
    print(f"Aluno-Alvo: {perfil['nome']} ({perfil['idioma']} - {perfil['nivel']})")
    print(f"Eixo Temático (Interesses Neo4j): {' & '.join(perfil['interesses'])}")
    print(f"Revisão de Pré-requisitos: {', '.join(perfil['prerequisitos'])}")
    print("Estrutura Sugerida (50 min):")
    print("  1. Warm-up (10 min): Simulação de check-in em viagem de negócios usando Simple Present.")
    print("  2. Revisão Guiada (15 min): Contraste prático entre Past Simple e Present Perfect em relatos de reuniões.")
    print("  3. Prática Contextualizada (15 min): Roleplay com 5 Phrasal Verbs Corporativos essenciais.")
    print("  4. Wrap-up e Feedback (10 min): Autoavaliação em ritmo reduzido para consolidar confiança.")

if __name__ == "__main__":
    gerar_plano_aula_ia("usr_001")