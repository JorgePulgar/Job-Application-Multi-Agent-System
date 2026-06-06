# Ejemplo · `needs_manual_context` — DataPyme (ficticio)

> Datos ficticios. Ilustra qué ocurre cuando el sistema **no** puede producir un
> borrador específico y honesto: en vez de inventar un mensaje genérico, marca
> el draft para revisión manual.

| Campo | Valor |
| --- | --- |
| Plataforma | Jooble |
| Ubicación | Barcelona (híbrido) |
| Puntuación de viabilidad | 61 / 100 |
| Recomendación | Considerar |
| Estado | **`needs_manual_context`** |

---

**Por qué se marcó para contexto manual**

El sistema aplica una **regla de especificidad**: todo borrador debe referenciar
al menos un hecho concreto de la empresa. Tras 2 intentos de generación, no se
encontró un gancho verificable para esta oferta:

- La investigación de empresa no devolvió producto, blog ni nota de prensa
  reciente (web corporativa mínima, sin fuentes fiables).
- La descripción de la oferta es genérica ("buscamos Data Engineer con
  experiencia") sin proyecto ni stack diferenciador.
- El único borrador posible habría sido un mensaje plantilla, que la lista de
  palabras prohibidas y la regla de especificidad rechazan.

**Resultado**

No se generó cuerpo de email ni carta. El draft queda en estado
`needs_manual_context` y aparece marcado en el dashboard, a la espera de que la
persona añada un dato concreto (un contacto, un proyecto conocido, un motivo
real de interés) antes de redactar.

> Esto es intencional: el sistema prefiere no enviar nada genérico. Mejor un
> hueco visible que un mensaje vacío.
