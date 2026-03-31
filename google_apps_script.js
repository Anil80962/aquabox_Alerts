// =====================================================
// Google Apps Script — FULL SYNC VERSION
// =====================================================
// SETUP:
// 1. Your Google Sheet needs 2 sheet tabs:
//    - "StatusUpdates" (for status data)
//    - "Employees" (for employee list)
//
// 2. "Employees" sheet - Row 1 headers:
//    A1: EmpID | B1: Name | C1: Role
//
// 3. "StatusUpdates" sheet - Row 1 headers:
//    A1: Timestamp | B1: EmpID | C1: EmpName | D1: Role
//    E1: SiteName | F1: WorkType | G1: ScopeOfWork | H1: Status | I1: Date
//
// 4. Extensions → Apps Script → paste this → Deploy as Web App
//    Execute as: Me | Who has access: Anyone
// =====================================================

function doGet(e) {
  var action = e.parameter.action || "";
  var callback = e.parameter.callback || "";
  var result = {};

  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (action === "getEmployees") {
      var sheet = ss.getSheetByName("Employees");
      if (!sheet) {
        result = { status: "success", employees: [] };
      } else {
        var data = sheet.getDataRange().getValues();
        var emps = [];
        for (var i = 1; i < data.length; i++) {
          if (data[i][0]) {
            emps.push({ id: String(data[i][0]), name: String(data[i][1]), role: String(data[i][2]) });
          }
        }
        result = { status: "success", employees: emps };
      }
    }

    else if (action === "getStatus") {
      var dateFilter = e.parameter.date || "";
      var sheet = ss.getSheetByName("StatusUpdates");
      if (!sheet) {
        result = { status: "success", data: [] };
      } else {
        var data = sheet.getDataRange().getValues();
        var rows = [];
        for (var i = 1; i < data.length; i++) {
          var rowDate = String(data[i][8]);
          if (dateFilter === "" || rowDate === dateFilter) {
            rows.push({
              empId: String(data[i][1]),
              empName: String(data[i][2]),
              role: String(data[i][3]),
              siteName: String(data[i][4]),
              workType: String(data[i][5]),
              scopeOfWork: String(data[i][6]),
              status: String(data[i][7]),
              date: rowDate
            });
          }
        }
        result = { status: "success", data: rows };
      }
    }

    else if (action === "getStatusRange") {
      var fromDate = e.parameter.from || "";
      var toDate = e.parameter.to || "";
      var empId = e.parameter.empId || "";
      var sheet = ss.getSheetByName("StatusUpdates");
      if (!sheet) {
        result = { status: "success", data: [] };
      } else {
        var data = sheet.getDataRange().getValues();
        var rows = [];
        for (var i = 1; i < data.length; i++) {
          var rowDate = String(data[i][8]);
          var rowEmpId = String(data[i][1]);
          if (rowDate >= fromDate && rowDate <= toDate) {
            if (empId === "ALL" || empId === "" || rowEmpId === empId) {
              rows.push({
                empId: rowEmpId,
                empName: String(data[i][2]),
                role: String(data[i][3]),
                siteName: String(data[i][4]),
                workType: String(data[i][5]),
                scopeOfWork: String(data[i][6]),
                status: String(data[i][7]),
                date: rowDate
              });
            }
          }
        }
        result = { status: "success", data: rows };
      }
    }

    else {
      result = { status: "success", message: "Fluxgen Operations API running." };
    }

  } catch (err) {
    result = { status: "error", message: err.toString() };
  }

  var output = JSON.stringify(result);
  if (callback) {
    return ContentService
      .createTextOutput(callback + "(" + output + ")")
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return ContentService
    .createTextOutput(output)
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var action = e.parameter.action || "submitStatus";

    if (action === "submitStatus") {
      var sheet = ss.getSheetByName("StatusUpdates");
      if (!sheet) {
        sheet = ss.insertSheet("StatusUpdates");
        sheet.appendRow(["Timestamp", "EmpID", "EmpName", "Role", "SiteName", "WorkType", "ScopeOfWork", "Status", "Date"]);
      }
      sheet.appendRow([
        new Date(),
        e.parameter.empId || "",
        e.parameter.empName || "",
        e.parameter.role || "",
        e.parameter.siteName || "",
        e.parameter.workType || "",
        e.parameter.scopeOfWork || "",
        e.parameter.status || "",
        e.parameter.date || ""
      ]);
    }

    else if (action === "addEmployee") {
      var sheet = ss.getSheetByName("Employees");
      if (!sheet) {
        sheet = ss.insertSheet("Employees");
        sheet.appendRow(["EmpID", "Name", "Role"]);
      }
      sheet.appendRow([
        e.parameter.empId || "",
        e.parameter.empName || "",
        e.parameter.role || ""
      ]);
    }

    else if (action === "deleteEmployee") {
      var sheet = ss.getSheetByName("Employees");
      if (sheet) {
        var data = sheet.getDataRange().getValues();
        var targetId = e.parameter.empId || "";
        for (var i = data.length - 1; i >= 1; i--) {
          if (String(data[i][0]) === targetId) {
            sheet.deleteRow(i + 1);
            break;
          }
        }
      }
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: "success" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
