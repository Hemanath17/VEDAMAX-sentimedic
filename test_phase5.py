"""Test script for Phase 5: Vector Store & Embeddings."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_phase5():
    """Test Phase 5 components."""
    print("\n" + "="*60)
    print("PHASE 5: VECTOR STORE & EMBEDDINGS - TEST")
    print("="*60)
    
    try:
        # Test imports
        print("\n1. Testing imports...")
        from src.retrieval.vector_store import (
            QdrantClient, EmbeddingModel, EmbeddingPipeline,
            EmbeddingCache, CollectionManager, VectorStore
        )
        print("✓ All components imported")
        
        # Test Qdrant connection
        print("\n2. Testing Qdrant connection...")
        qdrant = QdrantClient()
        if qdrant.health_check():
            print("✓ Qdrant connection successful")
        else:
            print("✗ Qdrant connection failed - is Qdrant running?")
            print("  Start with: docker run -p 6333:6333 qdrant/qdrant")
            return False
        
        # Test embedding model
        print("\n3. Testing BGE-M3 embedding model...")
        embedding_model = EmbeddingModel()
        print(f"✓ Model loaded: {embedding_model.model_name}")
        print(f"✓ Vector size: {embedding_model.get_vector_size()}")
        
        # Test embedding generation
        test_text = "What is diabetes?"
        embedding = embedding_model.encode_single(test_text)
        print(f"✓ Generated embedding: shape={embedding.shape}")
        
        # Test embedding pipeline
        print("\n4. Testing embedding pipeline...")
        pipeline = EmbeddingPipeline(model=embedding_model)
        results = pipeline.generate_embeddings([test_text], show_progress=False)
        print(f"✓ Pipeline generated {len(results)} embeddings")
        
        # Test cache
        print("\n5. Testing embedding cache...")
        cache = EmbeddingCache()
        cache.set(test_text, embedding)
        cached = cache.get(test_text)
        if cached is not None:
            print("✓ Cache working: stored and retrieved embedding")
        else:
            print("✗ Cache failed")
        
        # Test collection manager
        print("\n6. Testing collection manager...")
        collection_manager = CollectionManager(qdrant_client=qdrant)
        collection_name = "test_collection"
        
        if collection_manager.collection_exists(collection_name):
            collection_manager.delete_collection(collection_name)
        
        if collection_manager.create_collection(collection_name, vector_size=1024):
            print(f"✓ Collection '{collection_name}' created")
            
            info = collection_manager.get_collection_info(collection_name)
            if info:
                print(f"✓ Collection info retrieved: {info['points_count']} points")
            
            # Cleanup
            collection_manager.delete_collection(collection_name)
            print(f"✓ Collection '{collection_name}' deleted")
        else:
            print("✗ Failed to create collection")
        
        # Test vector store
        print("\n7. Testing vector store (main orchestrator)...")
        vector_store = VectorStore(collection_name="test_medical_docs")
        print("✓ VectorStore initialized")
        
        # Store test chunks
        test_chunks = [
            {
                "text": "Diabetes is a chronic condition that affects how your body processes blood sugar.",
                "metadata": {
                    "document_id": "test_doc_1",
                    "chunk_type": "text",
                    "page_number": 1,
                }
            },
            {
                "text": "Hypertension, also known as high blood pressure, is a common medical condition.",
                "metadata": {
                    "document_id": "test_doc_1",
                    "chunk_type": "text",
                    "page_number": 2,
                }
            },
        ]
        
        point_ids = vector_store.store_chunks(test_chunks, show_progress=False)
        print(f"✓ Stored {len(point_ids)} chunks")
        
        # Test search
        search_results = vector_store.search("What is diabetes?", top_k=2)
        print(f"✓ Search returned {len(search_results)} results")
        if search_results:
            print(f"  Top result: score={search_results[0]['score']:.4f}")
            print(f"  Text preview: {search_results[0]['text'][:50]}...")
        
        # Get collection info
        info = vector_store.get_collection_info()
        if info:
            print(f"✓ Collection has {info['points_count']} points")
        
        print("\n" + "="*60)
        print("🎉 ALL PHASE 5 TESTS PASSED!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_phase5()
    sys.exit(0 if success else 1)

