"""Deterministic Inline A2UI v0.9 3-Card Renderer for Synchrony Virtual PM (Alex).

Renders side-by-side 3-card layouts directly inline in the Gemini Enterprise chat stream
(using `MaterialColumn` as `root` instead of `Canvas`, so no right-hand panel opens).
Each card uses a vertical stack with a status banner and 2-column label/value rows
separated by vertical and horizontal `MaterialDivider` components.
"""

from __future__ import annotations

from typing import Any

CATALOG_ID = "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
A2UI_V09_CATALOG_ID = CATALOG_ID

_RECENT_EXECUTED_TOOLS: list[str] = []
_RECENT_TOOL_OUTPUTS: dict[str, Any] = {}


def record_tool_execution(tool_name: str, payload: dict[str, Any] | None = None) -> None:
    """Record a tool execution from tools.py for deterministic A2UI card selection."""
    if tool_name not in _RECENT_EXECUTED_TOOLS:
        _RECENT_EXECUTED_TOOLS.append(tool_name)
    if payload is not None:
        _RECENT_TOOL_OUTPUTS[tool_name] = payload


def get_and_clear_executed_tools() -> tuple[list[str], dict[str, Any]]:
    """Return and clear tools recorded during the current turn."""
    tools = list(_RECENT_EXECUTED_TOOLS)
    outputs = dict(_RECENT_TOOL_OUTPUTS)
    _RECENT_EXECUTED_TOOLS.clear()
    _RECENT_TOOL_OUTPUTS.clear()
    return tools, outputs


def _build_envelopes(
    surface_id: str,
    components: list[dict[str, Any]],
    data_model: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build standard A2UI v0.9 envelope sequence: createSurface -> updateComponents -> updateDataModel."""
    messages: list[dict[str, Any]] = [
        {
            "version": "v0.9",
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": CATALOG_ID,
                "sendDataModel": True,
            },
        },
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        },
    ]
    if data_model is not None:
        messages.append(
            {
                "version": "v0.9",
                "updateDataModel": {
                    "surfaceId": surface_id,
                    "path": "/",
                    "value": data_model,
                },
            }
        )
    return messages


def _build_two_col_card(
    prefix: str,
    title: str,
    title_color: str,
    card_border: str,
    card_bg: str,
    banner_text: str | None,
    banner_bg: str | None,
    banner_color: str | None,
    rows: list[tuple[str, str, bool]],
    extra_bottom_children: list[str] | None = None,
    extra_components: list[dict[str, Any]] | None = None,
    header_gray_bg: bool = True,
    alternate_rows: bool = True,
    banner_at_bottom: bool = True,
    banner_line2: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Build a single MaterialCard with slate-gray header bar, alternating 2-column label/value rows, and bottom verdict pill.

    Each tuple in `rows` is `(label_text, value_text, emphasize_value)`.
    """
    card_id = f"{prefix}_card"
    col_id = f"{prefix}_col"
    hdr_row_id = f"{prefix}_hdr_row"
    title_id = f"{prefix}_title"

    col_children: list[str] = [hdr_row_id if header_gray_bg else title_id]
    comps: list[dict[str, Any]] = [
        {
            "id": card_id,
            "component": "MaterialCard",
            "appearance": "outlined",
            "weight": 1,
            "style": {
                "minWidth": "240px",
                "padding": "14px",
                "border": card_border,
                "backgroundColor": card_bg or "#ffffff",
                "borderRadius": "8px",
            },
            "children": [col_id],
        },
        {
            "id": title_id,
            "component": "MaterialText",
            "text": title,
            "usageHint": "body2",
            "style": {
                "fontSize": "12.5px",
                "fontWeight": "bold",
                "color": "#111827",
            },
        },
    ]

    if header_gray_bg:
        comps.append(
            {
                "id": hdr_row_id,
                "component": "MaterialRow",
                "align": "center",
                "justify": "start",
                "style": {
                    "padding": "9px 8px",
                    "width": "100%",
                    "backgroundColor": "#e2e8f0",
                    "borderRadius": "4px",
                },
                "children": [title_id],
            }
        )

    if banner_text and not banner_at_bottom:
        banner_id = f"{prefix}_banner"
        col_children.append(banner_id)
        comps.append(
            {
                "id": banner_id,
                "component": "MaterialText",
                "text": banner_text,
                "usageHint": "caption",
                "style": {
                    "fontSize": "11px",
                    "color": banner_color or "#1b5e20",
                    "backgroundColor": banner_bg or "#e8f5e9",
                    "padding": "4px 8px",
                    "borderRadius": "4px",
                    "fontWeight": "bold",
                },
            }
        )

    header_div_id = f"{prefix}_hdiv_top"
    col_children.append(header_div_id)
    comps.append({"id": header_div_id, "component": "MaterialDivider"})

    for idx, (label_txt, val_txt, _emphasize_val) in enumerate(rows):
        row_id = f"{prefix}_row_{idx}"
        lbl_col_id = f"{prefix}_lbl_col_{idx}"
        lbl_id = f"{prefix}_lbl_{idx}"
        vdiv_id = f"{prefix}_vdiv_{idx}"
        val_col_id = f"{prefix}_val_col_{idx}"
        val_id = f"{prefix}_val_{idx}"

        row_bg = ("#f0f7ff" if idx % 2 == 0 else "#ffffff") if alternate_rows else "transparent"
        col_children.append(row_id)
        comps.extend(
            [
                {
                    "id": row_id,
                    "component": "MaterialRow",
                    "align": "stretch",
                    "justify": "start",
                    "style": {
                        "gap": "8px",
                        "padding": "7px 6px",
                        "width": "100%",
                        "backgroundColor": row_bg,
                        "borderRadius": "4px",
                    },
                    "children": [lbl_col_id, vdiv_id, val_col_id],
                },
                {
                    "id": lbl_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 1,
                    "style": {
                        "width": "28%",
                        "minWidth": "74px",
                        "maxWidth": "28%",
                    },
                    "children": [lbl_id],
                },
                {
                    "id": lbl_id,
                    "component": "MaterialText",
                    "text": label_txt,
                    "usageHint": "caption",
                    "style": {
                        "fontSize": "11.5px",
                        "fontWeight": "normal",
                        "color": "#111827",
                    },
                },
                {
                    "id": vdiv_id,
                    "component": "MaterialDivider",
                    "vertical": True,
                    "style": {"width": "1px", "maxWidth": "1px"},
                },
                {
                    "id": val_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 3,
                    "style": {
                        "width": "70%",
                        "minWidth": "70%",
                        "maxWidth": "70%",
                    },
                    "children": [val_id],
                },
                {
                    "id": val_id,
                    "component": "MaterialText",
                    "text": val_txt,
                    "usageHint": "caption",
                    "style": {
                        "fontSize": "11.5px",
                        "fontWeight": "normal",
                        "color": "#111827",
                    },
                },
            ]
        )

        if idx < len(rows) - 1 or (banner_text and banner_at_bottom):
            hdiv_id = f"{prefix}_hdiv_{idx}"
            col_children.append(hdiv_id)
            comps.append({"id": hdiv_id, "component": "MaterialDivider"})

    if banner_text and banner_at_bottom:
        v_row_id = f"{prefix}_verdict_row"
        v_lbl_col_id = f"{prefix}_verdict_lbl_col"
        v_lbl_id = f"{prefix}_verdict_lbl"
        v_vdiv_id = f"{prefix}_verdict_vdiv"
        v_val_col_id = f"{prefix}_verdict_val_col"
        banner_id = f"{prefix}_banner"
        col_children.append(v_row_id)
        comps.extend(
            [
                {
                    "id": v_row_id,
                    "component": "MaterialRow",
                    "align": "stretch",
                    "justify": "start",
                    "style": {
                        "gap": "8px",
                        "padding": "7px 6px",
                        "width": "100%",
                        "backgroundColor": "#ffffff",
                        "borderRadius": "4px",
                    },
                    "children": [v_lbl_col_id, v_vdiv_id, v_val_col_id],
                },
                {
                    "id": v_lbl_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 1,
                    "style": {
                        "width": "28%",
                        "minWidth": "74px",
                        "maxWidth": "28%",
                    },
                    "children": [v_lbl_id],
                },
                {
                    "id": v_lbl_id,
                    "component": "MaterialText",
                    "text": "Verdict",
                    "usageHint": "caption",
                    "style": {
                        "fontSize": "11.5px",
                        "fontWeight": "bold",
                        "color": "#111827",
                    },
                },
                {
                    "id": v_vdiv_id,
                    "component": "MaterialDivider",
                    "vertical": True,
                    "style": {"width": "1px", "maxWidth": "1px"},
                },
            ]
        )
        if banner_line2:
            badge_box_id = f"{prefix}_badge_box"
            banner_sub_id = f"{prefix}_banner_sub"
            comps.extend(
                [
                    {
                        "id": v_val_col_id,
                        "component": "MaterialColumn",
                        "align": "start",
                        "justify": "center",
                        "weight": 3,
                        "style": {
                            "width": "70%",
                            "minWidth": "70%",
                            "maxWidth": "70%",
                        },
                        "children": [badge_box_id],
                    },
                    {
                        "id": badge_box_id,
                        "component": "MaterialColumn",
                        "align": "center",
                        "justify": "center",
                        "style": {
                            "backgroundColor": banner_bg or "#0d47a1",
                            "padding": "6px 10px",
                            "borderRadius": "6px",
                            "width": "100%",
                            "gap": "2px",
                        },
                        "children": [banner_id, banner_sub_id],
                    },
                    {
                        "id": banner_id,
                        "component": "MaterialText",
                        "text": banner_text,
                        "usageHint": "caption",
                        "style": {
                            "fontSize": "11px",
                            "color": banner_color or "#ffffff",
                            "fontWeight": "bold",
                        },
                    },
                    {
                        "id": banner_sub_id,
                        "component": "MaterialText",
                        "text": banner_line2,
                        "usageHint": "caption",
                        "style": {
                            "fontSize": "10.5px",
                            "color": banner_color or "#ffffff",
                            "fontWeight": "bold",
                        },
                    },
                ]
            )
        else:
            comps.extend(
                [
                    {
                        "id": v_val_col_id,
                        "component": "MaterialColumn",
                        "align": "start",
                        "justify": "center",
                        "weight": 3,
                        "style": {
                            "width": "70%",
                            "minWidth": "70%",
                            "maxWidth": "70%",
                        },
                        "children": [banner_id],
                    },
                    {
                        "id": banner_id,
                        "component": "MaterialText",
                        "text": banner_text,
                        "usageHint": "caption",
                        "style": {
                            "fontSize": "11px",
                            "color": banner_color or "#1b5e20",
                            "backgroundColor": banner_bg or "#e8f5e9",
                            "padding": "4px 8px",
                            "borderRadius": "4px",
                            "fontWeight": "bold",
                        },
                    },
                ]
            )

    if extra_bottom_children:
        col_children.extend(extra_bottom_children)
    if extra_components:
        comps.extend(extra_components)

    comps.insert(
        1,
        {
            "id": col_id,
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "6px"},
            "children": col_children,
        },
    )
    return card_id, comps


