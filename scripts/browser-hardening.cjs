// Read-only browser checks against the preserved demo and an isolated evidence-gap graph.
// Start scripts/serve-evidence-gap.py first. No API responses are mocked.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const results = [];
    for (const [scenario, url, status] of [
      ['preserved-demo', 'http://127.0.0.1:8000', 'review_required'],
      ['expired-security-evidence', 'http://127.0.0.1:8001', 'unknown'],
    ]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
      const page = await context.newPage();
      const errors = [], violations = [], responses = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('response', r => { if (r.url().includes('/api/')) responses.push({path: new URL(r.url()).pathname, status: r.status()}); });
      await page.addInitScript(() => {
        window.__cspViolations = [];
        document.addEventListener('securitypolicyviolation', e => window.__cspViolations.push({ directive: e.violatedDirective, blocked: e.blockedURI }));
      });
      const response = await page.goto(url);
      assert(response.headers()['content-security-policy'].includes("script-src 'self'"));
      await page.getByRole('heading', { name: 'Good decisions start with context.' }).waitFor();
      await page.getByText('FalkorDB connected').waitFor();
      const before = await (await page.request.get(url + '/api/overview')).json();
      const ready = await (await page.request.get(url + '/api/readiness')).json();
      assert.equal(ready.status, status);
      await page.locator('.readiness-gaps summary').click();
      await page.getByText('Assessment within recorded traversal bounds', { exact: false }).waitFor();
      if (status === 'unknown') {
        await page.getByText('The graph lacks sufficient current, complete evidence to assess launch readiness.', { exact: true }).waitFor();
        assert(ready.issues.some(i => i.code === 'missing_current_evidence'));
        await page.getByText('Evidence gap', { exact: true }).waitFor();
        assert.equal(await page.locator('.readiness-summary .lucide-shield-check').count(), 0);
      }
      await page.screenshot({path: `artifacts/hardening-${scenario}-desktop.png`, fullPage: true});
      await page.getByRole('button', { name: 'Inspect decision evidence' }).click();
      await page.getByRole('dialog', { name: 'Entity evidence' }).waitFor();
      await page.keyboard.press('Escape');
      await page.getByRole('dialog', { name: 'Entity evidence' }).waitFor({state: 'hidden'});
      await page.setViewportSize({ width: 390, height: 844 });
      await page.screenshot({path: `artifacts/hardening-${scenario}-mobile.png`, fullPage: true});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile overflow');
      violations.push(...await page.evaluate(() => window.__cspViolations));
      assert.deepEqual(errors, []);
      assert.deepEqual(violations, []);
      assert(responses.every(r => r.status === 200), JSON.stringify(responses));
      const after = await (await page.request.get(url + '/api/overview')).json();
      assert.deepEqual(before.history, after.history);
      assert.deepEqual(before.actions, after.actions);
      results.push({scenario, status, page_errors: errors, csp_violations: violations, mobile_no_overflow: true, state_unchanged: true, api_responses: responses});
      await context.close();
    }
    const report = {verified_at: new Date().toISOString(), browser: 'Installed Chrome', real_database: true, scenarios: results};
    fs.writeFileSync('artifacts/browser-hardening.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
