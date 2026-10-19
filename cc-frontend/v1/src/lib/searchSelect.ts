import type { SearchSelectOption } from "@/components/SearchSelect";

// Build SearchSelect options from a list of objects
export function toSearchSelectOptions<T>(
  items: T[],
  labelKey: keyof T,
  valueKey: keyof T,
  disabledKey?: keyof T,
): SearchSelectOption[] {
  return items.map((item) => ({
    label: String(item[labelKey]),
    value: String(item[valueKey]),
    disabled: disabledKey ? Boolean(item[disabledKey]) : false,
  }));
}
