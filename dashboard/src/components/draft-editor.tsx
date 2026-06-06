"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { DraftActions } from "@/components/draft-actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  discardDraft,
  markSent,
  patchDraft,
  regenerateDraft,
} from "@/lib/api";
import type { DraftDetail } from "@/lib/types";

/** Lightweight toggle switch (no shadcn switch primitive available). */
function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-sm"
    >
      <span
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${
          checked ? "bg-primary" : "bg-input"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-background transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </span>
      {label}
    </button>
  );
}

/**
 * Editable draft workspace: subject, email body, cover letter, the optional
 * AI-disclosure P.S. toggle, and the action bar. The P.S. is never persisted to
 * the draft body — it is appended client-side and recorded only on send, so the
 * regeneration prompt never sees it.
 */
export function DraftEditor({
  draft,
  username,
  psDefault,
}: {
  draft: DraftDetail;
  username: string;
  psDefault: string;
}) {
  const router = useRouter();
  const [asunto, setAsunto] = useState(draft.asunto ?? "");
  const [cuerpo, setCuerpo] = useState(draft.cuerpo_email ?? "");
  const [carta, setCarta] = useState(draft.carta_presentacion ?? "");
  const [psEnabled, setPsEnabled] = useState(false);
  const [busy, setBusy] = useState(false);

  const alreadySent = draft.application !== null;
  const psText = psDefault;

  async function save() {
    await patchDraft(draft.id, {
      asunto,
      cuerpo_email: cuerpo,
      carta_presentacion: carta,
    });
  }

  async function handleSave() {
    setBusy(true);
    try {
      await save();
      toast.success("Cambios guardados");
      router.refresh();
    } catch (e) {
      toast.error(`No se pudo guardar: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleMarkSent(method: string, notes: string) {
    setBusy(true);
    try {
      await save();
      await markSent(draft.id, {
        method,
        notes: notes || undefined,
        ps_text: psEnabled ? psText : undefined,
      });
      toast.success("Marcado como enviado");
      router.push(`/${username}/drafts`);
      router.refresh();
    } catch (e) {
      toast.error(`No se pudo marcar como enviado: ${(e as Error).message}`);
      setBusy(false);
    }
  }

  async function handleRegenerate() {
    setBusy(true);
    try {
      const res = await regenerateDraft(draft.id);
      setAsunto(res.asunto ?? "");
      setCuerpo(res.cuerpo_email ?? "");
      setCarta(res.carta_presentacion ?? "");
      if (res.needs_manual_context) {
        toast.warning("Regenerado, pero requiere contexto manual");
      } else {
        toast.success("Borrador regenerado");
      }
      router.refresh();
    } catch (e) {
      toast.error(`No se pudo regenerar: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleDiscard() {
    setBusy(true);
    try {
      await discardDraft(draft.id);
      toast.success("Borrador descartado");
      router.refresh();
    } catch (e) {
      toast.error(`No se pudo descartar: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function copyEmail() {
    const text = psEnabled ? `${cuerpo}\n\n${psText}` : cuerpo;
    await navigator.clipboard.writeText(text);
    toast.success("Email copiado");
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Borrador</CardTitle>
        {draft.estado === "needs_manual_context" && (
          <Badge variant="destructive">Contexto manual</Badge>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div>
          <label className="mb-1 block text-xs text-muted-foreground">Asunto</label>
          <Input
            value={asunto}
            onChange={(e) => setAsunto(e.target.value)}
            disabled={alreadySent}
          />
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs text-muted-foreground">Cuerpo del email</label>
            <Button variant="ghost" size="xs" onClick={copyEmail}>
              Copiar
            </Button>
          </div>
          <Textarea
            value={cuerpo}
            onChange={(e) => setCuerpo(e.target.value)}
            rows={12}
            className="font-mono text-xs"
            disabled={alreadySent}
          />
        </div>

        <div className="flex flex-col gap-2 rounded-md border border-dashed p-3">
          <Switch
            checked={psEnabled}
            onChange={setPsEnabled}
            label="Añadir P.D. sobre asistencia IA"
          />
          {psEnabled && (
            <p className="whitespace-pre-wrap text-xs text-muted-foreground">
              {psText}
            </p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs text-muted-foreground">
            Carta de presentación
          </label>
          <Textarea
            value={carta}
            onChange={(e) => setCarta(e.target.value)}
            rows={10}
            disabled={alreadySent}
          />
        </div>

        {!alreadySent && (
          <Button variant="outline" onClick={handleSave} disabled={busy}>
            Guardar cambios
          </Button>
        )}

        <DraftActions
          busy={busy}
          alreadySent={alreadySent}
          onMarkSent={handleMarkSent}
          onRegenerate={handleRegenerate}
          onDiscard={handleDiscard}
        />
      </CardContent>
    </Card>
  );
}
