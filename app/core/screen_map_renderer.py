"""Render a ScreenMap into React + Tailwind scaffold files.

Component-type dispatch system: each ScreenMap component type has a
renderer function that produces TSX. The planning agent specifies
WHAT goes on each screen; this module builds it.

Called from build_plan_renderer._render_vite_scaffold_from_screen_map().
"""

from __future__ import annotations

import re
from collections.abc import Callable

from app.core.schemas_screen_map import (
    Component,
    ImageSlot,
    MockContext,
    Screen,
    ScreenMap,
)

# =============================================================================
# Helpers
# =============================================================================


def _escape_jsx(text: str) -> str:
    """Escape text for safe JSX embedding."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
    )


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def _pascal(text: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9 ]", " ", text).split()[:4]
    return "".join(w.capitalize() for w in words) + "Page"


def _kebab_to_pascal(name: str) -> str:
    """Convert kebab-case or camelCase icon name to PascalCase for lucide-react."""
    if not name:
        return "Circle"
    # Split on hyphens, uppercase first letter but preserve rest (capitalize() would
    # destroy internal caps like layoutDashboard → Layoutdashboard)
    parts = name.split("-")
    return "".join(p[0].upper() + p[1:] if p else "" for p in parts)


def _icon_svg(name: str, cls: str = "w-5 h-5") -> str:
    """Generate a LucideIcon component reference."""
    pascal = _kebab_to_pascal(name)
    return f'<LucideIcon name="{pascal}" className="{cls}" />'


def _render_image_slot(slot: ImageSlot) -> str:
    """Render an image slot to JSX."""
    if slot.source == "url":
        fb = slot.fallback_gradient or (
            "linear-gradient(135deg, var(--color-primary), var(--color-secondary))"
        )
        return (
            '<div className="relative overflow-hidden rounded-xl">\n'
            f'  <img src="{slot.value}" '
            f'alt="{_escape_jsx(slot.alt)}" '
            f'className="w-full h-full object-cover" '
            "onError={(e) => { "
            "(e.target as HTMLImageElement).style.display='none' "
            "}} />\n"
            '  <div className="absolute inset-0 -z-10" '
            f'style={{{{ background: "{fb}" }}}} />\n'
            "</div>"
        )
    elif slot.source == "gradient":
        return (
            '<div className="w-full h-full rounded-xl" '
            f'style={{{{ background: "{slot.value}" }}}} />'
        )
    elif slot.source == "initials":
        bg = "bg-primary" if "primary" in (slot.fallback_gradient or "primary") else "bg-accent"
        return (
            f'<div className="{bg} text-white rounded-full w-10 h-10 '
            'flex items-center justify-center text-sm font-semibold">'
            f"{_escape_jsx(slot.value)}</div>"
        )
    elif slot.source == "icon":
        return _icon_svg(slot.value, "w-8 h-8 text-primary")
    else:
        return '<div className="w-full h-32 bg-gray-100 rounded-xl" />'


# =============================================================================
# Component Renderers
# =============================================================================


def _render_hero(c: Component, screen: Screen, ctx: MockContext) -> str:
    p = c.props
    headline = _escape_jsx(p.get("headline", screen.title))
    subtitle = _escape_jsx(p.get("subtitle", ""))
    cta1 = _escape_jsx(p.get("cta_primary", "Get Started"))
    cta2 = p.get("cta_secondary")
    bg = p.get("background", "gradient")
    # Determine CTA navigation target from screen_map context
    cta_route = p.get("_cta_route", "")

    bg_class = "gradient-hero" if bg == "gradient" else "bg-gray-900"
    lines = [
        f'<section className="{bg_class} text-white py-20 px-8 rounded-2xl mb-8">',
        '  <div className="max-w-3xl mx-auto text-center">',
        f'    <h1 className="font-heading text-4xl md:text-5xl font-bold mb-4">{headline}</h1>',
    ]
    if subtitle:
        lines.append(
            f'    <p className="text-lg text-white/80 mb-8 max-w-xl mx-auto">{subtitle}</p>'
        )
    lines.append('    <div className="flex gap-4 justify-center">')
    if cta_route:
        lines.append(
            f'      <button onClick={{() => navigate("{cta_route}")}} '
            'className="bg-white text-gray-900 '
            "font-semibold px-8 py-3 "
            'rounded-full hover:shadow-lg transition-shadow cursor-pointer">'
            f"{cta1}</button>"
        )
    else:
        lines.append(
            '      <button className="bg-white text-gray-900 '
            "font-semibold px-8 py-3 "
            'rounded-full hover:shadow-lg transition-shadow">'
            f"{cta1}</button>"
        )
    if cta2:
        lines.append(
            '      <button className="border-2 border-white/60 '
            "text-white px-8 py-3 "
            'rounded-full hover:bg-white/10 transition-colors">'
            f"{_escape_jsx(cta2)}</button>"
        )
    lines.append("    </div>")
    lines.append("  </div>")
    lines.append("</section>")
    return "\n".join(lines)


def _render_metric_grid(c: Component, screen: Screen, ctx: MockContext) -> str:
    metrics = c.props.get("metrics", [])
    if not metrics:
        return ""
    colors = [
        "bg-primary/10 text-primary",
        "bg-accent/10 text-accent",
        "bg-secondary/10 text-secondary",
        "bg-green-50 text-green-600",
    ]
    cols = min(len(metrics), 4)
    lines = [f'<div className="grid grid-cols-2 md:grid-cols-{cols} gap-4 mb-8">']
    for i, m in enumerate(metrics):
        color = colors[i % len(colors)]
        label = _escape_jsx(str(m.get("label", "")))
        value = _escape_jsx(str(m.get("value", "0")))
        trend = m.get("trend", "")
        icon = m.get("icon", "")
        lines.append('  <Card className="!p-4">')
        lines.append('    <div className="flex items-center justify-between mb-2">')
        lines.append(
            '      <span className="text-xs font-medium '
            'text-gray-500 uppercase tracking-wide">'
            f"{label}</span>"
        )
        if icon:
            icon_el = _icon_svg(icon, "w-4 h-4")
            lines.append(f'      <span className="{color} rounded-lg p-2 text-sm">{icon_el}</span>')
        lines.append("    </div>")
        lines.append(
            f'    <p className="text-2xl font-heading font-bold text-gray-900">{value}</p>'
        )
        if trend:
            is_pos = not str(trend).startswith("-")
            tc = "text-green-600" if is_pos else "text-red-500"
            trend_text = _escape_jsx(str(trend))
            lines.append(f'    <p className="text-sm {tc} mt-1">{trend_text}</p>')
        lines.append("  </Card>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_form(c: Component, screen: Screen, ctx: MockContext) -> str:
    fields = c.props.get("fields", [])
    submit = _escape_jsx(c.props.get("submit_label", "Submit"))
    desc = c.props.get("description", "")
    lines = ['<div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-8">']
    if desc:
        lines.append(f'  <p className="text-gray-600 mb-6">{_escape_jsx(desc)}</p>')
    lines.append('  <div className="space-y-5">')
    for f in fields:
        name = _escape_jsx(f.get("name", ""))
        label = _escape_jsx(f.get("label", name.replace("_", " ").title()))
        ftype = f.get("type", "text")
        placeholder = _escape_jsx(f.get("placeholder", ""))
        options = f.get("options", [])
        required = f.get("required", False)
        req_mark = ' <span className="text-red-400">*</span>' if required else ""

        lines.append("    <div>")
        lines.append(
            '      <label className="block text-sm '
            'font-medium text-gray-700 mb-1">'
            f"{label}{req_mark}</label>"
        )
        # Common: value binding and onChange handler
        value_bind = f'value={{formData["{name}"] || ""}}'
        on_change = f'onChange={{(e) => setFormData(p => ({{...p, "{name}": e.target.value}}))}} '
        if ftype == "select" and options:
            lines.append(
                f"      <select {value_bind} {on_change}"
                'className="w-full rounded-xl '
                "border-gray-200 border px-4 py-2.5 "
                "text-gray-900 focus:ring-2 "
                'focus:ring-primary/30 focus:border-primary">'
            )
            lines.append('        <option value="">Select...</option>')
            for opt in options:
                lines.append(f"        <option>{_escape_jsx(str(opt))}</option>")
            lines.append("      </select>")
        elif ftype == "textarea":
            lines.append(
                f"      <textarea rows={{4}} "
                f'placeholder="{placeholder}" '
                f"{value_bind} {on_change}"
                'className="w-full rounded-xl border-gray-200 '
                "border px-4 py-2.5 text-gray-900 focus:ring-2 "
                "focus:ring-primary/30 focus:border-primary "
                'resize-none" />'
            )
        elif ftype == "radio" and options:
            lines.append('      <div className="flex flex-wrap gap-3 mt-1">')
            for opt in options:
                opt_esc = _escape_jsx(str(opt))
                lines.append(
                    '        <label className="flex items-center '
                    "gap-2 px-4 py-2 rounded-full border "
                    "border-gray-200 cursor-pointer "
                    "hover:border-primary/40 transition-colors "
                    'text-sm">'
                    f'<input type="radio" name="{name}" '
                    f'value="{opt_esc}" '
                    f'checked={{formData["{name}"] === "{opt_esc}"}} '
                    f"{on_change}"
                    f'className="text-primary" />'
                    f" {opt_esc}</label>"
                )
            lines.append("      </div>")
        elif ftype == "checkbox" and options:
            lines.append('      <div className="grid grid-cols-2 gap-3 mt-1">')
            for opt in options:
                lines.append(
                    '        <label className="flex items-center '
                    "gap-2 px-4 py-2.5 rounded-xl border "
                    "border-gray-200 cursor-pointer "
                    "hover:border-primary/40 transition-colors "
                    'text-sm">'
                    '<input type="checkbox" '
                    'className="text-primary rounded" />'
                    f" {_escape_jsx(str(opt))}</label>"
                )
            lines.append("      </div>")
        elif ftype == "range":
            lines.append(
                '      <input type="range" className="w-full accent-primary" min="0" max="100" />'
            )
        else:
            lines.append(
                f'      <input type="{ftype}" '
                f'placeholder="{placeholder}" '
                f"{value_bind} {on_change}"
                'className="w-full rounded-xl border-gray-200 '
                "border px-4 py-2.5 text-gray-900 focus:ring-2 "
                'focus:ring-primary/30 focus:border-primary" />'
            )
        lines.append("    </div>")
    lines.append("  </div>")
    lines.append(
        "  <button onClick={() => { toast('Saved successfully!'); setFormData({}) }} "
        'className="mt-6 w-full bg-primary text-white '
        "font-semibold py-3 rounded-full hover:shadow-lg "
        'hover:shadow-primary/20 transition-all cursor-pointer">'
        f"{submit}</button>"
    )
    lines.append("</div>")
    return "\n".join(lines)


def _render_data_table(c: Component, screen: Screen, ctx: MockContext) -> str:
    columns = c.props.get("columns", [])
    rows = c.props.get("rows", [])
    searchable = c.props.get("searchable", False)
    filters = c.props.get("filters", [])

    # Use _tableRows as the variable name for filtered data
    has_dict_rows = isinstance(rows, list) and rows and isinstance(rows[0], dict)

    lines = [
        '<div className="bg-white rounded-2xl shadow-sm '
        'border border-gray-100 overflow-hidden mb-8">'
    ]
    if searchable or filters:
        lines.append(
            '  <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-4">'
        )
        if searchable:
            lines.append(
                '    <input type="text" placeholder="Search..." '
                "value={tableSearch} "
                "onChange={(e) => setTableSearch(e.target.value)} "
                'className="flex-1 rounded-xl border-gray-200 '
                "border px-4 py-2 text-sm focus:ring-2 "
                'focus:ring-primary/30 focus:border-primary" />'
            )
        for filt in filters or []:
            filt_text = _escape_jsx(str(filt))
            lines.append(
                '    <select className="rounded-xl '
                'border-gray-200 border px-3 py-2 text-sm">'
                f"<option>{filt_text}: All</option></select>"
            )
        lines.append("  </div>")

    lines.append('  <div className="overflow-x-auto">')
    lines.append('    <table className="w-full">')
    lines.append("      <thead>")
    lines.append('        <tr className="border-b border-gray-100">')
    for col in columns:
        label = col.get("label", col.get("key", "")) if isinstance(col, dict) else str(col)
        lines.append(
            '          <th className="px-6 py-3 text-left '
            "text-xs font-semibold text-gray-500 uppercase "
            f'tracking-wider">{_escape_jsx(label)}</th>'
        )
    lines.append("        </tr>")
    lines.append("      </thead>")
    lines.append("      <tbody>")

    if has_dict_rows:
        for row in rows[:10]:
            lines.append(
                '        <tr className="border-b border-gray-50 '
                'hover:bg-gray-50/50 cursor-pointer hover:bg-primary/5 transition-colors">'
            )
            for col in columns:
                key = col.get("key", col.get("label", "")) if isinstance(col, dict) else str(col)
                val = _escape_jsx(str(row.get(key, "")))
                lines.append(
                    f'          <td className="px-6 py-4 text-sm text-gray-700">{val}</td>'
                )
            lines.append("        </tr>")
    else:
        row_count = rows if isinstance(rows, int) else 5
        for r in range(row_count):
            lines.append('        <tr className="border-b border-gray-50 hover:bg-gray-50/50">')
            for ci, _col in enumerate(columns):
                if ci == 0:
                    lines.append(
                        '          <td className="px-6 py-4 '
                        'text-sm font-medium text-gray-900">'
                        f"Item {r + 1}</td>"
                    )
                else:
                    lines.append(
                        '          <td className="px-6 py-4 text-sm text-gray-500">\u2014</td>'
                    )
            lines.append("        </tr>")

    lines.append("      </tbody>")
    lines.append("    </table>")
    lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_chart(c: Component, screen: Screen, ctx: MockContext) -> str:
    chart_type = c.props.get("chart_type", "area")
    title = _escape_jsx(c.props.get("title", "Chart"))
    series = c.props.get("mock_series", [])
    x_labels = c.props.get("x_labels", [])

    lines = ['<div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">']
    lines.append(f'  <h3 className="font-heading font-semibold text-gray-900 mb-4">{title}</h3>')
    if series and series[0].get("data"):
        data = series[0]["data"]
        max_val = max(data) if data else 1
        lines.append('  <div className="flex items-end gap-1 h-48">')
        for i, val in enumerate(data):
            pct = int((val / max_val) * 100) if max_val else 0
            label = x_labels[i] if i < len(x_labels) else ""
            lbl_esc = _escape_jsx(str(label))
            if chart_type == "bar":
                lines.append(
                    '    <div className="flex-1 flex '
                    'flex-col items-center">'
                    '<div className="w-full bg-primary/80 '
                    "rounded-t-md transition-all "
                    'hover:bg-primary" '
                    f'style={{{{ height: "{pct}%" }}}} '
                    f'title="{val}" />'
                    '<span className="text-[10px] '
                    f'text-gray-400 mt-1">{lbl_esc}</span>'
                    "</div>"
                )
            else:
                lines.append(
                    '    <div className="flex-1 flex '
                    'flex-col items-center">'
                    '<div className="w-full '
                    "bg-gradient-to-t from-primary/20 "
                    'to-primary/60 rounded-t-md" '
                    f'style={{{{ height: "{pct}%" }}}} '
                    f'title="{val}" />'
                    '<span className="text-[10px] '
                    f'text-gray-400 mt-1">{lbl_esc}</span>'
                    "</div>"
                )
        lines.append("  </div>")
    else:
        lines.append(
            '  <div className="h-48 bg-gray-50 rounded-xl flex items-center justify-center">'
        )
        lines.append(f'    <p className="text-gray-400 text-sm">{chart_type} chart</p>')
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_card_grid(c: Component, screen: Screen, ctx: MockContext) -> str:
    cards = c.props.get("cards", [])
    cols = c.props.get("columns", 3)
    border_colors = [
        "border-l-primary",
        "border-l-accent",
        "border-l-secondary",
        "border-l-green-500",
        "border-l-purple-500",
        "border-l-rose-500",
    ]
    lines = [f'<div className="grid grid-cols-1 md:grid-cols-{cols} gap-6 mb-8">']
    for i, card in enumerate(cards):
        title = _escape_jsx(card.get("title", ""))
        desc = _escape_jsx(card.get("description", ""))
        badge = card.get("badge", "")
        bc = border_colors[i % len(border_colors)]
        lines.append(
            f'  <Card className="border-l-4 {bc} !p-0 cursor-pointer '
            'hover:shadow-md transition-shadow">'
        )
        lines.append('    <div className="p-6">')
        lines.append('      <div className="flex items-start justify-between mb-2">')
        lines.append(
            f'        <h4 className="font-heading font-semibold text-gray-900">{title}</h4>'
        )
        if badge:
            badge_esc = _escape_jsx(str(badge))
            lines.append(f'        <Badge variant="accent">{badge_esc}</Badge>')
        lines.append("      </div>")
        if desc:
            lines.append(f'      <p className="text-sm text-gray-600 leading-relaxed">{desc}</p>')
        lines.append("    </div>")
        lines.append("  </Card>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_activity_feed(c: Component, screen: Screen, ctx: MockContext) -> str:
    entries = c.props.get("entries", [])
    lines = [
        '<Card className="mb-8" header={'
        '<h3 className="font-heading font-semibold text-gray-900">Recent Activity</h3>'
        "}>"
    ]
    lines.append('  <div className="space-y-4">')
    for e in entries[:8]:
        user = _escape_jsx(e.get("user", "User"))
        action = _escape_jsx(e.get("action", ""))
        time_str = _escape_jsx(e.get("time", ""))
        initials = user[:2].upper()
        lines.append('    <div className="flex items-start gap-3">')
        lines.append(
            '      <div className="bg-primary/10 text-primary '
            "rounded-full w-8 h-8 flex items-center "
            "justify-center text-xs font-semibold "
            f'flex-shrink-0">{initials}</div>'
        )
        lines.append('      <div className="flex-1 min-w-0">')
        lines.append(
            '        <p className="text-sm text-gray-700">'
            f'<span className="font-medium">{user}</span> '
            f"{action}</p>"
        )
        if time_str:
            lines.append(f'        <p className="text-xs text-gray-400 mt-0.5">{time_str}</p>')
        lines.append("      </div>")
        lines.append("    </div>")
    lines.append("  </div>")
    lines.append("</Card>")
    return "\n".join(lines)


def _render_stats_banner(c: Component, screen: Screen, ctx: MockContext) -> str:
    stats = c.props.get("stats", [])
    lines = ['<div className="gradient-hero rounded-2xl p-6 mb-8">']
    lines.append('  <div className="flex flex-wrap justify-around gap-6">')
    for s in stats:
        label = _escape_jsx(str(s.get("label", "")))
        value = _escape_jsx(str(s.get("value", "")))
        lines.append('    <div className="text-center">')
        lines.append(f'      <p className="text-3xl font-heading font-bold text-white">{value}</p>')
        lines.append(f'      <p className="text-sm text-white/70 mt-1">{label}</p>')
        lines.append("    </div>")
    lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_timeline(c: Component, screen: Screen, ctx: MockContext) -> str:
    events = c.props.get("events", [])
    orientation = c.props.get("orientation", "vertical")
    lines = ['<div className="mb-8">']
    if orientation == "horizontal":
        lines.append('  <div className="flex items-start overflow-x-auto gap-0 pb-4">')
        for i, ev in enumerate(events):
            title = _escape_jsx(ev.get("title", ""))
            desc = _escape_jsx(ev.get("description", ""))
            status = ev.get("status", "")
            dot = "bg-primary" if status == "complete" else "bg-gray-300"
            lines.append('    <div className="flex flex-col items-center min-w-[140px]">')
            lines.append(f'      <div className="w-4 h-4 {dot} rounded-full z-10" />')
            if i < len(events) - 1:
                lines.append('      <div className="w-full h-0.5 bg-gray-200 -mt-2 mb-2" />')
            lines.append(
                '      <p className="text-sm font-medium '
                f'text-gray-900 mt-2 text-center">{title}</p>'
            )
            if desc:
                lines.append(f'      <p className="text-xs text-gray-500 text-center">{desc}</p>')
            lines.append("    </div>")
        lines.append("  </div>")
    else:
        lines.append('  <div className="relative pl-8 space-y-6">')
        lines.append('    <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-gray-200" />')
        for ev in events:
            title = _escape_jsx(ev.get("title", ""))
            desc = _escape_jsx(ev.get("description", ""))
            date = _escape_jsx(ev.get("date", ""))
            status = ev.get("status", "")
            dot = "bg-primary" if status == "complete" else "bg-gray-300"
            lines.append('    <div className="relative">')
            lines.append(
                '      <div className="absolute -left-[22px] '
                f"w-3 h-3 {dot} rounded-full "
                'ring-4 ring-white" />'
            )
            lines.append(f'      <p className="font-medium text-gray-900">{title}</p>')
            if desc:
                lines.append(f'      <p className="text-sm text-gray-600 mt-0.5">{desc}</p>')
            if date:
                lines.append(f'      <p className="text-xs text-gray-400 mt-1">{date}</p>')
            lines.append("    </div>")
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_tabs(c: Component, screen: Screen, ctx: MockContext) -> str:
    tabs = c.props.get("tabs", [])
    default_tab = c.props.get("default_tab", 0)
    tab_items = []
    for i, tab in enumerate(tabs):
        label = _escape_jsx(tab.get("label", f"Tab {i + 1}"))
        summary = _escape_jsx(tab.get("content_summary", ""))
        content = f'<p className="text-gray-600">{summary}</p>' if summary else "<div />"
        tab_items.append(f'    {{ label: "{label}", content: {content} }}')
    items_str = ",\n".join(tab_items)
    return f"<TabGroup\n  defaultIndex={{{default_tab}}}\n  items={{[\n{items_str}\n  ]}}\n/>"


def _render_horizon_roadmap(c: Component, screen: Screen, ctx: MockContext) -> str:
    h2 = c.props.get("h2_features", [])
    h3 = c.props.get("h3_features", [])
    lines = ['<div className="space-y-8 mb-8">']
    if h2:
        lines.append("  <div>")
        lines.append(
            '    <h3 className="font-heading text-lg '
            "font-semibold text-gray-900 mb-4 "
            'flex items-center gap-2">'
        )
        lines.append(
            '      <span className="bg-accent/10 text-accent '
            "text-xs px-2 py-0.5 rounded-full "
            'font-medium">H2</span>'
        )
        lines.append("      Coming Next</h3>")
        lines.append('    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">')
        for feat in h2:
            name = _escape_jsx(feat.get("name", ""))
            desc = _escape_jsx(feat.get("description", ""))
            lines.append(
                '      <div className="bg-accent/5 border '
                'border-accent/20 rounded-xl p-5">'
                '<h4 className="font-medium '
                f'text-gray-900">{name}</h4>'
                '<p className="text-sm text-gray-600 '
                f'mt-1">{desc}</p></div>'
            )
        lines.append("    </div>")
        lines.append("  </div>")
    if h3:
        lines.append("  <div>")
        lines.append(
            '    <h3 className="font-heading text-lg '
            "font-semibold text-gray-900 mb-4 "
            'flex items-center gap-2">'
        )
        lines.append(
            '      <span className="bg-secondary/10 '
            "text-secondary text-xs px-2 py-0.5 "
            'rounded-full font-medium">H3</span>'
        )
        lines.append("      Future Vision</h3>")
        lines.append('    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">')
        for feat in h3:
            name = _escape_jsx(feat.get("name", ""))
            desc = _escape_jsx(feat.get("description", ""))
            lines.append(
                '      <div className="bg-gray-50 border '
                'border-gray-200 rounded-xl p-4">'
                '<h4 className="font-medium '
                f'text-gray-800 text-sm">{name}</h4>'
                '<p className="text-xs text-gray-500 '
                f'mt-1">{desc}</p></div>'
            )
        lines.append("    </div>")
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_chat_interface(c: Component, screen: Screen, ctx: MockContext) -> str:
    messages = c.props.get("messages", [])
    placeholder = _escape_jsx(c.props.get("input_placeholder", "Type a message..."))

    # Serialize initial messages for state
    init_msgs = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        init_msgs.append({"role": role, "content": content})

    lines = [
        '<div className="bg-white rounded-2xl shadow-sm '
        "border border-gray-100 overflow-hidden mb-8 "
        'flex flex-col" style={{ height: "400px" }}>'
    ]
    lines.append('  <div className="flex-1 overflow-y-auto p-6 space-y-4">')
    lines.append("    {chatMessages.map((msg, i) => (")
    lines.append("      msg.role === 'assistant' ? (")
    lines.append('        <div key={i} className="flex gap-3">')
    lines.append(
        '          <div className="bg-primary/10 text-primary '
        "rounded-full w-8 h-8 flex items-center "
        "justify-center text-xs font-bold "
        'flex-shrink-0">AI</div>'
    )
    lines.append(
        '          <div className="bg-gray-50 rounded-2xl '
        'rounded-tl-sm px-4 py-3 max-w-[80%]">'
        '<p className="text-sm text-gray-700">'
        "{msg.content}</p></div>"
    )
    lines.append("        </div>")
    lines.append("      ) : (")
    lines.append('        <div key={i} className="flex gap-3 justify-end">')
    lines.append(
        '          <div className="bg-primary text-white '
        "rounded-2xl rounded-tr-sm px-4 py-3 "
        'max-w-[80%]">'
        '<p className="text-sm">{msg.content}</p></div>'
    )
    lines.append("        </div>")
    lines.append("      )")
    lines.append("    ))}")
    lines.append("  </div>")
    lines.append('  <div className="border-t border-gray-100 p-4 flex gap-3">')
    lines.append(
        f'    <input type="text" placeholder="{placeholder}" '
        "value={chatInput} "
        "onChange={(e) => setChatInput(e.target.value)} "
        "onKeyDown={(e) => { if (e.key === 'Enter' && chatInput.trim()) { "
        "setChatMessages(m => [...m, {role:'user', content: chatInput}]); "
        "setChatInput('') } }} "
        'className="flex-1 rounded-full border-gray-200 '
        "border px-5 py-2.5 text-sm focus:ring-2 "
        'focus:ring-primary/30 focus:border-primary" />'
    )
    lines.append(
        "    <button onClick={() => { if (chatInput.trim()) { "
        "setChatMessages(m => [...m, {role:'user', content: chatInput}]); "
        "setChatInput('') } }} "
        'className="bg-primary text-white '
        "rounded-full px-6 py-2.5 text-sm font-medium "
        'hover:shadow-lg transition-shadow cursor-pointer">Send</button>'
    )
    lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_kanban(c: Component, screen: Screen, ctx: MockContext) -> str:
    columns = c.props.get("columns", [])
    lines = ['<div className="flex gap-4 overflow-x-auto pb-4 mb-8">']
    for col in columns:
        col_title = _escape_jsx(col.get("title", ""))
        cards = col.get("cards", [])
        lines.append('  <div className="min-w-[280px] flex-shrink-0">')
        lines.append(
            '    <h4 className="font-medium text-gray-700 '
            f'text-sm mb-3 px-1">{col_title} '
            f'<span className="text-gray-400">'
            f"({len(cards)})</span></h4>"
        )
        lines.append('    <div className="space-y-3">')
        for card in cards:
            ct = _escape_jsx(card.get("title", ""))
            assignee = _escape_jsx(card.get("assignee", ""))
            tag = card.get("tag", "")
            lines.append(
                '      <div className="bg-white rounded-xl '
                "border border-gray-100 p-4 shadow-sm "
                "hover:shadow-md transition-shadow "
                'cursor-pointer">'
            )
            lines.append(f'        <p className="text-sm font-medium text-gray-900">{ct}</p>')
            if assignee or tag:
                lines.append('        <div className="flex items-center justify-between mt-2">')
                if assignee:
                    lines.append(
                        f'          <span className="text-xs text-gray-500">{assignee}</span>'
                    )
                if tag:
                    tag_esc = _escape_jsx(str(tag))
                    lines.append(
                        '          <span className="text-xs '
                        "bg-primary/10 text-primary px-2 "
                        f'py-0.5 rounded-full">{tag_esc}'
                        "</span>"
                    )
                lines.append("        </div>")
            lines.append("      </div>")
        lines.append("    </div>")
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_calendar(c: Component, screen: Screen, ctx: MockContext) -> str:
    events = c.props.get("events", [])
    lines = ['<div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">']
    lines.append(
        '  <div className="grid grid-cols-7 gap-px bg-gray-200 rounded-xl overflow-hidden">'
    )
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        lines.append(
            '    <div className="bg-gray-50 p-2 text-center '
            f'text-xs font-medium text-gray-500">{day}</div>'
        )
    for d in range(1, 29):
        day_events = [e for e in events if str(d) in str(e.get("date", ""))]
        lines.append('    <div className="bg-white p-2 min-h-[80px]">')
        lines.append(f'      <span className="text-xs text-gray-400">{d}</span>')
        for ev in day_events[:2]:
            color = ev.get("color", "primary")
            ev_title = _escape_jsx(ev.get("title", ""))
            lines.append(
                '      <div className="mt-1 text-[10px] '
                f"bg-{color}/10 text-{color} "
                f'rounded px-1 py-0.5 truncate">'
                f"{ev_title}</div>"
            )
        lines.append("    </div>")
    lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_empty_state(c: Component, screen: Screen, ctx: MockContext) -> str:
    icon = c.props.get("icon", "inbox")
    headline = _escape_jsx(c.props.get("headline", "Nothing here yet"))
    desc = _escape_jsx(c.props.get("description", ""))
    cta = c.props.get("cta")
    lines = ['<div className="text-center py-16 mb-8">']
    icon_el = _icon_svg(icon, "w-8 h-8 text-gray-400")
    lines.append(
        '  <div className="bg-gray-100 rounded-full w-16 h-16 '
        "flex items-center justify-center "
        f'mx-auto mb-4">{icon_el}</div>'
    )
    lines.append(f'  <h3 className="font-heading font-semibold text-gray-900 mb-2">{headline}</h3>')
    if desc:
        lines.append(f'  <p className="text-gray-500 max-w-md mx-auto">{desc}</p>')
    if cta:
        cta_esc = _escape_jsx(str(cta))
        lines.append(
            '  <button className="mt-4 bg-primary '
            "text-white px-6 py-2 rounded-full text-sm "
            "font-medium hover:shadow-lg "
            f'transition-shadow">{cta_esc}</button>'
        )
    lines.append("</div>")
    return "\n".join(lines)


def _render_ai_indicator(c: Component, screen: Screen, ctx: MockContext) -> str:
    role = _escape_jsx(c.props.get("role", "AI Assistant"))
    status = c.props.get("status", "active")
    behaviors = c.props.get("behaviors", [])
    dot_color = {
        "active": "bg-green-400",
        "learning": "bg-yellow-400",
        "ready": "bg-blue-400",
    }.get(status, "bg-gray-400")
    lines = [
        '<div className="bg-gradient-to-r from-primary/5 '
        "to-accent/5 rounded-2xl p-5 mb-8 "
        'border border-primary/10">'
    ]
    lines.append('  <div className="flex items-center gap-3 mb-2">')
    lines.append(f'    <div className="w-2 h-2 {dot_color} rounded-full animate-pulse" />')
    lines.append(f'    <span className="text-sm font-medium text-gray-900">{role}</span>')
    lines.append(f'    <span className="text-xs text-gray-500 capitalize">{status}</span>')
    lines.append("  </div>")
    if behaviors:
        lines.append('  <div className="flex flex-wrap gap-2">')
        for b in behaviors[:4]:
            b_esc = _escape_jsx(str(b))
            lines.append(
                '    <span className="text-xs bg-white/80 '
                "text-gray-600 px-2.5 py-1 rounded-full "
                f'border border-gray-200">{b_esc}</span>'
            )
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_prose(c: Component, screen: Screen, ctx: MockContext) -> str:
    content = _escape_jsx(c.props.get("content", ""))
    style = c.props.get("style", "narrative")
    if style == "callout":
        return (
            '<div className="bg-accent/5 border-l-4 '
            'border-accent rounded-r-xl p-5 mb-8">'
            '<p className="text-gray-700 leading-relaxed">'
            f"{content}</p></div>"
        )
    elif style == "quote":
        return (
            '<blockquote className="border-l-4 '
            'border-primary/30 pl-5 py-2 mb-8">'
            '<p className="text-gray-600 italic '
            f'leading-relaxed">{content}</p></blockquote>'
        )
    return f'<p className="text-gray-700 leading-relaxed mb-8 max-w-3xl">{content}</p>'


def _render_cta_section(c: Component, screen: Screen, ctx: MockContext) -> str:
    headline = _escape_jsx(c.props.get("headline", ""))
    desc = _escape_jsx(c.props.get("description", ""))
    primary = _escape_jsx(c.props.get("primary_action", "Continue"))
    secondary = c.props.get("secondary_action")
    lines = ['<div className="gradient-accent text-white rounded-2xl p-8 text-center mb-8">']
    if headline:
        lines.append(f'  <h3 className="font-heading text-2xl font-bold mb-2">{headline}</h3>')
    if desc:
        lines.append(f'  <p className="text-white/80 mb-6 max-w-lg mx-auto">{desc}</p>')
    lines.append('  <div className="flex gap-4 justify-center">')
    lines.append(
        '    <button className="bg-white text-gray-900 '
        "font-semibold px-8 py-3 rounded-full "
        'hover:shadow-lg transition-shadow">'
        f"{primary}</button>"
    )
    if secondary:
        sec_esc = _escape_jsx(secondary)
        lines.append(
            '    <button className="border-2 border-white/60 '
            "text-white px-8 py-3 rounded-full "
            f'hover:bg-white/10">{sec_esc}</button>'
        )
    lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_image_section(c: Component, screen: Screen, ctx: MockContext) -> str:
    slot_id = c.props.get("image_slot", "")
    caption = c.props.get("caption", "")
    layout = c.props.get("layout", "full")
    width = "max-w-3xl mx-auto" if layout == "half" else "w-full"
    img = next((s for s in screen.images if s.slot == slot_id), None)
    if img:
        inner = _render_image_slot(img)
    else:
        inner = (
            '<div className="h-48 bg-gray-100 rounded-xl '
            'flex items-center justify-center">'
            '<span className="text-gray-400">Image</span></div>'
        )
    lines = [f'<div className="{width} mb-8">']
    lines.append(f"  {inner}")
    if caption:
        cap_esc = _escape_jsx(caption)
        lines.append(f'  <p className="text-sm text-gray-500 mt-2 text-center">{cap_esc}</p>')
    lines.append("</div>")
    return "\n".join(lines)


def _render_file_list(c: Component, screen: Screen, ctx: MockContext) -> str:
    files = c.props.get("files", [])
    lines = [
        '<div className="bg-white rounded-2xl shadow-sm '
        "border border-gray-100 divide-y "
        'divide-gray-50 mb-8">'
    ]
    for f in files:
        name = _escape_jsx(f.get("name", "file"))
        ftype = _escape_jsx(f.get("type", ""))
        size = _escape_jsx(f.get("size", ""))
        lines.append('  <div className="flex items-center px-6 py-4 hover:bg-gray-50/50">')
        lines.append(
            '    <div className="flex-1">'
            '<p className="text-sm font-medium '
            f'text-gray-900">{name}</p>'
        )
        lines.append(f'    <p className="text-xs text-gray-400">{ftype} \u00b7 {size}</p></div>')
        lines.append(
            '    <button className="text-primary text-sm hover:underline">Download</button>'
        )
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def _render_settings_form(c: Component, screen: Screen, ctx: MockContext) -> str:
    sections = c.props.get("sections", [])
    lines = ['<div className="space-y-8 mb-8">']
    for sec in sections:
        title = _escape_jsx(sec.get("title", ""))
        fields = sec.get("fields", [])
        lines.append(
            '  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">'
        )
        lines.append(
            f'    <h3 className="font-heading font-semibold text-gray-900 mb-4">{title}</h3>'
        )
        lines.append('    <div className="space-y-4">')
        for f in fields:
            label = _escape_jsx(f.get("label", ""))
            name = f.get("name", label.lower().replace(" ", "_"))
            val = _escape_jsx(str(f.get("value", "")))
            ftype = f.get("type", "text")
            if ftype == "toggle":
                toggle_handler = (
                    f'onClick={{() => setSettings(s => ({{...s, "{name}": !s["{name}"]}}))}} '
                )
                lines.append(
                    '      <div className="flex items-center justify-between">'
                    f'<span className="text-sm text-gray-700">{label}</span>'
                    f"<button {toggle_handler}"
                    'className="cursor-pointer">'
                    f"<div className={{`w-10 h-6 rounded-full relative transition-colors "
                    f"${{settings[\"{name}\"] ? 'bg-primary' : 'bg-gray-300'}}`}}>"
                    "<div className={`w-4 h-4 bg-white rounded-full absolute top-1 "
                    f'transition-transform ${{settings["{name}"] ? "right-1" : "left-1"}}`}} />'
                    "</div>"
                    "</button>"
                    "</div>"
                )
            else:
                lines.append(
                    "      <div>"
                    '<label className="block text-sm '
                    f'text-gray-700 mb-1">{label}</label>'
                    f'<input type="{ftype}" '
                    f'value={{settings["{name}"] ?? "{val}"}} '
                    f'onChange={{(e) => setSettings(s => ({{...s, "{name}": e.target.value}}))}} '
                    'className="w-full rounded-xl '
                    "border-gray-200 border px-4 py-2 "
                    'text-sm" /></div>'
                )
        lines.append("    </div>")
        lines.append(
            '    <button onClick={() => toast("Settings saved!")} '
            'className="mt-4 bg-primary text-white px-6 py-2 '
            "rounded-full text-sm font-medium hover:shadow-lg "
            'transition-shadow cursor-pointer">Save Changes</button>'
        )
        lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


# =============================================================================
# Component Dispatch
# =============================================================================


COMPONENT_RENDERERS: dict[str, Callable] = {
    "hero": _render_hero,
    "metric_grid": _render_metric_grid,
    "form": _render_form,
    "data_table": _render_data_table,
    "chart": _render_chart,
    "card_grid": _render_card_grid,
    "activity_feed": _render_activity_feed,
    "stats_banner": _render_stats_banner,
    "timeline": _render_timeline,
    "tabs": _render_tabs,
    "horizon_roadmap": _render_horizon_roadmap,
    "chat_interface": _render_chat_interface,
    "kanban": _render_kanban,
    "calendar": _render_calendar,
    "empty_state": _render_empty_state,
    "ai_indicator": _render_ai_indicator,
    "prose": _render_prose,
    "cta_section": _render_cta_section,
    "image_section": _render_image_section,
    "file_list": _render_file_list,
    "settings_form": _render_settings_form,
}


def render_component(component: Component, screen: Screen, ctx: MockContext) -> str:
    """Render a single component to TSX with optional Feature wrap."""
    renderer = COMPONENT_RENDERERS.get(component.type)
    if not renderer:
        return (
            '<div className="bg-yellow-50 border '
            "border-yellow-200 rounded-xl p-4 mb-8 "
            'text-sm text-yellow-700">'
            f"Unknown component: {component.type}</div>"
        )

    inner = renderer(component, screen, ctx)
    if not inner:
        return ""

    if component.feature_id:
        slug = _slugify(component.feature_id)
        return f'<Feature id="{slug}">\n{inner}\n</Feature>'
    return inner


# =============================================================================
# Layout Renderers
# =============================================================================


def render_layout(screen_map: ScreenMap, project_title: str) -> str:
    """Render Layout.tsx based on app shell navigation type."""
    shell = screen_map.app_shell
    nav = shell.navigation

    if nav == "sidebar":
        return _render_sidebar_layout(screen_map, project_title)
    elif nav == "wizard_flow":
        return _render_wizard_layout(screen_map, project_title)
    else:
        return _render_topnav_layout(screen_map, project_title)


def _render_sidebar_layout(sm: ScreenMap, title: str) -> str:
    safe_title = _escape_jsx(title)
    logo = _render_branding(sm.app_shell.branding, safe_title)

    # Build icon imports (direct lucide-react imports — we know all icons at render time)
    icon_names: list[str] = []
    for item in sm.app_shell.nav_items:
        if item.icon:
            icon_names.append(_kebab_to_pascal(item.icon))
    # Always-needed layout icons
    for needed in ["Search", "Bell", "ChevronRight", "Home", "PanelLeftClose", "Zap"]:
        if needed not in icon_names:
            icon_names.append(needed)
    icon_import = ", ".join(sorted(set(icon_names)))

    # Build nav links with icons
    links = []
    for item in sm.app_shell.nav_items:
        label = _escape_jsx(item.label)
        route = item.route
        icon_comp = _kebab_to_pascal(item.icon) if item.icon else "Circle"
        links.append(
            f'        <Link to="{route}" '
            f"className={{`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm "
            f'transition-colors ${{isActive("{route}") '
            "? 'bg-primary/10 text-primary font-medium' "
            ": 'text-gray-600 hover:bg-gray-100'}`}>\n"
            f"          <{icon_comp} size={{18}} />\n"
            f"          {{!collapsed && <span>{label}</span>}}\n"
            "        </Link>"
        )
    nav_block = "\n".join(links)

    # Breadcrumb label lookup
    breadcrumb_map_entries = []
    for item in sm.app_shell.nav_items:
        label = _escape_jsx(item.label)
        breadcrumb_map_entries.append(f"  '{item.route}': '{label}',")
    breadcrumb_map = "\n".join(breadcrumb_map_entries)

    # Persona toggle buttons from secondary users
    user = sm.mock_context.primary_user
    initials = _escape_jsx(user.avatar_initials)
    uname = _escape_jsx(user.name)
    urole = _escape_jsx(user.role)

    persona_buttons = []
    for su in sm.mock_context.secondary_users[:3]:
        su_init = _escape_jsx(su.avatar_initials)
        su_name = _escape_jsx(su.name)
        persona_buttons.append(
            f'            <button title="{su_name}" className="bg-gray-100 '
            "text-gray-600 rounded-full w-8 h-8 flex items-center justify-center "
            f'text-xs font-semibold hover:bg-primary/10 hover:text-primary transition-colors">'
            f"{su_init}</button>"
        )
    persona_block = "\n".join(persona_buttons)

    return (
        "import { useState } from 'react'\n"
        "import { Link, Outlet, useLocation }"
        " from 'react-router-dom'\n"
        f"import {{ {icon_import} }} from 'lucide-react'\n"
        "import { Avatar } from '../components/ui'\n\n"
        "export default function Layout() {\n"
        "  const { pathname } = useLocation()\n"
        "  const [collapsed, setCollapsed] = useState(false)\n"
        "  const isActive = (r: string) =>\n"
        '    pathname === r || (r !== "/" '
        "&& pathname.startsWith(r))\n\n"
        "  const labels: Record<string, string> = {\n"
        f"{breadcrumb_map}\n"
        "  }\n\n"
        "  const segments = pathname.split('/').filter(Boolean)\n"
        "  const crumbs = segments.map((_s, i) => {\n"
        "    const path = '/' + segments.slice(0, i + 1).join('/')\n"
        "    return { path, label: labels[path] || _s.replace(/-/g, ' ') }\n"
        "  })\n\n"
        "  return (\n"
        '    <div className="flex min-h-screen bg-gray-50">\n'
        "      {/* Sidebar */}\n"
        '      <aside className={`${collapsed ? "w-16" : "w-60"} '
        "bg-white border-r border-gray-200 flex flex-col "
        "transition-all duration-200`}>\n"
        "        <div "
        f'className="px-4 py-4 border-b border-gray-100 flex items-center gap-2">\n'
        f'          <Zap size={{20}} className="text-primary flex-shrink-0" />\n'
        f"          {{!collapsed && {logo}}}\n"
        "        </div>\n"
        '        <nav className="flex-1 px-2 py-4 '
        'space-y-1">\n'
        f"{nav_block}\n"
        "        </nav>\n"
        '        <div className="px-3 py-4 '
        'border-t border-gray-100 space-y-3">\n'
        '          <div className="flex items-center '
        'gap-3">\n'
        f'            <Avatar initials="{initials}" name="{uname}" size="sm" />\n'
        "            {!collapsed && (\n"
        "              <div>\n"
        f'                <p className="text-sm font-medium text-gray-900">{uname}</p>\n'
        f'                <p className="text-xs text-gray-500">{urole}</p>\n'
        "              </div>\n"
        "            )}\n"
        "          </div>\n"
        "          <button onClick={() => setCollapsed(c => !c)}\n"
        '            className="flex items-center gap-2 text-xs '
        'text-gray-400 hover:text-gray-600 transition-colors w-full">\n'
        "            <PanelLeftClose size={16}\n"
        "              className={collapsed ? 'rotate-180 transition-transform' "
        ": 'transition-transform'} />\n"
        "            {!collapsed && <span>Collapse</span>}\n"
        "          </button>\n"
        "        </div>\n"
        "      </aside>\n\n"
        "      {/* Main area */}\n"
        '      <div className="flex-1 flex flex-col overflow-y-auto">\n'
        "        {/* TopBar */}\n"
        '        <header className="h-14 bg-white/90 backdrop-blur-md border-b '
        "border-gray-200/60 sticky top-0 z-50 px-6 flex items-center "
        'gap-4">\n'
        '          <div className="flex-1 max-w-xs">\n'
        '            <div className="relative">\n'
        '              <Search size={16} className="absolute left-3 top-1/2 '
        '-translate-y-1/2 text-gray-400" />\n'
        '              <input type="text" placeholder="Search..." '
        'className="w-full pl-9 pr-4 py-1.5 text-sm rounded-lg border '
        "border-gray-200 focus:ring-2 focus:ring-primary/30 "
        'focus:border-primary bg-gray-50" />\n'
        "            </div>\n"
        "          </div>\n"
        '          <div className="flex-1" />\n'
        '          <div className="flex items-center gap-3">\n'
        + (f"{persona_block}\n" if persona_block else "")
        + '            <button className="relative text-gray-400 '
        'hover:text-gray-600 transition-colors">\n'
        "              <Bell size={18} />\n"
        '              <span className="absolute -top-1 -right-1 w-2 h-2 '
        'bg-red-500 rounded-full" />\n'
        "            </button>\n"
        f'            <Avatar initials="{initials}" name="{uname}" size="sm" />\n'
        "          </div>\n"
        "        </header>\n\n"
        "        {/* Breadcrumbs */}\n"
        '        <div className="px-8 pt-4 flex items-center gap-1.5 text-sm">\n'
        '          <Link to="/" className="text-gray-400 hover:text-primary transition-colors">\n'
        "            <Home size={14} />\n"
        "          </Link>\n"
        "          {crumbs.map((c) => (\n"
        '            <span key={c.path} className="flex items-center gap-1.5">\n'
        '              <ChevronRight size={12} className="text-gray-300" />\n'
        '              <Link to={c.path} className="text-gray-600 hover:text-primary '
        'capitalize transition-colors">\n'
        "                {c.label}\n"
        "              </Link>\n"
        "            </span>\n"
        "          ))}\n"
        "        </div>\n\n"
        "        {/* Page content with enter animation */}\n"
        '        <main className="flex-1">\n'
        '          <div key={pathname} className="animate-page-enter">\n'
        "            <Outlet />\n"
        "          </div>\n"
        "        </main>\n"
        "      </div>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
    )


def _render_wizard_layout(sm: ScreenMap, title: str) -> str:
    safe_title = _escape_jsx(title)
    logo = _render_branding(sm.app_shell.branding, safe_title)
    steps = []
    for i, item in enumerate(sm.app_shell.nav_items):
        label = _escape_jsx(item.label)
        route = item.route
        act_link = (
            "flex items-center gap-2 bg-primary/10 "
            "text-primary font-semibold px-4 py-1.5 "
            "rounded-full text-sm"
        )
        inact_link = "flex items-center gap-2 text-gray-400 px-4 py-1.5 text-sm hover:text-gray-600"
        act_dot = (
            "w-6 h-6 rounded-full bg-primary text-white "
            "flex items-center justify-center text-xs font-bold"
        )
        inact_dot = (
            "w-6 h-6 rounded-full bg-gray-200 text-gray-500 "
            "flex items-center justify-center text-xs"
        )
        steps.append(
            f'        <Link to="{route}" className={{'
            f'pathname === "{route}"'
            f' ? "{act_link}"'
            f' : "{inact_link}"'
            f"}}>"
            f"<span className={{"
            f'pathname === "{route}"'
            f' ? "{act_dot}"'
            f' : "{inact_dot}"'
            f"}}>{i + 1}</span>"
            f"{label}</Link>"
        )
    nav_block = "\n".join(steps)
    return (
        "import { Link, Outlet, useLocation }"
        " from 'react-router-dom'\n\n"
        "export default function Layout() {\n"
        "  const { pathname } = useLocation()\n"
        "  return (\n"
        '    <div className="min-h-screen flex '
        'flex-col bg-gray-50">\n'
        '      <nav className="bg-white/90 backdrop-blur-md '
        "border-b border-gray-200/60 sticky top-0 "
        'z-50 px-6 py-3">\n'
        '        <div className="max-w-5xl mx-auto '
        'flex items-center">\n'
        f"          {logo}\n"
        '          <div className="flex-1 flex items-center '
        'justify-center gap-1 overflow-x-auto">\n'
        f"{nav_block}\n"
        "          </div>\n"
        "        </div>\n"
        "      </nav>\n"
        '      <main className="flex-1 max-w-4xl '
        'mx-auto w-full px-6 py-8">\n'
        "        <Outlet />\n"
        "      </main>\n"
        '      <footer className="border-t '
        "border-gray-200/60 bg-white/60 "
        'backdrop-blur-sm py-6 text-center">\n'
        '        <p className="text-xs text-gray-400">'
        f"&copy; 2026 {safe_title}</p>\n"
        "      </footer>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
    )


def _render_topnav_layout(sm: ScreenMap, title: str) -> str:
    safe_title = _escape_jsx(title)
    logo = _render_branding(sm.app_shell.branding, safe_title)
    links = []
    for item in sm.app_shell.nav_items:
        label = _escape_jsx(item.label)
        route = item.route
        act_cls = "bg-primary/10 text-primary font-semibold px-3 py-1.5 rounded-full text-sm"
        inact_cls = "text-gray-500 hover:text-primary px-3 py-1.5 text-sm"
        links.append(
            f'        <Link to="{route}" className={{'
            f'pathname === "{route}"'
            f' ? "{act_cls}"'
            f' : "{inact_cls}"'
            f"}}>{label}</Link>"
        )
    nav_block = "\n".join(links)
    return (
        "import { Link, Outlet, useLocation }"
        " from 'react-router-dom'\n\n"
        "export default function Layout() {\n"
        "  const { pathname } = useLocation()\n"
        "  return (\n"
        '    <div className="min-h-screen flex '
        'flex-col bg-gray-50">\n'
        '      <nav className="bg-white/90 backdrop-blur-md '
        "border-b border-gray-200/60 sticky top-0 "
        'z-50 px-6 py-3 flex items-center gap-1">\n'
        f"        {logo}\n"
        f"{nav_block}\n"
        "      </nav>\n"
        '      <main className="flex-1">\n'
        "        <Outlet />\n"
        "      </main>\n"
        '      <footer className="border-t '
        "border-gray-200/60 bg-white/60 "
        'backdrop-blur-sm py-6 text-center">\n'
        '        <p className="text-xs text-gray-400">'
        f"&copy; 2026 {safe_title}</p>\n"
        "      </footer>\n"
        "    </div>\n"
        "  )\n"
        "}\n"
    )


def _render_branding(branding, safe_title: str) -> str:
    if branding.logo_source == "url" and branding.logo_value:
        return f'<img src="{branding.logo_value}" alt="{safe_title}" className="h-8 mr-6" />'
    app_name = _escape_jsx(branding.app_title or safe_title)
    return f'<span className="font-heading font-bold text-primary text-lg mr-6">{app_name}</span>'


# =============================================================================
# Page Renderer
# =============================================================================


def _build_page_hooks(
    components: list[Component],
    screen_map: ScreenMap,
) -> tuple[list[str], list[str]]:
    """Scan components and return (hook_lines, extra_imports) for interactivity.

    Inspects component types on the page and generates appropriate
    React hooks (useState) and imports (useNavigate, useToast, etc.).
    """
    hook_lines: list[str] = []
    extra_imports: set[str] = set()
    comp_types = {c.type for c in components}

    # Hero with CTA navigation
    if "hero" in comp_types:
        extra_imports.add("import { useNavigate } from 'react-router-dom'")
        hook_lines.append("  const navigate = useNavigate()")

    # Form state
    if "form" in comp_types:
        hook_lines.append("  const [formData, setFormData] = useState<Record<string, string>>({})")
        extra_imports.add("import { useToast } from '../components/ui/Toast'")
        if "  const { toast } = useToast()" not in hook_lines:
            hook_lines.append("  const { toast } = useToast()")

    # Data table search
    if "data_table" in comp_types:
        hook_lines.append("  const [tableSearch, setTableSearch] = useState('')")

    # Chat interface
    if "chat_interface" in comp_types:
        # Build initial messages from the first chat component
        chat_comp = next((c for c in components if c.type == "chat_interface"), None)
        init_msgs = []
        if chat_comp:
            for msg in chat_comp.props.get("messages", []):
                role = msg.get("role", "user")
                content = msg.get("content", "").replace("'", "\\'")
                init_msgs.append(f"{{role: '{role}', content: '{content}'}}")
        init_str = ", ".join(init_msgs)
        hook_lines.append(
            f"  const [chatMessages, setChatMessages] = "
            f"useState<{{role: string, content: string}}[]>([{init_str}])"
        )
        hook_lines.append("  const [chatInput, setChatInput] = useState('')")

    # Settings form
    if "settings_form" in comp_types:
        # Build initial settings from the first settings component
        settings_comp = next((c for c in components if c.type == "settings_form"), None)
        init_settings: dict = {}
        if settings_comp:
            for sec in settings_comp.props.get("sections", []):
                for f in sec.get("fields", []):
                    name = f.get("name", f.get("label", "").lower().replace(" ", "_"))
                    ftype = f.get("type", "text")
                    if ftype == "toggle":
                        init_settings[name] = True
                    else:
                        init_settings[name] = f.get("value", "")
        settings_str = ", ".join(
            f"'{k}': {'true' if v is True else 'false' if v is False else repr(str(v))}"
            for k, v in init_settings.items()
        )
        hook_lines.append(
            f"  const [settings, setSettings] = useState<Record<string, any>>({{{settings_str}}})"
        )
        extra_imports.add("import { useToast } from '../components/ui/Toast'")
        if "  const { toast } = useToast()" not in hook_lines:
            hook_lines.append("  const { toast } = useToast()")

    # Ensure useState is imported if hooks exist
    if hook_lines:
        extra_imports.add("import { useState } from 'react'")

    return hook_lines, sorted(extra_imports)


def render_page(
    screen: Screen,
    component_name: str,
    screen_map: ScreenMap,
) -> str:
    """Render a complete page TSX file from a Screen spec.

    Includes auto-interactivity: useState hooks for forms, tables,
    chat, settings; useNavigate for hero CTAs; toast for submissions.
    """
    ctx = screen_map.mock_context
    has_feature = any(c.feature_id for c in screen.components)

    # Inject CTA route into hero components for navigation
    if len(screen_map.screens) > 1:
        for comp in screen.components:
            if comp.type == "hero" and "_cta_route" not in comp.props:
                # Find next non-current screen route
                for s in screen_map.screens:
                    if s.route != screen.route:
                        comp.props["_cta_route"] = s.route
                        break

    # Build hooks and extra imports for interactivity
    hook_lines, extra_imports = _build_page_hooks(screen.components, screen_map)

    imports = [*extra_imports, "import { Screen } from '../lib/aios'"]
    if has_feature:
        imports.append("import { Feature } from '../lib/aios'")

    component_blocks = []
    for comp in screen.components:
        rendered = render_component(comp, screen, ctx)
        if rendered:
            component_blocks.append(rendered)

    header_block = ""
    if screen.ux_copy:
        ux = screen.ux_copy
        parts = []
        if ux.headline:
            parts.append(
                '<h1 className="font-heading text-3xl '
                'font-bold text-gray-900">'
                f"{_escape_jsx(ux.headline)}</h1>"
            )
        if ux.subtitle:
            parts.append(
                f'<p className="text-gray-600 mt-2 max-w-2xl">{_escape_jsx(ux.subtitle)}</p>'
            )
        if ux.pain_point_callout:
            parts.append(
                '<div className="mt-3 bg-accent/5 border-l-4 '
                'border-accent rounded-r-lg px-4 py-2">'
                '<p className="text-sm text-gray-700">'
                f"{_escape_jsx(ux.pain_point_callout)}"
                "</p></div>"
            )
        if parts:
            header_block = (
                '<div className="mb-8">\n' + "\n".join(f"  {p}" for p in parts) + "\n</div>"
            )

    body = "\n\n".join(component_blocks)
    screen_title = _escape_jsx(screen.title)

    # Auto-detect UI primitive usage and add imports
    ui_primitives = [
        ("Card", "<Card"),
        ("Badge", "<Badge"),
        ("TabGroup", "<TabGroup"),
        ("LucideIcon", "LucideIcon"),
        ("ProgressBar", "<ProgressBar"),
        ("Avatar", "<Avatar"),
        ("Button", "<Button"),
    ]
    used = [name for name, marker in ui_primitives if marker in body]
    if used:
        imports.append(f"import {{ {', '.join(sorted(used))} }} from '../components/ui'")

    hooks_block = "\n".join(hook_lines) + "\n" if hook_lines else ""

    return (
        "\n".join(imports) + "\n\n"
        f"export default function {component_name}() {{\n" + hooks_block + "  return (\n"
        f'    <Screen name="{screen_title}">\n'
        '      <div className="p-8">\n'
        + (f"        {header_block}\n" if header_block else "")
        + "\n".join(f"        {line}" for line in body.split("\n"))
        + "\n"
        + "      </div>\n"
        + "    </Screen>\n"
        + "  )\n"
        + "}\n"
    )


# =============================================================================
# App.tsx Renderer
# =============================================================================


def render_app_tsx(screen_map: ScreenMap) -> str:
    """Render App.tsx with routes from ScreenMap."""
    imports = [
        "import { Routes, Route, Navigate } from 'react-router-dom'",
        "import Layout from './components/Layout'",
        "import { AiosOverlay } from './lib/aios'",
    ]
    routes = []
    first_route = "/dashboard"
    for i, screen in enumerate(screen_map.screens):
        comp = _pascal(screen.title)
        imports.append(f"import {comp} from './pages/{comp}'")
        routes.append(f'        <Route path="{screen.route}" element={{<{comp} />}} />')
        if i == 0:
            first_route = screen.route

    # Add root redirect to first screen
    routes.append(f'        <Route path="/" element={{<Navigate to="{first_route}" replace />}} />')

    return (
        "\n".join(imports) + "\n\n"
        "export default function App() {\n"
        "  return (\n"
        "    <>\n"
        "      <Routes>\n"
        "        <Route element={<Layout />}>\n" + "\n".join(routes) + "\n" + "        </Route>\n"
        "      </Routes>\n"
        "      <AiosOverlay />\n"
        "    </>\n"
        "  )\n"
        "}\n"
    )


# =============================================================================
# Entry Point
# =============================================================================


def render_screen_map_files(screen_map: ScreenMap, project_title: str) -> dict[str, str]:
    """Render all ScreenMap-driven files.

    Returns a filename->content dict to merge with scaffold
    boilerplate.
    """
    files: dict[str, str] = {}

    files["src/components/Layout.tsx"] = render_layout(screen_map, project_title)
    files["src/App.tsx"] = render_app_tsx(screen_map)

    for screen in screen_map.screens:
        comp = _pascal(screen.title)
        files[f"src/pages/{comp}.tsx"] = render_page(screen, comp, screen_map)

    return files
