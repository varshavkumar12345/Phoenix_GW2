import ollama
import chromadb
import json

EMBEDDING_MODEL = "nomic-embed-text"
LANGUAGE_MODEL = "llama3"
COLLECTION_NAME = "news"

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space":"cosine"})

# Load dataset
try:
    with open("googlenews.json", "r") as file:
        dataset = json.load(file)
except FileNotFoundError:
    print("googlenews.json not found. Please run the web crawler first.")
    exit(1)

# Prepare data for ChromaDB
documents = []
embeddings = []
ids = []

for i, news_item in enumerate(dataset):
    doc_id = f"id_{i}"
    
    # Check if ID already exists in collection
    existing = collection.get(ids=[doc_id])
    if existing['ids']:  # ID already exists
        print(f"Skipping {doc_id} - already in collection")
        continue
    
    # Convert dictionary to a formatted string for embedding
    text_to_embed = f"Title: {news_item['title']}. Source: {news_item['source']}. Published: {news_item['pubDate']}"
    
    # Generate embedding
    embedding = ollama.embed(model=EMBEDDING_MODEL, input=text_to_embed)['embeddings'][0]
    
    # Store the original JSON string as the document
    documents.append(json.dumps(news_item))
    embeddings.append(embedding)
    ids.append(doc_id)

# Add to ChromaDB only if there are new documents
if documents:
    collection.add(
        documents=documents,
        embeddings=embeddings,
        ids=ids
    )
    print(f"Successfully added {len(documents)} news items to ChromaDB")
else:
    print("No new items to add - all IDs already in collection")

# Delete the JSON file after embedding
