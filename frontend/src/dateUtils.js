const CALENDAR_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function parseBackendDate(value) {
  if (value instanceof Date) return value;
  if (typeof value === "string") {
    const match = CALENDAR_DATE.exec(value);
    if (match) {
      const [, year, month, day] = match;
      return new Date(Number(year), Number(month) - 1, Number(day), 12);
    }
  }
  return new Date(value);
}

export function formatBackendDate(value, options, emptyValue = "Not scheduled") {
  if (!value) return emptyValue;
  const date = parseBackendDate(value);
  return Number.isFinite(date.getTime())
    ? new Intl.DateTimeFormat("en-US", options).format(date)
    : emptyValue;
}
