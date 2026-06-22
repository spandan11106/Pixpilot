interface UtilityField {
  field: string;
  label: string;
  description: string;
  placeholder: string;
}

interface UtilityModelsProps {
  models: Record<string, string>;
  onChange: (field: string, value: string) => void;
}

const UTILITY_FIELDS: UtilityField[] = [
  {
    field: "summary_model",
    label: "Summary model",
    description: "Condenses prompts, run logs, and research notes.",
    placeholder: "e.g. claude-haiku-4-5-20251001",
  },
  {
    field: "prompt_model",
    label: "Prompt model",
    description: "Expands and rewrites generation prompts.",
    placeholder: "e.g. claude-sonnet-4-6",
  },
];

export function UtilityModels({ models, onChange }: UtilityModelsProps) {
  return (
    <div className="card util">
      <div className="util-grid">
        {UTILITY_FIELDS.map(({ field, label, description, placeholder }) => (
          <div key={field} className="util-item">
            <div className="field-row">
              <span className="field-label">{label}</span>
              <span className="badge badge-utility">Utility</span>
            </div>
            <div className="util-desc">{description}</div>
            <input
              className="finput mono"
              type="text"
              value={models[field] ?? ""}
              onChange={(e) => onChange(field, e.target.value)}
              placeholder={placeholder}
              aria-label={label}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
