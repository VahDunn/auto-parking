const {expect, test} = require("@playwright/test");
const {login} = require("./helpers/auth");

test("manager can log in through the browser", async ({page}) => {
  await login(page);

  await expect(page.locator("#loginCard")).toBeHidden();
  await expect(page.getByRole("heading", {name: "Предприятия", exact: true})).toBeVisible();
  await expect(page.getByRole("heading", {name: /Уведомления/})).toBeVisible();
});
