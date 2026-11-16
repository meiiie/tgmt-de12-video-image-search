const { chromium, expect } = require('../desktop/node_modules/@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const output = path.resolve(process.argv[2] || 'outputs/sampling-verification');
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:1420/sampling-real-20261102/');
    await expect(page.locator('#query option')).toHaveCount(24);
    const queries = await page.locator('#query option').evaluateAll(nodes => nodes.map(n => n.value));
    const methods = await page.locator('#method option').evaluateAll(nodes => nodes.map(n => n.value));
    let states = 0;
    for (const query of queries) {
      await page.locator('#query').selectOption(query);
      for (const method of methods) {
        await page.locator('#method').selectOption(method);
        await page.locator('img').evaluateAll(async images => {
          for (const image of images) image.loading = 'eager';
          await Promise.all(images.map(image => image.decode()));
        });
        states++;
      }
    }
    const report = await page.evaluate(async () => (await fetch('review.json')).json());
    const missed = report.queries.find(q => q.category === 'known_source' && q.held_out &&
      !q.results.hybrid_detail.hits.slice(0, 5).some(h => Math.abs(h.peak_t - q.source_t) <= 3));
    for (const [name, query] of [['overview', queries[0]], ['miss', missed?.id], ['foreign', queries.at(-1)]]) {
      if (!query) continue;
      await page.locator('#query').selectOption(query);
      await page.locator('#method').selectOption('hybrid_detail');
      await page.screenshot({ path: path.join(output, `review-${name}.png`), fullPage: true });
    }
    await page.setViewportSize({ width: 920, height: 700 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    await fs.writeFile(path.join(output, 'review-ui-report.json'), JSON.stringify({ passed: true, states,
      all_images_decoded: true, page_errors: errors, no_horizontal_overflow: true }, null, 2));
    console.log(`Review page: ${states} query/mode states and images verified`);
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
