#!/usr/bin/env python3
"""
Data Ingestion Script for NeuroRAG
Processes documents and creates FAISS vector embeddings
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import pandas as pd
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the document processor with embedding model."""
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Initialized embedding model: {model_name} (dim: {self.dimension})")

    def process_documents(self, input_path: str) -> List[Dict[str, Any]]:
        """Process documents from various formats."""
        input_path = Path(input_path)
        documents = []

        if input_path.is_file():
            if input_path.suffix == '.json':
                documents = self._process_json(input_path)
            elif input_path.suffix == '.csv':
                documents = self._process_csv(input_path)
            elif input_path.suffix == '.txt':
                documents = self._process_text(input_path)
        elif input_path.is_dir():
            for file_path in input_path.rglob('*'):
                if file_path.is_file():
                    if file_path.suffix == '.json':
                        documents.extend(self._process_json(file_path))
                    elif file_path.suffix == '.csv':
                        documents.extend(self._process_csv(file_path))
                    elif file_path.suffix == '.txt':
                        documents.extend(self._process_text(file_path))

        logger.info(f"Processed {len(documents)} documents")
        return documents

    def _process_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process JSON documents."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        else:
            return [data]

    def _process_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process CSV documents."""
        df = pd.read_csv(file_path)
        return df.to_dict('records')

    def _process_text(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process text documents."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return [{
            'id': str(file_path.stem),
            'title': file_path.name,
            'content': content,
            'metadata': {
                'source': str(file_path),
                'timestamp': file_path.stat().st_mtime,
                'classification': 'public',
                'tags': []
            }
        }]

    def create_embeddings(self, documents: List[Dict[str, Any]]) -> np.ndarray:
        """Create embeddings for documents."""
        texts = [doc.get('content', '') for doc in documents]
        logger.info(f"Creating embeddings for {len(texts)} documents...")
        
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32,
            normalize_embeddings=True
        )
        
        return embeddings.astype(np.float32)

class FAISSIndexBuilder:
    def __init__(self, dimension: int):
        """Initialize FAISS index builder."""
        self.dimension = dimension
        self.index = None

    def build_index(self, embeddings: np.ndarray, index_type: str = "IVF_FLAT", nlist: int = 1024):
        """Build FAISS index from embeddings."""
        n_vectors = embeddings.shape[0]
        logger.info(f"Building {index_type} index for {n_vectors} vectors...")

        if index_type == "FLAT":
            self.index = faiss.IndexFlatIP(self.dimension)
        elif index_type == "IVF_FLAT":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, min(nlist, n_vectors // 10))
            
            # Train the index
            logger.info("Training IVF index...")
            self.index.train(embeddings)
        elif index_type == "HNSW":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            self.index.hnsw.efConstruction = 200
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        # Add vectors to index
        logger.info("Adding vectors to index...")
        self.index.add(embeddings)
        
        logger.info(f"Index built successfully. Total vectors: {self.index.ntotal}")

    def save_index(self, output_path: str):
        """Save FAISS index to disk."""
        if self.index is None:
            raise ValueError("No index to save. Build index first.")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        faiss.write_index(self.index, str(output_path))
        logger.info(f"Index saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Ingest data and build FAISS index for NeuroRAG")
    parser.add_argument("--input", required=True, help="Input data path (file or directory)")
    parser.add_argument("--output", required=True, help="Output directory for index and metadata")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Sentence transformer model")
    parser.add_argument("--index-type", default="IVF_FLAT", choices=["FLAT", "IVF_FLAT", "HNSW"])
    parser.add_argument("--nlist", type=int, default=1024, help="Number of clusters for IVF index")
    
    args = parser.parse_args()

    # Initialize processor
    processor = DocumentProcessor(args.model)
    
    # Process documents
    documents = processor.process_documents(args.input)
    if not documents:
        logger.error("No documents found to process")
        return

    # Create embeddings
    embeddings = processor.create_embeddings(documents)
    
    # Build FAISS index
    index_builder = FAISSIndexBuilder(processor.dimension)
    index_builder.build_index(embeddings, args.index_type, args.nlist)
    
    # Save outputs
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save index
    index_path = output_dir / "faiss_index.bin"
    index_builder.save_index(index_path)
    
    # Save document metadata
    metadata_path = output_dir / "documents.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    
    # Save configuration
    config = {
        "model_name": args.model,
        "dimension": processor.dimension,
        "index_type": args.index_type,
        "nlist": args.nlist,
        "num_documents": len(documents),
        "num_vectors": embeddings.shape[0]
    }
    
    config_path = output_dir / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Data ingestion completed successfully!")
    logger.info(f"Index: {index_path}")
    logger.info(f"Metadata: {metadata_path}")
    logger.info(f"Config: {config_path}")

if __name__ == "__main__":
    main()