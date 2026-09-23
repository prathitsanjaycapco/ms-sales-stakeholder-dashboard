import React, { useEffect, useId, useMemo, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import "./searchableSelect.css";

const optionValue = (option) => String(option?.value ?? option?.id ?? option ?? "");
const optionLabel = (option) => String(option?.label ?? option?.name ?? option ?? "");

export default function SearchableSelect({ value, options = [], onChange, placeholder = "Select", searchPlaceholder = "Search names…", disabled = false, allowClear = false, multiple = false, ariaLabel }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const selectedValues = multiple ? value || [] : [value].filter(Boolean).map(String);
  const selected = options.filter((option) => selectedValues.includes(optionValue(option)));
  const filtered = useMemo(() => options.filter((option) => JSON.stringify(option).toLowerCase().includes(query.trim().toLowerCase())).slice(0, 100), [options, query]);
  useEffect(() => setActiveIndex(0), [query, open]);
  const choose = (option) => {
    const next = optionValue(option);
    if (multiple) onChange(selectedValues.includes(next) ? selectedValues.filter((item) => item !== next) : [...selectedValues, next]);
    else { onChange(next); setOpen(false); setQuery(""); }
  };
  return <div className={`searchable-select ${open ? "open" : ""} ${disabled ? "disabled" : ""}`}>
    {multiple && selected.length > 0 && <div className="searchable-chips">{selected.map((option) => <button type="button" key={optionValue(option)} onClick={() => choose(option)}>{optionLabel(option)}<X /></button>)}</div>}
    <button type="button" className="searchable-trigger" disabled={disabled} aria-label={ariaLabel} aria-haspopup="listbox" aria-expanded={open} aria-controls={`${id}-list`} onClick={() => setOpen((current) => !current)} onKeyDown={(event) => { if (["ArrowDown", "Enter", " "].includes(event.key) && !open) { event.preventDefault(); setOpen(true); } }}>
      <span>{multiple ? selected.length ? `${selected.length} selected` : placeholder : selected[0] ? optionLabel(selected[0]) : placeholder}</span><ChevronDown />
    </button>
    {open && <div className="searchable-popover"><label><Search /><input autoFocus role="combobox" aria-autocomplete="list" aria-controls={`${id}-list`} aria-activedescendant={filtered[activeIndex] ? `${id}-option-${activeIndex}` : undefined} value={query} placeholder={searchPlaceholder} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((current) => Math.min(current + 1, filtered.length - 1)); } if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((current) => Math.max(current - 1, 0)); } if (event.key === "Enter" && filtered[activeIndex]) { event.preventDefault(); choose(filtered[activeIndex]); } }} /></label>
      <div id={`${id}-list`} role="listbox" aria-multiselectable={multiple || undefined}>{allowClear && !multiple && <button type="button" role="option" onClick={() => { onChange(""); setOpen(false); }}>Unassigned</button>}{filtered.map((option, index) => <button id={`${id}-option-${index}`} type="button" role="option" className={index === activeIndex ? "active" : ""} aria-selected={selectedValues.includes(optionValue(option))} key={optionValue(option)} onMouseEnter={() => setActiveIndex(index)} onClick={() => choose(option)}><span>{optionLabel(option)}{option.title || option.role ? <small>{option.title || option.role}</small> : null}</span>{selectedValues.includes(optionValue(option)) && <Check />}</button>)}{!filtered.length && <p>No matching options</p>}</div>
    </div>}
  </div>;
}

export function AdaptiveSelect({ options = [], searchableAt = 50, ...props }) {
  if (options.length >= searchableAt) return <SearchableSelect options={options} {...props} />;
  return <select value={props.value} onChange={(event) => props.onChange(event.target.value)} disabled={props.disabled}>{props.allowClear && <option value="">Unassigned</option>}{options.map((option) => <option key={optionValue(option)} value={optionValue(option)}>{optionLabel(option)}</option>)}</select>;
}
