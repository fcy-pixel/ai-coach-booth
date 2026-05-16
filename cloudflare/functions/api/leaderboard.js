/**
 * GET /api/leaderboard?limit=20
 * 返回排行榜（按總分降序）
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

export async function onRequest({ request, env }) {
  if (request.method === "OPTIONS") {
    return new Response(null, { headers: CORS });
  }
  if (request.method !== "GET") {
    return json({ error: "Method not allowed" }, 405);
  }

  const url   = new URL(request.url);
  const limit = Math.min(Math.max(1, parseInt(url.searchParams.get("limit") ?? "20")), 100);

  try {
    const rows = await env.DB.prepare(`
      SELECT name, class_name, total_score,
             squat_score, balance_score, reaction_score,
             squat_count, balance_time, played_at
      FROM scores
      ORDER BY total_score DESC
      LIMIT ?
    `).bind(limit).all();

    return json({ leaderboard: rows.results });
  } catch (err) {
    return json({ error: "Database error", detail: String(err) }, 500);
  }
}
