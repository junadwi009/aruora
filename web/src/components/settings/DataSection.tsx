import React, { useState } from "react";
import { Download, Trash2 } from "lucide-react";
import { api } from "../../lib/api/client";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useT } from "../../lib/i18n";

export const DataSection: React.FC = () => {
  const { t } = useT();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const exportData = async () => {
    setBusy(true);
    try {
      const data = await api.accountExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ielts-coach-data.json";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  };

  const deleteAccount = async () => {
    setBusy(true);
    try {
      await api.accountDelete();
      window.location.reload();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <p className="text-sm font-semibold text-[var(--color-text)]">{t("settings.data")}</p>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-[var(--color-text)]">{t("set.dataDownload")}</p>
        <Button variant="secondary" size="sm" onClick={exportData} loading={busy}>
          <Download size={14} className="mr-1.5" /> {t("set.export")}
        </Button>
      </div>

      <div className="border-t border-[var(--color-border)] pt-3">
        {!confirming ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-[var(--color-text)]">{t("set.deleteAccount")}</p>
            <Button variant="destructive" size="sm" onClick={() => setConfirming(true)}>
              <Trash2 size={14} className="mr-1.5" /> {t("set.delete")}
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-[var(--color-danger)]">
              {t("set.deleteWarning")}
            </p>
            <div className="flex gap-2">
              <Button variant="destructive" size="sm" onClick={deleteAccount} loading={busy}>{t("set.deleteConfirm")}</Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>{t("common.cancel")}</Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
