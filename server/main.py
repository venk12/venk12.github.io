from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from markdown import markdown

from database import engine, Article, Block, ArticleBlockLink, create_db_and_tables

app = FastAPI()
templates = Jinja2Templates(directory="templates")

templates.env.filters["markdown"] = markdown

# Dependency to get the database session
def get_db():
    with Session(engine) as session:
        yield session

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    create_db_and_tables()
    # Add some dummy data if the database is empty
    with Session(engine) as db:
        if not db.exec(select(Article)).first():
            article1 = Article(title="My First Article")
            block1_1 = Block(block_type="text", content="This is the first paragraph of the first article.")
            block1_2 = Block(block_type="text", content="some more content")
            block1_3 = Block(block_type="markdown", content="## Markdown Section\n\n* List item 1\n* List item 2")

            # New shared block
            shared_block = Block(block_type="text", content="This block is shared between Article 1 and Article 2.")

            db.add(article1)
            db.add(block1_1)
            db.add(block1_2)
            db.add(block1_3)
            db.add(shared_block) # Add shared block to the database

            db.commit()
            db.refresh(article1)
            db.refresh(block1_1)
            db.refresh(block1_2)
            db.refresh(block1_3)
            db.refresh(shared_block)

            # Link blocks to article1
            db.add(ArticleBlockLink(article_id=article1.id, block_id=block1_1.id, order=0))
            db.add(ArticleBlockLink(article_id=article1.id, block_id=block1_2.id, order=1))
            db.add(ArticleBlockLink(article_id=article1.id, block_id=shared_block.id, order=2)) # Link shared block to article1
            db.add(ArticleBlockLink(article_id=article1.id, block_id=block1_3.id, order=3))

            article2 = Article(title="Another Article")
            block2_1 = Block(block_type="text", content="Content for the second article.")
            db.add(article2)
            db.add(block2_1)
            db.commit()
            db.refresh(article2)
            db.refresh(block2_1)

            # Link blocks to article2, including the shared block
            db.add(ArticleBlockLink(article_id=article2.id, block_id=block2_1.id, order=0))
            db.add(ArticleBlockLink(article_id=article2.id, block_id=shared_block.id, order=1)) # Link shared block to article2

            db.commit()
            db.refresh(article1)
            db.refresh(article2)


@app.get("/", response_class=PlainTextResponse)
def index():                                     
    return "The API is running!"                 

@app.get("/articles", response_class=HTMLResponse)
def get_articles(request: Request, db: Session = Depends(get_db)):
    articles = db.exec(select(Article)).all()
    return templates.TemplateResponse("articles.html", {"request": request, "articles": articles})

@app.get("/articles/{article_id}", response_class=HTMLResponse)
def get_article_details(request: Request, article_id: int, db: Session = Depends(get_db)):
    # Fetch article and its associated blocks through the link model, sorted by order
    article = db.get(Article, article_id)

    if not article:
        return PlainTextResponse("Article not found", status_code=404)

    # Manually fetch blocks and their order using the ArticleBlockLink
    article_blocks_links = db.exec(
        select(ArticleBlockLink).where(ArticleBlockLink.article_id == article_id).order_by(ArticleBlockLink.order)
    ).all()

    blocks_with_order = []
    for link in article_blocks_links:
        block = db.get(Block, link.block_id)
        if block:
            blocks_with_order.append(block)
    article.blocks = blocks_with_order
    return templates.TemplateResponse("article-details.html", {"request": request, "article": article})

@app.get("/articles/{article_id}/edit", response_class=HTMLResponse)
def edit_article_form(request: Request, article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        return PlainTextResponse("Article not found", status_code=404)

    article_blocks_links = db.exec(
        select(ArticleBlockLink).where(ArticleBlockLink.article_id == article_id).order_by(ArticleBlockLink.order)
    ).all()
    blocks_with_order = []
    for link in article_blocks_links:
        block = db.get(Block, link.block_id)
        if block:
            blocks_with_order.append(block)
    article.blocks = blocks_with_order
    return templates.TemplateResponse("article-edit.html", {"request": request, "article": article})

@app.post("/articles/{article_id}/edit", response_class=RedirectResponse)
async def update_article(request: Request, article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    form_data = await request.form()

    # Update article title
    article.title = form_data.get("title")
    db.add(article)
    db.commit()
    db.refresh(article)

    # Update existing blocks and handle new/deleted blocks
    article_blocks_links = db.exec(
        select(ArticleBlockLink).where(ArticleBlockLink.article_id == article_id).order_by(ArticleBlockLink.order)
    ).all()

    for link in article_blocks_links:
        block = db.get(Block, link.block_id)
        if block:
            form_field_name = f"block_{link.order}"
            new_content = form_data.get(form_field_name)
            if new_content is not None:  # Check if the block was present in the form
                block.content = new_content
                db.add(block)
                db.commit()
                db.refresh(block)

    return RedirectResponse(url=f"/articles/{article_id}", status_code=302)