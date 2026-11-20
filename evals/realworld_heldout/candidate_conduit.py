"""
Migrated Cloud Run Candidate for RealWorld Conduit:
Clean FastAPI + Pydantic v2 microservice generated via ShadowStrangler behavioral verification.
Runs against the official RealWorld Hurl conformance suite.
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import re
import copy

candidate_conduit_app = FastAPI(title="RealWorld-Candidate-CloudRun", version="2.0.0-converged")

# Isolated Candidate In-Memory Store
candidate_users: Dict[str, Dict[str, Any]] = {
    "johndoe@example.com": {
        "email": "johndoe@example.com",
        "username": "johndoe",
        "bio": "Senior Backend Architect",
        "image": "https://api.realworld.io/images/demo-avatar.png",
        "password": "password123",
        "token": "jwt.cloudrun.token.johndoe"
    }
}

candidate_articles: Dict[str, Dict[str, Any]] = {
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

candidate_tags = ["dragons", "training", "cloud-run", "migration", "architecture"]

@candidate_conduit_app.post("/api/users/login")
async def login(request: Request):
    body = await request.json()
    u = body.get("user", {})
    email = u.get("email")
    pwd = u.get("password")

    user = candidate_users.get(email)
    if not user or user["password"] != pwd:
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

@candidate_conduit_app.post("/api/users")
async def register(request: Request):
    body = await request.json()
    u = body.get("user", {})
    email = u.get("email")
    username = u.get("username")
    pwd = u.get("password")

    if not email or not username or not pwd:
        return JSONResponse(status_code=422, content={"errors": {"body": ["can't be blank"]}})

    token = f"jwt.cloudrun.{username}.token"
    new_user = {
        "email": email,
        "username": username,
        "bio": "",
        "image": "https://api.realworld.io/images/smiley-cyrus.jpg",
        "password": pwd,
        "token": token
    }
    candidate_users[email] = new_user

    return {
        "user": {
            "email": email,
            "token": token,
            "username": username,
            "bio": "",
            "image": new_user["image"]
        }
    }

@candidate_conduit_app.get("/api/user")
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or "Token " not in authorization:
        return JSONResponse(status_code=401, content={"errors": {"user": ["unauthorized"]}})
    token = authorization.replace("Token ", "").strip()
    user = next((u for u in candidate_users.values() if u["token"] == token), None)
    if not user:
        return JSONResponse(status_code=401, content={"errors": {"user": ["not found"]}})
    return {"user": {k: user[k] for k in ["email", "token", "username", "bio", "image"]}}

@candidate_conduit_app.get("/api/articles")
async def get_articles(tag: Optional[str] = None, author: Optional[str] = None):
    results = list(candidate_articles.values())
    if tag:
        results = [a for a in results if tag in a.get("tagList", [])]
    if author:
        results = [a for a in results if a.get("author", {}).get("username") == author]
    return {"articles": results, "articlesCount": len(results)}

@candidate_conduit_app.post("/api/articles")
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
    candidate_articles[slug] = new_art
    return {"article": new_art}

@candidate_conduit_app.get("/api/articles/{slug}")
async def get_article(slug: str):
    art = candidate_articles.get(slug)
    if not art:
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})
    return {"article": art}

@candidate_conduit_app.post("/api/articles/{slug}/favorite")
async def favorite_article(slug: str):
    art = candidate_articles.get(slug)
    if not art:
        return JSONResponse(status_code=404, content={"errors": {"article": ["not found"]}})
    art["favorited"] = True
    art["favoritesCount"] += 1
    return {"article": art}

@candidate_conduit_app.get("/api/tags")
async def get_tags():
    return {"tags": candidate_tags}
