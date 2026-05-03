import { Input } from "./ui/input";

type Props = {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
};

export function KeybindField({ label, value, disabled, onChange }: Props) {
  return (
    <label className="grid gap-1 text-xs text-muted-foreground">
      <span>{label}</span>
      <Input
        value={value}
        disabled={disabled}
        className="font-mono"
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
