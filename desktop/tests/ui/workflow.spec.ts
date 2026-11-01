import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { stat } from "node:fs/promises";
import { resolve } from "node:path";
const token = "frameatlas-ui-test-token-01234567890123456789";
const entry = `/#port=18765&token=${token}`;

test("main search meets WCAG AA automated checks", async ({ page }) => {
  await page.goto(entry);
  await expect(
    page.getByRole("heading", { name: "Bạn đang tìm cảnh nào?" }),
  ).toBeVisible();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
});

test("text → real video seek → save → persist and remove saved moment", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(entry);
  await expect(
    page.getByRole("heading", { name: "Bạn đang tìm cảnh nào?" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Mô tả cảnh cần tìm" })
    .fill("red square");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  const first = page.locator(".moment-card:visible").first();
  await expect(first).toContainText("red-square.avi", { timeout: 30_000 });
  await first.click();
  const video = page.locator("video");
  await expect
    .poll(() => video.evaluate((el) => el.readyState))
    .toBeGreaterThanOrEqual(2);
  await page.getByLabel("Bắt đầu (giây)").fill("1");
  await page.getByLabel("Kết thúc (giây)").fill("3");
  await page.getByLabel("Tên khoảnh khắc").fill("Đoạn cần dùng");
  await page
    .getByRole("button", { name: "Lưu khoảnh khắc", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Đã lưu khoảnh khắc");
  await page.getByRole("button", { name: /^Đã lưu/ }).click();
  await expect(page.locator(".moment-card:visible").first()).toContainText(
    "Đoạn cần dùng",
  );
  await page.screenshot({ path: "../outputs/onboarding/ui-saved.png" });
  await page.reload();
  await page.getByRole("button", { name: /^Đã lưu/ }).click();
  await expect(page.locator(".moment-card:visible")).toHaveCount(1);
  await page.getByRole("button", { name: "Bỏ lưu Đoạn cần dùng" }).click();
  await expect(
    page.getByRole("heading", { name: "Giữ lại khoảnh khắc bạn cần." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("image query, library filtering, settings, narrow window and keyboard", async ({
  page,
}) => {
  await page.goto(entry);
  await page
    .getByLabel("Ảnh truy vấn", { exact: true })
    .setInputFiles("../outputs/onboarding/ui-query.png");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(page.locator(".moment-card:visible").first()).toContainText(
    "blue-scene.avi",
  );
  await page.screenshot({ path: "../outputs/onboarding/ui-search.png" });
  await page.getByRole("button", { name: "Thư viện", exact: true }).click();
  await page.getByRole("textbox", { name: "Lọc tên video" }).fill("red");
  await expect(page.locator(".video-row")).toHaveCount(1);
  await page.getByRole("button", { name: /red-square.avi.*khung/ }).click();
  await expect(
    page.getByRole("complementary", { name: "Chi tiết khoảnh khắc" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".inspector")).toHaveCount(0);
  await page.getByRole("button", { name: "Cài đặt", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bộ máy tìm kiếm EG2" }),
  ).toBeVisible();
  await page.getByLabel("Kích thước lô").selectOption("4");
  await page.getByRole("button", { name: "Lưu cài đặt", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Đã lưu cài đặt");
  await page.setViewportSize({ width: 920, height: 700 });
  await page
    .getByRole("button", { name: "Tìm khoảnh khắc", exact: true })
    .click();
  await page.keyboard.press("Control+k");
  await expect(
    page.getByRole("textbox", { name: "Mô tả cảnh cần tìm" }),
  ).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../outputs/onboarding/ui-narrow.png" });
});

test("panel imports paths and exports a playable clip without native dialogs", async ({
  page,
}) => {
  await page.goto(entry);
  await page.getByRole("button", { name: "Thư viện", exact: true }).click();
  await page.getByRole("button", { name: /red-square.avi.*khung/ }).click();
  const source = await page.locator(".source-info p").innerText();
  await page.getByRole("button", { name: "Thêm video", exact: true }).click();
  const picker = page.getByRole("dialog");
  await picker.getByRole("textbox").fill(source);
  await picker.getByRole("button", { name: "Dùng đường dẫn" }).click();
  await expect(page.getByRole("status")).toContainText("Đã thêm 0 video");
  await page
    .getByRole("button", { name: "Xuất đoạn MP4", exact: true })
    .click();
  const destination = resolve(
    `../outputs/onboarding/panel-export-${Date.now()}.mp4`,
  );
  await picker.getByRole("textbox").fill(destination);
  await picker.getByRole("button", { name: "Xuất clip", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(destination);
  expect((await stat(destination)).size).toBeGreaterThan(1000);
  await page
    .getByRole("button", { name: "Xuất đoạn MP4", exact: true })
    .click();
  await picker.getByRole("textbox").press("Escape");
  await expect(picker).toHaveCount(0);
  await expect(page.locator(".inspector")).toBeVisible();
});

test("image region changes retrieval, supports keyboard and drag, and restores the full image", async ({
  page,
}) => {
  await page.goto(entry);
  await page
    .getByLabel("Ảnh truy vấn", { exact: true })
    .setInputFiles("../outputs/onboarding/ui-query-mixed.png");
  const search = page.getByRole("button", { name: "Tìm kiếm", exact: true });
  await expect(page.getByAltText("Ảnh gốc để chọn chi tiết")).toBeVisible();
  await search.click();
  await expect(page.locator(".moment-card").first()).toContainText(
    "blue-scene.avi",
  );
  await page.getByText("Chọn vùng bằng bàn phím", { exact: true }).click();
  await page.getByLabel("Rộng (%)", { exact: true }).fill("20");
  await expect(search).toBeDisabled();
  await expect(page.locator(".moment-card")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Dùng vùng đã chọn", exact: true })
    .click();
  await expect(
    page.getByText("Đang dùng vùng đã chọn.", { exact: true }),
  ).toBeVisible();
  const request = page.waitForRequest(
    (request) =>
      request.url().endsWith("/search") && request.method() === "POST",
  );
  await search.click();
  const imagePayload: unknown = (await request).postDataJSON().image;
  expect(typeof imagePayload).toBe("string");
  if (typeof imagePayload !== "string")
    throw new Error("Missing cropped query");
  const dimensions = await page.evaluate(async (data) => {
    const image = new Image();
    image.src = `data:image/png;base64,${data}`;
    await image.decode();
    return [image.naturalWidth, image.naturalHeight];
  }, imagePayload);
  expect(dimensions).toEqual([64, 180]);
  await expect(page.locator(".moment-card").first()).toContainText(
    "red-square.avi",
  );
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
  await page
    .getByRole("button", { name: "Dùng toàn ảnh", exact: true })
    .click();
  await search.click();
  await expect(page.locator(".moment-card").first()).toContainText(
    "blue-scene.avi",
  );
  const bounds = await page
    .getByRole("group", { name: "Khoanh vùng ảnh bằng chuột" })
    .boundingBox();
  if (!bounds) throw new Error("Query image not visible");
  await page.mouse.move(
    bounds.x + bounds.width * 0.2,
    bounds.y + bounds.height * 0.9,
  );
  await page.mouse.down();
  await page.mouse.move(
    bounds.x + bounds.width * 0.02,
    bounds.y + bounds.height * 0.1,
    { steps: 5 },
  );
  await page.mouse.up();
  await page
    .getByRole("button", { name: "Dùng vùng đã chọn", exact: true })
    .click();
  await search.click();
  await expect(page.locator(".moment-card").first()).toContainText(
    "red-square.avi",
  );
  await page.setViewportSize({ width: 920, height: 700 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../outputs/onboarding/ui-image-region.png" });
});

test("search within a time range and clear the range", async ({ page }) => {
  await page.goto(entry);
  await page
    .getByRole("combobox", { name: "Phạm vi", exact: true })
    .selectOption({ label: "red-square.avi" });
  await page.getByLabel("Từ phút", { exact: true }).fill("0.05");
  await page.getByLabel("Đến phút", { exact: true }).fill("0.09");
  await page.getByRole("textbox", { name: "Mô tả cảnh cần tìm" }).fill("red");
  const request = page.waitForResponse(
    (response) =>
      response.url().endsWith("/search") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  const response = await request;
  expect(response.ok()).toBe(true);
  const result: {
    results: { start: number; end: number; peak: number }[];
    indexed_frames: number;
  } = await response.json();
  expect(result.results.length).toBeGreaterThan(0);
  expect(result.indexed_frames).toBe(3);
  for (const moment of result.results) {
    expect(moment.start).toBeGreaterThanOrEqual(3);
    expect(moment.end).toBeLessThanOrEqual(5.4);
  }
  await page.getByRole("button", { name: "Xóa giới hạn", exact: true }).click();
  await expect(page.getByLabel("Từ phút", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Đến phút", { exact: true })).toHaveValue("");
});
