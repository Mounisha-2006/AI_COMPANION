from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)  # 1-indexed page number from PDF
    chunk_index = Column(Integer, nullable=False)  # Sequence index in the document
    embedding = Column(JSON, nullable=True)         # Vector embedding as float array
    chunk_type = Column(String(50), default="text", nullable=False)  # text, table, diagram, chart, figure, image, scanned_page
    metadata_json = Column(JSON, nullable=True)     # structured visual data, table rows, figure details
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    material = relationship("Material", back_populates="chunks")
    project = relationship("Project", back_populates="chunks")
