---
name: "Burn Rate"
description: "Presupuesto familiar móvil, cálido y claro para una sola casa."
colors:
  paper: "#f6efe4"
  paper-muted: "#efe2d2"
  paper-warm: "#f8e7d3"
  surface: "#fffaf4"
  surface-soft: "#f7efe5"
  surface-neutral: "#fcf7f0"
  line: "#dccab7"
  line-strong: "#b89475"
  ink: "#261a14"
  ink-soft: "#534139"
  muted: "#78665b"
  ember: "#cc5a2b"
  ember-dark: "#9d4019"
  ember-soft: "#f8ebe1"
  plan-accent: "#2f7d74"
  plan-soft: "#e4f4ef"
  expenses-accent: "#d7643b"
  expenses-soft: "#fbece3"
  commitments-accent: "#7252d9"
  commitments-soft: "#eee8ff"
  settings-accent: "#2f65d7"
  settings-soft: "#eaf1ff"
  success: "#2f7d74"
  danger: "#cc5a2b"
  focus: "#a7481d"
typography:
  display:
    fontFamily: "Google Sans, Google Sans Text, Aptos, Segoe UI, Noto Sans, Arial, sans-serif"
    fontSize: "clamp(2.2rem, 8vw, 3rem)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0"
  headline:
    fontFamily: "Google Sans, Google Sans Text, Aptos, Segoe UI, Noto Sans, Arial, sans-serif"
    fontSize: "clamp(1.875rem, 6vw, 2.4rem)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "0"
  title:
    fontFamily: "Google Sans, Google Sans Text, Aptos, Segoe UI, Noto Sans, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "0"
  body:
    fontFamily: "Google Sans Text, Google Sans, Aptos, Segoe UI, Noto Sans, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  label:
    fontFamily: "Google Sans Text, Google Sans, Aptos, Segoe UI, Noto Sans, Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.45
    letterSpacing: "0"
rounded:
  control: "14px"
  surface: "18px"
  panel: "20px"
  pill: "999px"
spacing:
  "2xs": "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  "2xl": "48px"
components:
  button-primary:
    backgroundColor: "{colors.ember}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    rounded: "{rounded.surface}"
    padding: "12px 16px"
    height: "48px"
  button-secondary:
    backgroundColor: "{colors.paper-warm}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.surface}"
    padding: "12px 16px"
    height: "48px"
  input:
    backgroundColor: "{colors.surface-neutral}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "12px 14px"
    height: "48px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "16px"
  bottom-nav-active:
    backgroundColor: "{colors.plan-soft}"
    textColor: "{colors.plan-accent}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 6px"
---

# Design System: Burn Rate

## Overview

**Creative North Star: "La libreta clara de la casa"**

Burn Rate debe sentirse como una libreta familiar bien cuidada en el teléfono: cálida, práctica y suficientemente precisa para confiar en los números sin convertir la casa en un panel corporativo. El producto se usa con prisa y una sola mano, por eso la jerarquía pone primero el siguiente acto: revisar `Presupuesto`, capturar `Gastos`, confirmar `Pagos` o ajustar la casa.

La interfaz es mobile-first, con superficies de papel tibio, tinta café, acentos por tarea y controles grandes. Los nombres visibles usan español plano: `Sistema`, `Claro`, `Oscuro`, `Correo`, `Contraseña`, `Pago mensual` y `Compra a meses`. La app puede verse pulida, pero nunca debe sentirse genérica, fría, financiera ni demasiado analítica.

**Key Characteristics:**
- Cálida y doméstica antes que corporativa.
- Clara y guiada antes que densa.
- Práctica antes que decorativa.
- Precisa en números, suave en tono.
- Mobile-first con objetivos táctiles de 44 a 58px.

## Colors

La paleta parte de papel cálido, tinta café y acentos por flujo. El color explica la tarea activa, no decora la pantalla completa.

### Primary

- **Ember de gasto** (`ember`): acción principal, errores suaves, botones base y estados de gasto. Es cálido y urgente sin sonar alarmista.
- **Ember profundo** (`ember-dark`): texto de énfasis sobre fondos claros, alertas y estados negativos.
- **Ember suave** (`ember-soft`): fondos de aviso, botones de salida y superficies de bajo riesgo.

### Secondary

