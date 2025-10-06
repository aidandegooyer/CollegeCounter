import React, { useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

export interface SearchSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SearchSelectProps {
  options: SearchSelectOption[];
  value?: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
  allowClear?: boolean;
  clearText?: string;
}

export function SearchSelect({
  options,
  value,
  onValueChange,
  placeholder = "Select an option...",
  searchPlaceholder = "Search...",
  emptyText = "No options found.",
  disabled = false,
  className,
  allowClear = false,
  clearText = "Clear selection",
}: SearchSelectProps) {
  const [open, setOpen] = useState(false);

  // Find the selected option
  const selectedOption = options.find((option) => option.value === value);

  const handleSelect = (selectedValue: string) => {
    if (selectedValue === value) {
      // If clicking the same option, optionally deselect (if allowClear is true)
      if (allowClear) {
        onValueChange("");
      }
    } else {
      onValueChange(selectedValue);
    }
    setOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onValueChange("");
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between",
            !selectedOption && "text-muted-foreground",
            className,
          )}
          disabled={disabled}
        >
          <span className="truncate">
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          <div className="flex items-center gap-1">
            {allowClear && selectedOption && (
              <div
                role="button"
                onClick={handleClear}
                className="flex h-4 w-4 items-center justify-center rounded-sm opacity-50 hover:opacity-100"
              >
                <span className="text-xs">×</span>
              </div>
            )}
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="max-h-[300px] w-[--radix-popover-trigger-width] p-0"
        align="start"
      >
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {allowClear && selectedOption && (
                <CommandItem
                  value="__clear__"
                  onSelect={() => handleSelect("")}
                  className="text-muted-foreground"
                >
                  {clearText}
                </CommandItem>
              )}
              {options.map((option) => (
                <CommandItem
                  key={option.value}
                  value={option.label}
                  onSelect={() => handleSelect(option.value)}
                  disabled={option.disabled}
                  className={cn(
                    "cursor-pointer",
                    option.disabled && "cursor-not-allowed opacity-50",
                  )}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === option.value ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <span className="truncate">{option.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// Hook for easier option creation
export function useSearchSelectOptions<T>(
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

export default SearchSelect;
