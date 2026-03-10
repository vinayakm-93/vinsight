import sys
import os

# Add backend to path to use its services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from services.sec_rag import SECRAGBackend
except ImportError as e:
    print(f"Error: Could not import SECRAGBackend. Make sure you are running from the project root. Details: {e}")
    sys.exit(1)

def main():
    print("--- Microsoft SEC RAG Sample Implementation ---")
    
    # 1. Initialize RAG Backend
    # By default, it uses FAISS for local storage and SentenceTransformer for embeddings.
    rag = SECRAGBackend()
    
    symbol = "MSFT"
    
    # 2. Ingest Latest 10-K
    # This uses edgartools to fetch the latest 10-K, then extracts Item 1A and Item 7.
    print(f"\nStep 1: Ingesting latest 10-K for {symbol}...")
    success = rag.ingest_latest_10k(symbol)
    
    if not success:
        print(f"Failed to ingest 10-K for {symbol}. Check your internet connection or edgar identity.")
        return

    # 3. Perform Similarity Search
    # We'll ask a semantic question about Microsoft's competition in AI.
    print(f"\nStep 2: Performing semantic search for competition in AI...")
    query = "What does Microsoft say about competition in AI and cloud?"
    results = rag.similarity_search(symbol, query, top_k=3)
    
    print(f"\nResults for: '{query}'")
    for i, res in enumerate(results):
        print(f"\n[Result {i+1}] (Distance: {res['distance']:.4f})")
        print(f"Section: {res['metadata']['section']} ({res['metadata']['label']})")
        print(f"Source: {res['metadata']['source']}")
        print("-" * 30)
        # Showing the first 500 characters of the content
        print(res['content'][:500] + "...")
        print("-" * 30)

    # 4. Filtered Search
    # Example searching specifically in Risk Factors (Item 1A)
    print(f"\nStep 3: Specific search in Risk Factors (Item 1A)...")
    query_risk = "Cybersecurity risks related to cloud infrastructure"
    risk_results = rag.similarity_search(symbol, query_risk, section_filter="Item 1A", top_k=2)
    
    for i, res in enumerate(risk_results):
        print(f"\n[Risk Result {i+1}] (Distance: {res['distance']:.4f})")
        print(res['content'][:400] + "...")

    print("\n--- Sample Complete ---")

if __name__ == "__main__":
    main()
