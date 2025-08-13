from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, declarative_base
from Database.Database import Base

# NewsArticle
class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    url = Column(Text)
    title = Column(Text)
    date = Column(String(20))         # ISO date string like "2025-07-16"
    category = Column(String(100))    # e.g., "en.toram.jp"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sections = relationship("NewsSection", back_populates="article", cascade="all, delete-orphan")
    images = relationship("NewsImage", back_populates="article", cascade="all, delete-orphan")

# NewsSection
class NewsSection(Base):
    __tablename__ = "news_sections"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"))
    title = Column(Text)
    markdown = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("NewsArticle", back_populates="sections")
    images = relationship("NewsImage", back_populates="section", cascade="all, delete-orphan")

# NewsImage
class NewsImage(Base):
    __tablename__ = "news_images"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"))
    section_id = Column(Integer, ForeignKey("news_sections.id"), nullable=True)
    url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("NewsArticle", back_populates="images")
    section = relationship("NewsSection", back_populates="images")
