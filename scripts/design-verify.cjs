// Read-only UI audit by default. Mutations require a separately seeded, fresh QA graph.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:8000";
const mutate = process.env.DESIGN_MUTATION_QA === "1";
const output = path.resolve("artifacts/design");
fs.mkdirSync(output, { recursive: true });
const report = {
  baseURL,
  mutations: mutate,
  flow: "Chrome → frontend → FastAPI → real FalkorDB → UI",
  checks: [],
  responsive: [],
  accessibility: [],
  page_errors: [],
  api_failures: [],
};
let browser;
(async () => {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();
  page.on("pageerror", (error) => report.page_errors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400)
      report.api_failures.push({
        url: response.url(),
        status: response.status(),
      });
  });
  const check = (name) => {
    report.checks.push(name);
    console.log("PASS", name);
  };
  const stable = async () => {
    await page.waitForFunction(
      () => !document.querySelector(".message.loading"),
    );
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(260);
  };
  const go = async (view) => {
    await page
      .getByRole("button", {
        name: {
          context: "Company context",
          investigation: "Change investigation",
          queue: "Follow-up queue",
        }[view],
        exact: true,
      })
      .click();
    await page.waitForURL("**/#" + view);
    await stable();
  };
  const shot = async (name) => {
    await stable();
    await page.screenshot({
      path: path.join(output, name + ".png"),
      fullPage: !name.startsWith("evidence") && !name.startsWith("search"),
    });
  };
  const axePath = process.env.AXE_MODULE;
  const a11y = async (name) => {
    if (!axePath) return;
    await page.addScriptTag({ path: axePath });
    const result = await page.evaluate(
      async () =>
        await window.axe.run(document, {
          runOnly: {
            type: "tag",
            values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
          },
        }),
    );
    const violations = result.violations.map((item) => ({
      id: item.id,
      impact: item.impact,
      description: item.description,
      nodes: item.nodes.map((node) => ({
        target: node.target,
        summary: node.failureSummary,
      })),
    }));
    report.accessibility.push({ screen: name, violations });
    console.log("AXE", name, JSON.stringify(violations));
  };
  await page.goto(baseURL);
  await page.locator(".stats").waitFor();
  await stable();
  const initial = await (await page.request.get("/api/overview")).json();
  if (mutate)
    assert(
      initial.history.length === 0 && initial.actions.length === 0,
      "Mutation QA requires a fresh isolated graph; existing records will not be changed.",
    );
  await shot("context-initial");
  await page.keyboard.press("Control+k");
  await page.getByRole("dialog", { name: "Search workspace" }).waitFor();
  await page
    .getByRole("textbox", { name: "Search all company context" })
    .fill("doc-owner-current-v1");
  await page
    .getByRole("button", { name: /Authoritative ownership register/ })
    .waitFor();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await page.getByRole("dialog", { name: "Entity evidence" }).waitFor();
  await page
    .getByRole("heading", {
      name: "Authoritative ownership register",
      exact: true,
    })
    .waitFor();
  await page.keyboard.press("Escape");
  await page
    .getByRole("dialog", { name: "Entity evidence" })
    .waitFor({ state: "hidden" });
  check("Keyboard workspace search opens real source evidence; Escape closes");
  await page
    .getByRole("button", { name: "Inspect decision evidence", exact: true })
    .click();
  const drawer = page.getByRole("dialog", { name: "Entity evidence" });
  await drawer.waitFor();
  await drawer
    .getByRole("button", { name: "Resolution source", exact: false })
    .first()
    .click();
  await drawer
    .getByRole("button", { name: "Back to previous evidence" })
    .waitFor();
  await drawer
    .getByRole("button", { name: "Back to previous evidence" })
    .click();
  await drawer
    .getByRole("heading", { name: "Proceed with Atlas launch", exact: true })
    .waitFor();
  await shot("evidence-desktop");
  await a11y("evidence-desktop");
  for (let index = 0; index < 18; index++) {
    await page.keyboard.press("Tab");
    assert(
      await page.evaluate(() => !!document.activeElement.closest("dialog")),
      "Modal must contain keyboard focus",
    );
  }
  await page.keyboard.press("Escape");
  assert(
    await page
      .getByRole("button", { name: "Inspect decision evidence", exact: true })
      .evaluate((element) => element === document.activeElement),
  );
  check(
    "Nested evidence back navigation, native focus containment, and focus restoration",
  );
  const search = page.getByRole("textbox", {
    name: "Search company context",
    exact: true,
  });
  await search.fill("no-matching-context-qa");
  await search.press("Enter");
  await page
    .getByRole("heading", { name: "No matching context", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Clear search" }).click();
  await page.locator(".project-row").first().waitFor();
  check("Explicit zero-result search and clear action");
  await page
    .getByRole("button", { name: "Explore launch readiness", exact: true })
    .click();
  await page.locator(".answer").waitFor();
  await go("investigation");
  await go("context");
  assert(await page.locator(".answer").isVisible());
  await page.getByRole("button", { name: "Close answer" }).click();
  check(
    "Grounded readiness exploration and answer preservation across navigation",
  );
  if (mutate) {
    await page
      .getByRole("button", { name: "Introduce security update", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "7 connected items need review." })
      .waitFor();
    await stable();
    const impact = await (
      await page.request.get("/api/impact/approval-export")
    ).json();
    assert.equal(impact.count, 7);
    assert(
      !impact.items.some((item) =>
        ["project-beacon", "project-orbit"].includes(item.id),
      ),
    );
    check(
      "Synthetic withdrawal persists; seven impacted items; unrelated projects excluded",
    );
  } else await go("investigation");
  if (initial.history.length || mutate) {
    await page
      .getByRole("button", {
        name: "Inspect dependency evidence: commitment-acme depends on milestone-atlas",
        exact: true,
      })
      .click();
    await drawer.waitFor();
    await page.keyboard.press("Escape");
    await page
      .getByRole("combobox", { name: "Focused dependency path" })
      .selectOption("commitment-harbor");
    assert(
      await page
        .getByRole("button", { name: "Harbor commitment", exact: true })
        .isVisible(),
    );
    await page
      .getByRole("combobox", { name: "Focused dependency path" })
      .selectOption("commitment-acme");
    await page
      .getByText("Why is this affected?", { exact: true })
      .last()
      .click();
    await shot("investigation-expanded");
    await page
      .getByText("Why is this affected?", { exact: true })
      .last()
      .click();
    check(
      "Dependency nodes, edge evidence, path selection, and complete impact evidence",
    );
  }
  if (mutate) {
    await page
      .getByRole("button", { name: "Generate response plan", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Review before creating work." })
      .waitFor();
    await stable();
    const boxes = page.getByRole("checkbox");
    assert.equal(await boxes.count(), 4);
    await boxes.nth(2).uncheck();
    await boxes.nth(3).uncheck();
    await shot("proposal-review");
    await page
      .getByRole("button", { name: "Approve selected tasks", exact: true })
      .click();
    await page
      .getByText(
        "Selected internal tasks persisted in FalkorDB. No messages were sent.",
        { exact: true },
      )
      .waitFor();
    const approved = await (await page.request.get("/api/overview")).json();
    assert.equal(approved.actions.length, 2);
    check("Selected two of four proposals create exactly two persisted tasks");
    await page
      .getByRole("button", { name: "Complete", exact: true })
      .first()
      .click();
    await page.getByRole("dialog", { name: "Complete follow-up" }).waitFor();
    await page.keyboard.press("Escape");
    assert(
      (await (await page.request.get("/api/overview")).json()).actions.every(
        (item) => item.action.state === "approved",
      ),
    );
    await page
      .getByRole("button", { name: "Complete", exact: true })
      .first()
      .click();
    await page
      .getByRole("button", { name: "Mark complete", exact: true })
      .click();
    await page
      .getByText("Follow-up completed. Security approval still needs review.", {
        exact: true,
      })
      .waitFor();
    await page.getByRole("button", { name: /^Reject Review / }).click();
    await page.getByRole("dialog", { name: "Reject follow-up" }).waitFor();
    await page.getByRole("button", { name: "Keep open", exact: true }).click();
    await page.getByRole("button", { name: /^Reject Review / }).click();
    await page
      .getByRole("button", { name: "Reject follow-up", exact: true })
      .click();
    await page
      .getByText("Follow-up rejected. Its evidence and history are retained.", {
        exact: true,
      })
      .waitFor();
    const updated = await (await page.request.get("/api/overview")).json();
    assert.equal(
      updated.actions.filter((item) => item.action.state === "completed")
        .length,
      1,
    );
    assert.equal(
      updated.actions.filter((item) => item.action.state === "rejected").length,
      1,
    );
    assert.equal(
      (await (await page.request.get("/api/readiness")).json()).status,
      "review_required",
    );
    check(
      "Complete/reject confirmations, cancel safeguards, persisted states, and unresolved risk",
    );
    await page
      .getByRole("button", { name: "Completed 1", exact: true })
      .click();
    assert.equal(await page.locator(".action:visible").count(), 1);
    await page.getByRole("button", { name: "All work 2", exact: true }).click();
    await page
      .getByRole("button", { name: "Generate fresh plan", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Review before creating work." })
      .waitFor();
    await stable();
    const nextOverview = await (await page.request.get("/api/overview")).json();
    const currentPlan = nextOverview.plans.find(
      (item) => item.plan.revision === nextOverview.revision,
    );
    assert(currentPlan);
    const concurrent = await page.request.post("/api/actions/approve", {
      data: {
        plan_id: currentPlan.plan.id,
        selected: [
          currentPlan.proposals.find((item) => item.state === "proposed").id,
        ],
      },
    });
    assert.equal(concurrent.status(), 200);
    await page.getByRole("button", { name: "Refresh persisted state" }).click();
    await page.getByText("Refresh required", { exact: true }).waitFor();
    assert(
      await page
        .getByRole("button", { name: "Approve selected tasks", exact: true })
        .isDisabled(),
    );
    await shot("stale-plan");
    await page
      .getByRole("button", { name: "Refresh plan", exact: true })
      .click();
    await stable();
    assert(
      !(await page.getByText("Refresh required", { exact: true }).count()),
    );
    check(
      "A concurrent graph change blocks stale approval; regeneration recovers",
    );
    const freshContext = await browser.newContext({ baseURL });
    const fresh = await freshContext.newPage();
    await fresh.goto(baseURL);
    await fresh.locator(".stats").waitFor();
    await fresh
      .getByRole("button", { name: "What changed?", exact: true })
      .click();
    await fresh.locator(".answer h3").waitFor();
    assert(
      (await fresh.locator(".answer h3").innerText()).includes(
        "Security approval changed",
      ),
    );
    const recap = await (await fresh.request.get("/api/recap")).json();
    assert.equal(recap.actions.length, 3);
    assert.equal(recap.changes.length, 1);
    await freshContext.close();
    check("Fresh browser session recovers persisted history and tasks");
  }
  for (const width of [320, 375, 430, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: width < 701 ? 844 : 1000 });
    for (const view of ["context", "investigation", "queue"]) {
      await go(view);
      const layout = await page.evaluate(() => ({
        width: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      assert(
        layout.scrollWidth <= layout.width,
        `${view} overflow at ${width}`,
      );
      report.responsive.push({ view, ...layout });
      if (width === 375 || width === 1440) {
        await shot(`${view}-${width}`);
        await a11y(`${view}-${width}`);
      }
    }
  }
  check("All three screens fit seven widths from 320 to 1920 pixels");
  await page.setViewportSize({ width: 375, height: 844 });
  await go("context");
  await page
    .getByRole("button", { name: "Search context", exact: true })
    .click();
  await shot("search-mobile");
  await a11y("search-mobile");
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Inspect decision evidence", exact: true })
    .click();
  await drawer.waitFor();
  await shot("evidence-mobile");
  await a11y("evidence-mobile");
  await page.keyboard.press("Escape");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page
    .getByRole("button", { name: "Search context", exact: true })
    .click();
  assert.equal(
    await page
      .locator("dialog[open]")
      .evaluate((element) => getComputedStyle(element).animationName),
    "none",
  );
  await page.keyboard.press("Escape");
  check("Reduced-motion removes dialog animation");
  // Simulated transport failures are UI-state checks, separate from the real-data flow above.
  const outagePage = await context.newPage();
  await outagePage.route("**/api/**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "Design QA simulated database outage" }),
    }),
  );
  await outagePage.goto(baseURL);
  await outagePage.getByRole("button", { name: "Retry connection" }).waitFor();
  await outagePage.screenshot({
    path: path.join(output, "database-outage.png"),
    fullPage: true,
  });
  await outagePage.unroute("**/api/**");
  await outagePage.getByRole("button", { name: "Retry connection" }).click();
  await outagePage.locator(".stats").waitFor();
  await outagePage.close();
  check("Simulated database outage has clear feedback and a working retry");
  assert.deepEqual(report.page_errors, []);
  assert.deepEqual(report.api_failures, []);
  report.axe_version = axePath
    ? require(path.join(path.dirname(axePath), "package.json")).version
    : null;
  report.accessibility_violations = report.accessibility.reduce(
    (sum, item) => sum + item.violations.length,
    0,
  );
  report.verified_at = new Date().toISOString();
  fs.writeFileSync(
    path.join(
      output,
      mutate ? "verification-isolated.json" : "verification-readonly.json",
    ),
    JSON.stringify(report, null, 2),
  );
  assert.equal(
    report.accessibility_violations,
    0,
    "Accessibility violations require refinement; see report",
  );
  console.log(
    JSON.stringify(
      {
        checks: report.checks.length,
        responsive: report.responsive.length,
        accessibility: report.accessibility.length,
        violations: report.accessibility_violations,
        page_errors: report.page_errors,
      },
      null,
      2,
    ),
  );
  await browser.close();
})().catch(async (error) => {
  report.failure = error.stack;
  fs.writeFileSync(
    path.join(output, "verification-failure.json"),
    JSON.stringify(report, null, 2),
  );
  console.error(error);
  if (browser) await browser.close();
  process.exit(1);
});
