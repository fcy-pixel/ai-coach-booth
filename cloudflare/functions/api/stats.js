/**
 * GET /api/stats
 * 返回全場統計數據
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

  try {
    const stats = await env.DB.prepare(`
      SELECT
        COUNT(*)                    AS total_players,
        ROUND(AVG(total_score))     AS avg_score,
        MAX(total_score)            AS top_score,
        ROUND(AVG(squat_count))     AS avg_squats,
        ROUND(AVG(balance_time), 1) AS avg_balance
      FROM scores
    `).first();

    return json({ stats });
  } catch (err) {
    return json({ error: "Database error", detail: String(err) }, 500);
  }
}
