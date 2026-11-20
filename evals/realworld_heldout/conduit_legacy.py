"""
RealWorld Conduit Reference Legacy Backend (Held-Out Benchmark):
Implements the third-party RealWorld Medium-clone backend specification (Express/Spring Boot style)
used as an unbiased, external ground-truth conformance target.
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import time
import os
import re

legacy_conduit_app = FastAPI(title="RealWorld-Legacy-Conduit", version="1.0.0-legacy")

# In-memory storage for RealWorld entities
users_db: Dict[str, Dict[str, Any]] = {
    "johndoe@example.com": {
        "email": "johndoe@example.com",
        "username": "johndoe",
        "bio": "Senior Backend Architect",
        "image": "https://api.realworld.io/images/demo-avatar.png",
        "password": "password123",
        "token": "jwt.legacy.header.payload.johndoe"
    }
}

articles_db: Dict[str, Dict[str, Any]] = {
    "how-to-train-your-dragon": {
        "slug": "how-to-train-your-dragon",
        "title": "How to train your dragon",
        "description": "Ever wonder how?",
        "body": "It takes a dragon whisperer and high resilience.",
        "tagList": ["dragons", "training"],
        "createdAt": "2026-11-20T10:00:00.000Z",
        "updatedAt": "2026-11-20T10:00:00.000Z",
        "favorited": False,
        "favoritesCount": 42,
        "author": {
            "username": "johndoe",
            "bio": "Senior Backend Architect",
            "image": "https://api.realworld.io/images/demo-avatar.png",
            "following": False
        }
    }
}

comments_db: Dict[str, List[Dict[str, Any]]] = {}
tags_db = ["dragons", "training", "cloud-run", "migration", "architecture"]

@legacy_conduit_app.post("/api/users/login")
async def login(request: Request):
    body = await request.json()
    user_data = body.get("user", {})
    email = user_data.get("email")
    password = user_data.get("password")

    user = users_db.get(email)
    if not user or user["password"] != password:
        return JSONResponse(status_code=422, content={"errors": {"email or password": ["is invalid"]}})

    return {
        "user": {
            "email": user["email"],
            "token": user["token"],
            "username": user["username"],
            "bio": user["bio"],
            "image": user["image"]
        }
    }

@legacy_conduit_app.post("/api/users")
async def register(request: Request):
    body = await request.json()
    u = body.get("user", {})
    email = u.get("email")
    username = u.get("username")
    password = u.get("password")

    if not email or not username or not password:
        return JSONResponse(status_code=422, content={"errors": {"body": ["can't be blank"]}})

    token = f"jwt.legacy.{username}.token"
    new_user = {
        "email": email,
        "username": username,
        "bio": "",
        "image": "https://api.realworld.io/images/smiley-cyrus.jpg",
        "password": password,
        "token": token
    }
    users_db[email] = new_user

    return {
        "user": {
            "email": email,
            "token": token,
            "username": username,
            "bio": "",
            "image": new_user["image"]
        }
    }

@legacy_conduit_app.get("/api/user")
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or "Token " not in authorization:
        return JSONResponse(status_code=401, content={"errors": {"user": ["unauthorized"]}})
    token = authorization.replace("Token ", "").strip()
    user = next((u for u in users_db.values() if u["token"] == token), None)
    if not user:
        return JSONResponse(status_code=401, content={"errors": {"user": ["not found"]}})
    return {"user": {k: user[k] for k in ["email", "token", "username", "bio", "image"]}}

@legacy_conduit_app.get("/api/articles")
async def get_articles(tag: Optional[str] = None, author: Optional[str] = None):
    results = list(articles_db.values())
    if tag:
        results = [a for a in results if tag in a.get("tagList", [])]
    if author:
        results = [a for a in results if a.get("author", {}).get("username") == author]
    return {"articles": results, "articlesCount": len(results)}

@legacy_conduit_app.post("/api/articles")
async def create_article(request: Request, authorization: Optional[str] = Header(None)):
    body = await request.json()
    art = body.get("article", {})
    title = art.get("title", "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")

    new_art = {
        "slug": slug,
        "title": title,
        "description": art.get("description", ""),
        "body": art.get("body", ""),
        "tagList": art.get("tagList", []),
        "createdAt": "2026-11-20T12:00:00.000Z",
        "updatedAt": "2026-11-20T12:00:00.000Z",
        "favorited": False,
        "favoritesCount": 0,
        "author": {
            "username": "johndoe",
            "bio": "Senior Backend Architect",
            "image": "https://api.realworld.io/images/demo-avatar.png",
            "following": False
        }
    }
    articles_db[slug] = new_art
    return {"article": new_art}

@legacy_conduit_app.get("/api/articles/{slug}")
async def get_article(slug: str):
    art = articles_db.get(slug)
    if not art:
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})
    return {"article": art}

@legacy_conduit_app.post("/api/articles/{slug}/favorite")
async def favorite_article(slug: str):
    art = articles_db.get(slug)
    if not art:
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})
    art["favorited"] = True
    art["favoritesCount"] += 1
    return {"article": art}

@legacy_conduit_app.get("/api/tags")
async def get_tags():
    return {"tags": tags_db}
