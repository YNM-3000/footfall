import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const update = <K extends keyof CountingSettings>(key: K, value: CountingSettings[K]) =>
    onChange({ ...settings, [key]: value });

  return (
    <div className="settings">
      <label className="settings__field">
        <span className="settings__label">{t("settings.inDirection")}</span>
        <select
          value={settings.inDirection}
          disabled={disabled}
          onChange={(event) => update("inDirection", event.target.value as InDirection)}
        >
          <option value="negative-to-positive">{t("settings.inDirectionArrow")}</option>
          <option value="positive-to-negative">{t("settings.inDirectionOpposite")}</option>
        </select>
        <small>{t("settings.inDirectionHelp")}</small>
      </label>

      <label className="settings__field">
        <span className="settings__label">{t("settings.imgsz")}</span>
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
        <small>{t("settings.imgszHelp")}</small>
      </label>

      <label className="settings__field">
        <span className="settings__label">
          {t("settings.confidence")} <output>{settings.confidence.toFixed(2)}</output>
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
        <small>{t("settings.confidenceHelp")}</small>
      </label>

      <label className="settings__field">
        <span className="settings__label">
          {t("settings.frameStride")} <output>{settings.frameStride}</output>
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
        <small>{t("settings.frameStrideHelp")}</small>
      </label>
    </div>
  );
}
