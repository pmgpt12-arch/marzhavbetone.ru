import fs from "node:fs/promises";
import crypto from "node:crypto";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outDir = process.argv[2];
if (!outDir) throw new Error("output directory required");
await fs.mkdir(outDir, { recursive: true });

const COLORS = {
  graphite: "#2F343B",
  graphite2: "#4B5159",
  gold: "#B59A5B",
  goldLight: "#EFE7D2",
  paper: "#FFFFFF",
  ink: "#20242A",
  muted: "#6B7280",
  line: "#D9DDE3",
  ok: "#E2F0D9",
  warn: "#FFF2CC",
  bad: "#FCE8E6",
};
const font = "Arial";
const sha256 = (b) => crypto.createHash("sha256").update(b).digest("hex");

function titleBlock(sheet, title, subtitle, lastCol) {
  sheet.mergeCells(`A1:${lastCol}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: COLORS.graphite,
    font: { name: font, size: 16, bold: true, color: COLORS.paper },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}1`).format.rowHeight = 30;
  sheet.mergeCells(`A2:${lastCol}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${lastCol}2`).format = {
    fill: COLORS.goldLight,
    font: { name: font, size: 10, color: COLORS.ink },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${lastCol}2`).format.rowHeight = 34;
}

function styleHeader(sheet, address) {
  const r = sheet.getRange(address);
  r.format = {
    fill: COLORS.graphite2,
    font: { name: font, size: 10, bold: true, color: COLORS.paper },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: COLORS.line },
  };
  r.format.rowHeight = 34;
}

function styleBody(sheet, address) {
  const r = sheet.getRange(address);
  r.format = {
    font: { name: font, size: 10, color: COLORS.ink },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.line },
  };
  r.format.rowHeight = 24;
}

function addStatusFormats(range) {
  range.conditionalFormats.add("containsText", {
    text: "ГОТОВО",
    format: { fill: COLORS.ok, font: { bold: true, color: "#215E21" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "ЗАПОЛНИТЬ",
    format: { fill: COLORS.bad, font: { bold: true, color: "#9C0006" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "НЕ ГОТОВО",
    format: { fill: COLORS.bad, font: { bold: true, color: "#9C0006" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "ПРОВЕРИТЬ",
    format: { fill: COLORS.warn, font: { bold: true, color: "#7F6000" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "ВОЗВРАТ",
    format: { fill: COLORS.warn, font: { bold: true, color: "#7F6000" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "В РАБОТЕ",
    format: { fill: "#DDEBF7", font: { bold: true, color: "#1F4E78" } },
  });
}

function addInstructionSheet(wb, title, rows) {
  const s = wb.worksheets.add("Инструкция");
  s.showGridLines = false;
  s.mergeCells("A1:F1");
  s.getRange("A1").values = [[title]];
  s.getRange("A1:F1").format = {
    fill: COLORS.graphite,
    font: { name: font, size: 16, bold: true, color: COLORS.paper },
    verticalAlignment: "center",
  };
  s.getRange("A1:F1").format.rowHeight = 30;
  s.getRange("A3:B3").values = [["Шаг", "Действие"]];
  styleHeader(s, "A3:B3");
  s.getRange(`A4:B${3 + rows.length}`).values = rows.map((x, i) => [i + 1, x]);
  styleBody(s, `A4:B${3 + rows.length}`);
  s.getRange("A:A").format.columnWidth = 7;
  s.getRange("B:B").format.columnWidth = 88;
  s.freezePanes.freezeRows(3);
  return s;
}

async function buildRegistry02() {
  const wb = Workbook.create();
  const s = wb.worksheets.add("Реестр приложений");
  s.showGridLines = false;
  titleBlock(
    s,
    "РЕЕСТР ПРИЛОЖЕНИЙ К КОМПЛЕКТУ КС",
    "Строка становится «ГОТОВО» только при заполненных обязательных полях, корректной дате, наличии документа и отметке проверки.",
    "I",
  );
  s.getRange("A4:I4").values = [[
    "№", "Вид документа", "Номер / идентификатор", "Дата документа",
    "Кол-во листов", "Наличие", "Примечание / основание", "Проверено", "Контроль строки",
  ]];
  styleHeader(s, "A4:I4");
  const rows = 50;
  s.getRange(`A5:A${4 + rows}`).values = Array.from({ length: rows }, (_, i) => [i + 1]);
  styleBody(s, `A5:I${4 + rows}`);
  s.getRange("I5").formulas = [[
    '=IF(COUNTA(B5:H5)=0,"",IF(OR(B5="",C5="",NOT(ISNUMBER(D5)),E5<1,F5="",H5=""),"ЗАПОЛНИТЬ",IF(AND(F5="Приложено",H5="Да"),"ГОТОВО",IF(F5="Не требуется","ПРОВЕРИТЬ ОСНОВАНИЕ","НЕ ГОТОВО"))))',
  ]];
  s.getRange(`I5:I${4 + rows}`).fillDown();
  s.getRange(`D5:D${4 + rows}`).format.numberFormat = "dd.mm.yyyy";
  s.getRange(`E5:E${4 + rows}`).format.numberFormat = "0";
  s.getRange(`B5:B${4 + rows}`).dataValidation = {
    rule: { type: "list", values: [
      "КС-2 — акт о приёмке выполненных работ",
      "КС-3 — справка о стоимости выполненных работ и затрат",
      "АОСР — акт освидетельствования скрытых работ",
      "Исполнительная схема",
      "Паспорт / сертификат",
      "Иное приложение",
    ] },
  };
  s.getRange(`D5:D${4 + rows}`).dataValidation = {
    rule: { type: "date", operator: "between", formula1: "2000-01-01", formula2: "=TODAY()" },
  };
  s.getRange(`E5:E${4 + rows}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 10000 },
  };
  s.getRange(`F5:F${4 + rows}`).dataValidation = {
    rule: { type: "list", values: ["Приложено", "Не требуется", "Отсутствует"] },
  };
  s.getRange(`H5:H${4 + rows}`).dataValidation = {
    rule: { type: "list", values: ["Да", "Нет"] },
  };
  addStatusFormats(s.getRange(`I5:I${4 + rows}`));
  s.getRange("A:A").format.columnWidth = 6;
  s.getRange("B:B").format.columnWidth = 34;
  s.getRange("C:C").format.columnWidth = 22;
  s.getRange("D:D").format.columnWidth = 15;
  s.getRange("E:E").format.columnWidth = 12;
  s.getRange("F:F").format.columnWidth = 16;
  s.getRange("G:G").format.columnWidth = 30;
  s.getRange("H:H").format.columnWidth = 12;
  s.getRange("I:I").format.columnWidth = 22;
  s.freezePanes.freezeRows(4);
  addInstructionSheet(wb, "КАК РАБОТАТЬ С РЕЕСТРОМ ПРИЛОЖЕНИЙ", [
    "Заполняйте одну строку на один фактический документ; не подменяйте АОСР формой КС-11 и не называйте КС-4 ведомостью ресурсов.",
    "Укажите вид, номер, дату, количество листов и наличие. Для «Не требуется» внесите проверяемое основание в примечание.",
    "Отметьте «Проверено = Да» только после сверки реквизитов и состава. Пустая или некорректная дата не может дать положительный статус.",
    "Перед передачей отфильтруйте «Контроль строки»: в составе не должно оставаться «ЗАПОЛНИТЬ», «НЕ ГОТОВО» или неподтверждённых оснований.",
  ]);
  wb.recalculate();
  const preview = await wb.render({ sheetName: "Реестр приложений", autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outDir}/02-reestr-prilozheniy-artifact-preview.png`, new Uint8Array(await preview.arrayBuffer()));
  const xlsx = await SpreadsheetFile.exportXlsx(wb);
  await xlsx.save(`${outDir}/02-reestr-prilozheniy.xlsx`);
  const inspect = await wb.inspect({ kind: "sheet,formula,region", sheetId: "Реестр приложений", range: "A1:I12", maxChars: 8000 });
  return { wb, inspect };
}

async function buildJournal06() {
  const wb = Workbook.create();
  const s = wb.worksheets.add("Журнал передачи комплекта КС");
  s.showGridLines = false;
  titleBlock(
    s,
    "ЖУРНАЛ ПЕРЕДАЧИ КОМПЛЕКТА КС",
    "Контроль фиксирует передачу, получателя, подтверждение, текущий статус и параметры возврата. Положительный итог без обязательных реквизитов невозможен.",
    "L",
  );
  s.getRange("A4:L4").values = [[
    "№", "Дата передачи", "КС-2 №", "КС-3 №", "Получатель", "Должность",
    "Кол-во документов", "Подтверждение передачи", "Статус", "Дата возврата",
    "Причина / замечание", "Контроль строки",
  ]];
  styleHeader(s, "A4:L4");
  const rows = 50;
  s.getRange(`A5:A${4 + rows}`).values = Array.from({ length: rows }, (_, i) => [i + 1]);
  styleBody(s, `A5:L${4 + rows}`);
  s.getRange("L5").formulas = [[
    '=IF(COUNTA(B5:K5)=0,"",IF(OR(NOT(ISNUMBER(B5)),C5="",D5="",E5="",F5="",G5<1,H5="",I5=""),"ЗАПОЛНИТЬ",IF(I5="Принято","ЗАКРЫТО",IF(I5="Возврат",IF(OR(NOT(ISNUMBER(J5)),J5<B5,K5=""),"УКАЗАТЬ ВОЗВРАТ","ВОЗВРАТ ЗАФИКСИРОВАН"),IF(I5="На проверке","В РАБОТЕ","ПРОВЕРИТЬ")))))',
  ]];
  s.getRange(`L5:L${4 + rows}`).fillDown();
  s.getRange(`B5:B${4 + rows}`).format.numberFormat = "dd.mm.yyyy";
  s.getRange(`J5:J${4 + rows}`).format.numberFormat = "dd.mm.yyyy";
  s.getRange(`G5:G${4 + rows}`).format.numberFormat = "0";
  s.getRange(`B5:B${4 + rows}`).dataValidation = {
    rule: { type: "date", operator: "between", formula1: "2000-01-01", formula2: "=TODAY()" },
  };
  s.getRange(`G5:G${4 + rows}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 10000 },
  };
  s.getRange(`H5:H${4 + rows}`).dataValidation = {
    rule: { type: "list", values: ["Подпись на экземпляре", "ЭДО", "Письмо / курьер", "Иное подтверждение"] },
  };
  s.getRange(`I5:I${4 + rows}`).dataValidation = {
    rule: { type: "list", values: ["На проверке", "Принято", "Возврат"] },
  };
  s.getRange(`J5:J${4 + rows}`).dataValidation = {
    rule: { type: "date", operator: "between", formula1: "2000-01-01", formula2: "=TODAY()" },
  };
  addStatusFormats(s.getRange(`L5:L${4 + rows}`));
  const widths = [6,15,16,16,26,20,13,24,16,15,32,24];
  "ABCDEFGHIJKL".split("").forEach((c, i) => { s.getRange(`${c}:${c}`).format.columnWidth = widths[i]; });
  s.freezePanes.freezeRows(4);
  addInstructionSheet(wb, "КАК РАБОТАТЬ С ЖУРНАЛОМ ПЕРЕДАЧИ", [
    "Одна строка соответствует одной передаче комплекта. Укажите фактическую дату, номера КС-2/КС-3, получателя, должность и количество документов.",
    "Зафиксируйте способ подтверждения передачи и выберите статус. «Принято» закрывает строку только при заполненных обязательных реквизитах.",
    "При возврате обязательно укажите дату не ранее даты передачи и причину/замечание. Иначе контроль покажет «УКАЗАТЬ ВОЗВРАТ».",
    "Статус «На проверке» остаётся «В РАБОТЕ». Перед завершением процесса не должно оставаться строк с «ЗАПОЛНИТЬ», «ПРОВЕРИТЬ» или неполным возвратом.",
  ]);
  wb.recalculate();
  const preview = await wb.render({ sheetName: "Журнал передачи комплекта КС", autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outDir}/06-zhurnal-peredachi-artifact-preview.png`, new Uint8Array(await preview.arrayBuffer()));
  const xlsx = await SpreadsheetFile.exportXlsx(wb);
  await xlsx.save(`${outDir}/06-zhurnal-peredachi.xlsx`);
  const inspect = await wb.inspect({ kind: "sheet,formula,region", sheetId: "Журнал передачи комплекта КС", range: "A1:L12", maxChars: 8000 });
  return { wb, inspect };
}

const r02 = await buildRegistry02();
const r06 = await buildJournal06();
const files = {};
for (const name of [
  "02-reestr-prilozheniy.xlsx",
  "06-zhurnal-peredachi.xlsx",
  "02-reestr-prilozheniy-artifact-preview.png",
  "06-zhurnal-peredachi-artifact-preview.png",
]) {
  const b = await fs.readFile(`${outDir}/${name}`);
  files[name] = { bytes: b.length, sha256: sha256(b) };
}
const report = {
  status: "ARTIFACT_TOOL_AUTHOR_OUTPUT_PENDING_SERVER_RECALC_AND_ACCEPTANCE",
  artifact_tool: true,
  files,
  inspect02: r02.inspect.ndjson,
  inspect06: r06.inspect.ndjson,
};
await fs.writeFile(`${outDir}/artifact-author-report.json`, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ status: report.status, files }, null, 2));
