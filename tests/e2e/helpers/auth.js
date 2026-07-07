const {expect} = require("@playwright/test");

const username = process.env.E2E_USERNAME || "superman";
const password = process.env.E2E_PASSWORD || "superman";

async function login(page) {
  await page.goto("/");

  await expect(page.getByRole("heading", {name: "Вход"})).toBeVisible();
  await page.getByLabel("Логин").fill(username);
  await page.getByLabel("Пароль").fill(password);
  await page.getByRole("button", {name: "Войти"}).click();

  await expect(page.locator("#loginCard")).toBeHidden();
}

module.exports = {
  login,
};