def _build_four_col_matrix_card(
    prefix: str,
    corner_label: str,
    col_specs: list[dict[str, str]],
    rows: list[tuple[str, tuple[str, bool], tuple[str, bool], tuple[str, bool]]],
    verdict_pills: list[dict[str, str]] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Build a single full-width MaterialCard with 1 metric/dimension column + 3 comparison columns.

    Args:
        prefix: Unique component ID prefix.
        corner_label: Top-left header label (e.g., "Benchmarks" or "Audit Dimension").
        col_specs: List of 3 dicts with key `title`.
        rows: List of tuples `(row_label, (val1, emp1), (val2, emp2), (val3, emp3))`.
        verdict_pills: Optional list of 3 dicts (`text`, `bg`, `color`) for a bottom 'Final Verdict' row.
    """
    card_id = f"{prefix}_card"
    root_col_id = f"{prefix}_root_col"
    hdr_row_id = f"{prefix}_hdr_row"
    corner_col_id = f"{prefix}_corner_col"
    corner_txt_id = f"{prefix}_corner_txt"

    col_children: list[str] = [hdr_row_id]
    hdr_row_children: list[str] = [corner_col_id]

    comps: list[dict[str, Any]] = [
        {
            "id": card_id,
            "component": "MaterialCard",
            "appearance": "outlined",
            "style": {
                "width": "100%",
                "padding": "14px",
                "border": "1px solid #cfd8dc",
                "backgroundColor": "#ffffff",
                "borderRadius": "8px",
            },
            "children": [root_col_id],
        },
        {
            "id": corner_col_id,
            "component": "MaterialColumn",
            "align": "start",
            "justify": "center",
            "weight": 1,
            "style": {
                "width": "16%",
                "minWidth": "90px",
                "maxWidth": "16%",
            },
            "children": [corner_txt_id],
        },
        {
            "id": corner_txt_id,
            "component": "MaterialText",
            "text": corner_label,
            "usageHint": "caption",
            "style": {
                "fontSize": "12px",
                "fontWeight": "bold",
                "color": "#111827",
            },
        },
    ]

    for c_idx, spec in enumerate(col_specs):
        vdiv_hdr_id = f"{prefix}_hdr_vdiv_{c_idx}"
        hdr_col_id = f"{prefix}_hdr_col_{c_idx}"
        title_id = f"{prefix}_hdr_title_{c_idx}"

        hdr_row_children.extend([vdiv_hdr_id, hdr_col_id])
        comps.extend(
            [
                {
                    "id": vdiv_hdr_id,
                    "component": "MaterialDivider",
                    "vertical": True,
                    "style": {"width": "1px", "maxWidth": "1px"},
                },
                {
                    "id": hdr_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 2,
                    "style": {
                        "width": "27%",
                        "minWidth": "150px",
                        "maxWidth": "27%",
                    },
                    "children": [title_id],
                },
                {
                    "id": title_id,
                    "component": "MaterialText",
                    "text": spec["title"],
                    "usageHint": "body2",
                    "style": {
                        "fontSize": "12.5px",
                        "fontWeight": "bold",
                        "color": "#111827",
                    },
                },
            ]
        )

    comps.append(
        {
            "id": hdr_row_id,
            "component": "MaterialRow",
            "align": "stretch",
            "justify": "start",
            "style": {
                "gap": "8px",
                "padding": "9px 6px",
                "width": "100%",
                "backgroundColor": "#e2e8f0",
                "borderRadius": "4px",
            },
            "children": hdr_row_children,
        }
    )

    top_div_id = f"{prefix}_hdiv_top"
    col_children.append(top_div_id)
    comps.append({"id": top_div_id, "component": "MaterialDivider"})

    for r_idx, (row_lbl, cell0, cell1, cell2) in enumerate(rows):
        row_id = f"{prefix}_row_{r_idx}"
        lbl_col_id = f"{prefix}_r{r_idx}_lbl_col"
        lbl_txt_id = f"{prefix}_r{r_idx}_lbl_txt"

        row_children: list[str] = [lbl_col_id]
        comps.extend(
            [
                {
                    "id": lbl_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 1,
                    "style": {
                        "width": "16%",
                        "minWidth": "90px",
                        "maxWidth": "16%",
                    },
                    "children": [lbl_txt_id],
                },
                {
                    "id": lbl_txt_id,
                    "component": "MaterialText",
                    "text": row_lbl,
                    "usageHint": "caption",
                    "style": {
                        "fontSize": "11.5px",
                        "fontWeight": "normal",
                        "color": "#111827",
                    },
                },
            ]
        )

        for c_idx, (val_txt, _emphasize) in enumerate((cell0, cell1, cell2)):
            vdiv_id = f"{prefix}_r{r_idx}_vdiv_{c_idx}"
            val_col_id = f"{prefix}_r{r_idx}_c{c_idx}_col"
            val_txt_id = f"{prefix}_r{r_idx}_c{c_idx}_txt"

            row_children.extend([vdiv_id, val_col_id])
            comps.extend(
                [
                    {
                        "id": vdiv_id,
                        "component": "MaterialDivider",
                        "vertical": True,
                        "style": {"width": "1px", "maxWidth": "1px"},
                    },
                    {
                        "id": val_col_id,
                        "component": "MaterialColumn",
                        "align": "start",
                        "justify": "center",
                        "weight": 2,
                        "style": {
                            "width": "27%",
                            "minWidth": "150px",
                            "maxWidth": "27%",
                        },
                        "children": [val_txt_id],
                    },
                    {
                        "id": val_txt_id,
                        "component": "MaterialText",
                        "text": val_txt,
                        "usageHint": "caption",
                        "style": {
                            "fontSize": "11.5px",
                            "fontWeight": "normal",
                            "color": "#111827",
                        },
                    },
                ]
            )

        col_children.append(row_id)
        # Odd data rows (r_idx 0, 2, 4...) = Very Light Blue (#f0f7ff), Even data rows (r_idx 1, 3, 5...) = White (#ffffff)
        row_bg = "#f0f7ff" if r_idx % 2 == 0 else "#ffffff"
        comps.append(
            {
                "id": row_id,
                "component": "MaterialRow",
                "align": "stretch",
                "justify": "start",
                "style": {
                    "gap": "8px",
                    "padding": "7px 6px",
                    "width": "100%",
                    "backgroundColor": row_bg,
                    "borderRadius": "4px",
                },
                "children": row_children,
            }
        )

        if r_idx < len(rows) - 1 or verdict_pills:
            hdiv_id = f"{prefix}_hdiv_{r_idx}"
            col_children.append(hdiv_id)
            comps.append({"id": hdiv_id, "component": "MaterialDivider"})

    if verdict_pills:
        v_r_idx = len(rows)
        v_row_id = f"{prefix}_row_{v_r_idx}"
        v_lbl_col_id = f"{prefix}_r{v_r_idx}_lbl_col"
        v_lbl_txt_id = f"{prefix}_r{v_r_idx}_lbl_txt"
        v_row_children: list[str] = [v_lbl_col_id]

        comps.extend(
            [
                {
                    "id": v_lbl_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 1,
                    "style": {
                        "width": "16%",
                        "minWidth": "90px",
                        "maxWidth": "16%",
                    },
                    "children": [v_lbl_txt_id],
                },
                {
                    "id": v_lbl_txt_id,
                    "component": "MaterialText",
                    "text": "Final Verdict",
                    "usageHint": "caption",
                    "style": {
                        "fontSize": "11.5px",
                        "fontWeight": "bold",
                        "color": "#111827",
                    },
                },
            ]
        )

        for c_idx, pill in enumerate(verdict_pills):
            vdiv_id = f"{prefix}_r{v_r_idx}_vdiv_{c_idx}"
            val_col_id = f"{prefix}_r{v_r_idx}_c{c_idx}_col"
            banner_id = f"{prefix}_hdr_banner_{c_idx}"
            v_row_children.extend([vdiv_id, val_col_id])
            comps.append(
                {
                    "id": vdiv_id,
                    "component": "MaterialDivider",
                    "vertical": True,
                    "style": {"width": "1px", "maxWidth": "1px"},
                }
            )
            if pill.get("line1") and pill.get("line2"):
                badge_box_id = f"{prefix}_hdr_badge_box_{c_idx}"
                banner_sub_id = f"{prefix}_hdr_banner_{c_idx}_sub"
                comps.extend(
                    [
                        {
                            "id": val_col_id,
                            "component": "MaterialColumn",
                            "align": "start",
                            "justify": "center",
                            "weight": 2,
                            "style": {
                                "width": "27%",
                                "minWidth": "150px",
                                "maxWidth": "27%",
                            },
                            "children": [badge_box_id],
                        },
                        {
                            "id": badge_box_id,
                            "component": "MaterialColumn",
                            "align": "center",
                            "justify": "center",
                            "style": {
                                "backgroundColor": pill["bg"],
                                "padding": "6px 10px",
                                "borderRadius": "6px",
                                "width": "100%",
                                "gap": "2px",
                            },
                            "children": [banner_id, banner_sub_id],
                        },
                        {
                            "id": banner_id,
                            "component": "MaterialText",
                            "text": pill["line1"],
                            "usageHint": "caption",
                            "style": {
                                "fontSize": "11px",
                                "fontWeight": "bold",
                                "color": pill["color"],
                            },
                        },
                        {
                            "id": banner_sub_id,
                            "component": "MaterialText",
                            "text": pill["line2"],
                            "usageHint": "caption",
                            "style": {
                                "fontSize": "10.5px",
                                "fontWeight": "bold",
                                "color": pill["color"],
                            },
                        },
                    ]
                )
            else:
                comps.extend(
                    [
                        {
                            "id": val_col_id,
                            "component": "MaterialColumn",
                            "align": "start",
                            "justify": "center",
                            "weight": 2,
                            "style": {
                                "width": "27%",
                                "minWidth": "150px",
                                "maxWidth": "27%",
                            },
                            "children": [banner_id],
                        },
                        {
                            "id": banner_id,
                            "component": "MaterialText",
                            "text": pill["text"],
                            "usageHint": "caption",
                            "style": {
                                "fontSize": "11px",
                                "fontWeight": "bold",
                                "color": pill["color"],
                                "backgroundColor": pill["bg"],
                                "padding": "4px 8px",
                                "borderRadius": "4px",
                            },
                        },
                    ]
                )

        col_children.append(v_row_id)
        v_row_bg = "#f0f7ff" if v_r_idx % 2 == 0 else "#ffffff"
        comps.append(
            {
                "id": v_row_id,
                "component": "MaterialRow",
                "align": "stretch",
                "justify": "start",
                "style": {
                    "gap": "8px",
                    "padding": "8px 6px",
                    "width": "100%",
                    "backgroundColor": v_row_bg,
                    "borderRadius": "4px",
                },
                "children": v_row_children,
            }
        )

    comps.insert(
        1,
        {
            "id": root_col_id,
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "2px", "width": "100%"},
            "children": col_children,
        },
    )
    return card_id, comps


def _build_citations_card(
    prefix: str,
    title: str,
    groups: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Build a dedicated full-width MaterialCard containing categorized clickable `openUrl` citation buttons."""
    card_id = f"{prefix}_card"
    col_id = f"{prefix}_col"
    hdr_row_id = f"{prefix}_hdr_row"
    title_id = f"{prefix}_title"
    hdiv_top_id = f"{prefix}_hdiv_top"

    col_children: list[str] = [hdr_row_id, hdiv_top_id]
    comps: list[dict[str, Any]] = [
        {
            "id": card_id,
            "component": "MaterialCard",
            "appearance": "outlined",
            "style": {
                "width": "100%",
                "padding": "14px",
                "border": "1px solid #cfd8dc",
                "backgroundColor": "#ffffff",
                "borderRadius": "8px",
            },
            "children": [col_id],
        },
        {
            "id": hdr_row_id,
            "component": "MaterialRow",
            "align": "center",
            "justify": "start",
            "style": {
                "padding": "8px 8px",
                "width": "100%",
                "backgroundColor": "#e2e8f0",
                "borderRadius": "4px",
            },
            "children": [title_id],
        },
        {
            "id": title_id,
            "component": "MaterialText",
            "text": title,
            "usageHint": "body2",
            "style": {
                "fontSize": "12.5px",
                "fontWeight": "bold",
                "color": "#111827",
            },
        },
        {"id": hdiv_top_id, "component": "MaterialDivider"},
    ]

    for g_idx, grp in enumerate(groups):
        row_id = f"{prefix}_row_{g_idx}"
        lbl_col_id = f"{prefix}_lbl_col_{g_idx}"
        lbl_id = f"{prefix}_lbl_{g_idx}"
        vdiv_id = f"{prefix}_vdiv_{g_idx}"
        val_col_id = f"{prefix}_val_col_{g_idx}"
        links_row_id = f"{prefix}_links_row_{g_idx}"

        links = grp.get("links") or []
        btn_ids: list[str] = []
        btn_comps: list[dict[str, Any]] = []
        for l_idx, link in enumerate(links):
            btn_id = f"{prefix}_btn_{g_idx}_{l_idx}"
            btn_ids.append(btn_id)
            url_str = str(
                link.get("url")
                or "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/393219/PRD-AI-EVAL-101"
            )
            btn_comps.append(
                {
                    "id": btn_id,
                    "component": "MaterialButton",
                    "label": str(link.get("label") or "Open Reference"),
                    "variant": "stroked",
                    "color": "primary",
                    "leadingIcon": "open_in_new",
                    "style": {
                        "fontSize": "11px",
                        "fontWeight": "bold",
                        "color": "#0d47a1",
                        "border": "1px solid #90caf9",
                        "backgroundColor": "#ffffff",
                        "padding": "3px 10px",
                        "borderRadius": "4px",
                    },
                    "action": {
                        "functionCall": {
                            "call": "openUrl",
                            "args": {"url": url_str},
                            "returnType": "void",
                        }
                    },
                }
            )

        row_bg = "#f0f7ff" if g_idx % 2 == 0 else "#ffffff"
        col_children.append(row_id)
        comps.extend(
            [
                {
                    "id": row_id,
                    "component": "MaterialRow",
                    "align": "stretch",
                    "justify": "start",
                    "style": {
                        "gap": "8px",
                        "padding": "7px 6px",
                        "width": "100%",
                        "backgroundColor": row_bg,
                        "borderRadius": "4px",
                    },
                    "children": [lbl_col_id, vdiv_id, val_col_id],
                },
                {
                    "id": lbl_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 1,
                    "style": {
                        "width": "24%",
                        "minWidth": "140px",
                        "maxWidth": "24%",
                    },
                    "children": [lbl_id],
                },
                {
                    "id": lbl_id,
                    "component": "MaterialText",
                    "text": str(grp.get("category") or "References"),
                    "usageHint": "caption",
                    "style": {
                        "fontSize": "11.5px",
                        "fontWeight": "bold",
                        "color": "#111827",
                    },
                },
                {
                    "id": vdiv_id,
                    "component": "MaterialDivider",
                    "vertical": True,
                    "style": {"width": "1px", "maxWidth": "1px"},
                },
                {
                    "id": val_col_id,
                    "component": "MaterialColumn",
                    "align": "start",
                    "justify": "center",
                    "weight": 3,
                    "style": {
                        "width": "74%",
                        "minWidth": "74%",
                        "maxWidth": "74%",
                    },
                    "children": [links_row_id],
                },
                {
                    "id": links_row_id,
                    "component": "MaterialRow",
                    "align": "center",
                    "justify": "start",
                    "style": {
                        "gap": "8px",
                        "flexWrap": "wrap",
                        "width": "100%",
                    },
                    "children": btn_ids,
                },
                *btn_comps,
            ]
        )

        if g_idx < len(groups) - 1:
            hdiv_id = f"{prefix}_hdiv_{g_idx}"
            col_children.append(hdiv_id)
            comps.append({"id": hdiv_id, "component": "MaterialDivider"})

    comps.insert(
        1,
        {
            "id": col_id,
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "4px", "width": "100%"},
            "children": col_children,
        },
    )
    return card_id, comps


