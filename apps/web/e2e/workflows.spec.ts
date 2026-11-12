import { test, expect } from "@playwright/test";

test("discovery, filtering, detail history and persistent watchlist", async ({
  page,
}) => {
  await page.goto("/discover");
  await expect(page.getByText(/DEMO MODE —/)).toBeVisible();
  await expect(
    page.getByRole("link", { name: /fixture-agent-kit/ }).first(),
  ).toBeVisible();
  await page.getByLabel("Language", { exact: true }).selectOption("Rust");
  await expect(
    page.getByRole("link", { name: /fixture-query-engine/ }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /fixture-agent-kit/ }),
  ).toHaveCount(0);
  await page.getByLabel("Language", { exact: true }).selectOption("");
  await page.getByLabel("Search stored repositories").fill("fixture-agent-kit");
  await expect(
    page.getByRole("link", { name: /fixture-agent-kit/ }),
  ).toHaveCount(1);
  await page.getByRole("link", { name: /fixture-agent-kit/ }).click();
  await expect(
    page.getByRole("heading", { name: "Star history" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "stars observations over time" }),
  ).toBeVisible();
  await expect(
    page.getByText("Observed momentum", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Add .*fixture-agent-kit.* to watchlist/ })
    .click();
  await expect(
    page.getByRole("button", {
      name: /Remove .*fixture-agent-kit.* from watchlist/,
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Watchlist", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /fixture-agent-kit/ }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("link", { name: /fixture-agent-kit/ }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: /Remove .*fixture-agent-kit.* from watchlist/,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "A space for your next big find" }),
  ).toBeVisible();
});

test("overview, honest baseline, analytics and settings", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "The open-source pulse" }),
  ).toBeVisible();
  await expect(
    page.getByText("Repositories tracked", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/overview-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.goto("/discover?q=fixture-new-project");
  await page.getByRole("link", { name: /fixture-new-project/ }).click();
  await expect(
    page.getByRole("heading", { name: "Star history" }),
  ).toBeVisible();
  await expect(
    page.getByText("Discovery heuristic", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Building a trustworthy baseline."),
  ).toBeVisible();
  await page.goto("/analytics");
  await expect(
    page.getByRole("heading", { name: "What goes into momentum?" }),
  ).toBeVisible();
  await page.goto("/settings");
  await expect(
    page.getByRole("heading", { name: "Connect GitHub" }),
  ).toBeVisible();
});

test("mobile navigation fits viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByText(/DEMO MODE —/)).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Discover", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Discover what’s next" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBeTruthy();
  await page.screenshot({
    path: "test-results/discover-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
});

test("API error and empty filter states", async ({ page }) => {
  await page.goto("/discover?q=no-such-fixture-repository");
  await expect(
    page.getByRole("heading", { name: "Your next discovery starts here" }),
  ).toBeVisible();
  await page.route("**/api/v1/discover?**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Test-only service outage" }),
    }),
  );
  await page.getByLabel("Search stored repositories").fill("outage");
  await expect(
    page.getByRole("alert").filter({ hasText: "Test-only service outage" }),
  ).toContainText("Test-only service outage");
});

test("forecast outlook, filtering, repository explanation and mobile layout", async ({
  page,
}) => {
  await page.goto("/forecast");
  await expect(
    page.getByRole("heading", { name: "CodePulse Forecast", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Forecast results" }),
  ).toBeVisible();
  await expect(
    page.getByText("Synthetic evaluation only", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("No evaluated outcomes yet.", { exact: false }),
  ).toBeVisible();
  const before = await page.locator("tbody tr").count();
  await page.getByLabel("Potential breakouts only").check();
  await expect
    .poll(async () => {
      const response = await page.request.get(
        "/api/v1/forecast?breakouts_only=true",
      );
      const data = await response.json();
      return data.total
        ? (await page.locator("tbody tr").count()) === data.total
        : await page
            .getByRole("heading", {
              name: "No potential breakouts in the current forecast",
            })
            .isVisible();
    })
    .toBeTruthy();
  expect(await page.locator("tbody tr").count()).toBeLessThanOrEqual(before);
  await page.getByLabel("Potential breakouts only").uncheck();
  await page
    .getByRole("link", { name: /fixture-agent-kit/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "CodePulse Forecast" }),
  ).toBeVisible();
  await expect(page.getByText(/projected net stars/)).toBeVisible();
  await expect(
    page.getByText(/no calibrated probability or validated accuracy yet/),
  ).toBeVisible();
  await page.goto("/discover?q=fixture-new-project");
  await page.getByRole("link", { name: /fixture-new-project/ }).click();
  await expect(
    page.getByText(/Awaiting a forecast run with at least 14 days/),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/forecast");
  await expect(
    page.getByRole("region", { name: "Forecast results" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBeTruthy();
  await page.screenshot({
    path: "test-results/forecast-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "test-results/forecast-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
});

test("forecast empty and error states", async ({ page }) => {
  await page.route("**/api/v1/forecast?**", (route) =>
    route.fulfill({
      json: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        demo: true,
        model_version: "trend-1.0.0",
      },
    }),
  );
  await page.goto("/forecast");
  await expect(
    page.getByRole("heading", { name: "Building a forecast history" }),
  ).toBeVisible();
  await page.route("**/api/v1/forecast?**", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Test-only forecast outage" },
    }),
  );
  await page.getByLabel("Potential breakouts only").check();
  await expect(
    page.getByRole("alert").filter({ hasText: "Test-only forecast outage" }),
  ).toBeVisible();
});
