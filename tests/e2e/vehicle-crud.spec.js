const {expect, test} = require("@playwright/test");
const {login} = require("./helpers/auth");

test("manager can create, update and delete a vehicle through the browser", async ({page}) => {
  test.skip(
    process.env.E2E_RUN_CRUD !== "1",
    "set E2E_RUN_CRUD=1 to run the full vehicle CRUD browser scenario",
  );

  await login(page);

  const preconditions = await page.evaluate(async () => {
    const [enterprisesResponse, modelsResponse] = await Promise.all([
      fetch("/api/enterprises", {credentials: "include"}),
      fetch("/api/vehicle-models", {credentials: "include"}),
    ]);

    return {
      enterprises: enterprisesResponse.ok ? await enterprisesResponse.json() : [],
      models: modelsResponse.ok ? await modelsResponse.json() : [],
    };
  });

  test.skip(
    preconditions.enterprises.length === 0 || preconditions.models.length === 0,
    "vehicle CRUD e2e needs at least one visible enterprise and one vehicle model",
  );

  const enterprise = preconditions.enterprises[0];
  const model = preconditions.models[0];
  const plate = uniquePlate();

  await page
    .locator("#enterpriseList .list-group-item")
    .filter({hasText: enterprise.name})
    .first()
    .click();

  await expect(page.locator("#vehicleCard")).toBeVisible();
  await page.getByRole("button", {name: "Добавить машину"}).click();

  await page.getByLabel("Цена").fill("1700000");
  await page.getByLabel("Пробег").fill("4200");
  await page.getByLabel("Госномер").fill(plate);
  await page.getByLabel("Кол-во владельцев").fill("1");
  await page.getByLabel("Кол-во ДТП").fill("0");
  await page.getByLabel("Год выпуска").fill("2024");
  await page.locator("#modelId").selectOption(String(model.id));
  await page.getByLabel("Цвет").fill("blue");
  await page.getByLabel("Дата и время покупки").fill("2026-06-01T12:00");
  await page.locator("#vehicleSubmitBtn").click();

  await expect(page.locator("#vehicleMessage")).toContainText("Машина создана");
  await expect(page.locator("#vehicleTableBody")).toContainText(plate);

  const row = page.locator("#vehicleTableBody tr").filter({hasText: plate});
  await row.getByRole("button", {name: "Редактировать"}).click();
  await page.getByLabel("Цвет").fill("green");
  await page.locator("#vehicleSubmitBtn").click();

  await expect(page.locator("#vehicleMessage")).toContainText("Машина обновлена");

  const updatedVehicle = await page.evaluate(async (vehicleNumber) => {
    const response = await fetch(
      `/api/vehicles?vehicle_number_prefix=${encodeURIComponent(vehicleNumber)}`,
      {credentials: "include"},
    );
    const vehicles = await response.json();
    return vehicles.find((vehicle) => vehicle.vehicle_number === vehicleNumber);
  }, plate);

  expect(updatedVehicle.color).toBe("green");

  page.once("dialog", async (dialog) => {
    await dialog.accept();
  });
  await row.getByRole("button", {name: "Удалить"}).click();

  await expect(page.locator("#vehicleMessage")).toContainText("Машина удалена");
  await expect(page.locator("#vehicleTableBody")).not.toContainText(plate);
});

function uniquePlate() {
  const number = String(Date.now() % 1000).padStart(3, "0");
  return `А${number}ВС77`;
}
