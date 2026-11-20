// Conduit RealWorld Backend in Node.js (Zero external dependencies, uses native node:sqlite)
const http = require('node:http');
const { DatabaseSync } = require('node:sqlite');
const fs = require('node:fs');
const path = require('node:path');

const PORT = 3001;
const DB_FILE = path.join(__dirname, 'conduit_node.db');

let db;

function initDb() {
  if (fs.existsSync(DB_FILE)) {
    fs.unlinkSync(DB_FILE);
  }
  db = new DatabaseSync(DB_FILE);

  db.exec(`
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
  `);
}

initDb();

function sendJson(res, statusCode, data) {
  const jsonStr = JSON.stringify(data);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(jsonStr)
  });
  res.end(jsonStr);
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        resolve({});
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;
  const method = req.method.toUpperCase();

  // Health
  if (method === 'GET' && pathname === '/health') {
    return sendJson(res, 200, { status: 'UP', backend: 'node-conduit' });
  }

  // Admin Reset
  if (method === 'POST' && pathname === '/api/admin/reset') {
    initDb();
    return sendJson(res, 200, { status: 'RESET_OK' });
  }

  // 1. POST /api/users/login
  if (method === 'POST' && pathname === '/api/users/login') {
    const body = await parseBody(req);
    const uData = body.user || {};
    const query = db.prepare('SELECT * FROM users WHERE email = ? AND password = ?');
    const user = query.get(uData.email || '', uData.password || '');
    if (!user) {
      return sendJson(res, 401, { errors: { 'email or password': ['is invalid'] } });
    }
    const token = `jwt.node.${user.id}.${Date.now()}`;
    return sendJson(res, 200, {
      user: {
        email: user.email,
        token: token,
        username: user.username,
        bio: user.bio,
        image: user.image
      }
    });
  }

  // 2. POST /api/users (Registration)
  if (method === 'POST' && pathname === '/api/users') {
    const body = await parseBody(req);
    const u = body.user || {};
    try {
      const insert = db.prepare('INSERT INTO users (email, username, password) VALUES (?, ?, ?)');
      const result = insert.run(u.email, u.username, u.password || 'default123');
      const token = `jwt.node.${result.lastInsertRowid}.${Date.now()}`;
      return sendJson(res, 201, {
        user: {
          email: u.email,
          token: token,
          username: u.username,
          bio: '',
          image: ''
        }
      });
    } catch (e) {
      return sendJson(res, 422, { errors: { body: [e.message] } });
    }
  }

  // 3. POST /api/articles (Create Article)
  if (method === 'POST' && pathname === '/api/articles') {
    const body = await parseBody(req);
    const a = body.article || {};
    const slug = a.title ? a.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') : `article-${Date.now()}`;
    const nowIso = new Date().toISOString();

    const insert = db.prepare(`
      INSERT INTO articles (slug, title, description, body, favorites_count, author_id, created_at, updated_at)
      VALUES (?, ?, ?, ?, 0, 1, ?, ?)
    `);
    const result = insert.run(slug, a.title, a.description || '', a.body || '', nowIso, nowIso);
    const articleId = result.lastInsertRowid;

    const tagList = Array.isArray(a.tagList) ? a.tagList : [];
    const insertTag = db.prepare('INSERT INTO article_tags (article_id, tag) VALUES (?, ?)');
    for (const tag of tagList) {
      insertTag.run(articleId, tag);
    }

    return sendJson(res, 201, {
      article: {
        slug: slug,
        title: a.title,
        description: a.description || '',
        body: a.body || '',
        tagList: tagList,
        createdAt: nowIso,
        updatedAt: nowIso,
        favorited: false,
        favoritesCount: 0,
        author: {
          username: 'jake',
          bio: 'I write code',
          image: 'https://static.productionready.io/images/smiley-cyrus.jpg',
          following: false
        }
      }
    });
  }

  // 4. GET /api/articles/:slug
  const articleGetMatch = pathname.match(/^\/api\/articles\/([a-zA-Z0-9\-]+)$/);
  if (method === 'GET' && articleGetMatch) {
    const slug = articleGetMatch[1];
    const art = db.prepare('SELECT * FROM articles WHERE slug = ?').get(slug);
    if (!art) {
      return sendJson(res, 404, { errors: { article: ['not found'] } });
    }
    const tags = db.prepare('SELECT tag FROM article_tags WHERE article_id = ?').all(art.id).map(r => r.tag);
    return sendJson(res, 200, {
      article: {
        slug: art.slug,
        title: art.title,
        description: art.description,
        body: art.body,
        tagList: tags,
        createdAt: art.created_at,
        updatedAt: art.updated_at,
        favorited: false,
        favoritesCount: art.favorites_count,
        author: {
          username: 'jake',
          bio: 'I write code',
          image: 'https://static.productionready.io/images/smiley-cyrus.jpg',
          following: false
        }
      }
    });
  }

  // 5. POST /api/articles/:slug/favorite
  const favoriteMatch = pathname.match(/^\/api\/articles\/([a-zA-Z0-9\-]+)\/favorite$/);
  if (method === 'POST' && favoriteMatch) {
    const slug = favoriteMatch[1];
    const art = db.prepare('SELECT * FROM articles WHERE slug = ?').get(slug);
    if (!art) {
      return sendJson(res, 404, { errors: { article: ['not found'] } });
    }

    // Node quirk: Idempotent favorite insert! Ignores duplicates without crashing
    const existingFav = db.prepare('SELECT * FROM favorites WHERE user_id = 1 AND article_id = ?').get(art.id);
    let newCount = art.favorites_count;
    if (!existingFav) {
      db.prepare('INSERT INTO favorites (user_id, article_id) VALUES (1, ?)').run(art.id);
      newCount += 1;
      db.prepare('UPDATE articles SET favorites_count = ? WHERE id = ?').run(newCount, art.id);
    }

    return sendJson(res, 200, {
      article: {
        slug: art.slug,
        title: art.title,
        description: art.description,
        body: art.body,
        tagList: [],
        createdAt: art.created_at,
        updatedAt: art.updated_at,
        favorited: true,
        favoritesCount: newCount,
        author: { username: 'jake', bio: 'I write code', image: '', following: false }
      }
    });
  }

  // 6. POST /api/articles/:slug/comments
  const commentMatch = pathname.match(/^\/api\/articles\/([a-zA-Z0-9\-]+)\/comments$/);
  if (method === 'POST' && commentMatch) {
    const slug = commentMatch[1];
    const body = await parseBody(req);
    const cData = body.comment || {};
    const art = db.prepare('SELECT * FROM articles WHERE slug = ?').get(slug);
    if (!art) {
      return sendJson(res, 404, { errors: { article: ['not found'] } });
    }

    const nowIso = new Date().toISOString();
    const insert = db.prepare('INSERT INTO comments (article_id, author_id, body, created_at) VALUES (?, 1, ?, ?)');
    const resRow = insert.run(art.id, cData.body || '', nowIso);

    return sendJson(res, 201, {
      comment: {
        id: resRow.lastInsertRowid,
        createdAt: nowIso,
        updatedAt: nowIso,
        body: cData.body,
        author: { username: 'jake', bio: 'I write code', image: '', following: false }
      }
    });
  }

  sendJson(res, 404, { error: 'Route not found' });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`Node.js Conduit RealWorld backend running on http://127.0.0.1:${PORT}`);
});
