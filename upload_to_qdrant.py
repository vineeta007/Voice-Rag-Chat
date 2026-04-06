#!/usr/bin/env python3
"""
Upload university data to Qdrant vector database
Processes rag_chunks_optimized.json and creates embeddings using all-mpnet-base-v2
"""
import json
import os
import time
from typing import List, Dict
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Configuration
DATA_FILE = "rag_chunks_with_faculty.json"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_DIM = 768
BATCH_SIZE = 20  # Reduced batch size to avoid timeouts

def main():
    print("=" * 80)
    print("QDRANT VECTOR DATABASE UPLOAD")
    print("=" * 80)
    
    # 1. Load Qdrant configuration
    print("\n[1/6] Loading configuration...")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "university_knowledge_base")
    
    if not qdrant_url or not qdrant_api_key:
        raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in .env file")
    
    print(f"   ✓ Qdrant URL: {qdrant_url}")
    print(f"   ✓ Collection: {collection_name}")
    
    # 2. Initialize Qdrant client
    print("\n[2/6] Connecting to Qdrant cluster...")
    try:
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=60  # Increase timeout to 60 seconds
        )
        # Test connection
        collections = client.get_collections()
        print(f"   ✓ Connected successfully!")
        print(f"   ✓ Existing collections: {len(collections.collections)}")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        raise
    
    # 3. Load data
    print(f"\n[3/6] Loading data from {DATA_FILE}...")
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data_chunks = json.load(f)
        print(f"   ✓ Loaded {len(data_chunks)} data chunks")
    except Exception as e:
        print(f"   ✗ Failed to load data: {e}")
        raise
    
    # 4. Initialize embedding model
    print(f"\n[4/6] Initializing embedding model: {EMBEDDING_MODEL}...")
    try:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"   ✓ Model loaded successfully")
        print(f"   ✓ Embedding dimension: {EMBEDDING_DIM}")
    except Exception as e:
        print(f"   ✗ Failed to load model: {e}")
        raise
    
    # 5. Create or recreate collection
    print(f"\n[5/6] Setting up collection '{collection_name}'...")
    try:
        # Check if collection exists
        existing_collections = [col.name for col in client.get_collections().collections]
        
        if collection_name in existing_collections:
            print(f"   ⚠ Collection '{collection_name}' already exists. Deleting as requested...")
            client.delete_collection(collection_name)
            print(f"   ✓ Deleted existing collection")
        
        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE
            )
        )
        print(f"   ✓ Collection created with {EMBEDDING_DIM}D vectors (COSINE distance)")
    except Exception as e:
        print(f"   ✗ Failed to create collection: {e}")
        raise
    
    # 6. Generate embeddings and upload
    print(f"\n[6/6] Generating embeddings and uploading to Qdrant...")
    print(f"   Processing {len(data_chunks)} chunks in batches of {BATCH_SIZE}...")
    
    try:
        # Extract content for embedding
        contents = [chunk['content'] for chunk in data_chunks]
        
        # Generate embeddings with progress bar
        print("\n   Generating embeddings...")
        embeddings = embedding_model.encode(
            contents,
            show_progress_bar=True,
            batch_size=32
        )
        
        # Prepare points for upload
        print("\n   Preparing points for upload...")
        points = []
        for idx, (chunk, embedding) in enumerate(zip(data_chunks, embeddings)):
            point = PointStruct(
                id=idx,
                vector=embedding.tolist(),
                payload={
                    "chunk_id": chunk.get("id", f"chunk_{idx}"),
                    "content": chunk["content"],
                    "category": chunk.get("category", "general"),
                    "program": chunk.get("program", "ALL"),
                    "keywords": chunk.get("keywords", [])
                }
            )
            points.append(point)
        
        # Upload in batches
        print(f"\n   Uploading {len(points)} points in batches...")
        for i in tqdm(range(0, len(points), BATCH_SIZE), desc="   Upload progress"):
            batch = points[i:i + BATCH_SIZE]
            retries = 3
            for attempt in range(retries):
                try:
                    client.upsert(
                        collection_name=collection_name,
                        points=batch,
                        wait=True
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt < retries - 1:
                        print(f"\n   ⚠ Batch upload failed (attempt {attempt + 1}/{retries}), retrying...")
                        time.sleep(2)  # Wait before retry
                    else:
                        raise  # Final attempt failed
            time.sleep(0.5)  # Small delay between batches
        
        print(f"\n   ✓ Upload complete!")
        
    except Exception as e:
        print(f"\n   ✗ Upload failed: {e}")
        raise
    
    # 7. Verify upload
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    try:
        collection_info = client.get_collection(collection_name)
        print(f"\n✓ Collection: {collection_name}")
        print(f"✓ Total points: {collection_info.points_count}")
        print(f"✓ Vector dimension: {collection_info.config.params.vectors.size}")
        print(f"✓ Distance metric: {collection_info.config.params.vectors.distance}")
        
        # Test search
        print("\n" + "-" * 80)
        print("Testing semantic search...")
        test_query = "What are the admission requirements for B.Tech AI and Machine Learning?"
        print(f"Query: '{test_query}'")
        
        query_embedding = embedding_model.encode(test_query).tolist()
        search_results = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=3
        )
        
        print(f"\nTop 3 results:")
        for i, hit in enumerate(search_results.points, 1):
            print(f"\n{i}. Score: {hit.score:.4f}")
            print(f"   Category: {hit.payload.get('category')}")
            print(f"   Program: {hit.payload.get('program')}")
            print(f"   Content: {hit.payload.get('content')[:100]}...")
        
        print("\n" + "=" * 80)
        print("✅ UPLOAD SUCCESSFUL!")
        print("=" * 80)
        print(f"\nNext steps:")
        print(f"1. Update backend/rag_engine.py to use the new embedding model")
        print(f"2. Restart your backend server")
        print(f"3. Test with real queries")
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        raise

if __name__ == "__main__":
    main()
