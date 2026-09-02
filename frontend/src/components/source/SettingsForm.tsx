import type { InDirection } from "../../api/types";
import "./settings-form.css";

export interface CountingSettings {
  inDirection: InDirection;
  confidence: number;
  imgsz: number;
  frameStride: number;
}

interface SettingsFormProps {
  settings: CountingSettings;
  disabled: boolean;
  onChange: (settings: CountingSettings) => void;
}

const IMGSZ_CHOICES = [640, 960, 1280, 1600];

export function SettingsForm({ settings, disabled, onChange }: SettingsFormProps) {
  const update = <K extends keyof CountingSettings>(key: K, value: CountingSettings[K]) =>
    onChange({ ...settings, [key]: value });

  return (
    <div className="settings">
      <label className="settings__field">
        <span className="settings__label">Counts as “in”</span>
        <select
          value={settings.inDirection}
          disabled={disabled}
          onChange={(event) => update("inDirection", event.target.value as InDirection)}
        >
          <option value="negative-to-positive">Arrow side</option>
          <option value="positive-to-negative">Opposite side</option>
        </select>
        <small>Flip this if a test run reports IN and OUT swapped.</small>
      </label>

      <label className="settings__field">
        <span className="settings__label">Detection size</span>
        <select
          value={settings.imgsz}
          disabled={disabled}
          onChange={(event) => update("imgsz", Number(event.target.value))}
        >
          {IMGSZ_CHOICES.map((size) => (
            <option key={size} value={size}>
              {size} px
            </option>
          ))}
        </select>
        <small>Higher finds distant people in wide shots; costs speed.</small>
      </label>

      <label className="settings__field">
        <span className="settings__label">
          Confidence <output>{settings.confidence.toFixed(2)}</output>
        </span>
        <input
          type="range"
          min={0.05}
          max={0.9}
          step={0.05}
          value={settings.confidence}
          disabled={disabled}
          onChange={(event) => update("confidence", Number(event.target.value))}
        />
        <small>Lower catches more people, and more false positives.</small>
      </label>

      <label className="settings__field">
        <span className="settings__label">
          Frame stride <output>{settings.frameStride}</output>
        </span>
        <input
          type="range"
          min={1}
          max={10}
          step={1}
          value={settings.frameStride}
          disabled={disabled}
          onChange={(event) => update("frameStride", Number(event.target.value))}
        />
        <small>Process every Nth frame. Faster, but tracking degrades.</small>
      </label>
    </div>
  );
}