def get_vendor_comparison_3cards_ui(
    finops_spec: dict[str, Any] | None = None,
    ciso_spec: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Render Turn 1 inline in chat using runtime dynamic specs from Morgan and Marcus:
    - Card 1: Morgan's Comparative FinOps TCO Evaluation (pure unit-rate math + live Google Search patterns)
    - Card 2: Marcus's Zero-Trust & Architecture Compliance Review (1-2 liner CISO mandate summary)
    - Card 3: Marcus's Final Audit Verdict Card directly underneath Card 2
    - Card 4: Authoritative References & Grounding Citations Card at the bottom
    """
    surface_id = "syf_turn1_baseline_inline"
    f_spec = finops_spec or {}
    c_spec = ciso_spec or {}

    vendor_rows = f_spec.get("rows") or [
        (
            "Deployment",
            ("⚠️ Multi-Tenant Cloud SaaS (External Egress)", False),
            ("⚠️ Hybrid SaaS Control + Customer VPC Data Plane", False),
            ("100% Self-Hosted on SYF AWS ROSA OpenShift", True),
        ),
        (
            "5M Baseline",
            ("⚠️ $185,000 / yr", True),
            ("⚠️ $135,000 / yr", True),
            ("$76,000 / yr", True),
        ),
        (
            "50M Surge",
            ("⚠️ $1,085,000 / yr", True),
            ("⚠️ $804,000 / yr", True),
            ("$130,000 / yr", True),
        ),
        (
            "P95 Latency",
            ("⚠️ 85.0 ms", False),
            ("⚠️ 48.0 ms", False),
            ("13.8 ms", True),
        ),
        (
            "Metering",
            ("⚠️ Metered SaaS ($1,667/1M spans + $85k base)", False),
            ("⚠️ Metered spans ($1,200/1M) + hybrid proxy", False),
            ("Flat $36k/yr License ($0 per-span penalty)", True),
        ),
        (
            "Storage/Infra",
            ("Proprietary SaaS store; zero customer compression", False),
            ("Hybrid S3/Parquet; cross-account proxy overhead", False),
            ("ClickHouse ZSTD (8x-10x); ROSA $40k->$94k/yr", False),
        ),
        (
            "3-Yr Impact",
            ("⚠️ $3,255,000 3-Yr TCO", True),
            ("⚠️ $2,412,000 3-Yr TCO", True),
            ("$390,000 3-Yr TCO (Saves $2,865,000)", True),
        ),
    ]
    vendor_pills = f_spec.get("verdict_pills") or [
        {
            "text": "✕ Rejected (8.3x TCO) | 85.0ms (>25ms SLA)",
            "line1": "✕ Rejected (8.3x TCO)",
            "line2": "85.0ms (>25ms SLA)",
            "bg": "#c62828",
            "color": "#ffffff",
        },
        {
            "text": "✕ Rejected (6.2x TCO) | 48.0ms (>25ms SLA)",
            "line1": "✕ Rejected (6.2x TCO)",
            "line2": "48.0ms (>25ms SLA)",
            "bg": "#c62828",
            "color": "#ffffff",
        },
        {
            "text": "✓ Selected (Best TCO) | 13.8ms (<25ms SLA)",
            "line1": "✓ Selected (Best TCO)",
            "line2": "13.8ms (<25ms SLA)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
    ]

    vendor_card_id, vendor_card_comps = _build_four_col_matrix_card(
        prefix="t1_vendors",
        corner_label="Benchmarks",
        col_specs=[
            {
                "title": "Arize AX Enterprise",
                "title_color": "#111827",
            },
            {
                "title": "Braintrust Enterprise",
                "title_color": "#111827",
            },
            {
                "title": "Langfuse v3",
                "title_color": "#111827",
            },
        ],
        rows=vendor_rows,
        verdict_pills=vendor_pills,
    )

    ciso_rows = c_spec.get("rows") or [
        (
            "Mandate / SLA",
            ("Prohibits any external cloud egress of unmasked PAN, SSN, or CareCredit PHI.", False),
            ("Requires Entra ID OAuth 2.0 / OIDC tokens and strict mTLS 1.3 inside AWS ROSA.", False),
            ("Enforces a <25.0 ms P95 telemetry budget with zero impact on checkout flows.", False),
        ),
        (
            "Control Plane",
            ("FastAPI sidecar scrubs PAN, SSN, and PHI inline before telemetry leaves the pod.", False),
            ("Kong v3.4 ingress validates Entra ID JWTs locally using a 300s JWKS cache.", False),
            ("Async OTel BatchSpanProcessor exports traces in 13.8 ms P95 on Red Hat UBI9.", False),
        ),
        (
            "Zero-Trust",
            ("100% of telemetry stays inside Synchrony's private AWS ROSA ClickHouse cluster.", True),
            ("Eliminates external SaaS API keys, public webhooks, and cross-account proxies.", True),
            ("Circuit breaker drops spans silently if ClickHouse degrades, protecting checkout.", True),
        ),
    ]
    ciso_verdict_badge = c_spec.get("verdict_badge") or "✅ FINAL AUDIT VERDICT — Langfuse v3 Approved"
    ciso_verdict_lead = (
        c_spec.get("verdict_lead")
        or "Langfuse v3 is the only platform that satisfies all three Synchrony CISO mandates:"
    )
    ciso_verdict_checks = c_spec.get("verdict_checks") or [
        "• ✓ Zero External Egress (PCI & HIPAA)",
        "• ✓ Strict In-VPC mTLS 1.3 Isolation",
        "• ✓ 13.8 ms P95 Latency (<25ms SLA)",
    ]

    ciso_card_id, ciso_card_comps = _build_four_col_matrix_card(
        prefix="t1_ciso",
        corner_label="Audit Dimension",
        col_specs=[
            {
                "title": "PCI-DSS v4.0 & CareCredit HIPAA",
                "title_color": "#111827",
            },
            {
                "title": "Identity, mTLS & Ingress Gateway",
                "title_color": "#111827",
            },
            {
                "title": "Cross-Cloud Latency SLA (<25ms)",
                "title_color": "#111827",
            },
        ],
        rows=ciso_rows,
    )

    ciso_verdict_card_id = "t1_ciso_verdict_card"
    ciso_verdict_comps: list[dict[str, Any]] = [
        {
            "id": ciso_verdict_card_id,
            "component": "MaterialCard",
            "appearance": "outlined",
            "style": {
                "width": "100%",
                "padding": "14px",
                "border": "1px solid #cfd8dc",
                "backgroundColor": "#ffffff",
                "borderRadius": "8px",
            },
            "children": ["t1_ciso_verdict_col"],
        },
        {
            "id": "t1_ciso_verdict_col",
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "8px", "width": "100%"},
            "children": [
                "t1_ciso_verdict_hdr_row",
                "t1_ciso_verdict_hdiv",
                "t1_ciso_verdict_lead",
                "t1_ciso_verdict_checks_row",
            ],
        },
        {
            "id": "t1_ciso_verdict_hdr_row",
            "component": "MaterialRow",
            "align": "center",
            "justify": "spaceBetween",
            "style": {
                "gap": "8px",
                "padding": "7px 8px",
                "width": "100%",
                "backgroundColor": "#e2e8f0",
                "borderRadius": "4px",
            },
            "children": ["t1_ciso_verdict_title", "t1_ciso_verdict_badge"],
        },
        {
            "id": "t1_ciso_verdict_title",
            "component": "MaterialText",
            "text": "Final CISO Audit Verdict",
            "usageHint": "body2",
            "style": {
                "fontSize": "12.5px",
                "fontWeight": "bold",
                "color": "#111827",
            },
        },
        {
            "id": "t1_ciso_verdict_badge",
            "component": "MaterialText",
            "text": ciso_verdict_badge,
            "usageHint": "caption",
            "style": {
                "fontSize": "11px",
                "fontWeight": "bold",
                "color": "#1b5e20",
                "backgroundColor": "#e8f5e9",
                "padding": "4px 10px",
                "borderRadius": "4px",
            },
        },
        {"id": "t1_ciso_verdict_hdiv", "component": "MaterialDivider"},
        {
            "id": "t1_ciso_verdict_lead",
            "component": "MaterialText",
            "text": ciso_verdict_lead,
            "usageHint": "body2",
            "style": {
                "fontSize": "12px",
                "fontWeight": "bold",
                "color": "#111827",
                "padding": "2px 4px",
            },
        },
        {
            "id": "t1_ciso_verdict_checks_row",
            "component": "MaterialRow",
            "align": "center",
            "justify": "spaceBetween",
            "style": {
                "gap": "8px",
                "padding": "8px 8px",
                "width": "100%",
                "backgroundColor": "#f0f7ff",
                "borderRadius": "4px",
            },
            "children": [
                "t1_ciso_chk_0",
                "t1_ciso_chk_vdiv_0",
                "t1_ciso_chk_1",
                "t1_ciso_chk_vdiv_1",
                "t1_ciso_chk_2",
            ],
        },
        {
            "id": "t1_ciso_chk_0",
            "component": "MaterialText",
            "text": ciso_verdict_checks[0],
            "usageHint": "caption",
            "style": {
                "fontSize": "11.5px",
                "fontWeight": "normal",
                "color": "#111827",
            },
        },
        {
            "id": "t1_ciso_chk_vdiv_0",
            "component": "MaterialDivider",
            "vertical": True,
            "style": {"width": "1px", "maxWidth": "1px"},
        },
        {
            "id": "t1_ciso_chk_1",
            "component": "MaterialText",
            "text": ciso_verdict_checks[1],
            "usageHint": "caption",
            "style": {
                "fontSize": "11.5px",
                "fontWeight": "normal",
                "color": "#111827",
            },
        },
        {
            "id": "t1_ciso_chk_vdiv_1",
            "component": "MaterialDivider",
            "vertical": True,
            "style": {"width": "1px", "maxWidth": "1px"},
        },
        {
            "id": "t1_ciso_chk_2",
            "component": "MaterialText",
            "text": ciso_verdict_checks[2],
            "usageHint": "caption",
            "style": {
                "fontSize": "11.5px",
                "fontWeight": "normal",
                "color": "#111827",
            },
        },
    ]

    t1_citations_groups = f_spec.get("citations_groups") or [
        {
            "category": "Confluence Cloud (v1.0 DRAFT)",
            "links": [
                {
                    "label": "Confluence PRD (PRD-AI-EVAL-101)",
                    "url": "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/393219/PRD-AI-EVAL-101",
                },
                {
                    "label": "Architecture Decision Record (ADR-001)",
                    "url": "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/458759/ADR-001-Eval-Gateway",
                },
            ],
        },
        {
            "category": "Synchrony Governance & FinOps (GCS)",
            "links": [
                {
                    "label": "SYF CISO Governance Standards",
                    "url": "https://storage.cloud.google.com/Utility-synchrony-data-2026/governance/SYF-Enterprise-Architecture-Standards.md",
                },
                {
                    "label": "SYF FinOps Vendor Benchmarks",
                    "url": "https://storage.cloud.google.com/Utility-synchrony-data-2026/benchmarks/eval_vendor_benchmarks.json",
                },
            ],
        },
        {
            "category": "Google Search Grounding Citations",
            "links": [
                {
                    "label": "Langfuse v3 Self-Hosted ClickHouse Docs",
                    "url": "https://langfuse.com/docs/deployment/v3/overview",
                },
                {
                    "label": "Arize AX Enterprise SaaS Pricing",
                    "url": "https://arize.com/pricing",
                },
                {
                    "label": "Braintrust Hybrid Deployment Guide",
                    "url": "https://www.braintrust.dev/docs/guides/self-hosting",
                },
            ],
        },
    ]
    t1_cit_card_id, t1_cit_comps = _build_citations_card(
        prefix="t1_citations",
        title="Authoritative References, Confluence v1.0 & Grounding Citations",
        groups=t1_citations_groups,
    )

    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "14px", "width": "100%"},
            "children": [
                "t1_part1_heading",
                vendor_card_id,
                "t1_section_div",
                "t1_part2_heading",
                ciso_card_id,
                ciso_verdict_card_id,
                "t1_section_div_2",
                "t1_part3_heading",
                t1_cit_card_id,
            ],
        },
        {
            "id": "t1_part1_heading",
            "component": "MaterialText",
            "text": "Part 1: Morgan's Comparative FinOps TCO Evaluation",
            "usageHint": "subtitle1",
            "style": {"fontSize": "14px", "fontWeight": "bold", "color": "#111827"},
        },
        *vendor_card_comps,
        {"id": "t1_section_div", "component": "MaterialDivider"},
        {
            "id": "t1_part2_heading",
            "component": "MaterialText",
            "text": "Part 2: Marcus's Zero-Trust & Architecture Compliance Review",
            "usageHint": "subtitle1",
            "style": {"fontSize": "14px", "fontWeight": "bold", "color": "#111827"},
        },
        *ciso_card_comps,
        *ciso_verdict_comps,
        {"id": "t1_section_div_2", "component": "MaterialDivider"},
        {
            "id": "t1_part3_heading",
            "component": "MaterialText",
            "text": "Part 3: Authoritative References & Grounding Citations",
            "usageHint": "subtitle1",
            "style": {"fontSize": "14px", "fontWeight": "bold", "color": "#111827"},
        },
        *t1_cit_comps,
    ]

    data_model = {
        "stage": "vendor_comparison",
        "selected_vendor": "Langfuse Enterprise v3",
    }
    return _build_envelopes(surface_id, components, data_model)


_CURVEBALL_CARD_SPECS: dict[str, dict[str, Any]] = {
    "CB-1": {
        "surface_id": "syf_turn2_curveball_inline",
        "heading": "Executive Curveball Assessment (v1.1 Draft — CB-1 Kong Deprecation)",
        "cb1_banner": {
            "text": "✓ CISO & SLA Approved | 11.2ms P95 (<25ms SLA)",
            "line1": "✓ CISO & SLA Approved",
            "line2": "11.2ms P95 (<25ms SLA)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb1_rows": [
            ("Replaced v1.0", "Kong Enterprise API Gateway v3.4", True),
            ("v1.1 Fix", "Envoy Sidecars + mTLS 1.3 (24h Certs)", True),
            ("P95 Latency", "11.2 ms P95 (< 25.0 ms SLA)", True),
        ],
        "cb2_banner": {
            "text": "✓ FinOps Approved | $130k/yr at 50M ($0 Delta)",
            "line1": "✓ FinOps Approved",
            "line2": "$130k/yr at 50M ($0 Delta)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb2_rows": [
            ("Cost Delta", "$0 / yr (In-VPC AWS ROSA Mesh)", True),
            ("Annual TCO", "$76k/yr (5M) | $130k/yr (50M)", True),
            ("Sprint Scope", "1 Sprint (8 Stories -> @Devin)", True),
        ],
    },
    "CB-2": {
        "surface_id": "syf_turn2_curveball_cb2_inline",
        "heading": "Executive Curveball Assessment (v1.1 Draft — CB-2 OTel gRPC Memory Leak)",
        "cb1_banner": {
            "text": "✓ CISO & SLA Approved | 13.8ms P95 (<25ms SLA)",
            "line1": "✓ CISO & SLA Approved",
            "line2": "13.8ms P95 (<25ms SLA)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb1_rows": [
            ("Replaced v1.0", "OTel gRPC Exporter (C-Core Leak)", True),
            ("v1.1 Fix", "OTLP/HTTP Protobuf + BoundedQueue", True),
            ("P95 Latency", "13.8 ms P95 (< 25.0 ms SLA)", True),
        ],
        "cb2_banner": {
            "text": "✓ FinOps Approved | $130k/yr at 50M ($0 Delta)",
            "line1": "✓ FinOps Approved",
            "line2": "$130k/yr at 50M ($0 Delta)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb2_rows": [
            ("Cost Delta", "$0 / yr (No Pod RAM Increase)", True),
            ("Annual TCO", "$76k/yr (5M) | $130k/yr (50M)", True),
            ("Sprint Scope", "1 Sprint (8 Stories -> @Devin)", True),
        ],
    },
    "CB-3": {
        "surface_id": "syf_turn2_curveball_cb3_inline",
        "heading": "Executive Curveball Assessment (v1.1 Draft — CB-3 50M Spans/Mo Surge)",
        "cb1_banner": {
            "text": "✓ CISO & SLA Approved | 13.8ms P95 (<25ms SLA)",
            "line1": "✓ CISO & SLA Approved",
            "line2": "13.8ms P95 (<25ms SLA)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb1_rows": [
            ("Replaced v1.0", "Fixed 3-Pod Gateway (5M Spans/Mo)", True),
            ("v1.1 Fix", "ClickHouse ZSTD(3) + HPA (3->12 Pods)", True),
            ("P95 Latency", "13.8 ms P95 (< 25.0 ms SLA)", True),
        ],
        "cb2_banner": {
            "text": "✓ FinOps Approved | $130k/yr at 50M ($0 Delta)",
            "line1": "✓ FinOps Approved",
            "line2": "$130k/yr at 50M ($0 Delta)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb2_rows": [
            ("Cost Delta", "$0 / yr (Flat License at 50M)", True),
            ("Annual TCO", "$76k/yr (5M) | $130k/yr (50M)", True),
            ("Sprint Scope", "1 Sprint (8 Stories -> @Devin)", True),
        ],
    },
    "CB-4": {
        "surface_id": "syf_turn2_curveball_cb4_inline",
        "heading": "Executive Curveball Assessment (v1.1 Draft — CB-4 CareCredit HIPAA PHI)",
        "cb1_banner": {
            "text": "✓ CISO & SLA Approved | 13.8ms P95 (<25ms SLA)",
            "line1": "✓ CISO & SLA Approved",
            "line2": "13.8ms P95 (<25ms SLA)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb1_rows": [
            ("Replaced v1.0", "PCI-Only Scrubber (PAN, CVV, SSN)", True),
            ("v1.1 Fix", "Adds CareCredit MRN, ICD-10 & NPI", True),
            ("P95 Latency", "13.8 ms P95 (< 25.0 ms SLA)", True),
        ],
        "cb2_banner": {
            "text": "✓ FinOps Approved | $130k/yr at 50M ($0 Delta)",
            "line1": "✓ FinOps Approved",
            "line2": "$130k/yr at 50M ($0 Delta)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb2_rows": [
            ("Cost Delta", "$0 / yr (In-Process FastAPI Regex)", True),
            ("Annual TCO", "$76k/yr (5M) | $130k/yr (50M)", True),
            ("Sprint Scope", "1 Sprint (8 Stories -> @Devin)", True),
        ],
    },
    "CB-5": {
        "surface_id": "syf_turn2_curveball_cb5_inline",
        "heading": "Executive Curveball Assessment (v1.1 Draft — CB-5 Entra ID JWKS Cache)",
        "cb1_banner": {
            "text": "✓ CISO & SLA Approved | 13.8ms P95 (<25ms SLA)",
            "line1": "✓ CISO & SLA Approved",
            "line2": "13.8ms P95 (<25ms SLA)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb1_rows": [
            ("Replaced v1.0", "Per-Request JWKS Fetch (190 ms)", True),
            ("v1.1 Fix", "PyJWKClient(lifespan=300) Local Cache", True),
            ("P95 Latency", "13.8 ms P95 (< 25.0 ms SLA)", True),
        ],
        "cb2_banner": {
            "text": "✓ FinOps Approved | $130k/yr at 50M ($0 Delta)",
            "line1": "✓ FinOps Approved",
            "line2": "$130k/yr at 50M ($0 Delta)",
            "bg": "#0d47a1",
            "color": "#ffffff",
        },
        "cb2_rows": [
            ("Cost Delta", "$0 / yr (In-Memory Pod Cache)", True),
            ("Annual TCO", "$76k/yr (5M) | $130k/yr (50M)", True),
            ("Sprint Scope", "1 Sprint (8 Stories -> @Devin)", True),
        ],
    },
}


def get_curveball_3cards_ui(
    cb_id: str | None = None,
    dynamic_spec: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Render Turn 2 inline in chat: 2 Side-by-Side Curveball Impact Cards + Citations Card + Centered Approve/Reject Bar."""
    norm_cb = (cb_id or "CB-1").upper().strip()
    base_spec = _CURVEBALL_CARD_SPECS.get(norm_cb, _CURVEBALL_CARD_SPECS["CB-1"])

    dyn = dynamic_spec or {}
    surface_id = dyn.get("surface_id") or base_spec["surface_id"]
    heading = dyn.get("heading") or base_spec["heading"]
    cb1_rows = dyn.get("cb1_rows") or base_spec["cb1_rows"]
    cb1_raw = dyn.get("cb1_verdict_pill") or base_spec["cb1_banner"]
    cb2_rows = dyn.get("cb2_rows") or base_spec["cb2_rows"]
    cb2_raw = dyn.get("cb2_verdict_pill") or base_spec["cb2_banner"]

    if isinstance(cb1_raw, dict):
        cb1_line1 = cb1_raw.get("line1") or cb1_raw.get("text") or "✓ CISO & SLA Approved"
        cb1_line2 = cb1_raw.get("line2") or "13.8ms P95 (<25ms SLA)"
        cb1_bg = cb1_raw.get("bg") or "#0d47a1"
        cb1_color = cb1_raw.get("color") or "#ffffff"
    else:
        cb1_line1 = str(cb1_raw)
        cb1_line2 = "13.8ms P95 (<25ms SLA)"
        cb1_bg = "#0d47a1"
        cb1_color = "#ffffff"

    if isinstance(cb2_raw, dict):
        cb2_line1 = cb2_raw.get("line1") or cb2_raw.get("text") or "✓ FinOps Approved"
        cb2_line2 = cb2_raw.get("line2") or "$130k/yr at 50M ($0 Delta)"
        cb2_bg = cb2_raw.get("bg") or "#0d47a1"
        cb2_color = cb2_raw.get("color") or "#ffffff"
    else:
        cb2_line1 = str(cb2_raw)
        cb2_line2 = "$130k/yr at 50M ($0 Delta)"
        cb2_bg = "#0d47a1"
        cb2_color = "#ffffff"

    cb1_id, cb1_comps = _build_two_col_card(
        prefix="t2_cb1",
        title="Architecture Delta (v1.0 → v1.1)",
        title_color="#111827",
        card_border="1px solid #cfd8dc",
        card_bg="#ffffff",
        banner_text=cb1_line1,
        banner_bg=cb1_bg,
        banner_color=cb1_color,
        rows=cb1_rows,
        header_gray_bg=True,
        alternate_rows=True,
        banner_at_bottom=True,
        banner_line2=cb1_line2,
    )

    cb2_id, cb2_comps = _build_two_col_card(
        prefix="t2_cb2",
        title="FinOps & Schedule Blast Radius",
        title_color="#111827",
        card_border="1px solid #cfd8dc",
        card_bg="#ffffff",
        banner_text=cb2_line1,
        banner_bg=cb2_bg,
        banner_color=cb2_color,
        rows=cb2_rows,
        header_gray_bg=True,
        alternate_rows=True,
        banner_at_bottom=True,
        banner_line2=cb2_line2,
    )

    t2_citations_groups = dyn.get("citations_groups") or [
        {
            "category": "Live Confluence PRD (v1.1 DRAFT)",
            "links": [
                {
                    "label": "Open PRD-AI-EVAL-101 (v1.1)",
                    "url": "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/393219/PRD-AI-EVAL-101",
                },
                {
                    "label": "View Line-by-Line Revision Diff",
                    "url": "https://synchrony-team.atlassian.net/wiki/spaces/SD/pages/viewpreviousversions.action?pageId=393219",
                },
            ],
        },
        {
            "category": "Synchrony Governance Policy (GCS)",
            "links": [
                {
                    "label": "SYF CISO & Enterprise Architecture Standards",
                    "url": "https://storage.cloud.google.com/Utility-synchrony-data-2026/governance/SYF-Enterprise-Architecture-Standards.md",
                }
            ],
        },
        {
            "category": "External Technical & Community Grounding",
            "links": [
                {
                    "label": "StackOverflow Technical Citation",
                    "url": "https://stackoverflow.com/questions/tagged/opentelemetry",
                },
                {
                    "label": "GitHub Issue Tracker Citation",
                    "url": "https://github.com/open-telemetry/opentelemetry-python/issues",
                },
                {
                    "label": "Reddit / HN Community Thread",
                    "url": "https://www.reddit.com/r/devops/",
                },
            ],
        },
    ]
    t2_cit_card_id, t2_cit_comps = _build_citations_card(
        prefix="t2_citations",
        title="Live Confluence v1.1 Revision, Governance & Technical Citations",
        groups=t2_citations_groups,
    )

    btn_extra_comps: list[dict[str, Any]] = [
        {
            "id": "t2_cb3_btn_row",
            "component": "MaterialRow",
            "justify": "center",
            "align": "center",
            "style": {
                "gap": "14px",
                "paddingTop": "4px",
                "flexWrap": "wrap",
                "width": "100%",
            },
            "children": ["btn_approve_commit_t3", "btn_reject_draft_t3"],
        },
        {
            "id": "btn_approve_commit_t3",
            "component": "MaterialButton",
            "label": "Approve & Commit",
            "variant": "raised",
            "color": "primary",
            "leadingIcon": "rocket_launch",
            "style": {
                "backgroundColor": "#0d47a1",
                "color": "#ffffff",
                "fontWeight": "bold",
                "padding": "6px 18px",
                "borderRadius": "6px",
            },
            "action": {
                "event": {
                    "name": "approve_v2_sdlc",
                    "context": {
                        "stage": "sdlc_approved",
                        "curveball_id": norm_cb,
                        "message": "Approve & Commit [State: stage=sdlc_approved]",
                    },
                }
            },
        },
        {
            "id": "btn_reject_draft_t3",
            "component": "MaterialButton",
            "label": "Reject / Keep in Draft",
            "variant": "raised",
            "color": "warn",
            "leadingIcon": "cancel",
            "style": {
                "backgroundColor": "#c62828",
                "color": "#ffffff",
                "fontWeight": "bold",
                "padding": "6px 18px",
                "borderRadius": "6px",
            },
            "action": {
                "event": {
                    "name": "reject_v2_sdlc",
                    "context": {
                        "stage": "sdlc_rejected",
                        "curveball_id": norm_cb,
                        "message": "Reject / Keep in Draft [State: stage=sdlc_rejected]",
                    },
                }
            },
        },
    ]

    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "14px", "width": "100%"},
            "children": [
                "t2_heading",
                "t2_cards_row",
                t2_cit_card_id,
                "t2_cb3_btn_row",
            ],
        },
        {
            "id": "t2_heading",
            "component": "MaterialText",
            "text": heading,
            "usageHint": "subtitle1",
            "style": {"fontSize": "14px", "fontWeight": "bold", "color": "#111827"},
        },
        {
            "id": "t2_cards_row",
            "component": "MaterialRow",
            "align": "stretch",
            "justify": "spaceBetween",
            "style": {"gap": "12px", "flexWrap": "nowrap"},
            "children": [cb1_id, cb2_id],
        },
        *cb1_comps,
        *cb2_comps,
        *t2_cit_comps,
        *btn_extra_comps,
    ]

    data_model = {
        "stage": "curveball",
        "curveball_id": norm_cb,
        "ingress_architecture": "Synchrony Internal Service Mesh (Envoy + mTLS 1.3)",
    }
    return _build_envelopes(surface_id, components, data_model)


