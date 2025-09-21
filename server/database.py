from typing import List, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, Relationship

DATABASE_URL = "sqlite:///weblog.db"

class ArticleBlockLink(SQLModel, table=True):
    article_id: Optional[int] = Field(default=None, foreign_key="article.id", primary_key=True)
    block_id: Optional[int] = Field(default=None, foreign_key="block.id", primary_key=True)
    order: int = Field(index=True) # Add order to the link model

class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str

    blocks: List["Block"] = Relationship(back_populates="articles", link_model=ArticleBlockLink)

class Block(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    block_type: str
    content: str
    # order: int = Field(index=True) # Removed from Block, moved to ArticleBlockLink
    # article_id: Optional[int] = Field(default=None, foreign_key="article.id") # Removed

    articles: List["Article"] = Relationship(back_populates="blocks", link_model=ArticleBlockLink)

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
