"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const METHOD_OPTS = [
  { value: "email", label: "Email" },
  { value: "formulario", label: "Formulario" },
  { value: "easy_apply", label: "Easy Apply" },
  { value: "manual", label: "Manual" },
];

type Props = {
  busy: boolean;
  alreadySent: boolean;
  onMarkSent: (method: string, notes: string) => void;
  onRegenerate: () => void;
  onDiscard: () => void;
};

/** Sticky action bar: mark-sent (with dialog), regenerate, discard. */
export function DraftActions({
  busy,
  alreadySent,
  onMarkSent,
  onRegenerate,
  onDiscard,
}: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [method, setMethod] = useState("email");
  const [notes, setNotes] = useState("");

  function confirmSent() {
    onMarkSent(method, notes);
    setDialogOpen(false);
    setNotes("");
  }

  return (
    <>
      <div className="sticky bottom-0 z-30 -mx-4 flex flex-wrap gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:static md:mx-0 md:border-0 md:bg-transparent md:px-0 md:py-0 md:backdrop-blur-none">
        <Button
          onClick={() => setDialogOpen(true)}
          disabled={busy || alreadySent}
        >
          {alreadySent ? "Ya enviado" : "Marcar como enviado"}
        </Button>
        <Button variant="outline" onClick={onRegenerate} disabled={busy}>
          Regenerar
        </Button>
        <Button variant="destructive" onClick={onDiscard} disabled={busy}>
          Descartar
        </Button>
      </div>

      {dialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setDialogOpen(false)}
        >
          <div
            className="w-full max-w-sm rounded-lg border bg-background p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-3 text-lg font-semibold">Marcar como enviado</h2>

            <label className="mb-1 block text-xs text-muted-foreground">
              Método de envío
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="mb-3 h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {METHOD_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>

            <label className="mb-1 block text-xs text-muted-foreground">
              Notas (opcional)
            </label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="mb-4"
            />

            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={confirmSent} disabled={busy}>
                Confirmar
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
