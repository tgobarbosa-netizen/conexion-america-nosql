import os
from dotenv import load_dotenv
from pymongo import MongoClient
from neo4j import GraphDatabase

load_dotenv()

def get_mongo_db():
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME", "conexion_america")
    if not uri:
        raise ValueError("MONGO_URI não encontrada no arquivo .env")
    client = MongoClient(uri)
    return client[db_name]

def get_neo4j_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not password:
        raise ValueError("Credenciais do Neo4j não encontradas no arquivo .env")
    return GraphDatabase.driver(uri, auth=(user, password))