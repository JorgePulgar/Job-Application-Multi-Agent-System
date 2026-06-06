# Antes de empezar la Fase 11 (Warm Outreach)

v1 (Fases 1-10) está completo y etiquetado como `v1.0.0`. **No se debe empezar
la Fase 11 sin aprobación explícita.** Esta lista reúne todo lo pendiente antes
de extender el sistema.

## 1. Acciones manuales pendientes (entorno externo)

Estas no se pueden hacer desde el entorno de build (sin `gh`, sin claves):

- [ ] **Crear la GitHub Release `v1.0.0`.** El tag ya está empujado; falta
      adjuntar las notas. Ver `tasks/phase-10-polish/05-portfolio-tag.md` o el
      comando `gh release create` / la UI web. Cuerpo = "Visión general" de
      `docs/architecture.md` + capturas.
- [ ] **Verificación en vivo de la Fase 9 (automatización).** Pendiente desde
      que se construyó; ver `docs/operations.md` → "Pending manual verification":
  - [ ] Añadir los 12 secretos de CLAUDE.md §5 en GitHub
        (Settings → Secrets and variables → Actions), incluidos
        `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
  - [ ] Lanzar `daily-run` a mano (Actions → Run workflow) primero con
        **Dry run**, luego una ejecución real.
  - [ ] Confirmar: workflow en verde, aparece la rama `data` con `state.db`,
        llega el resumen por Telegram (y la alerta de coste solo si supera
        `DAILY_COST_ALERT_EUR`).

## 2. Decisión pendiente: perfiles en CI

El cron `daily-run` ejecuta `orchestrator run --all-users`, que descubre usuarios
en `config/users/*.yaml`. Esos YAML están **gitignored**, así que en CI no hay
usuarios y el run no produce nada.

- [ ] Decidir cómo proveer los perfiles al runner antes de confiar en el cron:
      commit cifrado, secreto de Actions que se materializa a YAML al inicio del
      job, u otra opción. (No resuelto en v1; elegir antes de depender del cron.)

## 3. Validación en uso real

- [ ] **Usar v1 en real durante al menos unas semanas** antes de decidir
      extender. Es el criterio del brief: medir si Flow B aporta antes de añadir
      el outreach en caliente.

## 4. Aprobación para la Fase 11

- [ ] Dar la aprobación explícita ("approve Phase 11"). Solo entonces se empieza
      por `tasks/phase-11-warm-outreach/01-schema-additions.md`.

> Recordatorio de alcance (CLAUDE.md): la Fase 11 es outreach **en caliente** a
> leads de IA/ML en empresas ya investigadas en Flow B. Nunca se scrapea
> LinkedIn. Flow A (frío) sigue fuera de alcance. Límite: 2 drafts de outreach
> por usuario y día, 10 por semana.