def get_turn3_approval_3cards_ui() -> list[dict[str, Any]]:
    """Render Turn 3 inline in chat: 3 Side-by-Side SDLC Execution & @Devin Handoff Cards."""
    surface_id = "syf_turn3_approval_inline"

    c1_id, c1_comps = _build_two_col_card(
        prefix="t3_conf",
        title="Confluence Artifacts Finalized",
        title_color="#1b5e20",
        card_border="2px solid #2e7d32",
        card_bg="#ffffff",
        banner_text="✅ APPROVED — v1.1 Finalized in Confluence",
        banner_bg="#e8f5e9",
        banner_color="#1b5e20",
        rows=[
            ("PRD Status", "PRD-AI-EVAL-101.md promoted to v1.1 | ✅ APPROVED", True),
            ("ADR Status", "ADR-001-Eval-Gateway.md promoted to v1.1 | ✅ APPROVED", True),
            ("Diff History", "Inline v1.1 additions (green) & v1.0 deprecations (red) preserved", False),
        ],
    )

    c2_id, c2_comps = _build_two_col_card(
        prefix="t3_jira",
        title="Jira Sprint 1 Backlog Synced",
        title_color="#0d47a1",
        card_border="1px solid #90caf9",
        card_bg="#ffffff",
        banner_text="✅ CREATED — 8 Stories Linked to SYF-5",
        banner_bg="#e3f2fd",
        banner_color="#0d47a1",
        rows=[
            ("Sprint 1 Scope", "8 Stories (SYF-6..SYF-13 / AI-STORY-101..108, 32 SP) created in Jira", True),
            ("Assignee", "All 8 Sprint 1 stories assigned to @Devin (syf-dev-agent)", True),
            ("GCS State", "BACKLOG-AI-EVAL-101.json synced with live Jira keys & custom spec", False),
        ],
    )

    c3_id, c3_comps = _build_two_col_card(
        prefix="t3_devin",
        title="@Devin Implementation Handoff",
        title_color="#4a148c",
        card_border="1px solid #ce93d8",
        card_bg="#ffffff",
        banner_text="🚀 READY — Invoke @Devin for 7-Step Build",
        banner_bg="#f3e5f5",
        banner_color="#4a148c",
        rows=[
            ("Assignee", "@Devin (SYF Lead Platform Developer Agent in Gemini Enterprise)", True),
            ("Target Build", "8-File OpenShift Gateway + 12/12 Security, DLP & Latency QA Suite", False),
            ("Live Gateway", "Deploys & verifies live FastAPI Gateway + opens Bitbucket PR", True),
        ],
    )

    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialColumn",
            "align": "stretch",
            "style": {"gap": "14px", "width": "100%"},
            "children": [
                "t3_heading",
                "t3_cards_row",
            ],
        },
        {
            "id": "t3_heading",
            "component": "MaterialText",
            "text": "SDLC Approval Complete — Confluence v1.1, Jira Sprint 1 & @Devin Handoff",
            "usageHint": "subtitle1",
            "style": {"fontSize": "14px", "fontWeight": "normal", "color": "#1b5e20"},
        },
        {
            "id": "t3_cards_row",
            "component": "MaterialRow",
            "align": "stretch",
            "justify": "spaceBetween",
            "style": {"gap": "12px", "flexWrap": "nowrap"},
            "children": [c1_id, c2_id, c3_id],
        },
        *c1_comps,
        *c2_comps,
        *c3_comps,
    ]

    data_model = {
        "stage": "sdlc_approved",
        "prd_status": "v1.1 | APPROVED",
    }
    return _build_envelopes(surface_id, components, data_model)


