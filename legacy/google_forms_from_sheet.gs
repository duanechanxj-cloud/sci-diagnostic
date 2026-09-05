/**
 * PRIMARY SCIENCE DIAGNOSTIC -> GOOGLE FORM
 *
 * 1. Import google_forms_ready.csv into Google Sheets.
 * 2. Extensions -> Apps Script.
 * 3. Paste this file.
 * 4. Run createDiagnosticForm().
 *
 * The Question_ID is embedded in each item title as [QID:...].
 * This lets the Python response importer map Google Forms columns
 * back to the Master Question Bank reliably.
 */
function createDiagnosticForm() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getDisplayValues();

  if (data.length < 2) {
    throw new Error("No question rows found.");
  }

  const headers = data[0];
  const idx = {};
  headers.forEach((h, i) => idx[h.trim()] = i);

  const required = [
    "Form_Title", "Question_Number", "Question_ID", "Question_Text",
    "Option_A", "Option_B", "Option_C", "Option_D", "Correct_Option"
  ];

  required.forEach(h => {
    if (idx[h] === undefined) {
      throw new Error("Missing column: " + h);
    }
  });

  const title = data[1][idx["Form_Title"]] || "Science Diagnostic";
  const form = FormApp.create(title);
  form.setIsQuiz(true);
  form.setDescription(
    "Low-stakes Science diagnostic used to identify learning gaps and guide revision."
  );

  data.slice(1).forEach(row => {
    const qText = row[idx["Question_Text"]].trim();
    if (!qText) return;

    const qNo = row[idx["Question_Number"]].trim();
    const qid = row[idx["Question_ID"]].trim();
    const correct = row[idx["Correct_Option"]].trim().toUpperCase();

    const opts = {
      A: row[idx["Option_A"]],
      B: row[idx["Option_B"]],
      C: row[idx["Option_C"]],
      D: row[idx["Option_D"]]
    };

    if (!["A","B","C","D"].includes(correct)) {
      throw new Error("Invalid correct option for " + qid);
    }

    const item = form.addMultipleChoiceItem();
    item.setTitle(qNo + ". " + qText + " [QID:" + qid + "]");
    item.setRequired(true);
    item.setPoints(1);

    const choices = ["A","B","C","D"].map(letter =>
      item.createChoice(opts[letter], letter === correct)
    );

    item.setChoices(choices);
  });

  SpreadsheetApp.getUi().alert(
    "Form created.\n\nEdit URL:\n" + form.getEditUrl() +
    "\n\nStudent URL:\n" + form.getPublishedUrl()
  );
}
