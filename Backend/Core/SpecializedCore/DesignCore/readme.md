# DesignCore

The spatial layout architect and dark-mode UI generation engine. DesignCore generates production-ready HTML/CSS components and full page layouts on demand — triggered by OrchestratorCore when a prompt requests a design output.

## Responsibility

Transform a natural language design description into rendered HTML/CSS output using a template-driven generation engine. All output follows the Vibhu-Oska dark-mode design system.

## Supported Actions

| Action | Description |
|---|---|
| `generate_layout` | Full page HTML/CSS layout from a text description |
| `generate_component` | Single UI component (card, modal, table, nav, stat_card, chat) |
| `generate_dashboard` | Full dashboard with sidebar, stats cards, and content area |
| `list_templates` | Return all available template types |

## Template Library (8 templates)

| Template | Component Types |
|---|---|
| `card` | Info card with title, body, optional footer |
| `modal` | Dialog overlay with header, content, action buttons |
| `table` | Data table with header row and striped body |
| `nav_item` | Navigation list item with icon and label |
| `stat_card` | KPI card with metric, label, and trend indicator |
| `chat` | Chat message bubble (user / assistant variants) |
| `sidebar` | Collapsible navigation sidebar |
| `dashboard` | Full dashboard shell with sidebar + content area |

## Design System

All generated output uses the Vibhu-Oska dark-mode token set:
- Background: `#0d0d0d` / `#1a1a2e`
- Accent: `#7c3aed` (violet) / `#06b6d4` (cyan)
- Typography: Inter, system-ui fallback
- Spacing: 4px base unit grid

## Key File

`DesignCore.py`

## OrchestratorCore Trigger Keywords

```
design, layout, ui component, generate component,
create a dashboard, build a ui, html, css layout,
interface, webpage, make a page
```
