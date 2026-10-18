export async function api(path, method = 'GET', payload) {
  const response = await fetch(`/api/v1${path}`, {
    method, headers: {'Content-Type': 'application/json'},
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* Use the fallback below. */ }
    if (Array.isArray(detail)) detail = detail.map(e => `${e.loc.slice(1).join(' ')}: ${e.msg}`).join('. ');
    throw new Error(detail || `Request failed (${response.status}). Please retry.`);
  }
  return response.json();
}

export const date = value => new Date(value).toLocaleString(undefined, {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
export const actionLabel = action => ({profile_saved:'Profile confirmed', discovery_saved:'Contact research saved', outbox_draft:'Draft saved', outbox_simulated:'Simulation recorded', draft_updated:'Draft updated'}[action] || action);
