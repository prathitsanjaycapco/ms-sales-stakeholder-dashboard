"""Fillable Excel workbook for a complete account people and organization import."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from pydantic import ValidationError

from .portable_import import PortableImportBatch


SHEETS = {
    "Account": ("name",),
    "Pods": ("name", "head_stakeholder_id"),
    "Divisions": ("id", "pod", "name", "color", "head_stakeholder_id"),
    "BusinessUnits": ("id", "division_id", "name", "sort_order"),
    "Employees": ("id", "name", "first_name", "last_name", "title", "level", "role", "capability", "location", "active", "manager_employee_id", "skills", "source_record_id"),
    "Stakeholders": ("id", "name", "title", "pod", "division_id", "business_unit_id", "team_type", "organizational_role", "level", "location", "country_code", "manager_stakeholder_id", "is_primary_technology", "is_buyer", "is_influencer", "is_budget_holder", "relationship_strength", "capco_contingents", "budget_amount", "biography", "tags", "source_record_id"),
    "Relationships": ("id", "stakeholder_id", "employee_id", "relationship_role", "is_primary", "effective_from", "effective_to", "is_current"),
}
BOOLEAN_COLUMNS = {"active", "is_primary_technology", "is_buyer", "is_influencer", "is_budget_holder", "is_primary", "is_current"}
LIST_COLUMNS = {"skills", "tags"}
DATE_COLUMNS = {"effective_from", "effective_to"}


def template_bytes() -> bytes:
    workbook = Workbook()
    guide = workbook.active
    guide.title = "Instructions"
    guide.append(["Account import template", "Version 1"])
    for line in (
        "Fill the seven data tabs. Keep the header row exactly as supplied. Leave optional cells blank.",
        "Every ID is a stable text identifier. Use the same ID when another sheet references a record.",
        "Required: Account.name; Pods.name and head_stakeholder_id; Divisions.id, pod, name; BusinessUnits.id, division_id, name.",
        "Required: Employees.id, name, level, role, location; Stakeholders.id, name, title, pod, team_type, organizational_role.",
        "Required: Relationships.id, stakeholder_id, employee_id, effective_from. Employees, BusinessUnits, and Relationships may have no rows.",
        "Start with Account and Pods. Each pod needs one Stakeholder whose organizational_role is Pod Head.",
        "The pod head has no division, business unit, or manager. Other stakeholders need a division and manager.",
        "Use Business or Technology for team_type. One Technology person per business unit may be primary.",
        "Employees are your team. Stakeholders are client contacts. Relationships link their IDs.",
        "Use TRUE or FALSE for Boolean fields. Use YYYY-MM-DD for dates. Separate skills and tags with semicolons.",
        "Example: a relationship can connect stakeholder_id client-1 to employee_id consultant-1.",
        "Preview the workbook in Account master data before importing. An import requires an empty local account database.",
        "The clear demo action makes a database backup and requires two confirmations.",
    ):
        guide.append([line])
    guide.column_dimensions["A"].width = 115
    guide["A1"].font = Font(bold=True, size=15, color="FFFFFF")
    guide["A1"].fill = PatternFill("solid", fgColor="173F59")
    for sheet_name, headers in SHEETS.items():
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(headers)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{sheet.cell(1, len(headers)).column_letter}1"
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="176F9F")
            cell.alignment = Alignment(wrap_text=True)
            sheet.column_dimensions[cell.column_letter].width = min(28, max(17, len(str(cell.value)) + 3))
        sheet.row_dimensions[1].height = 30
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _cell_value(value, field: str, sheet: str, row: int):
    if value is None or value == "":
        return None
    if field in BOOLEAN_COLUMNS:
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in {"true", "yes", "1"}:
            return True
        if str(value).strip().lower() in {"false", "no", "0"}:
            return False
        raise ValueError(f"{sheet} row {row}, {field}: use TRUE or FALSE")
    if field in LIST_COLUMNS:
        return [part.strip() for part in str(value).split(";") if part.strip()]
    if field in DATE_COLUMNS:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value).strip())
        except ValueError as error:
            raise ValueError(f"{sheet} row {row}, {field}: use YYYY-MM-DD") from error
    return value.strip() if isinstance(value, str) else value


def parse_workbook(content: bytes) -> PortableImportBatch:
    if not content or len(content) > 5 * 1024 * 1024:
        raise ValueError("Choose a nonempty .xlsx workbook no larger than 5 MB")
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as error:
        raise ValueError("The file is not a readable .xlsx workbook") from error
    payload: dict = {"schema_version": 1}
    try:
        for sheet_name, headers in SHEETS.items():
            if sheet_name not in workbook:
                raise ValueError(f"Missing sheet: {sheet_name}")
            sheet = workbook[sheet_name]
            if sheet.max_row and sheet.max_row > 5001:
                raise ValueError(f"{sheet_name} exceeds the 5,000 row limit")
            rows = sheet.iter_rows(values_only=True)
            actual = tuple(next(rows, ()))
            if actual[:len(headers)] != headers or any(value is not None for value in actual[len(headers):]):
                raise ValueError(f"{sheet_name} headers do not match the template")
            items = []
            for row_number, values in enumerate(rows, start=2):
                if not any(value is not None and value != "" for value in values):
                    continue
                if any(value is not None and value != "" for value in values[len(headers):]):
                    raise ValueError(f"{sheet_name} row {row_number}: data exists outside template columns")
                items.append({field: parsed for field, value in zip(headers, values)
                              if (parsed := _cell_value(value, field, sheet_name, row_number)) is not None})
            key = {"BusinessUnits": "business_units"}.get(sheet_name, sheet_name.lower())
            payload[key] = items[0] if sheet_name == "Account" and len(items) == 1 else items
            if sheet_name == "Account" and len(items) != 1:
                raise ValueError("Account must have exactly one data row")
    finally:
        workbook.close()
    try:
        return PortableImportBatch.model_validate(payload)
    except ValidationError as error:
        detail = []
        for issue in error.errors()[:12]:
            location = ".".join(str(part) for part in issue["loc"])
            detail.append(f"{location}: {issue['msg']}")
        raise ValueError("; ".join(detail)) from error
