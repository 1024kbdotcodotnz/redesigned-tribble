#!/usr/bin/env python3
"""
Confidential Document Processor
Securely handles sensitive legal documents with PII redaction and encryption
"""

import os
import re
import hashlib
import uuid
from pathlib import Path
from typing import Dict, List, Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

@dataclass
class DocumentMetadata:
    doc_id: str
    original_filename: str
    file_hash: str
    file_size: int
    mime_type: str
    created_at: str
    client_id: str
    retention_days: int
    pii_detected: List[str]
    redacted: bool

class PIIDetector:
    """
    Detects and redacts Personally Identifiable Information
    """
    
    # NZ-specific patterns
    PATTERNS = {
        "nz_phone": r'\b(?:0|64)[\s\-]?(?:2[0-9]|[3-9])[\s\-]?\d{3}[\s\-]?\d{3,4}\b',
        "nz_mobile": r'\b(?:0|64)?[\s\-]?2[0-9][\s\-]?\d{3}[\s\-]?\d{3,4}\b',
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "ird_number": r'\b\d{2}[\s\-]?\d{3}[\s\-]?\d{3}\b',  # IRD numbers
        "driver_license": r'\b[A-Z]{2}[\s\-]?\d{6}\b',  # NZ driver license
        "date_of_birth": r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b',
        "bank_account": r'\b\d{2}[\s\-]?\d{4}[\s\-]?\d{7}[\s\-]?\d{2,3}\b',  # NZ bank account
        "passport": r'\b[A-Z]{2}\d{6,7}\b',
    }
    
    def __init__(self):
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }
    
    def detect(self, text: str) -> Dict[str, List[str]]:
        """Detect PII in text"""
        findings = {}
        for name, pattern in self.compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                findings[name] = matches
        return findings
    
    def redact(self, text: str, keep_structure: bool = True) -> str:
        """
        Redact PII from text
        If keep_structure is True, replaces with [REDACTED:TYPE]
        Otherwise replaces with [REDACTED]
        """
        redacted = text
        for name, pattern in self.compiled_patterns.items():
            if keep_structure:
                replacement = f"[REDACTED:{name.upper()}]"
            else:
                replacement = "[REDACTED]"
            redacted = pattern.sub(replacement, redacted)
        return redacted
    
    def redact_names(self, text: str, known_names: List[str]) -> str:
        """Redact specific names (e.g., client name)"""
        for name in known_names:
            # Word boundary matching for full names
            pattern = rf'\b{re.escape(name)}\b'
            text = re.sub(pattern, "[REDACTED:NAME]", text, flags=re.IGNORECASE)
        return text