- **Verde presupuesto** (`plan-accent`): salud del presupuesto, resumen de casa, estados de calma y navegación de `Presupuesto`.
- **Naranja gasto** (`expenses-accent`): captura de `Gastos`, listas de movimiento y acciones de registrar.
- **Morado pagos** (`commitments-accent`): `Pagos`, `Pago mensual`, `Compra a meses` y proyección de compras a meses.
- **Azul ajustes** (`settings-accent`): configuración, invitaciones, tema y ajustes de casa.

### Neutral

- **Papel base** (`paper`): fondo general cálido.
- **Papel apagado** (`paper-muted`): bandas, segmentos inactivos y separaciones suaves.
- **Superficie limpia** (`surface`): tarjetas, paneles, listas y formularios.
- **Superficie neutral** (`surface-neutral`): campos, filas compactas y contenedores de edición.
- **Línea tibia** (`line`): bordes de estructura, nunca divisores pesados.
- **Tinta casa** (`ink`): texto principal.
- **Tinta suave** (`ink-soft`): etiquetas, ayuda y estados secundarios.
- **Muted doméstico** (`muted`): metadatos, notas y conteos.

### Named Rules

**The Task Accent Rule.** Cada vista tiene un acento de tarea: verde para `Presupuesto`, naranja para `Gastos`, morado para `Pagos`, azul para ajustes. No mezcles acentos en el mismo control salvo que el dato venga de una categoría.

**The Warm Paper Rule.** Los fondos principales deben quedarse en papel tibio y superficies crema. Evita blanco puro y negro puro.

## Typography

**Display Font:** Google Sans con fallbacks del sistema.  
**Body Font:** Google Sans Text con fallbacks del sistema.  
**Label Font:** Google Sans Text con peso alto para controles y metadatos.

**Character:** La tipografía es legible y humana, con pesos fuertes para decisiones rápidas y texto de apoyo breve. Los números usan tabular figures para que importes, saldos y pagos se lean estables.

### Hierarchy

- **Display** (800, `clamp(2.2rem, 8vw, 3rem)`, `1`): encabezados de pantalla y resumen principal de `Presupuesto`.
- **Headline** (800, `clamp(1.875rem, 6vw, 2.4rem)`, `1.02`): títulos móviles como `Gastos` y `Pagos del mes`.
- **Title** (800 a 900, `1.125rem` a `1.25rem`, `1.2`): títulos de secciones, paneles y tarjetas.
- **Body** (400 a 600, `1rem`, `1.5`): texto funcional, mensajes y descripciones cortas. Mantén líneas de ayuda por debajo de 52ch en paneles.
- **Label** (700 a 900, `0.75rem` a `0.875rem`, `1.35` a `1.45`): botones, chips, metadatos, campos y estados compactos.

### Named Rules

**The Parent Scan Rule.** Lo importante debe poder entenderse en un vistazo: título fuerte, dato claro, una acción primaria. No escondas la decisión detrás de párrafos.

## Elevation

Burn Rate usa un sistema híbrido: bordes tibios para estructura y sombras suaves para superficies importantes. La profundidad debe sentirse como papel elevado, no como vidrio ni como dashboard oscuro. En reposo, la mayoría de tarjetas tienen la misma sombra ambiental; estados activos se comunican con color, borde y pequeño inset.

### Shadow Vocabulary

- **Soft surface** (`0 18px 40px rgba(74, 46, 24, 0.08)`): paneles, tarjetas de categoría, resumen de casa y sugerencias.
- **Sticky nav** (`0 18px 42px rgba(74, 46, 24, 0.14)`): navegación inferior pegada al inicio de la pantalla.
- **Modal gallery** (`0 28px 68px rgba(35, 25, 19, 0.24)`): galería de iconos y superficies que bloquean el flujo.
- **Inset press** (`inset 0 -1px 0 rgba(44, 28, 20, 0.22)`): botones primarios para dar tactilidad sin brillo.

### Named Rules

**The Paper Lift Rule.** Una sombra debe hacer que la superficie se lea cercana, no lujosa. Si la sombra parece una tarjeta SaaS flotante, bájala.

## Components

### Buttons

- **Shape:** esquinas grandes y táctiles (`18px`) con altura mínima de `48px`.
- **Primary:** fondo de acento por vista, texto crema y peso `800`. Base naranja para acciones generales, morado para `Pagos`, azul para ajustes y naranja gasto para capturar `Gastos`.
- **Secondary:** borde tibio, fondo crema mezclado con papel cálido y texto `ink`.
- **Hover / Focus:** hover sube `1px`; foco visible usa anillo de `3px` con `focus`. Active baja `1px`.
- **Danger:** usa ember profundo y fondo suave, nunca rojo saturado ni copy dramático.