def _detect_curveball_id(text: str) -> str:
    t = (text or "").lower()
    if "cb-2" in t or "grpc" in t or "memory leak" in t or "512mi" in t:
        return "CB-2"
    if "cb-3" in t or "50m" in t or "capacity freeze" in t or "black friday" in t or "10x" in t or "zstd" in t or "hpa" in t:
        return "CB-3"
    if "cb-4" in t or "hipaa" in t or "mrn" in t or "icd-10" in t or "phi" in t:
        return "CB-4"
    if "cb-5" in t or "jwks" in t or "190ms" in t or "42.3ms" in t or "entra id token introspection" in t:
        return "CB-5"
    return "CB-1"


def select_a2ui_cards_for_turn(
    query: str,
    full_text: str,
    stage: str | None = None,
    executed_tools: list[str] | set[str] | None = None,
    tool_outputs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically select the inline A2UI v0.9 cards based on executed tools and turn stage."""
    q_lower = (query or "").lower()
    combined = f"{query or ''} {full_text or ''}"
    rec_tools, rec_outputs = get_and_clear_executed_tools()

    # 1. When executed_tools is provided by a2a.py (or recorded in-turn), use strict tool-execution state machine:
    if executed_tools is not None or rec_tools:
        tools_set = set(executed_tools or []) | set(rec_tools)
        merged_outputs = {**(rec_outputs or {}), **(tool_outputs or {})}
        marcus_out = merged_outputs.get("consult_marcus_architecture_specialist") or {}

        # Out-of-Nowhere / Unscripted technical question or Reject / Blocker -> 0 A2UI cards
        if (
            ("stage_runtime_custom_story" in tools_set and "execute_approved_sdlc_sync" not in tools_set)
            or marcus_out.get("mode") == "unscripted"
            or marcus_out.get("review_mode") == "UNSCRIPTED_TECHNICAL_DEEP_DIVE"
            or marcus_out.get("a2ui_cards_mode") == "NONE_PURE_MARKDOWN"
            or "sync_sdlc_ticket_blocker" in tools_set
            or stage in ("sdlc_rejected", "blocker_triage")
        ):
            return []

        # Turn 3: Approve & Commit -> 3 Approval Summary cards
        if (
            stage == "sdlc_approved"
            or bool(
                tools_set
                & {
                    "publish_confluence_prd",
                    "create_jira_epic",
                    "create_jira_story",
                    "consolidate_executive_memory",
                    "execute_approved_sdlc_sync",
                }
            )
        ):
            return get_turn3_approval_3cards_ui()

        # Turn 2: Curveball analysis & staging -> 2 Curveball cards + Bottom Approve/Reject Bar
        if (
            stage == "curveball"
            or "stage_curveball_jira_story" in tools_set
            or "patch_document_section" in tools_set
            or marcus_out.get("mode") == "curveball"
            or marcus_out.get("review_mode") == "EXECUTIVE_CURVEBALL_IMPACT_ANALYSIS"
        ):
            cb_from_out = (
                (merged_outputs.get("stage_curveball_jira_story") or {}).get("curveball_id")
                or marcus_out.get("curveball_code")
                or (marcus_out.get("curveball_impact") or {}).get("code")
            )
            dyn_spec = marcus_out.get("dynamic_card_spec") or (
                (marcus_out.get("curveball_impact") or {}).get("dynamic_card_spec")
            )
            return get_curveball_3cards_ui(
                cb_from_out or _detect_curveball_id(combined),
                dynamic_spec=dyn_spec,
            )

        # Turn 1: Baseline vendor evaluation -> Dynamic FinOps + CISO Matrix Cards
        if (
            "consult_morgan_finops_specialist" in tools_set
            or (
                "consult_marcus_architecture_specialist" in tools_set
                and marcus_out.get("mode") in (None, "baseline")
            )
        ):
            morgan_out = merged_outputs.get("consult_morgan_finops_specialist") or {}
            return get_vendor_comparison_3cards_ui(
                finops_spec=morgan_out.get("turn1_finops_card_spec"),
                ciso_spec=marcus_out.get("turn1_ciso_card_spec"),
            )

        # No catch-all else when executed_tools is provided
        return []

    # 2. Fallback when executed_tools is None (e.g., direct unit-test calls):
    if stage == "sdlc_approved" or any(
        kw in q_lower
        for kw in [
            "stage=sdlc_approved",
            "approve & commit",
            "approve and commit",
            "approve langfuse",
            "approve the v2",
            "approve v2",
            "commit jira",
            "execute_sdlc",
        ]
    ):
        return get_turn3_approval_3cards_ui()

    if stage in ("blocker_triage", "sdlc_rejected") or (
        "curveball" not in q_lower
        and "cb-5" not in q_lower
        and any(
            kw in q_lower
            for kw in [
                "syf-7",
                "ai-story-102",
                "load test",
                "blocker",
                "custom requirement",
                "out of nowhere",
            ]
        )
    ):
        return []

    if stage in ("curveball", "curveball_evaluated") or any(
        kw in q_lower
        for kw in [
            "stage=curveball",
            "curveball",
            "kong",
            "cve-2026",
            "envoy",
            "service mesh",
            "wasm",
            "deprecat",
            "memory leak",
            "grpc",
            "cb-1",
            "cb-2",
            "cb-3",
            "cb-4",
            "cb-5",
            "190ms",
            "jwks",
        ]
    ):
        return get_curveball_3cards_ui(_detect_curveball_id(combined))

    return get_vendor_comparison_3cards_ui()
