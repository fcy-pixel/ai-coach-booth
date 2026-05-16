/**
 * POST /api/score
 * 提交一位玩家的分數到 D1 資料庫
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

async function ensureTable(db) {
  await db.prepare("CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER, class_name TEXT, squat_score INTEGER DEFAULT 0, balance_score INTEGER DEFAULT 0, reaction_score INTEGER DEFAULT 0, total_score INTEGER DEFAULT 0, squat_count INTEGER DEFAULT 0, squat_accuracy INTEGER DEFAULT 0, balance_time REAL DEFAULT 0, reaction_time REAL DEFAULT 0, played_at TEXT)").run();
}

export async function onRequest({ request, env }) {
  if (request.method === "OPTIONS") {
    return new Response(null, { headers: CORS });
  }
  if (request.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  const {
    name,
    age,
    class_name,
    squat_score    = 0,
    balance_score  = 0,
    reaction_score = 0,
    squat_count    = 0,
    squat_accuracy = 0,
    balance_time   = 0,
    reaction_time  = 0,
  } = body;

  if (!name || String(name).trim() === "") {
    return json({ error: "name is required" }, 400);
  }

  // Sanitize inputs
  const safeName      = String(name).trim().slice(0, 50);
  const safeClass     = class_name ? String(class_name).trim().slice(0, 20) : null;
  const safeAge       = Number.isInteger(Number(age)) ? Math.max(0, Math.min(120, Number(age))) : null;
  const total_score   = Math.round((Number(squat_score) + Number(balance_score) + Number(reaction_score)) / 3);
  const played_at     = new Date().toISOString();

  try {
    await ensureTable(env.DB);

    const result = await env.DB.prepare(`
      INSERT INTO scores
        (name, age, class_name, squat_score, balance_score, reaction_score,
         total_score, squat_count, squat_accuracy, balance_time, reaction_time, played_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      safeName, safeAge, safeClass,
      Number(squat_score), Number(balance_score), Number(reaction_score),
      total_score,
      Number(squat_count), Number(squat_accuracy),
      Number(balance_time), Number(reaction_time),
      played_at
    ).run();

    const rankRow  = await env.DB.prepare(
      "SELECT COUNT(*)+1 AS rank FROM scores WHERE total_score > ?"
    ).bind(total_score).first();

    const totalRow = await env.DB.prepare(
      "SELECT COUNT(*) AS total FROM scores"
    ).first();

    return json({
      success:       true,
      id:            result.meta.last_row_id,
      total_score,
      rank:          rankRow?.rank   ?? 1,
      total_players: totalRow?.total ?? 1,
    });
  } catch (err) {
    return json({ error: "Database error", detail: String(err) }, 500);
  }
}