### Chips

- **Style:** chips de contexto y categoría usan borde tintado, fondo suave de la categoría y tipografía alta.
- **State:** seleccionado se marca con borde más fuerte e inset de `1px`, no con sombras pesadas.
- **Usage:** útiles para categorías, cuentas, personas, tema (`Sistema`, `Claro`, `Oscuro`) y filtros breves.

### Cards / Containers

- **Corner Style:** tarjetas principales usan `18px`; login y hero pueden usar `20px`.
- **Background:** `surface` sobre papel cálido; variaciones suaves según tarea.
- **Shadow Strategy:** `shadow-soft` solo para superficies principales. Listas densas pueden usar borde y fondo sin sombra nueva.
- **Border:** siempre completo y bajo contraste. No uses acentos en un solo lado como decoración.
- **Internal Padding:** `16px` por defecto, `24px` cuando el panel guía una configuración o resumen.

### Inputs / Fields

- **Style:** fondo `surface-neutral`, borde `line`, radio `14px`, altura mínima `48px`.
- **Focus:** borde ember mezclado con `line` y anillo suave de `3px`.
- **Copy:** etiquetas simples como `Correo`, `Contraseña`, `Monto`, `Fecha`, `Día de corte`.
- **Error / Disabled:** errores nombran el campo faltante y la siguiente acción. Disabled baja opacidad, no desaparece.

### Navigation

- **Style:** navegación sticky superior en móvil, ancho máximo `420px`, fondo translúcido cálido y sombra `shadow-nav`.
- **Items:** `Presupuesto`, `Gastos`, `Pagos`, ajustes. Cada activo toma su acento y fondo suave.
- **Iconography:** `Presupuesto` usa casa con control, `Gastos` usa billete, `Pagos` usa tarjeta y ajustes usa engrane.
- **Typography:** icono de `20px`, etiqueta de `0.75rem`, peso `600` inactivo y `800` activo.
- **Behavior:** la navegación debe quedar compacta y legible, sin texto truncado incoherente.

### Signature Components

- **Presupuesto overview:** resumen de casa después del ledger, con saldo grande, totales compactos y acento verde.
- **Cycle picker:** selector de ciclo como botón táctil con lista de ciclos recientes; muestra `Ciclo actual`, `Ciclo anterior` y fechas completas sin depender del select nativo.
- **Category ledger:** tarjetas clicables con icono, presupuesto, gasto, compromisos y barra segmentada.
- **Expense capture:** flujo guiado por categoría, cuenta, datos y guardar. La acción principal debe quedar al final del formulario.
- **Payments projection:** `Pagos` separa mensuales y compras a meses. La proyección usa morado como acento de compromiso futuro.
- **Settings disclosure:** opciones avanzadas como color, estado, permisos e icono viven en disclosures, no en el estado default.

## Do's and Don'ts

### Do:

- **Do** mantener el tono visual warm, home-like, clear, practical y mobile-first.
- **Do** usar español plano y vocabulario estándar: `Presupuesto`, `Gastos`, `Pagos`, `Sistema`, `Claro`, `Oscuro`, `Correo`, `Contraseña`, `compras a meses`.
- **Do** poner la siguiente acción de presupuesto familiar primero: revisar saldo, registrar gasto o revisar compromisos.
- **Do** conservar controles táctiles de al menos `44px`, con botones principales de `48px`.
- **Do** usar tabular figures en saldos, importes, pagos y proyecciones.
- **Do** revelar configuración avanzada solo cuando la persona la pide.

### Don't:

- **Don't** hacer que Burn Rate se sienta corporate, analytical, overly technical o SaaS-dashboard generic.
- **Don't** usar blanco puro, negro puro, neón financiero ni gradientes morados dominantes.
- **Don't** usar side-stripe borders decorativos o bordes de un solo lado mayores a `1px`.
- **Don't** usar gradient text, glassmorphism decorativo ni tarjetas idénticas como solución principal.
- **Don't** volver a mostrar `Plan`, `Cargos`, `MSI`, `Email`, `Password`, `Light` o `Dark` como etiquetas visibles.
- **Don't** añadir copy explicando la app dentro de la app cuando una etiqueta o estado corto resuelve el flujo.
