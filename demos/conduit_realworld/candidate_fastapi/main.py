"""
Candidate Microservice in FastAPI (Python):
Modernized, strongly-typed reimplementation of the RealWorld Conduit Backend.
"""

import sqlite3
import os
import re
import time
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DB_FILE = os.path.join(os.path.dirname(__file__), "conduit_candidate.db")

def init_candidate_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT '',
            image TEXT DEFAULT ''
        );

        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            body TEXT NOT NULL,
            favorites_count INTEGER NOT NULL DEFAULT 0,
            author_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE article_tags (
            article_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (article_id, tag)
        );

        CREATE TABLE favorites (
            user_id INTEGER NOT NULL,
            article_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, article_id)
        );

        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        INSERT INTO users (email, username, password, bio, image)
        VALUES ('jake@conduit.io', 'jake', 'jake123', 'I write code', 'https://static.productionready.io/images/smiley-cyrus.jpg');
    """)
    conn.commit()
    conn.close()

init_candidate_db()

app = FastAPI(title="Candidate-Conduit-FastAPI", version="2.0.0")

# ---------------- Pydantic Schemas ----------------

class LoginUser(BaseModel):
    email: str
    password: str

class UserLoginRequest(BaseModel):
    user: LoginUser

class RegisterUser(BaseModel):
    email: str
    username: str
    password: Optional[str] = "default123"

class UserRegisterRequest(BaseModel):
    user: RegisterUser

class ArticleCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    body: Optional[str] = ""
    tagList: Optional[List[str]] = []

class ArticleCreateRequest(BaseModel):
    article: ArticleCreate

class CommentCreate(BaseModel):
    body: str

class CommentCreateRequest(BaseModel):
    comment: CommentCreate

# ---------------- Endpoints ----------------

@app.get("/health")
def health():
    return {"status": "UP", "backend": "fastapi-conduit"}

@app.post("/api/admin/reset")
def reset():
    init_candidate_db()
    return {"status": "RESET_OK"}

@app.post("/api/users/login")
def login(req: UserLoginRequest):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (req.user.email, req.user.password))
    user = cur.fetchone()
    conn.close()

    if not user:
        return JSONResponse(status_code=401, content={"errors": {"email or password": ["is invalid"]}})

    now_ts = int(time.time() * 1000)
    token = f"jwt.fastapi.{user['id']}.{now_ts}"
    return {
        "user": {
            "email": user["email"],
            "token": token,
            "username": user["username"],
            "bio": user["bio"],
            "image": user["image"]
        }
    }

@app.post("/api/users", status_code=201)
def register(req: UserRegisterRequest):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)",
                    (req.user.email, req.user.username, req.user.password))
        user_id = cur.lastrowid
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        return JSONResponse(status_code=422, content={"errors": {"body": [str(e)]}})
    conn.close()

    now_ts = int(time.time() * 1000)
    token = f"jwt.fastapi.{user_id}.{now_ts}"
    return {
        "user": {
            "email": req.user.email,
            "token": token,
            "username": req.user.username,
            "bio": "",
            "image": ""
        }
    }

@app.post("/api/articles", status_code=201)
def create_article(req: ArticleCreateRequest):
    a = req.article
    slug = re.sub(r'[^a-z0-9]+', '-', a.title.lower()).strip('-') if a.title else f"article-{int(time.time()*1000)}"
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO articles (slug, title, description, body, favorites_count, author_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, 1, ?, ?)
    """, (slug, a.title, a.description or "", a.body or "", now_iso, now_iso))
    article_id = cur.lastrowid

    tag_list = a.tagList or []
    for tag in tag_list:
        cur.execute("INSERT INTO article_tags (article_id, tag) VALUES (?, ?)", (article_id, tag))

    conn.commit()
    conn.close()

    return {
        "article": {
            "slug": slug,
            "title": a.title,
            "description": a.description or "",
            "body": a.body or "",
            "tagList": tag_list,
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "favorited": False,
            "favoritesCount": 0,
            "author": {
                "username": "jake",
                "bio": "I write code",
                "image": "https://static.productionready.io/images/smiley-cyrus.jpg",
                "following": False
            }
        }
    }

@app.get("/api/articles/{slug}")
def get_article(slug: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM articles WHERE slug = ?", (slug,))
    art = cur.fetchone()
    if not art:
        conn.close()
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})

    cur.execute("SELECT tag FROM article_tags WHERE article_id = ?", (art["id"],))
    tags = [r["tag"] for r in cur.fetchall()]
    conn.close()

    return {
        "article": {
            "slug": art["slug"],
            "title": art["title"],
            "description": art["description"],
            "body": art["body"],
            "tagList": tags,
            "createdAt": art["created_at"],
            "updatedAt": art["updated_at"],
            "favorited": False,
            "favoritesCount": art["favorites_count"],
            "author": {
                "username": "jake",
                "bio": "I write code",
                "image": "https://static.productionready.io/images/smiley-cyrus.jpg",
                "following": False
            }
        }
    }

@app.post("/api/articles/{slug}/favorite")
def favorite_article(slug: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM articles WHERE slug = ?", (slug,))
    art = cur.fetchone()
    if not art:
        conn.close()
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})

    # Idempotent favorite matching Node.js behavior
    cur.execute("SELECT * FROM favorites WHERE user_id = 1 AND article_id = ?", (art["id"],))
    existing_fav = cur.fetchone()
    new_count = art["favorites_count"]
    if not existing_fav:
        cur.execute("INSERT INTO favorites (user_id, article_id) VALUES (1, ?)", (art["id"],))
        new_count += 1
        cur.execute("UPDATE articles SET favorites_count = ? WHERE id = ?", (new_count, art["id"]))
        conn.commit()
    conn.close()

    return {
        "article": {
            "slug": art["slug"],
            "title": art["title"],
            "description": art["description"],
            "body": art["body"],
            "tagList": [],
            "createdAt": art["created_at"],
            "updatedAt": art["updated_at"],
            "favorited": True,
            "favoritesCount": new_count,
            "author": {"username": "jake", "bio": "I write code", "image": "", "following": False}
        }
    }

@app.post("/api/articles/{slug}/comments", status_code=201)
def add_comment(slug: str, req: CommentCreateRequest):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM articles WHERE slug = ?", (slug,))
    art = cur.fetchone()
    if not art:
        conn.close()
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cur.execute("INSERT INTO comments (article_id, author_id, body, created_at) VALUES (?, 1, ?, ?)",
                (art["id"], req.comment.body, now_iso))
    cid = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "comment": {
            "id": cid,
            "createdAt": now_iso,
            "updatedAt": now_iso,
            "body": req.comment.body,
            "author": {"username": "jake", "bio": "I write code", "image": "", "following": False}
        }
    }
