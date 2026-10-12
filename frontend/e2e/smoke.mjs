import { chromium } from "playwright";

// Drives the real dashboard against a running API. Requires:
//   1. `uv run footfall-api` (serves frontend/dist)
//   2. `npm run build`
// Usage: BASE=... VIDEO=... node e2e/smoke.mjs
const BASE = process.env.BASE ?? "http://127.0.0.1:8000";
const CLIP = process.env.VIDEO ?? "../data/pedestrian.mp4";
const SHOTS = process.env.SHOTS ?? "/tmp";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 });
const problems = [];
// Negative tests below provoke failures on purpose; only unexpected ones count.
let expectingFailure = false;
page.on("console", (m) => {
  if (m.type() === "error" && !expectingFailure) problems.push(`console: ${m.text()}`);
});
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));

await page.goto(BASE);
await page.waitForSelector("h1");

// Default language is Chinese, and the choice survives a reload.
const defaults = {
  lang: await page.getAttribute("html", "lang"),
  title: await page.locator("h1").textContent(),
};
console.log("default language:", JSON.stringify(defaults));
await page.getByRole("button", { name: "English" }).click();
console.log("after switch to English:", await page.locator("h1").textContent());
await page.reload();
console.log("after reload (persisted):", await page.locator("h1").textContent());
// Server-side errors localize too — they carry a code, not English prose.
expectingFailure = true;
await page.setInputFiles("input[type=file]", {
  name: "notes.txt",
  mimeType: "text/plain",
  buffer: Buffer.from("not a video"),
});
await page.waitForSelector(".upload__error");
console.log("api error (en):", await page.locator(".upload__error").textContent());

await page.getByRole("button", { name: "中文" }).click();
console.log("back to Chinese:", await page.locator("h1").textContent());
await page.setInputFiles("input[type=file]", {
  name: "notes.txt",
  mimeType: "text/plain",
  buffer: Buffer.from("not a video"),
});
await page.waitForSelector(".upload__error");
console.log("api error (zh):", await page.locator(".upload__error").textContent());
expectingFailure = false;
await page.screenshot({ path: `${SHOTS}/ui-1-empty.png` });

// Upload
await page.setInputFiles("input[type=file]", CLIP);
await page.waitForSelector(".line-editor__frame", { timeout: 60000 });
await page.waitForFunction(() => {
  const img = document.querySelector(".line-editor__frame");
  return img && img.complete && img.naturalWidth > 0;
}, null, { timeout: 60000 });
await page.screenshot({ path: `${SHOTS}/ui-2-line.png` });

// Drag the lower handle to reposition the gate
const handles = page.locator(".line-editor__handle");
await handles.nth(0).scrollIntoViewIfNeeded();
const svg = await page.locator(".line-editor__overlay").boundingBox();
const start = await handles.nth(0).boundingBox();
await page.mouse.move(start.x + start.width / 2, start.y + start.height / 2);
await page.mouse.down();
await page.mouse.move(svg.x + 10, svg.y + svg.height * 0.72, { steps: 12 });
await page.mouse.up();
const lineAfterDrag = await page.locator(".line-editor__gate").evaluate((el) => ({
  y1: Number(el.getAttribute("y1")).toFixed(0),
  y2: Number(el.getAttribute("y2")).toFixed(0),
}));
console.log("line after drag:", JSON.stringify(lineAfterDrag));

// Faster run for the check
await page.selectOption(".settings__field:nth-child(2) select", "1280");
await page.locator('input[type="range"]').nth(1).fill("3");
await page.screenshot({ path: `${SHOTS}/ui-3-configured.png` });

// Language-independent selectors from here on.
await page.locator(".app__primary").click();
await page.waitForSelector(".readout__value", { timeout: 30000 });
await page.waitForTimeout(6000);
await page.screenshot({ path: `${SHOTS}/ui-4-running.png` });
console.log("status mid-run:", await page.locator(".progress__status").getAttribute("data-status"));
console.log("occupancy mid-run:", await page.locator(".readout__value").textContent());

await page.waitForFunction(
  () =>
    ["completed", "failed", "cancelled"].includes(
      document.querySelector(".progress__status")?.dataset.status ?? "",
    ),
  null,
  { timeout: 180000 },
);
await page.waitForTimeout(1200);
await page.screenshot({ path: `${SHOTS}/ui-5-done.png`, fullPage: true });

console.log("final status:", await page.locator(".progress__status").getAttribute("data-status"));
console.log("final status label:", await page.locator(".progress__status").textContent());
console.log("final counts:", await page.locator(".readout__value").textContent(),
  "| in:", await page.locator(".readout__flow--in dd").textContent(),
  "| out:", await page.locator(".readout__flow--out dd").textContent());
console.log("crossings listed:", await page.locator(".crossing-feed__row").count());
console.log("runs listed:", await page.locator(".runs__item").count());
console.log("problems:", problems.length ? problems : "none");
await browser.close();

if (problems.length > 0) {
  process.exitCode = 1;
}
