// Real-library acceptance. Run after evaluate_real_video_sampling.py; never opens a native window.
const { chromium, expect } = require('../desktop/node_modules/@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const directory = path.resolve(process.argv[2] || 'outputs/sampling-verification');
  const session = JSON.parse(await fs.readFile(path.join(directory, 'panel-session.json'), 'utf8'));
  const report = JSON.parse(await fs.readFile(path.join(directory, 'real-run-v1/report.json'), 'utf8'));
  const manifest = JSON.parse(await fs.readFile(path.join(directory, 'real-queries/manifest.json'), 'utf8'));
  const params = new URLSearchParams(new URL(session.url).hash.slice(1));
  const base = `http://127.0.0.1:${params.get('port')}`;
  const headers = { Authorization: `Bearer ${params.get('token')}` };
  async function api(route, method = 'GET', body) {
    const response = await fetch(base + route, { method, headers: { ...headers, 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    assert(response.ok, `HTTP ${response.status} at ${route}`);
    return response.json();
  }
  const originalMoments = (await api('/moments')).map(m => m.id).sort();
  const query = report.queries.find(q => q.category === 'known_source' && q.held_out && q.results.hybrid_detail.hits.length);
  assert(query, 'No real positive query with detail results');
  const image = manifest.queries.find(q => q.id === query.id);
  const browser = await chromium.launch({ headless: true, args: ['--mute-audio'] });
  let temporaryMoment;
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.setDefaultTimeout(180_000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(session.url);
    await page.getByLabel('Ảnh truy vấn', { exact: true }).setInputFiles(path.join(directory, 'real-queries', image.image));
    await page.getByRole('combobox', { name: 'Cách tìm ảnh' }).selectOption('detail');
    async function search() {
      const pending = page.waitForResponse(r => r.url().endsWith('/search') && r.request().method() === 'POST');
      await page.getByRole('button', { name: 'Tìm kiếm', exact: true }).click();
      const response = await pending;
      assert(response.ok());
      return response.json();
    }
    const detail = await search();
    assert(detail.results.length && detail.verification.mode === 'detail');
    await expect(page.locator('.moment-card').first()).toBeVisible();
    await page.locator('.moment-card').first().click();
    const player = page.locator('video');
    await expect.poll(() => player.evaluate(v => v.readyState), { timeout: 60_000 }).toBeGreaterThanOrEqual(2);
    const playback = await player.evaluate(v => ({ currentTime: v.currentTime, paused: v.paused, width: v.videoWidth }));
    assert(playback.paused && playback.width === 1920);
    assert(Math.abs(playback.currentTime - detail.results[0].peak) < .15);
    await page.screenshot({ path: path.join(directory, 'real-detail-ui.png'), fullPage: true });
    const peak = detail.results[0].peak;
    const start = Math.max(0, Math.min(peak - 1, detail.results[0].duration - 2));
    await page.getByLabel('Bắt đầu (giây)').fill(String(start));
    await page.getByLabel('Kết thúc (giây)').fill(String(start + 2));
    const label = `Kiểm thử lấy mẫu ${Date.now()}`;
    await page.getByLabel('Tên khoảnh khắc').fill(label);
    const saving = page.waitForResponse(r => r.url().endsWith('/moments') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Lưu khoảnh khắc', exact: true }).click();
    const saved = await saving;
    assert(saved.ok());
    temporaryMoment = (await saved.json()).id;
    assert((await api('/moments')).some(m => m.id === temporaryMoment && m.label === label));
    const range = await fetch(`${base}/media/${detail.results[0].video_id}`, { headers: { ...headers, Range: 'bytes=0-99' } });
    assert.equal(range.status, 206);
    assert.equal((await range.arrayBuffer()).byteLength, 100);
    const clip = path.join(directory, `real-acceptance-${Date.now()}.mp4`);
    await api('/export', 'POST', { video_id: detail.results[0].video_id, start, end: start + 2, path: clip });
    assert((await fs.stat(clip)).size > 1000);
    await page.getByRole('button', { name: 'Đóng chi tiết' }).click();
    await page.getByRole('combobox', { name: 'Cách tìm ảnh' }).selectOption('similar');
    const similar = await search();
    assert(similar.results.length);
    await page.getByRole('button', { name: 'Bỏ ảnh truy vấn' }).click();
    await page.getByRole('textbox', { name: 'Mô tả cảnh cần tìm' }).fill('màn hình bỏ phiếu cho người chơi');
    const text = await search();
    assert(text.results.length);
    await page.screenshot({ path: path.join(directory, 'real-text-ui.png'), fullPage: true });
    await page.setViewportSize({ width: 920, height: 700 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    await api(`/moments/${temporaryMoment}`, 'DELETE');
    temporaryMoment = undefined;
    assert.deepEqual((await api('/moments')).map(m => m.id).sort(), originalMoments);
    await fs.writeFile(path.join(directory, 'real-ui-report.json'), JSON.stringify({ passed: true,
      query_id: query.id, indexed_frames: detail.indexed_frames, detail_results: detail.results.length,
      detail_elapsed_ms: detail.elapsed_ms, similar_results: similar.results.length,
      text_results: text.results.length, playback, range_status: 206,
      saved_and_removed_temporary_moment: true, preserved_moments: originalMoments.length,
      export_seconds_requested: 2, exported_file: path.basename(clip), no_horizontal_overflow: true,
      page_errors: errors, native_window_opened: false }, null, 2));
    console.log('Real image modes, text, silent seek, save/remove, range and clip export: PASSED');
  } finally {
    if (temporaryMoment) await api(`/moments/${temporaryMoment}`, 'DELETE');
    await browser.close();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
