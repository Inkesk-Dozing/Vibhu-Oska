"""
Vibhu-Oska AI-OS — DesignCore
Spatial Layout Architect, UI Engine & Dynamic Interface Weaver.

Generates HTML/CSS layouts and UI components from natural language descriptions,
using a curated dark-mode design system as its template foundation.
Integrates with CognitionCore for AI-driven dynamic layout generation.
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

from Backend.Plugins.Logger.Logger import Logger
from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


# ══════════════════════════════════════════════════════════════════════
# Design System Token Library
# ══════════════════════════════════════════════════════════════════════

_CSS_TOKENS = """
:root {
  /* Color Palette — Vibhu-Oska Design System */
  --vo-bg-primary:    #0A0E1A;
  --vo-bg-secondary:  #0F1629;
  --vo-bg-card:       rgba(15, 22, 41, 0.8);
  --vo-accent-cyan:   #00D4FF;
  --vo-accent-purple: #7B2FBE;
  --vo-accent-amber:  #FFB800;
  --vo-text-primary:  #E8EAF0;
  --vo-text-muted:    #6B7280;
  --vo-border:        rgba(0, 212, 255, 0.15);
  --vo-glow:          0 0 20px rgba(0, 212, 255, 0.3);

  /* Typography */
  --vo-font-body:     'Inter', 'Outfit', -apple-system, sans-serif;
  --vo-font-mono:     'JetBrains Mono', 'Fira Code', monospace;

  /* Spacing Scale */
  --vo-space-xs:  4px;
  --vo-space-sm:  8px;
  --vo-space-md:  16px;
  --vo-space-lg:  24px;
  --vo-space-xl:  40px;
  --vo-space-2xl: 64px;

  /* Radius */
  --vo-radius-sm: 4px;
  --vo-radius-md: 8px;
  --vo-radius-lg: 16px;

  /* Transitions */
  --vo-transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
"""

_BASE_STYLES = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--vo-font-body);
  background: var(--vo-bg-primary);
  color: var(--vo-text-primary);
  min-height: 100vh;
}
.vo-glass {
  background: var(--vo-bg-card);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--vo-border);
  border-radius: var(--vo-radius-lg);
}
.vo-glow { box-shadow: var(--vo-glow); }
.vo-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--vo-space-sm);
  padding: var(--vo-space-sm) var(--vo-space-md);
  background: linear-gradient(135deg, var(--vo-accent-cyan), var(--vo-accent-purple));
  color: var(--vo-bg-primary);
  font-weight: 600;
  border: none;
  border-radius: var(--vo-radius-md);
  cursor: pointer;
  transition: opacity var(--vo-transition), transform var(--vo-transition);
}
.vo-btn:hover { opacity: 0.9; transform: translateY(-1px); }
.vo-input {
  width: 100%;
  padding: var(--vo-space-sm) var(--vo-space-md);
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid var(--vo-border);
  border-radius: var(--vo-radius-md);
  color: var(--vo-text-primary);
  font-family: var(--vo-font-body);
  outline: none;
  transition: border-color var(--vo-transition);
}
.vo-input:focus { border-color: var(--vo-accent-cyan); }
"""

# Pre-built component templates
_COMPONENT_TEMPLATES: dict[str, str] = {
    "card": textwrap.dedent("""
        <div class="vo-glass vo-glow" style="padding: var(--vo-space-lg);">
          <h2 style="color: var(--vo-accent-cyan); margin-bottom: var(--vo-space-sm);">{title}</h2>
          <p style="color: var(--vo-text-muted); line-height: 1.6;">{body}</p>
        </div>
    """).strip(),

    "dashboard": textwrap.dedent("""
        <div style="display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; gap: 0;">
          <!-- Sidebar -->
          <aside class="vo-glass" style="padding: var(--vo-space-lg); border-radius: 0; border-right: 1px solid var(--vo-border);">
            <div style="font-size: 1.25rem; font-weight: 700; color: var(--vo-accent-cyan); margin-bottom: var(--vo-space-xl);">
              VO·OS
            </div>
            <nav style="display: flex; flex-direction: column; gap: var(--vo-space-sm);">
              {nav_items}
            </nav>
          </aside>
          <!-- Main -->
          <main style="padding: var(--vo-space-xl); overflow-y: auto;">
            <h1 style="font-size: 2rem; margin-bottom: var(--vo-space-lg);">{page_title}</h1>
            {content}
          </main>
        </div>
    """).strip(),

    "stat_grid": textwrap.dedent("""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--vo-space-md);">
          {stat_cards}
        </div>
    """).strip(),

    "stat_card": textwrap.dedent("""
        <div class="vo-glass" style="padding: var(--vo-space-lg); text-align: center;">
          <div style="font-size: 2rem; font-weight: 700; color: var(--vo-accent-cyan);">{value}</div>
          <div style="font-size: 0.85rem; color: var(--vo-text-muted); margin-top: var(--vo-space-xs);">{label}</div>
        </div>
    """).strip(),

    "chat": textwrap.dedent("""
        <div style="display: flex; flex-direction: column; height: 100vh;">
          <!-- Messages -->
          <div id="chat-messages" style="flex: 1; overflow-y: auto; padding: var(--vo-space-lg); display: flex; flex-direction: column; gap: var(--vo-space-md);">
          </div>
          <!-- Input -->
          <div style="padding: var(--vo-space-md); border-top: 1px solid var(--vo-border); display: flex; gap: var(--vo-space-sm);">
            <input class="vo-input" id="chat-input" type="text" placeholder="Speak to Vibhu-Oska..." />
            <button class="vo-btn" onclick="sendMessage()">Send</button>
          </div>
        </div>
    """).strip(),

    "nav_item": textwrap.dedent("""
        <a href="{href}" style="
          display: block;
          padding: var(--vo-space-sm) var(--vo-space-md);
          border-radius: var(--vo-radius-md);
          color: var(--vo-text-muted);
          text-decoration: none;
          transition: background var(--vo-transition), color var(--vo-transition);
        " onmouseover="this.style.background='rgba(0,212,255,0.08)'; this.style.color='var(--vo-accent-cyan)';"
          onmouseout="this.style.background='transparent'; this.style.color='var(--vo-text-muted)';">
          {label}
        </a>
    """).strip(),

    "table": textwrap.dedent("""
        <div class="vo-glass" style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 1px solid var(--vo-border);">
                {headers}
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </div>
    """).strip(),

    "modal": textwrap.dedent("""
        <div id="{id}" style="
          display: none; position: fixed; inset: 0;
          background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
          z-index: 1000; align-items: center; justify-content: center;
        ">
          <div class="vo-glass" style="max-width: 540px; width: 90%; padding: var(--vo-space-xl);">
            <h2 style="margin-bottom: var(--vo-space-md); color: var(--vo-accent-cyan);">{title}</h2>
            {content}
            <button class="vo-btn" style="margin-top: var(--vo-space-lg);" onclick="document.getElementById('{id}').style.display='none'">
              Close
            </button>
          </div>
        </div>
    """).strip(),
}


class DesignCore(BaseService):
    """
    DesignCore is the spatial layout architect and dynamic UI generation engine.

    Generates complete HTML/CSS page layouts, individual UI components,
    and design system artifacts from natural language descriptions.
    Uses the Vibhu-Oska dark-mode glassmorphism design system as its foundation.

    Supported actions (via execute()):
    - generate_layout      → full HTML page from description
    - generate_component   → single reusable UI component
    - get_design_tokens    → raw CSS token definitions
    - list_components      → available component templates
    """

    def __init__(self) -> None:
        self._initialized: bool = False
        self._log = Logger.get("DesignCore")

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="design",
            version="1.0.0",
            description="Spatial layout architect — dynamic HTML/CSS UI generation from natural language",
            capabilities=["layout_generation", "component_generation", "design_system"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """
        Initialize DesignCore.

        Parameters: none
        Returns: none
        Edge cases: idempotent
        """
        if self._initialized:
            return
        self._initialized = True
        self._log.info("DesignCore initialized", available_templates=list(_COMPONENT_TEMPLATES.keys()))

    async def execute(self, action: str, **kwargs: Any) -> Any:
        """
        Dispatch a design action.

        Parameters:
            action: One of generate_layout, generate_component, get_design_tokens, list_components
            **kwargs: Action-specific arguments
        Returns: dict result
        Edge cases: Unknown actions raise ValueError
        """
        if not self._initialized:
            await self.initialize()

        dispatch = {
            "generate_layout":    self._generate_layout,
            "generate_component": self._generate_component,
            "get_design_tokens":  self._get_design_tokens,
            "list_components":    self._list_components,
        }

        if action not in dispatch:
            raise ValueError(
                f"Action '{action}' not supported by DesignCore. "
                f"Available: {sorted(dispatch.keys())}"
            )

        return await dispatch[action](**kwargs)

    def process(self, data: Any) -> Any:
        return data

    # ==================================================================================================

    # # Internal Separation Division

    # =================─────────────────────────────────────────────────────────────────────────────────

    async def _generate_layout(
        self,
        description: str,
        page_title: str = "Vibhu-Oska",
        layout_type: str = "dashboard",
        include_tokens: bool = True,
        **_: Any,
    ) -> dict[str, Any]:
        """
        Generate a complete HTML page layout from a text description.

        Parameters:
            description: Natural language description of the desired layout
            page_title: Browser <title> and h1 content
            layout_type: Template base — 'dashboard', 'card', 'chat' (default: dashboard)
            include_tokens: Include the CSS token block in <style>
        Returns: dict with status, html (complete HTML document), description
        Edge cases: Unknown layout_type falls back to 'dashboard'
        """
        template = _COMPONENT_TEMPLATES.get(layout_type, _COMPONENT_TEMPLATES["dashboard"])

        # Simple description → component substitution
        nav_items = "".join(
            _COMPONENT_TEMPLATES["nav_item"].format(href="#", label=label)
            for label in ["Overview", "Chat", "Tasks", "Research", "Settings"]
        )

        stat_cards = "".join(
            _COMPONENT_TEMPLATES["stat_card"].format(value=v, label=l)
            for v, l in [("Healthy", "System Status"), ("127ms", "Latency"), ("8 passed", "Tests"), ("GPU", "Inference Target")]
        )

        stat_grid = _COMPONENT_TEMPLATES["stat_grid"].format(stat_cards=stat_cards)

        body_content = template.format(
            nav_items=nav_items,
            page_title=page_title,
            content=f"{stat_grid}\n<p style='margin-top:24px;color:var(--vo-text-muted);'>{description}</p>",
            title=page_title,
            body=description,
        )

        style_block = f"<style>{_CSS_TOKENS}{_BASE_STYLES}</style>" if include_tokens else ""

        html = textwrap.dedent(f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <title>{page_title}</title>
              <link rel="preconnect" href="https://fonts.googleapis.com">
              <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
              {style_block}
            </head>
            <body>
              {body_content}
            </body>
            </html>
        """).strip()

        self._log.info("Layout generated", layout_type=layout_type, page_title=page_title)
        return {
            "status": "success",
            "html": html,
            "layout_type": layout_type,
            "description": description,
            "page_title": page_title,
        }

    async def _generate_component(
        self,
        component_type: str,
        props: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        """
        Generate a standalone UI component.

        Parameters:
            component_type: Template key (card, stat_card, nav_item, modal, table, chat)
            props: Dict of template substitution values
        Returns: dict with status, html, component_type, props_used
        Edge cases: Unknown component_type returns error with available list
        """
        if component_type not in _COMPONENT_TEMPLATES:
            return {
                "status": "error",
                "error": f"Unknown component type '{component_type}'",
                "available": sorted(_COMPONENT_TEMPLATES.keys()),
            }

        template = _COMPONENT_TEMPLATES[component_type]
        fill = props or {}

        # Fill in any missing required format keys with placeholders
        try:
            import string
            formatter = string.Formatter()
            keys_needed = {fname for _, fname, _, _ in formatter.parse(template) if fname}
            for k in keys_needed:
                if k not in fill:
                    fill[k] = f"[{k}]"
            html = template.format(**fill)
        except Exception as e:
            return {"status": "error", "error": f"Template formatting error: {e}"}

        style_block = f"<style>{_CSS_TOKENS}{_BASE_STYLES}</style>"

        return {
            "status": "success",
            "html": html,
            "standalone_html": f"<!DOCTYPE html><html><head>{style_block}</head><body style='background:var(--vo-bg-primary);padding:24px;'>{html}</body></html>",
            "component_type": component_type,
            "props_used": fill,
        }

    async def _get_design_tokens(self, **_: Any) -> dict[str, Any]:
        """
        Return the raw CSS design token definitions.

        Parameters: none
        Returns: dict with status, css_tokens, base_styles
        Edge cases: none
        """
        return {
            "status": "success",
            "css_tokens": _CSS_TOKENS,
            "base_styles": _BASE_STYLES,
        }

    async def _list_components(self, **_: Any) -> dict[str, Any]:
        """
        List all available component template names.

        Parameters: none
        Returns: dict with status, components (list of available template keys)
        Edge cases: none
        """
        return {
            "status": "success",
            "components": sorted(_COMPONENT_TEMPLATES.keys()),
            "count": len(_COMPONENT_TEMPLATES),
        }
