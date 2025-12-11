import chromadb
from chromadb.config import Settings
from app.util.config import Config
# settings=Settings(
#             chroma_db_impl="duckdb+parquet",
#             anonymized_telemetry=self.cfg.settings.anonymized_telemetry
#         )
class ChromaManager:
    def __init__(self):
        self.config = Config()
        self.cfg = self.config.database
        self.client = chromadb.PersistentClient(path=self.cfg.path)

        self.collections = {}
        print(vars(self.cfg.collections))
        for key, col in vars(self.cfg.collections).items():
            print(f"Loading collection {key} -> name={col.name}")
            self.collections[key] = self.client.get_or_create_collection(
                name=col.name,
                metadata={"description": col.description},
                embedding_function=None
            )

    def add_document(self, collection, doc_id, embedding, metadata):
        self.collections[collection].add(ids=[doc_id], embeddings=[embedding], metadatas=[metadata])

    
    def query(self, collection, embedding, top_k=3):
        return self.collections[collection].query(query_embeddings=[embedding], n_results=top_k)