class ConfidentialDocumentProcessor:
    """
    Processes confidential legal documents securely
    - PII detection and redaction
    - Client isolation
    - Audit logging
    - Encryption at rest
    """
    
    def __init__(self, 
                 storage_dir: str = "./secure_data",
                 encryption_key: Optional[bytes] = None):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.pii_detector = PIIDetector()
        
        # Initialize encryption
        if encryption_key:
            self.cipher = Fernet(encryption_key)
        else:
            # Generate new key (should be saved securely!)
            self.cipher = Fernet(Fernet.generate_key())
        
        # Audit log
        self.audit_log = []
    
    @staticmethod
    def generate_encryption_key(password: str, salt: Optional[bytes] = None) -> bytes:
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def process_document(self, 
                         file_path: str,
                         client_id: str,
                         retention_days: int = 2555,  # 7 years default
                         redact_pii: bool = True,
                         known_names: Optional[List[str]] = None) -> DocumentMetadata:
        """
        Process a confidential document
        
        Args:
            file_path: Path to the document
            client_id: Unique client identifier (hashed)
            retention_days: How long to retain the document
            redact_pii: Whether to redact PII
            known_names: Specific names to redact
        """
        file_path = Path(file_path)
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Read file
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Calculate hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Extract text (placeholder - would use proper PDF/DOCX extraction)
        text_content = self._extract_text(file_path, content)
        
        # Detect PII
        pii_found = self.pii_detector.detect(text_content)
        
        # Redact if requested
        if redact_pii:
            text_content = self.pii_detector.redact(text_content)
            if known_names:
                text_content = self.pii_detector.redact_names(text_content, known_names)
        
        # Create metadata
        metadata = DocumentMetadata(
            doc_id=doc_id,
            original_filename=file_path.name,
            file_hash=file_hash,
            file_size=len(content),
            mime_type=self._detect_mime_type(file_path),
            created_at=datetime.now().isoformat(),
            client_id=hashlib.sha256(client_id.encode()).hexdigest()[:16],  # Hash client ID
            retention_days=retention_days,
            pii_detected=list(pii_found.keys()),
            redacted=redact_pii
        )
        
        # Create client directory
        client_dir = self.storage_dir / metadata.client_id
        client_dir.mkdir(exist_ok=True)
        
        # Save encrypted content
        content_path = client_dir / f"{doc_id}.encrypted"
        encrypted_content = self.cipher.encrypt(content)
        with open(content_path, 'wb') as f:
            f.write(encrypted_content)
        
        # Save processed text
        text_path = client_dir / f"{doc_id}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Save metadata
        meta_path = client_dir / f"{doc_id}.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(metadata.__dict__, f, indent=2)
        
        # Audit log
        self._log_audit("PROCESS", metadata)
        
        return metadata
    
    def _extract_text(self, file_path: Path, content: bytes) -> str:
        """Extract text from document (simplified)"""
        # In production, use:
        # - PyPDF2/pdfplumber for PDFs
        # - python-docx for Word
        # - pytesseract for scanned images
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.txt':
            return content.decode('utf-8', errors='ignore')
        elif suffix == '.pdf':
            # Placeholder - would use actual PDF extraction
            return f"[PDF content: {file_path.name}]"
        elif suffix in ['.doc', '.docx']:
            # Placeholder - would use python-docx
            return f"[DOCX content: {file_path.name}]"
        else:
            return f"[Binary content: {file_path.name}]"
    
    def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type from extension"""
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff'
        }
        return mime_types.get(file_path.suffix.lower(), 'application/octet-stream')
    
    def _log_audit(self, action: str, metadata: DocumentMetadata):
        """Log action for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "doc_id": metadata.doc_id,
            "client_id_hash": metadata.client_id,
            "filename_hash": hashlib.sha256(metadata.original_filename.encode()).hexdigest()[:16]
        }
        self.audit_log.append(log_entry)
        
        # Write to file
        log_path = self.storage_dir / "audit.log"
        with open(log_path, 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps(log_entry) + '\n')
    
    def get_client_documents(self, client_id: str) -> List[DocumentMetadata]:
        """Get all documents for a client"""
        client_hash = hashlib.sha256(client_id.encode()).hexdigest()[:16]
        client_dir = self.storage_dir / client_hash
        
        if not client_dir.exists():
            return []
        
        documents = []
        for meta_file in client_dir.glob("*.json"):
            if meta_file.name == "audit.log":
                continue
            try:
                import json
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                documents.append(DocumentMetadata(**data))
            except Exception as e:
                print(f"Error loading {meta_file}: {e}")
        
        return documents
    
    def retrieve_text(self, doc_id: str, client_id: str) -> Optional[str]:
        """Retrieve processed text for a document"""
        client_hash = hashlib.sha256(client_id.encode()).hexdigest()[:16]
        text_path = self.storage_dir / client_hash / f"{doc_id}.txt"
        
        if text_path.exists():
            with open(text_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def delete_document(self, doc_id: str, client_id: str) -> bool:
        """Securely delete a document"""
        client_hash = hashlib.sha256(client_id.encode()).hexdigest()[:16]
        client_dir = self.storage_dir / client_hash
        
        files_to_delete = [
            client_dir / f"{doc_id}.encrypted",
            client_dir / f"{doc_id}.txt",
            client_dir / f"{doc_id}.json"
        ]
        
        deleted = False
        for file_path in files_to_delete:
            if file_path.exists():
                # Overwrite before delete (basic secure deletion)
                file_size = file_path.stat().st_size
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))
                file_path.unlink()
                deleted = True
        
        return deleted


class SecureSession:
    """
    Context manager for secure document processing sessions
    """
    
    def __init__(self, processor: ConfidentialDocumentProcessor, client_id: str):
        self.processor = processor
        self.client_id = client_id
        self.documents: List[DocumentMetadata] = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up any temporary files
        pass
    
    def ingest(self, file_path: str, **kwargs) -> DocumentMetadata:
        """Ingest a document in this session"""
        metadata = self.processor.process_document(
            file_path=file_path,
            client_id=self.client_id,
            **kwargs
        )
        self.documents.append(metadata)
        return metadata
    
    def get_text(self, doc_id: str) -> Optional[str]:
        """Get text for a document in this session"""
        return self.processor.retrieve_text(doc_id, self.client_id)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Confidential Document Processor")
    parser.add_argument("file", help="Document to process")
    parser.add_argument("--client-id", "-c", required=True, help="Client identifier")
    parser.add_argument("--storage", "-s", default="./secure_data", help="Storage directory")
    parser.add_argument("--no-redact", action="store_true", help="Don't redact PII")
    parser.add_argument("--names", "-n", nargs="+", help="Names to redact")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = ConfidentialDocumentProcessor(storage_dir=args.storage)
    
    # Process document
    metadata = processor.process_document(
        file_path=args.file,
        client_id=args.client_id,
        redact_pii=not args.no_redact,
        known_names=args.names
    )
    
    print(f"\n✓ Document processed")
    print(f"  ID: {metadata.doc_id}")
    print(f"  Original: {metadata.original_filename}")
    print(f"  Size: {metadata.file_size} bytes")
    print(f"  PII detected: {', '.join(metadata.pii_detected) if metadata.pii_detected else 'None'}")
    print(f"  Redacted: {metadata.redacted}")


if __name__ == "__main__":
    main()
