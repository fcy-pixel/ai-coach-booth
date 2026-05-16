/**
 * AI Coach Leaderboard - Cloudflare Worker
 * Routes:
 *   POST /api/score      - submit a player score
 *   GET  /api/leaderboard - get top scores
 *   GET  /api/stats       - get overall stats
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

async function initDB(db) {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS scores (
      id        INTEGER PRIMARY KEY AUTOINCREMENT,
      name      TEXT    NOT NULL,
      age       INTEGER,
      class_name TEXT,
      squat_score   INTEGER DEFAULT 0,
      balance_score INTEGER DEFAULT 0,
      reaction_score INTEGER DEFAULT 0,
      total_score   INTEGER DEFAULT 0,
      squat_count   INTEGER DEFAULT 0,
      squat_accuracy INTEGER DEFAULT 0,
      balance_time  REAL DEFAULT 0,
      reaction_time REAL DEFAULT 0,
      played_at TEXT
    )
  `);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }

    // Initialize DB on first use
    try {
      await initDB(env.DB);
    } catch (e) {
      // Table may already exist, ignore
    }

    // ── POST /api/score ──────────────────────────────
    if (request.method === "POST" && url.pathname === "/api/score") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "Invalid JSON" }, 400);
      }

      const {
        name, age, class_name,
        squat_score = 0, balance_score = 0, reaction_score = 0,
        squat_count = 0, squat_accuracy = 0,
        balance_time = 0, reaction_time = 0,
      } = body;

      if (!name) return json({ error: "name is required" }, 400);

      const total_score = Math.round((squat_score + balance_score + reaction_score) / 3);
      const played_at = new Date().toISOString();

      const result = await env.DB.prepare(`
        INSERT INTO scores
          (name, age, class_name, squat_score, balance_score, reaction_score,
           total_score, squat_count, squat_accuracy, balance_time, reaction_time, played_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        name, age ?? null, class_name ?? null,
        squat_score, balance_score, reaction_score,
        total_score, squat_count, squat_accuracy,
        balance_time, reaction_time, played_at
      ).run();

      // Get rank
      const rankRow = await env.DB.prepare(
        "SELECT COUNT(*)+1 as rank FROM scores WHERE total_score > ?"
      ).bind(total_score).first();

      const totalRow = await env.DB.prepare(
        "SELECT COUNT(*) as total FROM scores"
      ).first();

      return json({
        success: true,
        id: result.meta.last_row_id,
        total_score,
        rank: rankRow?.rank ?? 1,
        total_players: totalRow?.total ?? 1,
      });
    }

    // ── GET /api/leaderboard ─────────────────────────
    if (request.method === "GET" && url.pathname === "/api/leaderboard") {
      const limit = parseInt(url.searchParams.get("limit") ?? "20");
      const rows = await env.DB.prepare(`
        SELECT name, class_name, total_score, squat_score, balance_score,
               reaction_score, squat_count, balance_time, played_at
        FROM scores
        ORDER BY total_score DESC
        LIMIT ?
      `).bind(Math.min(limit, 100)).all();

      return json({ leaderboard: rows.results });
    }

    // ── GET /api/stats ───────────────────────────────
    if (request.method === "GET" && url.pathname === "/api/stats") {
      const stats = await env.DB.prepare(`
        SELECT
          COUNT(*)           AS total_players,
          ROUND(AVG(total_score))  AS avg_score,
          MAX(total_score)   AS top_score,
          ROUND(AVG(squat_count))  AS avg_squats,
          ROUND(AVG(balance_time), 1) AS avg_balance
        FROM scores
      `).first();

      return json({ stats });
    }

    // ── Static assets (Cloudflare Assets will handle /) ──
    return new Response("Not found", { status: 404 });
  },
};
