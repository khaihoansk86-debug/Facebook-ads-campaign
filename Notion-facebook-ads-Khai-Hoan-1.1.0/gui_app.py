#!/usr/bin/env python3
TAG_COLORS = {
    "objective": "#3b82f6", # Blue
    "destination": "#10b981", # Emerald
    "budget": "#f59e0b", # Amber
    "audience": "#8b5cf6", # Violet
    "placement": "#ec4899", # Pink
    "default": "#64748b" # Slate
}
import json
import os
import queue
import hashlib
import sys
import threading
import time
import customtkinter as ctk
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import bulk_ads_tool as tool


APP_TITLE = "Notion -> Facebook Ads Khải Hoàn"

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR

ENV_PATH = APP_DIR / ".env"
ASSET_DIR = RESOURCE_DIR / "assets"
SAMPLE_DIR = RESOURCE_DIR / "sample"
APP_ICON = ASSET_DIR / "app_icon.ico"
APP_LOGO = ASSET_DIR / "app_logo.png"
PACKAGE_SAMPLE_CSV = SAMPLE_DIR / "facebook_ads_template.csv"

COLORS = {
    "bg": "#edf2f8",
    "surface": "#ffffff",
    "surface_alt": "#f4f8ff",
    "border": "#d8e1ee",
    "shadow": "#d9e2ef",
    "text": "#142033",
    "muted": "#5f6f86",
    "primary": "#1768d1",
    "primary_dark": "#0d4fa8",
    "success": "#0f9f6e",
    "warning": "#c77700",
    "danger": "#d93025",
    "sidebar": "#0d1b2a",
    "sidebar_active": "#153b68",
    "canvas": "#0f1724",
    "canvas_soft": "#182233",
    "canvas_line": "#243247",
    "canvas_text": "#f4f7fb",
    "accent_soft": "#dce9ff",
    "field": "#f7faff",
    "field_border": "#cbd8ea",
}

FONTS = {
    "h1": ("Roboto", 18, "bold"),
    "h2": ("Roboto", 14, "bold"),
    "body": ("Roboto", 13),
    "body_bold": ("Roboto", 13, "bold"),
    "small": ("Roboto", 12),
    "small_bold": ("Roboto", 12, "bold"),
}


class BulkAdsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme('blue')
        self.title(APP_TITLE)
        self.geometry("1240x820")
        self.minsize(1080, 720)
        self.configure(fg_color=COLORS["bg"])
        if APP_ICON.exists():
            self.iconbitmap(str(APP_ICON))

        self.log_queue = queue.Queue()
        self.auto_scan = False
        self.scan_thread = None
        self.telegram_update_offset = None
        self.last_canceled_signature = ""
        self.pages = {}
        self.nav_buttons = {}
        self.planner_catalog = tool.load_planner_bundles()
        self.planner_campaign_bundles = []
        self.planner_adset_bundles = []
        self.planner_audience_presets = []
        self.planner_dataset_presets = []
        self.planner_budget_presets = []
        self.planner_placement_presets = []
        self.planner_campaign_vars = {}
        self.planner_campaign_cards = {}
        self.planner_adset_listboxes = {}
        self.planner_location_vars = {}
        self.planner_selected_adset_codes = set()
        self.planner_focus_campaign_code = None
        self.planner_flows = []
        self.planner_flow_sequence = 0

        sample_default = str(PACKAGE_SAMPLE_CSV if PACKAGE_SAMPLE_CSV.exists() else tool.DEFAULT_SAMPLE_CSV)
        self.vars = {
            "NOTION_TOKEN": tk.StringVar(),
            "NOTION_DATA_SOURCE_ID": tk.StringVar(value=tool.DEFAULT_DATA_SOURCE_ID),
            "NOTION_DATABASE_ID": tk.StringVar(value=tool.DEFAULT_DATA_SOURCE_ID),
            "PARENT_PAGE_ID": tk.StringVar(value=tool.DEFAULT_PARENT_PAGE_ID),
            "SAMPLE_CSV": tk.StringVar(value=sample_default),
            "TEMPLATE_ROW_INDEX": tk.StringVar(value="0"),
            "TELEGRAM_BOT_TOKEN": tk.StringVar(),
            "TELEGRAM_CHAT_ID": tk.StringVar(),
            "SCAN_INTERVAL_SECONDS": tk.StringVar(value="300"),
            "READY_STATUS_NAMES": tk.StringVar(value="Ready,To-do,Not started"),
            "EXPORTED_STATUS_NAMES": tk.StringVar(value="Done,Complete,Exported"),
            "SUPABASE_URL": tk.StringVar(),
            "SUPABASE_PUBLISHABLE_KEY": tk.StringVar(),
            "SUPABASE_SECRET_KEY": tk.StringVar(),
            "ADS_SYNC_TOKEN": tk.StringVar(),
            "MARK_EXPORTED": tk.BooleanVar(value=True),
            "INCLUDE_EXPORTED": tk.BooleanVar(value=False),
            "EXPORT_IN_PROGRESS": tk.BooleanVar(value=False),
            "TELEGRAM_CONFIRM_EXPORT": tk.BooleanVar(value=True),
        }
        self.planner_creative_mode_var = tk.StringVar(value="Dùng bài có sẵn")
        self.planner_summary_var = tk.StringVar(value="Chưa chọn cách chạy quảng cáo nào.")
        self.planner_campaign_detail_var = tk.StringVar(value="Chọn một mẫu chiến dịch để xem thiết lập.")
        self.planner_audience_summary_var = tk.StringVar(value="Chưa chọn tệp đối tượng.")
        self.planner_dataset_summary_var = tk.StringVar(value="Chưa chọn tập dữ liệu.")
        self.planner_budget_summary_var = tk.StringVar(value="Chưa chọn ngân sách.")
        self.planner_placement_summary_var = tk.StringVar(value="Chưa chọn vị trí quảng cáo.")
        self.planner_matrix_summary_var = tk.StringVar(value="Chưa có dữ liệu để tạo planner.")
        self.planner_budget_type_var = tk.StringVar(value="Ngân sách/ngày")
        self.planner_budget_amount_var = tk.StringVar()
        self.planner_audience_choice_var = tk.StringVar()
        self.planner_dataset_choice_var = tk.StringVar()
        self.planner_budget_choice_var = tk.StringVar()
        self.planner_placement_choice_var = tk.StringVar()

        self._load_env_to_vars()
        self._build_ui()
        self.after(150, self._drain_logs)

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["surface"], relief="flat")
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONTS["body"])
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=FONTS["body"])
        style.configure("Card.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["body"])
        style.configure("CardMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=FONTS["body"])
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONTS["h1"])
        style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["h2"])
        style.configure("StepTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["body_bold"])
        style.configure("StepMeta.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=FONTS["body"])
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=COLORS["field_border"], lightcolor=COLORS["field_border"], padding=10)
        style.map("TEntry", bordercolor=[("focus", COLORS["primary"])], lightcolor=[("focus", COLORS["primary"])])
        style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"], font=FONTS["body"])
        style.configure(
            "Planner.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=COLORS["text"],
            bordercolor=COLORS["field_border"],
            lightcolor=COLORS["field_border"],
            darkcolor=COLORS["field_border"],
            arrowcolor=COLORS["primary"],
            padding=8,
        )
        style.map(
            "Planner.TCombobox",
            bordercolor=[("focus", COLORS["primary"]), ("readonly", COLORS["field_border"])],
            lightcolor=[("focus", COLORS["primary"]), ("readonly", COLORS["field_border"])],
        )
        style.configure(
            "Primary.TButton",
            background=COLORS["primary"],
            foreground="#ffffff",
            font=FONTS["body_bold"],
            padding=(16, 10),
            borderwidth=1,
            relief="flat",
            bordercolor=COLORS["primary_dark"],
            lightcolor=COLORS["primary"],
            darkcolor=COLORS["primary_dark"],
        )
        style.map("Primary.TButton", background=[("active", COLORS["primary_dark"])], bordercolor=[("active", COLORS["primary_dark"])])
        style.configure(
            "Secondary.TButton",
            background="#ffffff",
            foreground=COLORS["text"],
            font=FONTS["body_bold"],
            padding=(14, 10),
            borderwidth=1,
            relief="flat",
            bordercolor=COLORS["field_border"],
            lightcolor="#ffffff",
            darkcolor=COLORS["field_border"],
        )
        style.map("Secondary.TButton", background=[("active", "#f4f8ff")], bordercolor=[("active", COLORS["primary"])])
        style.configure("Danger.TButton", background=COLORS["danger"], foreground="#ffffff", font=FONTS["body_bold"], padding=(12, 8), borderwidth=0)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=240)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        main = ctk.CTkFrame(self)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self._build_sidebar(sidebar)
        self._build_header(main)

        container = ctk.CTkFrame(main)
        container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.pages["dashboard"] = self._page_dashboard(container)
        self.pages["import"] = self._page_import(container)
        self.pages["audiences"] = self._page_audiences(container)
        self.pages["export"] = self._page_export(container)
        self.pages["config"] = self._page_config(container)
        self.pages["notion"] = self._page_notion(container)
        self.pages["logs"] = self._page_logs(container)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.show_page("dashboard")

    def _build_sidebar(self, sidebar):
        brand = ctk.CTkFrame(sidebar)
        brand.pack(fill="x", padx=18, pady=(18, 20))

        self.logo_image = None
        if APP_LOGO.exists():
            try:
                from PIL import Image
                self.logo_image = ctk.CTkImage(Image.open(APP_LOGO), size=(60, 60))
                ctk.CTkLabel(brand, image=self.logo_image, text="").pack(anchor="w")
            except tk.TclError:
                pass

        ctk.CTkLabel(
            brand,
            text="Khải Hoàn Ads",
                                    font=FONTS["h1"],
        ).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(
            brand,
            text="Notion -> Facebook Ads",
                                    font=FONTS["body"],
        ).pack(anchor="w")

        nav_items = [
            ("dashboard", "Tổng quan"),
            ("import", "Lập kế hoạch"),
            ("audiences", "Tệp đối tượng"),
            ("export", "Xuất tệp quảng cáo"),
            ("config", "Cấu hình"),
            ("notion", "Notion mẫu"),
            ("logs", "Nhật ký"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                                                                                                                                                font=FONTS["body_bold"],
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = btn

        footer = ctk.CTkFrame(sidebar)
        footer.pack(side="bottom", fill="x", padx=18, pady=18)
        ctk.CTkLabel(
            footer,
            text="Dùng cấu hình\ntừ tệp mẫu",
            justify="left",
                                    font=FONTS["small"],
        ).pack(anchor="w")

    def _build_header(self, main):
        header = ctk.CTkFrame(main)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 18))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=APP_TITLE).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Tạo bản nháp từ bài Facebook, duyệt trên Notion và xuất tệp cho Trình quản lý quảng cáo.",
                    ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        actions = ctk.CTkFrame(header)
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkButton(actions, text="Mở thư mục kết quả", command=self.open_exports).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Xuất tệp", command=self.export_now).pack(side="left")

    def _card(self, parent, title=None, subtitle=None):
        outer = ctk.CTkFrame(parent)
        border = ctk.CTkFrame(outer)
        border.pack(fill="both", expand=True, padx=(0, 0), pady=(0, 3))
        inner = ctk.CTkFrame(border)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        if title:
            ctk.CTkLabel(inner, text=title).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(inner, text=subtitle, wraplength=820).pack(anchor="w", pady=(4, 12))
        content = ctk.CTkFrame(inner)
        content.pack(fill="both", expand=True)
        return outer, content

    def _planner_creative_mode_options(self):
        return {
            "Dùng bài có sẵn": "existing_post",
            "Tạo bài mới": "new_creative",
        }

    def _selected_creative_mode(self):
        return self._planner_creative_mode_options().get(
            self.planner_creative_mode_var.get().strip(),
            "existing_post",
        )

    def _campaign_palette(self, code):
        palettes = {
            "ENG_BASE": {"bg": "#17335c", "line": "#2e74d9", "text": "#f5f9ff", "muted": "#a9c4f0"},
            "TRAFFIC_BASE": {"bg": "#123a34", "line": "#11a87d", "text": "#f4fffc", "muted": "#9fd8c9"},
            "AWARENESS_BASE": {"bg": "#4a2b14", "line": "#f2994a", "text": "#fff8f2", "muted": "#f0c39a"},
            "LEADS_BASE": {"bg": "#3b183f", "line": "#d06be8", "text": "#fff6ff", "muted": "#e5b8ef"},
            "SALES_BASE": {"bg": "#3f2514", "line": "#e0a12b", "text": "#fffaf0", "muted": "#ecd39a"},
        }
        return palettes.get(code, {"bg": "#1d2636", "line": "#61728c", "text": "#f4f7fb", "muted": "#9fb0c5"})

    def _campaign_card_title(self, bundle):
        title = bundle.get("objectiveName") or bundle.get("campaignType") or bundle.get("name") or bundle.get("code")
        return title.split(" (", 1)[0] if title else ""

    def _campaign_card_subtitle(self, bundle):
        return bundle.get("name") or bundle.get("code") or ""

    def _current_import_links(self):
        if not hasattr(self, "import_links_text"):
            return []
        return [line.strip() for line in self.import_links_text.get("1.0", "end").splitlines() if line.strip()]

    def _adset_flow_tag(self, adset_bundle):
        code = adset_bundle.get("code", "")
        tags = []

        # 1. Mục tiêu (Objective)
        if "LEAD" in code:
            tags.append({"text": "Lead", "color": TAG_COLORS["objective"]})
        elif "SALE" in code:
            tags.append({"text": "Sales", "color": TAG_COLORS["objective"]})
        elif "ENG" in code:
            tags.append({"text": "Tương tác", "color": TAG_COLORS["objective"]})
        elif "AWR" in code:
            tags.append({"text": "Nhận biết", "color": TAG_COLORS["objective"]})
        elif "APP" in code:
            tags.append({"text": "App", "color": TAG_COLORS["objective"]})
        elif "TRF" in code or "TRAFFIC" in code:
            tags.append({"text": "Traffic", "color": TAG_COLORS["objective"]})

        # 2. Đích đến / Vị trí (Destination)
        if "WEB" in code or "WEBSITE" in code:
            tags.append({"text": "Website", "color": TAG_COLORS["destination"]})
        elif "MESSENGER" in code or "MESSAGE" in code or "CONVERSATION" in code:
            tags.append({"text": "Tin nhắn", "color": TAG_COLORS["destination"]})
        elif "CALL" in code:
            tags.append({"text": "Cuộc gọi", "color": TAG_COLORS["destination"]})
        elif "APP" in code and "SALE" in code:
            tags.append({"text": "Ứng dụng", "color": TAG_COLORS["destination"]})
        elif "VIDEO" in code:
            tags.append({"text": "Xem video", "color": TAG_COLORS["destination"]})

        if not tags:
            tags.append({"text": "Tùy chỉnh", "color": TAG_COLORS["default"]})

        return tags

    def _render_campaign_card_state(self, code):
        refs = self.planner_campaign_cards.get(code)
        if not refs:
            return
        selected = bool(self.planner_campaign_vars.get(code) and self.planner_campaign_vars[code].get())
        focused = selected and self.planner_focus_campaign_code == code
        palette = self._campaign_palette(code)
        frame = refs["frame"]
        bar = refs["bar"]
        title = refs["title"]
        subtitle = refs["subtitle"]
        dot = refs["dot"]
        try:
            frame.configure(fg_color=palette["line"] if selected else COLORS["canvas_line"])
            refs["body"].configure(fg_color=palette["bg"] if selected else "#121b29")
            bar.configure(fg_color=palette["line"])
            title.configure(fg_color=palette["bg"] if selected else "#121b29", text_color=palette["text"])
            subtitle.configure(fg_color=palette["bg"] if selected else "#121b29", text_color=palette["muted"])
            dot.configure(
                text="✓" if selected else "○",
                fg_color=palette["line"] if selected else COLORS["surface_alt"],
                text_color="#ffffff" if selected else COLORS["muted"],
            )
        except ValueError:
            pass

    def _render_all_campaign_card_states(self):
        for code in self.planner_campaign_cards:
            self._render_campaign_card_state(code)

    def _toggle_campaign_bundle(self, code):
        if code not in self.planner_campaign_vars:
            return
        if self.planner_focus_campaign_code != code:
            for campaign_var in self.planner_campaign_vars.values():
                campaign_var.set(False)
            self.planner_campaign_vars[code].set(True)
            self.planner_focus_campaign_code = code
            self.planner_selected_adset_codes.clear()
            for location_var in self.planner_location_vars.values():
                location_var.set(False)
        self._render_all_campaign_card_states()
        self._refresh_planner_adset_list()

    def _toggle_conversion_location(self, key):
        if key not in self.planner_location_vars:
            return
        current = bool(self.planner_location_vars[key].get())
        for location_var in self.planner_location_vars.values():
            location_var.set(False)
        self.planner_location_vars[key].set(not current)
        self.planner_selected_adset_codes.clear()
        self._refresh_planner_adset_list()

    def _remove_selected_adset_code(self, code):
        self.planner_selected_adset_codes.discard(code)
        self._restore_rendered_adset_selections()
        self._refresh_matrix_summary()

    def _toggle_adset_chip(self, code):
        if code in self.planner_selected_adset_codes:
            self.planner_selected_adset_codes.clear()
        elif code:
            self.planner_selected_adset_codes = {code}
        self._restore_rendered_adset_selections()
        self._refresh_matrix_summary()
        if self.planner_selected_adset_codes:
            self._show_planner_setup_stage()
        else:
            self._show_planner_selection_stage()

    def _current_planner_flow_is_valid(self):
        return (
            len(self._selected_campaign_bundle_codes()) == 1
            and len(self._selected_adset_bundle_codes()) == 1
        )

    def _current_planner_draft_summary(self):
        campaign_codes = self._selected_campaign_bundle_codes()
        adset_codes = self._selected_adset_bundle_codes()
        if len(campaign_codes) != 1 or len(adset_codes) != 1:
            return "Chưa chọn đủ chiến dịch và nhóm quảng cáo"
        return self._planner_flow_summary(
            {"campaign_code": campaign_codes[0], "adset_code": adset_codes[0]}
        )

    def _show_planner_setup_stage(self):
        if not all(
            hasattr(self, name)
            for name in (
                "planner_campaign_panel",
                "planner_adset_panel",
                "planner_draft_summary_frame",
                "planner_setup_panel",
            )
        ):
            return
        self.planner_campaign_panel.grid_remove()
        self.planner_adset_panel.grid_remove()
        self.planner_structure_frame.grid_rowconfigure(2, weight=0)
        self.planner_structure_frame.grid_rowconfigure(3, weight=1)
        self.planner_draft_summary_var.set(self._current_planner_draft_summary())
        self.planner_draft_summary_frame.grid()
        self.planner_setup_panel.grid()

    def _show_planner_selection_stage(self):
        if not hasattr(self, "planner_campaign_panel"):
            return
        self.planner_draft_summary_frame.grid_remove()
        self.planner_setup_panel.grid_remove()
        self.planner_structure_frame.grid_rowconfigure(2, weight=1)
        self.planner_structure_frame.grid_rowconfigure(3, weight=0)
        self.planner_campaign_panel.grid()
        self.planner_adset_panel.grid()

    def _restore_rendered_adset_selections(self):
        for group in self.planner_adset_listboxes.values():
            bundles = group["bundles"]
            if "listbox" in group:
                listbox = group["listbox"]
                listbox.selection_clear(0, "end")
                for index, bundle in enumerate(bundles):
                    if bundle.get("code") in self.planner_selected_adset_codes:
                        listbox.selection_set(index)
            for bundle, chip, palette in group.get("chips", []):
                selected = bundle.get("code") in self.planner_selected_adset_codes
                try:
                    chip.configure(
                        fg_color=palette["line"] if selected else COLORS["surface_alt"],
                        text_color="#ffffff" if selected else COLORS["text"],
                        border_width=1,
                        border_color=palette["line"] if selected else COLORS["field_border"],
                    )
                except ValueError:
                    pass

    def _current_allowed_adset_codes(self):
        campaign_codes = set(self._selected_campaign_bundle_codes())
        return {
            bundle.get("code")
            for bundle in self.planner_catalog.get("adSetBundles", [])
            if bundle.get("campaignBundleCode") in campaign_codes and bundle.get("code")
        }

    def _selected_adset_bundle_codes(self):
        adset_lookup = {
            item.get("code"): item
            for item in self.planner_catalog.get("adSetBundles", [])
            if item.get("code")
        }
        return [
            code
            for code in self.planner_selected_adset_codes
            if code in self._current_allowed_adset_codes() and code in adset_lookup
        ]


    def _campaign_detail_text(self, bundle):
        if not bundle:
            return "Chọn ít nhất một mẫu chiến dịch để xem cấu hình."
        settings = bundle.get("campaignSettings", {})
        objective = self._campaign_card_title(bundle)
        budget_status = "Bật" if settings.get("budgetStrategyEnabled") else "Tắt"
        sharing_status = "Bật" if settings.get("budgetSharingEnabled") else "Tắt"
        ab_test_status = "Bật" if settings.get("abTestEnabled") else "Tắt"
        lines = [
            f"{objective} · {settings.get('buyingType', 'Chưa cấu hình')} · {settings.get('bidStrategy', 'Chưa cấu hình')}",
            f"Ngân sách {budget_status} · Chia sẻ {sharing_status} · A/B {ab_test_status} · {settings.get('specialAdCategory', 'Không áp dụng')}",
        ]
        guidance = bundle.get("guidance") or []
        if guidance:
            lines.append(f"Gợi ý: {guidance[0]}")
        return "\n".join(lines)

    def _refresh_matrix_summary(self):
        links = self._current_import_links()
        flows = list(self.planner_flows) if hasattr(self, "planner_flows") else []
        campaigns = len({flow.get("campaign_code") for flow in flows if flow.get("campaign_code")})
        adsets = len(flows)
        audience_units = sum(max(1, len(flow.get("audience_codes", []))) for flow in flows)
        total = len(links) * audience_units
        self._refresh_selected_adset_tags()
        if hasattr(self, "planner_link_overview_var"):
            self.planner_link_overview_var.set(
                f"{len(links)} bài · {adsets} cách chạy · {total} mục sẽ tạo"
            )
        missing = []
        if not links:
            missing.append("đường dẫn bài viết")
        if not flows:
            missing.append("cách chạy đã thêm")
        ready = not missing
        if hasattr(self, "planner_readiness_var"):
            if ready:
                self.planner_readiness_var.set("✓ Sẵn sàng")
                self.planner_readiness_label.configure(text_color=COLORS["success"])
            else:
                self.planner_readiness_var.set(f"Thiếu {len(missing)} mục")
                self.planner_readiness_label.configure(text_color=COLORS["muted"])
        if hasattr(self, "planner_primary_button"):
            self.planner_primary_button.configure(state="normal" if ready else "disabled")
        if hasattr(self, "planner_add_flow_button"):
            self.planner_add_flow_button.configure(
                state="normal" if self._current_planner_flow_is_valid() else "disabled"
            )
        if not links and not flows:
            self.planner_matrix_summary_var.set("Chưa có dữ liệu để tạo kế hoạch.")
            self._refresh_link_plan_preview()
            return
        lines = [
            f"{len(links)} bài · {campaigns} chiến dịch",
            f"{adsets} cách chạy",
            f"→ {total} mục sẽ tạo",
        ]
        self.planner_matrix_summary_var.set("\n".join(lines))
        self._refresh_link_plan_preview()

    def _page_base(self, container):
        page = ctk.CTkFrame(container)
        page.grid_columnconfigure(0, weight=1)
        return page

    def _page_dashboard(self, container):
        page = self._page_base(container)
        grid = ctk.CTkFrame(page)
        grid.pack(fill="x")
        for i in range(3):
            grid.grid_columnconfigure(i, weight=1)

        cards = [
            ("1", "Nhập link", "Dán link bài Facebook để tạo dòng nháp Notion."),
            ("2", "Duyệt nội dung", "Quản lý sửa thông tin và đổi trạng thái sang To-do/Ready."),
            ("3", "Xuất CSV", "Tool clone dòng mẫu CSV cũ để Meta dễ import."),
        ]
        for i, (num, title, desc) in enumerate(cards):
            outer, inner = self._card(grid)
            outer.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            ctk.CTkLabel(inner, text=num, font=FONTS["h1"], width=3).pack(anchor="w")
            ctk.CTkLabel(inner, text=title).pack(anchor="w", pady=(12, 2))
            ctk.CTkLabel(inner, text=desc, wraplength=250).pack(anchor="w")

        outer, inner = self._card(page, "Quy trình chuẩn", "Không export bản nháp nếu chưa duyệt, trừ khi bật tùy chọn xuất In progress.")
        outer.pack(fill="x", pady=(18, 0))
        text = (
            "- Link mới tạo trong Notion ở trạng thái In progress.\n"
            "- Khi quản lý duyệt xong, đổi trạng thái sang To-do hoặc Ready.\n"
            "- Sau khi xuất thành công, tool tick Đã xuất và chuyển trạng thái sang Done.\n"
            "- Cấu hình nhóm quảng cáo được lấy nguyên từ file CSV mẫu theo Tên nhóm QC."
        )
        ctk.CTkLabel(inner, text=text, justify="left", font=FONTS["body"]).pack(anchor="w")
        return page


    def _page_import(self, container):
        page = self._page_base(container)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(page, corner_radius=14)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top,
            text="Lập kế hoạch quảng cáo",
            font=FONTS["h1"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(7, 0))
        ctk.CTkLabel(
            top,
            text="Bài viết và thiết lập luôn hiện bên phải để bạn dễ kiểm tra.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 4))

        step_nav = ctk.CTkFrame(top, fg_color="transparent")
        step_nav.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.planner_step_buttons = {}
        step_specs = [
            ("creative", "01", "Nội dung"),
            ("structure", "02", "Tạo cách chạy"),
        ]
        for column, (key, number, title) in enumerate(step_specs):
            step_nav.grid_columnconfigure(column, weight=1)
            button = ctk.CTkButton(
                step_nav,
                text=f"{number}  {title}",
                height=32,
                corner_radius=9,
                fg_color="transparent",
                text_color=COLORS["text"],
                hover_color=COLORS["surface_alt"],
                font=FONTS["body_bold"],
                command=lambda item_key=key: self._planner_show_step(item_key),
            )
            button.grid(row=0, column=column, sticky="ew", padx=4)
            self.planner_step_buttons[key] = button

        ctk.CTkButton(
            top,
            text="Nạp lại mẫu",
            command=self.reload_planner_catalog,
            fg_color="transparent",
            border_width=1,
            text_color=COLORS["text"],
            font=FONTS["small_bold"],
            width=130,
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=14)

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=320)

        workspace = ctk.CTkFrame(body, corner_radius=14)
        workspace.grid(row=0, column=0, sticky="nsew")
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1)
        self.planner_step_frames = {}

        creative = ctk.CTkScrollableFrame(workspace, fg_color="transparent")
        creative.grid_columnconfigure(0, weight=1)
        self.planner_step_frames["creative"] = creative
        ctk.CTkLabel(creative, text="Nội dung quảng cáo", font=FONTS["h1"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 2)
        )
        ctk.CTkLabel(
            creative,
            text="Mỗi dòng là một đường dẫn bài viết Facebook. Dòng trống sẽ được bỏ qua.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))
        creative_form = ctk.CTkFrame(creative)
        creative_form.grid(row=2, column=0, sticky="ew", padx=18)
        creative_form.grid_columnconfigure(0, weight=1)
        creative_form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(creative_form, text="Danh sách bài viết Facebook", font=FONTS["body_bold"]).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 5)
        )
        ctk.CTkLabel(creative_form, text="Tên nháp (khi chỉ có 1 link)", font=FONTS["body_bold"]).grid(
            row=0, column=1, sticky="w", padx=12, pady=(12, 5)
        )
        self.import_links_text = ctk.CTkTextbox(
            creative_form,
            height=180,
            wrap="word",
            font=FONTS["body"],
            fg_color=COLORS["field"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["field_border"],
        )
        self.import_links_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.import_links_text.bind("<KeyRelease>", lambda _event: self._refresh_matrix_summary())
        creative_side = ctk.CTkFrame(creative_form, fg_color="transparent")
        creative_side.grid(row=1, column=1, sticky="new", padx=12, pady=(0, 12))
        creative_side.grid_columnconfigure(0, weight=1)
        self.import_name_var = tk.StringVar()
        self.import_name_entry = ctk.CTkEntry(
            creative_side,
            textvariable=self.import_name_var,
            font=FONTS["body"],
            fg_color=COLORS["field"],
            text_color=COLORS["text"],
            border_color=COLORS["field_border"],
        )
        self.import_name_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(creative_side, text="Kiểu nội dung", font=FONTS["body_bold"], anchor="w").grid(
            row=1, column=0, sticky="w", pady=(16, 5)
        )
        self.planner_creative_mode_combo = ctk.CTkComboBox(
            creative_side,
            variable=self.planner_creative_mode_var,
            state="readonly",
            values=list(self._planner_creative_mode_options().keys()),
        )
        self.planner_creative_mode_combo.grid(row=2, column=0, sticky="ew")
        ctk.CTkButton(
            creative_side,
            text="Tạo bản nháp không kèm thiết lập",
            command=self.import_links_to_notion,
            fg_color="transparent",
            border_width=1,
            text_color=COLORS["text"],
        ).grid(row=3, column=0, sticky="ew", pady=(16, 0))
        ctk.CTkLabel(
            creative,
            text="Sau khi nhập, thiết lập của từng bài luôn hiện trong cột “Bài viết & thiết lập”.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=18, pady=12)

        structure = ctk.CTkFrame(workspace, fg_color="transparent")
        self.planner_structure_frame = structure
        structure.grid_rowconfigure(2, weight=1)
        structure.grid_columnconfigure(1, weight=1)
        self.planner_step_frames["structure"] = structure
        ctk.CTkLabel(
            structure,
            text="Tạo một cách chạy quảng cáo",
            font=FONTS["h1"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(
            structure,
            text="Chọn lần lượt chiến dịch, nhóm quảng cáo và thiết lập; sau đó bấm Thêm cách chạy.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 12))

        campaign_panel = ctk.CTkFrame(structure, width=225, corner_radius=10)
        self.planner_campaign_panel = campaign_panel
        campaign_panel.grid(row=2, column=0, sticky="ns", padx=(18, 8), pady=(0, 12))
        campaign_panel.grid_propagate(False)
        campaign_panel.grid_rowconfigure(2, weight=1)
        campaign_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            campaign_panel,
            text="1. CHỌN CHIẾN DỊCH",
            font=FONTS["small_bold"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=(12, 8))
        self.planner_campaign_cards_host = ctk.CTkScrollableFrame(
            campaign_panel,
            fg_color="transparent",
            width=205,
        )
        self.planner_campaign_cards_host.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 6))
        self.planner_campaign_cards_host.grid_columnconfigure(0, weight=1)
        adset_panel = ctk.CTkFrame(structure, corner_radius=10)
        self.planner_adset_panel = adset_panel
        adset_panel.grid(row=2, column=1, sticky="nsew", padx=(0, 12), pady=(0, 12))
        adset_panel.grid_rowconfigure(2, weight=1)
        adset_panel.grid_columnconfigure(0, weight=1)
        self.planner_bundle_heading_label = ctk.CTkLabel(
            adset_panel, text="2. CHỌN NHÓM QUẢNG CÁO", font=FONTS["small_bold"], anchor="w"
        )
        self.planner_bundle_heading_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        self.planner_selected_tags_host = ctk.CTkFrame(adset_panel, fg_color="transparent")
        self.planner_selected_tags_host.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.planner_selected_tags_host.grid_columnconfigure(0, weight=1)
        self.planner_adset_groups_host = ctk.CTkScrollableFrame(adset_panel, fg_color="transparent")
        self.planner_adset_groups_host.grid(row=2, column=0, sticky="nsew", padx=(6, 2), pady=(0, 8))
        self.planner_adset_groups_host.grid_columnconfigure(0, weight=1)

        self.planner_draft_summary_frame = ctk.CTkFrame(structure, corner_radius=10)
        self.planner_draft_summary_frame.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 8)
        )
        self.planner_draft_summary_frame.grid_columnconfigure(0, weight=1)
        self.planner_draft_summary_var = tk.StringVar()
        ctk.CTkLabel(
            self.planner_draft_summary_frame,
            textvariable=self.planner_draft_summary_var,
            font=FONTS["body_bold"],
            anchor="w",
            justify="left",
            wraplength=345,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        ctk.CTkButton(
            self.planner_draft_summary_frame,
            text="Đổi lựa chọn",
            command=self._show_planner_selection_stage,
            width=110,
            height=30,
            fg_color="transparent",
            border_width=1,
            text_color=COLORS["text"],
        ).grid(row=0, column=1, padx=10, pady=6)

        setup = ctk.CTkFrame(structure, corner_radius=10)
        self.planner_setup_panel = setup
        setup.grid(row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 12))
        for column in range(2):
            setup.grid_columnconfigure(column, weight=1)
        ctk.CTkLabel(
            setup,
            text="3. HOÀN THIỆN VÀ THÊM CÁCH CHẠY",
            font=FONTS["small_bold"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 4))

        def planner_choice(parent, title, row, column, variable):
            card = ctk.CTkFrame(parent)
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=2)
            card.grid_columnconfigure(0, weight=1)
            heading = ctk.CTkLabel(card, text=title, font=FONTS["body_bold"], anchor="w")
            heading.grid(
                row=0, column=0, sticky="w", padx=8, pady=(6, 3)
            )
            choice = ctk.CTkComboBox(
                card,
                variable=variable,
                values=["Chưa có lựa chọn"],
                state="readonly",
                font=FONTS["body"],
                command=lambda _value: self._refresh_matrix_summary(),
            )
            choice.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 7))
            return card, heading, choice

        audience_card, self.planner_audience_heading_label, self.planner_audience_combo = planner_choice(
            setup, "Nhóm người xem", 1, 0, self.planner_audience_choice_var
        )
        _, _, self.planner_dataset_combo = planner_choice(
            setup, "Nguồn dữ liệu", 1, 1, self.planner_dataset_choice_var
        )
        budget_card, _, self.planner_budget_combo = planner_choice(
            setup, "Ngân sách", 2, 0, self.planner_budget_choice_var
        )
        budget_custom = ctk.CTkFrame(budget_card, fg_color="transparent")
        budget_custom.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))
        budget_custom.grid_columnconfigure(1, weight=1)
        self.planner_budget_type_combo = ctk.CTkComboBox(
            budget_custom,
            variable=self.planner_budget_type_var,
            state="readonly",
            values=["Ngân sách/ngày", "Ngân sách trọn đời"],
            width=86,
        )
        self.planner_budget_type_combo.grid(row=0, column=0, padx=(0, 4))
        self.planner_budget_type_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_matrix_summary())
        self.planner_budget_amount_entry = ctk.CTkEntry(
            budget_custom, textvariable=self.planner_budget_amount_var, placeholder_text="Số tiền", width=60
        )
        self.planner_budget_amount_entry.grid(row=0, column=1, sticky="ew")
        self.planner_budget_amount_entry.bind("<KeyRelease>", lambda _event: self._refresh_matrix_summary())
        _, _, self.planner_placement_combo = planner_choice(
            setup, "Vị trí hiển thị", 2, 1, self.planner_placement_choice_var
        )
        self.planner_add_flow_button = ctk.CTkButton(
            setup,
            text="+ Thêm cách chạy vào kế hoạch",
            command=self.add_current_planner_flow,
            font=FONTS["body_bold"],
            height=36,
        )
        self.planner_add_flow_button.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 8))
        self.planner_add_flow_button.configure(state="disabled")
        self.planner_draft_summary_frame.grid_remove()
        self.planner_setup_panel.grid_remove()

        summary = ctk.CTkFrame(body, width=320, corner_radius=14)
        summary.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        summary.grid_propagate(False)
        summary_header = ctk.CTkFrame(summary, fg_color="transparent")
        summary_header.pack(fill="x", padx=12, pady=(12, 6))
        summary_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(summary_header, text="Bài viết & thiết lập", font=FONTS["h1"], anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self.planner_link_overview_var = tk.StringVar(value="0 bài · 0 cách chạy · 0 mục")
        ctk.CTkLabel(
            summary_header,
            textvariable=self.planner_link_overview_var,
            font=FONTS["small_bold"],
            text_color=COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.planner_readiness_var = tk.StringVar(value="Chưa đủ thông tin")
        self.planner_readiness_label = ctk.CTkLabel(
            summary_header,
            textvariable=self.planner_readiness_var,
            anchor="e",
            font=FONTS["small_bold"],
            text_color=COLORS["muted"],
        )
        self.planner_readiness_label.grid(row=0, column=1, rowspan=2, sticky="e", padx=(4, 0))
        flow_box = ctk.CTkFrame(
            summary,
            fg_color=COLORS["surface_alt"],
            height=126,
            corner_radius=8,
        )
        flow_box.pack(fill="x", padx=6, pady=(0, 6))
        flow_box.pack_propagate(False)
        ctk.CTkLabel(
            flow_box,
            text="Cách chạy đã thêm",
            font=FONTS["small_bold"],
            anchor="w",
        ).pack(fill="x", padx=8, pady=(6, 3))
        self.planner_flows_host = ctk.CTkFrame(flow_box, fg_color="transparent")
        self.planner_flows_host.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.planner_flows_host.grid_columnconfigure(0, weight=1)
        self.link_plan_preview_host = ctk.CTkScrollableFrame(
            summary,
            fg_color="transparent",
        )
        self.link_plan_preview_host.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.link_plan_preview_host.grid_columnconfigure(0, weight=1)

        actions = ctk.CTkFrame(page, corner_radius=14)
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        actions.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            actions,
            text="Dữ liệu chỉ được gửi khi bạn bấm Tạo bản nháp.",
            font=FONTS["small"],
            text_color=COLORS["muted"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkButton(actions, text="Xem trước", command=self.preview_planner_selection, width=120).grid(
            row=0, column=1, padx=6, pady=8
        )
        self.planner_primary_button = ctk.CTkButton(
            actions,
            text="Tạo bản nháp trên Notion",
            command=self.import_links_with_planner,
            width=190,
            font=FONTS["body_bold"],
        )
        self.planner_primary_button.grid(row=0, column=2, padx=(6, 12), pady=8)

        self.reload_planner_catalog()
        self._planner_show_step("creative")
        self._refresh_planner_flows_panel()
        self._refresh_matrix_summary()
        return page

    def _planner_show_step(self, key):
        if not hasattr(self, "planner_step_frames") or key not in self.planner_step_frames:
            return
        self.planner_active_step = key
        for step_key, frame in self.planner_step_frames.items():
            if step_key == key:
                frame.grid(row=0, column=0, sticky="nsew")
                frame.tkraise()
            else:
                frame.grid_remove()
        for step_key, button in self.planner_step_buttons.items():
            selected = step_key == key
            button.configure(
                fg_color=COLORS["primary"] if selected else "transparent",
                text_color="#ffffff" if selected else COLORS["text"],
            )

    def _page_audiences(self, container):
        page = self._page_base(container)
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=4)
        page.grid_rowconfigure(0, weight=1)

        list_outer, list_inner = self._card(page, "Thư viện tệp đối tượng")
        list_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        list_inner.grid_columnconfigure(0, weight=1)
        list_inner.grid_rowconfigure(0, weight=1)

        self.audience_library_listbox = tk.Listbox(
            list_inner,
            selectmode="browse",
            exportselection=False,
            relief="flat",
            bd=0,
            bg=COLORS["field"],
            fg=COLORS["text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            font=FONTS["body"],
            activestyle="none",
            highlightthickness=1,
            highlightbackground=COLORS["field_border"],
        )
        self.audience_library_listbox.grid(row=0, column=0, sticky="nsew")
        self.audience_library_listbox.bind("<<ListboxSelect>>", lambda _event: self._load_selected_audience_preset())
        list_scrollbar = ctk.CTkScrollbar(list_inner, orientation="vertical", command=self.audience_library_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.audience_library_listbox.configure(yscrollcommand=list_scrollbar.set)

        form_outer, form_inner = self._card(page, "Tạo tệp đối tượng")
        form_outer.grid(row=0, column=1, sticky="nsew")
        form_inner.grid_columnconfigure(1, weight=1)

        self.audience_form_vars = {
            "code": tk.StringVar(),
            "name": tk.StringVar(),
            "location": tk.StringVar(value="Phan Thiet, Bình Thuận Province, Vietnam +25km"),
            "age_min": tk.StringVar(value="18"),
            "age_max": tk.StringVar(value="45"),
            "gender": tk.StringVar(value="Nữ"),
            "language": tk.StringVar(value="Tiếng Việt"),
            "custom_audiences": tk.StringVar(),
            "excluded_custom_audiences": tk.StringVar(),
            "device": tk.StringVar(value="Di động"),
            "publisher_platforms": tk.StringVar(value="Facebook + Messenger"),
            "facebook_positions": tk.StringVar(value="feed, story, search, facebook_reels"),
            "messenger_positions": tk.StringVar(value="story"),
            "advantage_audience": tk.StringVar(value="Tắt"),
            "summary": tk.StringVar(),
        }

        fields = [
            ("Tên tệp", "name"),
            ("Mã tệp", "code"),
            ("Vị trí", "location"),
            ("Tuổi min", "age_min"),
            ("Tuổi max", "age_max"),
            ("Giới tính", "gender"),
            ("Ngôn ngữ", "language"),
            ("Đối tượng tùy chỉnh", "custom_audiences"),
            ("Loại trừ đối tượng", "excluded_custom_audiences"),
            ("Thiết bị", "device"),
            ("Nền tảng", "publisher_platforms"),
            ("Vị trí Facebook", "facebook_positions"),
            ("Vị trí Messenger", "messenger_positions"),
            ("Mở rộng tệp", "advantage_audience"),
            ("Ghi chú", "summary"),
        ]
        for row, (label, key) in enumerate(fields):
            ctk.CTkLabel(form_inner, text=label).grid(row=row, column=0, sticky="w", pady=6)
            ctk.CTkEntry(form_inner, textvariable=self.audience_form_vars[key]).grid(row=row, column=1, sticky="ew", pady=6, padx=(12, 0))

        actions = ctk.CTkFrame(form_inner)
        actions.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ctk.CTkButton(actions, text="Tạo mới", command=self.clear_audience_form).pack(side="left")
        ctk.CTkButton(actions, text="Lưu tệp đối tượng", command=self.save_audience_preset).pack(side="left", padx=(8, 0))
        ctk.CTkButton(actions, text="Nạp lại", command=self.reload_audience_library).pack(side="left", padx=(8, 0))

        self.reload_audience_library()
        return page

    def _page_export(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Xuất CSV Facebook", "CSV xuất ra giữ format UTF-16 + tab và clone cấu hình từ file mẫu cũ.")
        outer.pack(fill="x")

        checks = ctk.CTkFrame(inner)
        checks.pack(fill="x")
        ctk.CTkCheckBox(checks, text="Đánh dấu Đã xuất sau khi xuất", variable=self.vars["MARK_EXPORTED"]).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(checks, text="Xuất cả bài đã xuất", variable=self.vars["INCLUDE_EXPORTED"]).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(checks, text="Xuất cả bản nháp In progress", variable=self.vars["EXPORT_IN_PROGRESS"]).pack(side="left")

        buttons = ctk.CTkFrame(inner)
        buttons.pack(fill="x", pady=(18, 0))
        ctk.CTkButton(buttons, text="Xuất CSV ngay", command=self.export_now).pack(side="left")
        ctk.CTkButton(buttons, text="Mở thư mục exports", command=self.open_exports).pack(side="left", padx=8)

        scan_outer, scan_inner = self._card(page, "Tự quét Notion", "Bật khi muốn tool tự kiểm tra bài Ready theo chu kỳ.")
        scan_outer.pack(fill="x", pady=(18, 0))
        row = ctk.CTkFrame(scan_inner)
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Chu kỳ quét (giây)").pack(side="left")
        ctk.CTkEntry(row, textvariable=self.vars["SCAN_INTERVAL_SECONDS"], width=12).pack(side="left", padx=10)
        self.scan_button = ctk.CTkButton(row, text="Bật tự quét", command=self.toggle_auto_scan)
        self.scan_button.pack(side="left")
        ctk.CTkCheckBox(
            scan_inner,
            text="Telegram xác nhận trước khi tự xuất",
            variable=self.vars["TELEGRAM_CONFIRM_EXPORT"],
        ).pack(anchor="w", pady=(14, 0))
        return page

    def _page_config(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Cấu hình kết nối", "Thông tin được lưu trong file .env cạnh file exe.")
        outer.pack(fill="both", expand=True)
        inner.grid_columnconfigure(1, weight=1)

        fields = [
            ("Notion token", "NOTION_TOKEN", "*", False),
            ("Notion data source ID", "NOTION_DATA_SOURCE_ID", None, False),
            ("File CSV mẫu Facebook", "SAMPLE_CSV", None, True),
            ("Dòng mẫu mặc định", "TEMPLATE_ROW_INDEX", None, False),
            ("Telegram bot token", "TELEGRAM_BOT_TOKEN", "*", False),
            ("Telegram chat ID", "TELEGRAM_CHAT_ID", None, False),
            ("Trạng thái cần xuất", "READY_STATUS_NAMES", None, False),
            ("Trạng thái sau export", "EXPORTED_STATUS_NAMES", None, False),
            ("Supabase URL", "SUPABASE_URL", None, False),
            ("Supabase publishable key", "SUPABASE_PUBLISHABLE_KEY", None, False),
            ("Supabase secret key", "SUPABASE_SECRET_KEY", "*", False),
            ("Ads sync token", "ADS_SYNC_TOKEN", "*", False),
        ]
        for row, (label, key, show, browse) in enumerate(fields):
            self._field(inner, row, label, self.vars[key], show=show, browse=browse)

        actions = ctk.CTkFrame(inner)
        actions.grid(row=len(fields), column=0, columnspan=3, sticky="ew", pady=(18, 0))
        ctk.CTkButton(actions, text="Lưu cấu hình", command=self.save_config).pack(side="left")
        ctk.CTkButton(actions, text="Test Telegram", command=self.test_telegram).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="Mở thư mục tool", command=lambda: os.startfile(APP_DIR)).pack(side="left")
        return page

    def _page_notion(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Notion mẫu", "Chỉ cần dùng nếu muốn tạo database mới từ một page cha trong Notion.")
        outer.pack(fill="both", expand=True)
        inner.grid_columnconfigure(1, weight=1)
        self._field(inner, 0, "Parent page ID", self.vars["PARENT_PAGE_ID"])
        ctk.CTkButton(inner, text="Tạo database Notion mẫu", command=self.create_template).grid(row=1, column=0, sticky="w", pady=(14, 0))
        ctk.CTkButton(inner, text="Lưu cấu hình", command=self.save_config).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(14, 0))
        guide = (
            "1. Tạo một page trống trong Notion.\n"
            "2. Share page đó cho integration đang giữ token.\n"
            "3. Copy Page ID và dán vào ô trên.\n"
            "4. Bấm tạo database mẫu, sau đó copy Data Source ID vào cấu hình."
        )
        ctk.CTkLabel(inner, text=guide, justify="left", font=FONTS["body"]).grid(row=2, column=0, columnspan=3, sticky="w", pady=(18, 0))
        return page

    def _page_logs(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Nhật ký hoạt động", "Theo dõi thao tác nhập link, export CSV và tự quét Notion.")
        outer.pack(fill="both", expand=True)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(0, weight=1)
        self.log_text = ctk.CTkTextbox(inner, wrap="word", state="disabled", font=FONTS["body"])
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ctk.CTkScrollbar(inner, orientation="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        return page

    def _field(self, parent, row, label, var, show=None, browse=False):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", pady=7)
        entry = ctk.CTkEntry(parent, textvariable=var, show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=7, padx=(12, 8))
        if browse:
            ctk.CTkButton(parent, text="Chọn file", command=self._choose_sample_csv).grid(row=row, column=2, pady=7)
        return entry

    def show_page(self, key):
        for nav_key, btn in self.nav_buttons.items():
            if nav_key == key:
                btn.configure(fg_color=COLORS["sidebar_active"], text_color="#ffffff")
            else:
                btn.configure(fg_color=COLORS["sidebar"], text_color="#dce7f8")
        self.pages[key].tkraise()


    def _choose_sample_csv(self):
        path = filedialog.askopenfilename(
            title="Chọn file CSV mẫu Facebook",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.vars["SAMPLE_CSV"].set(path)

    def _load_env_to_vars(self):
        tool.load_env(ENV_PATH)
        if "SUPABASE_SERVICE_ROLE_KEY" in os.environ and "SUPABASE_SECRET_KEY" not in os.environ:
            os.environ["SUPABASE_SECRET_KEY"] = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        for key, var in self.vars.items():
            if key in os.environ:
                if isinstance(var, tk.BooleanVar):
                    var.set(os.environ[key].lower() in ("1", "true", "yes"))
                else:
                    var.set(os.environ[key])

    def _apply_vars_to_env(self):
        for key, var in self.vars.items():
            if isinstance(var, tk.BooleanVar):
                os.environ[key] = "true" if var.get() else "false"
            else:
                os.environ[key] = var.get().strip()

    def save_config(self):
        self._apply_vars_to_env()
        lines = []
        for key, var in self.vars.items():
            value = "true" if isinstance(var, tk.BooleanVar) and var.get() else "false" if isinstance(var, tk.BooleanVar) else var.get().strip()
            lines.append(f"{key}={value}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.log("Đã lưu cấu hình vào .env")
        messagebox.showinfo(APP_TITLE, "Đã lưu cấu hình.")

    def create_template(self):
        parent_id = self.vars["PARENT_PAGE_ID"].get().strip()
        if not parent_id:
            messagebox.showwarning(APP_TITLE, "Cần nhập Parent page ID trước.")
            return
        self.save_config()
        self._run_background(self._create_template_worker, parent_id)

    def _create_template_worker(self, parent_id):
        self.log("Đang tạo database Notion mẫu...")
        result = tool.create_notion_template(parent_id)
        database_id = result.get("id", "")
        url = result.get("url", "")
        self.after(0, lambda: self.vars["NOTION_DATABASE_ID"].set(database_id))
        self.after(0, lambda: self.vars["NOTION_DATA_SOURCE_ID"].set(database_id))
        self.after(0, self.save_config)
        self.log(f"Đã tạo Notion mẫu: {url}")
        self._message_info("Đã tạo Notion mẫu", f"Link database:\n{url}")

    def import_links_to_notion(self):
        self.save_config()
        links = [line.strip() for line in self.import_links_text.get("1.0", "end").splitlines() if line.strip()]
        if not links:
            messagebox.showwarning(APP_TITLE, "Cần dán ít nhất 1 link Facebook.")
            return
        self._run_background(self._import_links_worker, links, self.import_name_var.get().strip())

    def _import_links_worker(self, links, ad_name):
        data_source_id = os.environ.get("NOTION_DATA_SOURCE_ID") or os.environ.get("NOTION_DATABASE_ID") or tool.DEFAULT_DATA_SOURCE_ID
        created = 0
        for index, link in enumerate(links, start=1):
            name = ad_name if len(links) == 1 else ""
            self.log(f"Đang tạo nháp Notion từ link {index}/{len(links)}...")
            tool.create_notion_ad_draft(data_source_id, link, name or None)
            created += 1
        self.log(f"Đã tạo {created} dòng nháp trong Notion.")
        self._message_info(APP_TITLE, f"Đã tạo {created} dòng nháp trong Notion.")

    def _audience_code_from_name(self, name):
        raw = "".join(ch if ch.isalnum() else "_" for ch in name.upper())
        parts = [part for part in raw.split("_") if part]
        return "AUD_" + "_".join(parts[:6]) if parts else "AUD_CUSTOM"

    def reload_audience_library(self):
        if not hasattr(self, "audience_library_listbox"):
            return
        self.planner_catalog = tool.load_planner_bundles()
        self.audience_library_presets = self.planner_catalog.get("audiencePresets", [])
        self.audience_library_listbox.delete(0, "end")
        for preset in self.audience_library_presets:
            self.audience_library_listbox.insert("end", preset.get("name") or preset.get("code"))

    def clear_audience_form(self):
        if not hasattr(self, "audience_form_vars"):
            return
        defaults = {
            "code": "",
            "name": "",
            "location": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
            "age_min": "18",
            "age_max": "45",
            "gender": "Nữ",
            "language": "Tiếng Việt",
            "custom_audiences": "",
            "excluded_custom_audiences": "",
            "device": "Di động",
            "publisher_platforms": "Facebook + Messenger",
            "facebook_positions": "feed, story, search, facebook_reels",
            "messenger_positions": "story",
            "advantage_audience": "Tắt",
            "summary": "",
        }
        for key, value in defaults.items():
            self.audience_form_vars[key].set(value)

    def _load_selected_audience_preset(self):
        selection = self.audience_library_listbox.curselection()
        if not selection:
            return
        preset = self.audience_library_presets[selection[0]]
        values = preset.get("notionValues", {})
        mapping = {
            "code": preset.get("code", ""),
            "name": preset.get("name", ""),
            "location": values.get("Vị trí địa lý", ""),
            "age_min": str(values.get("Tuổi min", "")),
            "age_max": str(values.get("Tuổi max", "")),
            "gender": values.get("Giới tính", ""),
            "language": values.get("Ngôn ngữ", ""),
            "custom_audiences": values.get("Đối tượng tuỳ chỉnh", ""),
            "excluded_custom_audiences": values.get("Loại trừ đối tượng tuỳ chỉnh", ""),
            "device": values.get("Thiết bị", ""),
            "publisher_platforms": values.get("Nền tảng quảng cáo", ""),
            "facebook_positions": values.get("Vị trí Facebook", ""),
            "messenger_positions": values.get("Vị trí Messenger", ""),
            "advantage_audience": values.get("Mở rộng tệp", ""),
            "summary": preset.get("summary", ""),
        }
        for key, value in mapping.items():
            self.audience_form_vars[key].set(value)

    def save_audience_preset(self):
        name = self.audience_form_vars["name"].get().strip()
        if not name:
            messagebox.showwarning(APP_TITLE, "Cần nhập tên tệp đối tượng.")
            return
        code = self.audience_form_vars["code"].get().strip() or self._audience_code_from_name(name)
        catalog = tool.load_planner_bundles()
        presets = catalog.setdefault("audiencePresets", [])
        notion_values = {
            "Mẫu đối tượng": name,
            "Đối tượng tuỳ chỉnh": self.audience_form_vars["custom_audiences"].get().strip(),
            "Loại trừ đối tượng tuỳ chỉnh": self.audience_form_vars["excluded_custom_audiences"].get().strip(),
            "Vị trí địa lý": self.audience_form_vars["location"].get().strip(),
            "Tuổi min": int(self.audience_form_vars["age_min"].get() or 18),
            "Tuổi max": int(self.audience_form_vars["age_max"].get() or 65),
            "Giới tính": self.audience_form_vars["gender"].get().strip(),
            "Ngôn ngữ": self.audience_form_vars["language"].get().strip(),
            "Thiết bị": self.audience_form_vars["device"].get().strip(),
            "Nền tảng quảng cáo": self.audience_form_vars["publisher_platforms"].get().strip(),
            "Vị trí Facebook": self.audience_form_vars["facebook_positions"].get().strip(),
            "Vị trí Messenger": self.audience_form_vars["messenger_positions"].get().strip(),
            "Mở rộng tệp": self.audience_form_vars["advantage_audience"].get().strip(),
        }
        preset = {
            "code": code,
            "name": name,
            "summary": self.audience_form_vars["summary"].get().strip(),
            "notionValues": notion_values,
        }
        replaced = False
        for index, existing in enumerate(presets):
            if existing.get("code") == code:
                presets[index] = preset
                replaced = True
                break
        if not replaced:
            presets.append(preset)
        for campaign in catalog.get("campaignBundles", []):
            allowed = campaign.setdefault("allowedAudiencePresetCodes", [])
            if code not in allowed:
                allowed.append(code)
        tool.save_planner_bundles(catalog)
        self.log(f"Đã lưu tệp đối tượng: {code} - {name}")
        self.reload_audience_library()
        self.reload_planner_catalog()
        messagebox.showinfo(APP_TITLE, "Đã lưu tệp đối tượng và cập nhật planner.")
 
    def reload_planner_catalog(self):
        self.planner_catalog = tool.load_planner_bundles()
        self.planner_campaign_bundles = self.planner_catalog.get("campaignBundles", [])
        self.planner_campaign_vars = {}
        self.planner_campaign_cards = {}
        self.planner_selected_adset_codes = set()
        self.planner_focus_campaign_code = None
        for child in self.planner_campaign_cards_host.winfo_children():
            child.destroy()

        for index, item in enumerate(self.planner_campaign_bundles):
            code = item.get("code")
            var = tk.BooleanVar(value=False)
            self.planner_campaign_vars[code] = var
            palette = self._campaign_palette(code)

            frame = ctk.CTkFrame(self.planner_campaign_cards_host, cursor="hand2", height=90)
            frame.grid_propagate(False)
            frame.pack_propagate(False)
            frame.grid(
                row=index,
                column=0,
                sticky="ew",
                padx=(0, 4),
                pady=(0, 8),
            )
            body = ctk.CTkFrame(frame, cursor="hand2")
            body.pack(fill="both", expand=True, padx=1, pady=1)
            body.grid_columnconfigure(1, weight=1)

            bar = ctk.CTkFrame(body, width=3)
            bar.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
            dot = ctk.CTkLabel(body, text="●", font=FONTS["small"], cursor="hand2")
            dot.grid(row=0, column=2, sticky="ne")
            title = ctk.CTkLabel(
                body,
                text=self._campaign_card_title(item),
                                                font=FONTS["body_bold"],
                anchor="w",
                justify="left",
                cursor="hand2",
            )
            title.grid(row=0, column=1, sticky="w")
            subtitle = ctk.CTkLabel(
                body,
                text=self._campaign_card_subtitle(item),
                                                font=FONTS["small"],
                anchor="w",
                justify="left",
                wraplength=195,
                cursor="hand2",
            )
            subtitle.grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 0))

            for widget in (frame, body, bar, dot, title, subtitle):
                widget.bind("<Button-1>", lambda _event, bundle_code=code: self._toggle_campaign_bundle(bundle_code))

            self.planner_campaign_cards[code] = {
                "frame": frame,
                "body": body,
                "bar": bar,
                "dot": dot,
                "title": title,
                "subtitle": subtitle,
            }
            self._render_campaign_card_state(code)

        self._refresh_planner_adset_list()

    def _selected_campaign_bundle_codes(self):
        return [
            item.get("code")
            for item in self.planner_campaign_bundles
            if self.planner_campaign_vars.get(item.get("code")) and self.planner_campaign_vars[item.get("code")].get()
        ]

    def _selected_campaign_bundles(self):
        selected_codes = set(self._selected_campaign_bundle_codes())
        return [item for item in self.planner_campaign_bundles if item.get("code") in selected_codes]

    def _refresh_planner_adset_list(self):
        campaign_bundles = self._selected_campaign_bundles()
        for child in self.planner_adset_groups_host.winfo_children():
            child.destroy()
        self.planner_adset_listboxes = {}
        self.planner_audience_choice_var.set("Theo thiết lập nhóm quảng cáo")
        self.planner_dataset_choice_var.set("Chưa có lựa chọn")
        self.planner_budget_choice_var.set("Chưa có lựa chọn")
        self.planner_placement_choice_var.set("Chưa có lựa chọn")
        self.planner_adset_bundles = []
        self.planner_audience_presets = []
        self.planner_dataset_presets = []
        self.planner_budget_presets = []
        self.planner_placement_presets = []
        if not campaign_bundles:
            self.planner_campaign_detail_var.set("Chọn ít nhất một mẫu chiến dịch để xem cấu hình.")
            self.planner_summary_var.set("Chưa có mẫu chiến dịch được chọn.")
            self.planner_audience_summary_var.set("Chưa có tệp đối tượng khả dụng.")
            if hasattr(self, "planner_bundle_heading_label"):
                self.planner_bundle_heading_label.configure(text="Bundle nhóm quảng cáo")
            if hasattr(self, "planner_audience_heading_label"):
                self.planner_audience_heading_label.configure(text="Tệp đối tượng")
            self.planner_selected_adset_codes.clear()
            self._refresh_selected_adset_tags()
            self._refresh_matrix_summary()
            return
        selected_campaign_codes = {bundle.get("code") for bundle in campaign_bundles}
        if self.planner_focus_campaign_code not in selected_campaign_codes:
            self.planner_focus_campaign_code = campaign_bundles[0].get("code")
        self._render_all_campaign_card_states()
        self.planner_campaign_detail_var.set(
            "\n\n".join(self._campaign_detail_text(bundle) for bundle in campaign_bundles[:2])
            + ("\n\n..." if len(campaign_bundles) > 2 else "")
        )
        allowed = {
            code
            for bundle in campaign_bundles
            for code in bundle.get("allowedAdSetBundleCodes", [])
        }
        self.planner_adset_bundles = [
            item for item in self.planner_catalog.get("adSetBundles", []) if item.get("code") in allowed
        ]
        adsets_by_campaign = {}
        for item in self.planner_adset_bundles:
            adsets_by_campaign.setdefault(item.get("campaignBundleCode"), []).append(item)

        visible_campaign_bundles = [
            bundle for bundle in campaign_bundles if bundle.get("code") == self.planner_focus_campaign_code
        ] or campaign_bundles[:1]
        self.planner_selected_adset_codes.intersection_update(allowed)
        self._refresh_selected_adset_tags()

        for row, campaign in enumerate(visible_campaign_bundles):
            campaign_code = campaign.get("code")
            campaign_adsets = adsets_by_campaign.get(campaign_code, [])
            palette = self._campaign_palette(campaign_code)

            group = ctk.CTkFrame(self.planner_adset_groups_host)
            group.grid(row=row, column=0, sticky="ew", pady=(0, 6))
            group.grid_columnconfigure(0, weight=1)

            body = ctk.CTkFrame(group)
            body.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
            body.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                body,
                text=self._campaign_card_title(campaign),
                                                font=FONTS["body_bold"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                body,
                text=f"{len(campaign_adsets)} nhóm khả dụng",
                                                font=FONTS["small"],
                anchor="e",
            ).grid(row=0, column=1, sticky="e")

            location_groups = {}
            for item in campaign_adsets:
                location = item.get("conversionLocation") or "Chưa phân loại vị trí chuyển đổi"
                interaction = item.get("interactionType") or "Chưa phân loại tương tác"
                location_groups.setdefault(location, {}).setdefault(interaction, []).append(item)

            location_picker = ctk.CTkFrame(body)
            location_picker.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            location_picker.grid_columnconfigure(0, weight=1)
            location_picker.grid_columnconfigure(1, weight=1)

            for location_index, location in enumerate(location_groups):
                location_key = f"{campaign_code}:{location}"
                if location_key not in self.planner_location_vars:
                    self.planner_location_vars[location_key] = tk.BooleanVar(value=False)
                selected_location = self.planner_location_vars[location_key].get()
                location_card = ctk.CTkFrame(
                    location_picker,
                    cursor="hand2",
                    fg_color=palette["line"] if selected_location else COLORS["field_border"],
                    corner_radius=8,
                )
                location_card.grid(
                    row=location_index // 2,
                    column=location_index % 2,
                    sticky="ew",
                    padx=(0, 6),
                    pady=(0, 6),
                )
                location_body = ctk.CTkFrame(
                    location_card,
                    cursor="hand2",
                    fg_color=palette["bg"] if selected_location else COLORS["surface_alt"],
                    corner_radius=7,
                )
                location_body.pack(fill="both", expand=True, padx=1, pady=1)
                location_count = sum(len(items) for items in location_groups[location].values())
                location_label = ctk.CTkLabel(
                    location_body,
                    text=f"{location} · {location_count}",
                    font=FONTS["small_bold"],
                    text_color=palette["text"] if selected_location else COLORS["text"],
                    anchor="w",
                    justify="left",
                    cursor="hand2",
                )
                location_label.pack(anchor="w")
                for widget in (location_card, location_body, location_label):
                    widget.bind("<Button-1>", lambda _event, item_key=location_key: self._toggle_conversion_location(item_key))

            listbox_index = 0
            current_row = 2
            for location, interaction_groups in location_groups.items():
                location_key = f"{campaign_code}:{location}"
                if not self.planner_location_vars.get(location_key) or not self.planner_location_vars[location_key].get():
                    continue
                location_frame = ctk.CTkFrame(body)
                location_frame.grid(row=current_row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
                location_frame.grid_columnconfigure(0, weight=1)
                current_row += 1

                ctk.CTkLabel(
                    location_frame,
                    text=f"Vị trí chuyển đổi: {location}",
                                                            font=FONTS["body_bold"],
                    anchor="w",
                                                        ).grid(row=0, column=0, sticky="ew")

                interaction_row = 1
                simple_location_flow = (
                    len(interaction_groups) == 1
                    and all(
                        bundle.get("simpleFlow")
                        for bundles in interaction_groups.values()
                        for bundle in bundles
                    )
                )
                for interaction, bundles in interaction_groups.items():
                    if simple_location_flow:
                        list_frame = ctk.CTkFrame(location_frame)
                        list_frame.grid(row=interaction_row, column=0, sticky="ew", padx=8, pady=(0, 8))
                        interaction_row += 1
                    else:
                        interaction_frame = ctk.CTkFrame(location_frame)
                        interaction_frame.grid(row=interaction_row, column=0, sticky="ew", padx=8, pady=(0, 8))
                        interaction_frame.grid_columnconfigure(0, weight=1)
                        interaction_row += 1

                        ctk.CTkLabel(
                            interaction_frame,
                            text=f"Loại tương tác: {interaction}",
                                                                                    font=FONTS["body"],
                            anchor="w",
                                                                                ).grid(row=0, column=0, sticky="ew")

                        list_frame = ctk.CTkFrame(interaction_frame)
                        list_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
                    list_frame.grid_columnconfigure(0, weight=1)

                    chip_host = ctk.CTkFrame(list_frame)
                    chip_host.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
                    for col in range(2):
                        chip_host.grid_columnconfigure(col, weight=1)

                    chips = []
                    for item_index, item in enumerate(bundles):
                        selected = item.get("code") in self.planner_selected_adset_codes
                        chip = ctk.CTkLabel(
                            chip_host,
                            text=item.get("performanceGoal") or item.get("name") or item.get("code"),
                            font=FONTS["small_bold"],
                            anchor="w",
                            justify="left",
                            cursor="hand2",
                            corner_radius=7,
                            fg_color=palette["line"] if selected else COLORS["surface_alt"],
                            text_color="#ffffff" if selected else COLORS["text"],
                        )
                        chip.grid(
                            row=item_index // 2,
                            column=item_index % 2,
                            sticky="ew",
                            padx=(0, 5),
                            pady=(0, 5),
                        )
                        chip.bind("<Button-1>", lambda _event, item_code=item.get("code"): self._toggle_adset_chip(item_code))
                        chips.append((item, chip, palette))
                    self.planner_adset_listboxes[f"{campaign_code}:{listbox_index}"] = {
                        "bundles": bundles,
                        "chips": chips,
                    }
                    listbox_index += 1
        self._restore_rendered_adset_selections()

        self.planner_summary_var.set(
            f"Đã nạp {len(campaign_bundles)} campaign. Có {len(self.planner_adset_bundles)} bundle nhóm khả dụng."
        )
        if hasattr(self, "planner_bundle_heading_label"):
            self.planner_bundle_heading_label.configure(
                text=f"2. CHỌN NHÓM QUẢNG CÁO · {len(self.planner_adset_bundles)} lựa chọn"
            )
        allowed_audiences = {
            code
            for bundle in campaign_bundles
            for code in bundle.get("allowedAudiencePresetCodes", [])
        }
        self.planner_audience_presets = [
            item for item in self.planner_catalog.get("audiencePresets", []) if item.get("code") in allowed_audiences
        ]
        audience_values = ["Theo thiết lập nhóm quảng cáo"] + [
            item.get("name") or item.get("code") for item in self.planner_audience_presets
        ]
        self.planner_audience_combo.configure(values=audience_values)
        self.planner_audience_choice_var.set(audience_values[0])
        self.planner_dataset_presets = self.planner_catalog.get("datasetPresets", [])
        dataset_values = [item.get("name") or item.get("code") for item in self.planner_dataset_presets]
        self.planner_dataset_combo.configure(values=dataset_values or ["Chưa có lựa chọn"])
        self.planner_dataset_choice_var.set(dataset_values[0] if dataset_values else "Chưa có lựa chọn")
        self.planner_budget_presets = self.planner_catalog.get("budgetPresets", [])
        budget_values = [item.get("name") or item.get("code") for item in self.planner_budget_presets]
        self.planner_budget_combo.configure(values=budget_values or ["Chưa có lựa chọn"])
        self.planner_budget_choice_var.set(budget_values[0] if budget_values else "Chưa có lựa chọn")
        self.planner_placement_presets = self.planner_catalog.get("placementPresets", [])
        placement_values = [item.get("name") or item.get("code") for item in self.planner_placement_presets]
        self.planner_placement_combo.configure(values=placement_values or ["Chưa có lựa chọn"])
        self.planner_placement_choice_var.set(placement_values[0] if placement_values else "Chưa có lựa chọn")
        self.planner_audience_summary_var.set(
            f"Có {len(self.planner_audience_presets)} tệp đối tượng dùng chung theo campaign đang chọn."
        )
        if hasattr(self, "planner_audience_heading_label"):
            self.planner_audience_heading_label.configure(
                text=f"Nhóm người xem · {len(self.planner_audience_presets)} lựa chọn"
            )
        self._refresh_matrix_summary()

    def _refresh_selected_adset_tags(self):
        if not hasattr(self, "planner_selected_tags_host"):
            return
        for child in self.planner_selected_tags_host.winfo_children():
            child.destroy()
        adset_lookup = {
            item.get("code"): item
            for item in self.planner_catalog.get("adSetBundles", [])
            if item.get("code")
        }
        selected_codes = [
            code
            for code in self.planner_selected_adset_codes
            if code in self._current_allowed_adset_codes()
        ]
        selected_codes.sort(key=lambda code: (
            adset_lookup.get(code, {}).get("campaignBundleCode", ""),
            adset_lookup.get(code, {}).get("conversionLocation", ""),
            adset_lookup.get(code, {}).get("performanceGoal", ""),
        ))
        if not selected_codes:
            ctk.CTkLabel(
                self.planner_selected_tags_host,
                text="Chưa chọn tag nhóm",
                                                font=FONTS["body"],
                anchor="e",
            ).grid(row=0, column=0, sticky="e")
            return

        for index, code in enumerate(selected_codes[:6]):
            bundle = adset_lookup.get(code, {})
            tags = self._adset_flow_tag(bundle)

            # Create a container for the bundle
            bundle_container = ctk.CTkFrame(self.planner_selected_tags_host, fg_color="transparent")
            bundle_container.grid(row=index // 3, column=index % 3, sticky="e", padx=(8, 0), pady=(0, 4))

            for t_idx, t in enumerate(tags):
                chip = ctk.CTkFrame(bundle_container, fg_color=t["color"], corner_radius=12)
                chip.pack(side="left", padx=2)
                ctk.CTkLabel(
                    chip,
                    text=t["text"],
                    font=FONTS["small_bold"],
                    text_color="white",
                ).pack(side="left", padx=(8, 4), pady=2)

                # Only add close button to the last chip
                if t_idx == len(tags) - 1:
                    close = ctk.CTkLabel(chip, text="✕", font=FONTS["small_bold"], text_color="white", cursor="hand2")
                    close.pack(side="left", padx=(0, 8), pady=2)
                    close.bind("<Button-1>", lambda _event, item_code=code: self._remove_selected_adset_code(item_code))
        if len(selected_codes) > 6:
            ctk.CTkLabel(
                self.planner_selected_tags_host,
                text=f"+{len(selected_codes) - 6}",
                                                font=FONTS["small_bold"],
                                            ).grid(row=2, column=2, sticky="e", padx=(4, 0))


    def _refresh_link_plan_preview(self):
        if not hasattr(self, "link_plan_preview_host"):
            return
        for child in self.link_plan_preview_host.winfo_children():
            child.destroy()

        links = self._current_import_links()
        if not links:
            ctk.CTkLabel(
                self.link_plan_preview_host,
                text="Chưa có bài viết.\nNhập đường dẫn ở bước 01 để bắt đầu.",
                justify="left",
                anchor="nw",
                wraplength=300,
                font=FONTS["body"],
                text_color=COLORS["muted"],
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=10)
            return

        flows = list(self.planner_flows)
        first_flow = flows[0] if flows else {}
        campaign_lookup = {
            item.get("code"): item for item in self.planner_catalog.get("campaignBundles", [])
        }
        adset_lookup = {
            item.get("code"): item for item in self.planner_catalog.get("adSetBundles", [])
        }
        campaign = campaign_lookup.get(first_flow.get("campaign_code"), {})
        campaign_text = self._campaign_card_title(campaign) or "Chưa thêm"
        adset = adset_lookup.get(first_flow.get("adset_code"), {})
        adset_text = adset.get("performanceGoal") or adset.get("name") or "Chưa thêm"
        if len(flows) > 1:
            adset_text += f" +{len(flows) - 1}"
        for prefix in ("Tối đa hóa số ", "Tối đa hóa ", "Tăng tối đa "):
            if adset_text.startswith(prefix):
                adset_text = adset_text[len(prefix):]
                break
        adset_text = (
            adset_text
            .replace("lượt xem ThruPlay", "lượt xem video lâu")
            .replace("lượt phát video liên tục trong tối thiểu 2 giây", "lượt xem video từ 2 giây")
        )

        audience_codes = first_flow.get("audience_codes", [])
        audience_lookup = {item.get("code"): item for item in self.planner_audience_presets}
        audience_names = [
            audience_lookup.get(code, {}).get("name") or code
            for code in audience_codes
        ]
        audience_text = ", ".join(audience_names[:2]) or "Theo nhóm"
        if len(audience_names) > 2:
            audience_text += f" (+{len(audience_names) - 2})"

        dataset_code = first_flow.get("dataset_code")
        dataset_lookup = {item.get("code"): item for item in self.planner_dataset_presets}
        dataset_text = dataset_lookup.get(dataset_code, {}).get("name") or dataset_code or "Chưa chọn"
        dataset_text = dataset_text.replace("Không chọn tập dữ liệu", "Không chọn").replace("Tập dữ liệu ", "")
        placement_code = first_flow.get("placement_code")
        placement_lookup = {item.get("code"): item for item in self.planner_placement_presets}
        placement_text = placement_lookup.get(placement_code, {}).get("name") or placement_code or "Chưa chọn"
        budget_code = first_flow.get("budget_code")
        custom_budget = first_flow.get("custom_budget_values", {})
        budget_lookup = {item.get("code"): item for item in self.planner_budget_presets}
        budget_text = (
            self._budget_summary_text(None, custom_budget)
            if custom_budget
            else budget_lookup.get(budget_code, {}).get("name") or budget_code or "Chưa chọn"
        )
        budget_text = budget_text.replace("Ngân sách hằng ngày ", "").replace("Ngân sách trọn đời ", "Trọn đời ")
        placement_text = placement_text.replace("Messenger", "Tin nhắn").replace("mobile", "di động")

        def compact(value, limit=17):
            value = str(value)
            return value if len(value) <= limit else value[: limit - 1] + "…"

        chip_specs = [
            ("Mục tiêu", compact(campaign_text, 13), TAG_COLORS["objective"]),
            ("Tối ưu", compact(adset_text, 13), TAG_COLORS["destination"]),
            ("Người xem", compact(audience_text, 12), TAG_COLORS["audience"]),
            ("Dữ liệu", compact(dataset_text, 12), TAG_COLORS["default"]),
            ("Ngân sách", compact(budget_text, 11), TAG_COLORS["budget"]),
            ("Vị trí", compact(placement_text, 13), TAG_COLORS["placement"]),
        ]
        link_palettes = [
            ("#eef5ff", "#1768d1"),
            ("#edfbf6", "#0f9f6e"),
            ("#fff7e8", "#c77700"),
            ("#f7efff", "#8b5cf6"),
        ]

        for index, link in enumerate(links[:30]):
            card_bg, accent = link_palettes[index % len(link_palettes)]
            card = ctk.CTkFrame(
                self.link_plan_preview_host,
                fg_color=card_bg,
                border_width=1,
                border_color=accent,
                corner_radius=10,
            )
            card.grid(row=index, column=0, sticky="ew", padx=3, pady=(0, 6))
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card,
                text=f"BÀI {index + 1}",
                font=FONTS["small_bold"],
                text_color=accent,
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=(9, 4), pady=(7, 0))
            ctk.CTkLabel(
                card,
                text=link if len(link) <= 46 else link[:43] + "…",
                font=FONTS["small"],
                text_color=COLORS["text"],
                anchor="e",
                justify="left",
            ).grid(row=0, column=1, sticky="e", padx=(4, 9), pady=(7, 0))
            for chip_index, (label, value, color) in enumerate(chip_specs):
                chip = ctk.CTkLabel(
                    card,
                    text=f"{label}\n{value}",
                    font=FONTS["small"],
                    fg_color=color,
                    text_color="#ffffff",
                    corner_radius=7,
                    anchor="center",
                    justify="center",
                    height=34,
                )
                chip.grid(
                    row=1 + chip_index // 2,
                    column=chip_index % 2,
                    sticky="ew",
                    padx=(8 if chip_index % 2 == 0 else 3, 3 if chip_index % 2 == 0 else 8),
                    pady=(5 if chip_index < 2 else 2, 7 if chip_index >= 4 else 2),
                )

        if len(links) > 30:
            ctk.CTkLabel(
                self.link_plan_preview_host,
                text=f"Còn {len(links) - 30} bài khác dùng cùng thiết lập.",
                font=FONTS["small_bold"],
                text_color=COLORS["muted"],
            ).grid(row=30, column=0, sticky="w", padx=8, pady=8)

    def _selected_audience_preset_codes(self):
        code = self._preset_code_for_choice(
            self.planner_audience_presets,
            self.planner_audience_choice_var.get(),
        )
        return [code] if code else []

    def _preset_code_for_choice(self, presets, choice):
        for item in presets:
            label = item.get("name") or item.get("code")
            if label == choice:
                return item.get("code")
        return None

    def _selected_budget_preset_code(self):
        return self._preset_code_for_choice(
            self.planner_budget_presets,
            self.planner_budget_choice_var.get(),
        )

    def _custom_budget_values(self):
        raw = self.planner_budget_amount_var.get().strip() if hasattr(self, "planner_budget_amount_var") else ""
        if not raw:
            return {}
        normalized = raw.replace(",", "").replace("₱", "").replace("PHP", "").strip()
        try:
            amount = float(normalized)
        except ValueError:
            return {}
        if amount <= 0:
            return {}
        if amount.is_integer():
            amount = int(amount)
        budget_type = self.planner_budget_type_var.get() if hasattr(self, "planner_budget_type_var") else "Ngân sách/ngày"
        if budget_type == "Ngân sách trọn đời":
            return {"Loại ngân sách": "Lifetime", "Ngân sách trọn đời": amount, "Ngân sách/ngày": 0}
        return {"Loại ngân sách": "Daily", "Ngân sách/ngày": amount, "Ngân sách trọn đời": 0}

    def _budget_summary_text(self, budget_code=None, custom_budget=None):
        custom_budget = custom_budget or self._custom_budget_values()
        if custom_budget:
            if custom_budget.get("Ngân sách/ngày"):
                return f"ngày {custom_budget.get('Ngân sách/ngày')} PHP"
            if custom_budget.get("Ngân sách trọn đời"):
                return f"trọn đời {custom_budget.get('Ngân sách trọn đời')} PHP"
        return budget_code or "chưa chọn"

    def _selected_dataset_preset_code(self):
        return self._preset_code_for_choice(
            self.planner_dataset_presets,
            self.planner_dataset_choice_var.get(),
        )

    def _selected_placement_preset_code(self):
        return self._preset_code_for_choice(
            self.planner_placement_presets,
            self.planner_placement_choice_var.get(),
        )

    def _planner_flow_summary(self, flow):
        campaign_lookup = {
            item.get("code"): item for item in self.planner_catalog.get("campaignBundles", [])
        }
        adset_lookup = {
            item.get("code"): item for item in self.planner_catalog.get("adSetBundles", [])
        }
        campaign = campaign_lookup.get(flow.get("campaign_code"), {})
        adset = adset_lookup.get(flow.get("adset_code"), {})
        campaign_name = self._campaign_card_title(campaign) or "Chưa chọn chiến dịch"
        conversion_location = adset.get("conversionLocation") or "Chưa chọn vị trí chuyển đổi"
        goal = adset.get("performanceGoal") or adset.get("name") or "Chưa chọn cách tối ưu"
        for prefix in ("Tối đa hóa số ", "Tối đa hóa ", "Tăng tối đa "):
            if goal.startswith(prefix):
                goal = goal[len(prefix):]
                break
        goal = goal.replace("lượt xem ThruPlay", "lượt xem video lâu")
        return f"{campaign_name} → {conversion_location} → {goal}"

    def add_current_planner_flow(self):
        campaign_codes = self._selected_campaign_bundle_codes()
        adset_codes = self._selected_adset_bundle_codes()
        if len(campaign_codes) != 1:
            self._message_warning(APP_TITLE, "Hãy chọn một chiến dịch.")
            return
        if len(adset_codes) != 1:
            self._message_warning(APP_TITLE, "Hãy chọn một nhóm quảng cáo cho cách chạy này.")
            return
        self.planner_flow_sequence += 1
        flow = {
            "id": self.planner_flow_sequence,
            "campaign_code": campaign_codes[0],
            "adset_code": adset_codes[0],
            "audience_codes": list(self._selected_audience_preset_codes()),
            "dataset_code": self._selected_dataset_preset_code(),
            "budget_code": self._selected_budget_preset_code(),
            "custom_budget_values": dict(self._custom_budget_values()),
            "placement_code": self._selected_placement_preset_code(),
            "creative_mode": self._selected_creative_mode(),
        }
        self.planner_flows.append(flow)
        self.planner_selected_adset_codes.clear()
        for location_var in self.planner_location_vars.values():
            location_var.set(False)
        self._refresh_planner_adset_list()
        self._show_planner_selection_stage()
        self._refresh_planner_flows_panel()
        self._refresh_matrix_summary()
        self.log(f"Đã thêm cách chạy {flow['id']}: {self._planner_flow_summary(flow)}")

    def delete_planner_flow(self, flow_id):
        self.planner_flows = [flow for flow in self.planner_flows if flow.get("id") != flow_id]
        self._refresh_planner_flows_panel()
        self._refresh_matrix_summary()

    def duplicate_planner_flow(self, flow_id):
        source = next((flow for flow in self.planner_flows if flow.get("id") == flow_id), None)
        if not source:
            return
        self.planner_flow_sequence += 1
        duplicate = json.loads(json.dumps(source))
        duplicate["id"] = self.planner_flow_sequence
        self.planner_flows.append(duplicate)
        self._refresh_planner_flows_panel()
        self._refresh_matrix_summary()

    def _refresh_planner_flows_panel(self):
        if not hasattr(self, "planner_flows_host"):
            return
        for child in self.planner_flows_host.winfo_children():
            child.destroy()
        if not self.planner_flows:
            ctk.CTkLabel(
                self.planner_flows_host,
                text="Chưa thêm cách chạy nào.",
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
            return
        for row, flow in enumerate(self.planner_flows[:2]):
            item = ctk.CTkFrame(self.planner_flows_host, fg_color=COLORS["surface"])
            item.grid(row=row, column=0, sticky="ew", pady=(0, 4))
            item.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                item,
                text=f"{row + 1}. {self._planner_flow_summary(flow)}",
                font=FONTS["small"],
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)
            ctk.CTkButton(
                item,
                text="Chép",
                width=42,
                height=24,
                command=lambda item_id=flow.get("id"): self.duplicate_planner_flow(item_id),
            ).grid(row=0, column=1, padx=2)
            ctk.CTkButton(
                item,
                text="Xóa",
                width=38,
                height=24,
                fg_color=COLORS["danger"],
                hover_color="#a61f18",
                command=lambda item_id=flow.get("id"): self.delete_planner_flow(item_id),
            ).grid(row=0, column=2, padx=(0, 4))
        if len(self.planner_flows) > 2:
            ctk.CTkLabel(
                self.planner_flows_host,
                text=f"Còn {len(self.planner_flows) - 2} cách chạy khác.",
                font=FONTS["small"],
                text_color=COLORS["muted"],
                anchor="w",
            ).grid(row=2, column=0, sticky="w", padx=6, pady=2)

    def preview_planner_selection(self):
        links = self._current_import_links()
        if not self.planner_flows:
            self._message_warning(APP_TITLE, "Hãy thêm ít nhất một cách chạy vào kế hoạch.")
            return
        total_units = sum(max(1, len(flow.get("audience_codes", []))) for flow in self.planner_flows)
        total_rows = len(links) * total_units
        flow_lines = "\n".join(
            f"{index}. {self._planner_flow_summary(flow)}"
            for index, flow in enumerate(self.planner_flows, start=1)
        )
        message = (
            f"Số bài viết: {len(links)}\n"
            f"Số cách chạy: {len(self.planner_flows)}\n"
            f"Số mục dự kiến tạo: {total_rows}\n\n"
            f"{flow_lines}"
        )
        self.log(message.replace("\n", " | "))
        self._message_info("Xem nhanh kế hoạch", message)

    def import_links_with_planner(self):
        self.save_config()
        links = self._current_import_links()
        if not links:
            messagebox.showwarning(APP_TITLE, "Cần dán ít nhất một đường dẫn bài viết Facebook.")
            return
        if not self.planner_flows:
            messagebox.showwarning(APP_TITLE, "Hãy thêm ít nhất một cách chạy vào kế hoạch.")
            return
        self._run_background(
            self._import_links_with_planner_worker,
            links,
            self.import_name_var.get().strip(),
            json.loads(json.dumps(self.planner_flows)),
        )

    def _import_links_with_planner_worker(
        self,
        links,
        ad_name,
        flows,
    ):
        data_source_id = os.environ.get("NOTION_DATA_SOURCE_ID") or os.environ.get("NOTION_DATABASE_ID") or tool.DEFAULT_DATA_SOURCE_ID
        created = 0
        for index, link in enumerate(links, start=1):
            self.log(
                f"Đang tạo bản nháp {index}/{len(links)} với {len(flows)} cách chạy..."
            )
            name = ad_name if len(links) == 1 else ""
            for flow in flows:
                result = tool.create_notion_ad_drafts_from_bundles(
                    data_source_id,
                    link,
                    flow.get("campaign_code"),
                    [flow.get("adset_code")],
                    audience_preset_codes=flow.get("audience_codes", []),
                    dataset_preset_code=flow.get("dataset_code"),
                    budget_preset_code=flow.get("budget_code"),
                    custom_budget_values=flow.get("custom_budget_values", {}),
                    placement_preset_code=flow.get("placement_code"),
                    creative_mode=flow.get("creative_mode", "existing_post"),
                    ad_name=name or None,
                )
                created += len(result)
        self.log(f"Đã tạo {created} mục nháp trong Notion.")
        self._message_info(APP_TITLE, f"Đã tạo {created} mục nháp trong Notion.")

    def export_now(self):
        self.save_config()
        self._run_background(self._export_worker, True)

    def _build_export_args(self):
        class Args:
            env = str(ENV_PATH)
            database_id = None
            sample_csv = None
            output = None
            mapping = None
            template_row_index = None
            include_exported = False
            mark_exported = True
            ready_status_names = None

        Args.include_exported = self.vars["INCLUDE_EXPORTED"].get()
        Args.mark_exported = self.vars["MARK_EXPORTED"].get()
        if self.vars["EXPORT_IN_PROGRESS"].get():
            Args.ready_status_names = ["Ready", "To-do", "Not started", "In progress"]
        else:
            Args.ready_status_names = [
                item.strip()
                for item in self.vars["READY_STATUS_NAMES"].get().split(",")
                if item.strip()
            ]
        return Args

    def _export_worker(self, show_popup=False):
        Args = self._build_export_args()
        self.log("Đang quét Notion và xuất CSV...")
        result = tool.export_command(Args) or {"count": 0, "output": None}
        if not result.get("count"):
            self.log("Không có bài phù hợp trạng thái xuất.")
            if show_popup:
                self._message_warning(APP_TITLE, "Không có bài phù hợp để xuất.\n\nĐổi Trạng thái sang To-do/Ready hoặc bật xuất In progress.")
            return
        self.log(f"Hoàn tất export: {result.get('output')}")
        if show_popup:
            message = (
                "Đã export xong 1 file duy nhất.\n\n"
                f"File CSV mở được bằng Excel và dùng để import Facebook:\n{result.get('output')}"
            )
            self._message_info(APP_TITLE, message)

    def test_telegram(self):
        self.save_config()
        self._run_background(self._telegram_worker)

    def _telegram_worker(self):
        ok = tool.telegram_send("Test Telegram từ Notion -> Facebook Ads Khải Hoàn.")
        if ok:
            self.log("Test Telegram thành công.")
            self._message_info(APP_TITLE, "Test Telegram thành công.")
        else:
            self.log("Chưa cấu hình Telegram bot token hoặc chat ID.")
            self._message_warning(APP_TITLE, "Chưa cấu hình Telegram bot token hoặc chat ID.")

    def toggle_auto_scan(self):
        if self.auto_scan:
            self.auto_scan = False
            self.scan_button.configure(text="Bật tự quét")
            self.log("Đã tắt tự quét.")
            return
        self.save_config()
        self.auto_scan = True
        self.scan_button.configure(text="Tắt tự quét")
        self.scan_thread = threading.Thread(target=self._auto_scan_loop, daemon=True)
        self.scan_thread.start()
        self.log("Đã bật tự quét.")

    def _query_pending_pages(self):
        self._apply_vars_to_env()
        args = self._build_export_args()
        database_id = args.database_id or os.environ.get("NOTION_DATA_SOURCE_ID") or os.environ.get("NOTION_DATABASE_ID") or tool.DEFAULT_DATA_SOURCE_ID
        return tool.query_ready_pages(database_id, include_exported=args.include_exported, ready_names=args.ready_status_names)

    def _page_signature(self, pages):
        raw = "|".join(sorted(page.get("id", "") for page in pages))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def _telegram_confirmation_message(self, pages):
        names = []
        for page in pages[:5]:
            values = tool.notion_page_to_values(page)
            name = values.get("Tên chiến dịch / bài ads") or values.get("Tên quảng cáo") or values.get("Link bài viết") or page.get("id", "")
            names.append(f"- {name}")
        more = "" if len(pages) <= 5 else f"\n... và {len(pages) - 5} bài khác"
        return (
            "Có bài quảng cáo mới chờ xuất CSV.\n\n"
            f"Số bài: {len(pages)}\n"
            + "\n".join(names)
            + more
            + "\n\nBạn muốn xuất file CSV bây giờ không?"
        )

    def _request_telegram_export_confirmation(self, pages, wait_seconds):
        if not (os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")):
            return True
            
        # Gỡ webhook cũ của Telegram bot trước khi polling getUpdates
        try:
            tool.telegram_delete_webhook()
        except Exception:
            pass
            
        signature = self._page_signature(pages)
        token = f"{int(time.time())}_{signature}"
        reply_markup = {
            "inline_keyboard": [[
                {"text": "Xác nhận", "callback_data": f"khads_confirm:{token}"},
                {"text": "Hủy", "callback_data": f"khads_cancel:{token}"},
            ]]
        }
        sent = tool.telegram_send(self._telegram_confirmation_message(pages), reply_markup=reply_markup)
        if not sent:
            self.log("Không gửi được yêu cầu xác nhận Telegram, bỏ qua lần quét này.")
            return None
        chat_id = sent.get("chat", {}).get("id")
        message_id = sent.get("message_id")
        self.log("Đã gửi yêu cầu xác nhận Telegram.")
        deadline = time.time() + max(30, wait_seconds)
        while self.auto_scan and time.time() < deadline:
            timeout = min(20, max(1, int(deadline - time.time())))
            for update in tool.telegram_get_updates(self.telegram_update_offset, timeout=timeout):
                self.telegram_update_offset = update.get("update_id", 0) + 1
                callback = update.get("callback_query") or {}
                data = callback.get("data", "")
                if not data.endswith(token):
                    continue
                callback_id = callback.get("id")
                if data.startswith("khads_confirm:"):
                    tool.telegram_answer_callback(callback_id, "Đã xác nhận xuất CSV.")
                    if chat_id and message_id:
                        tool.telegram_edit_message(chat_id, message_id, "Đã xác nhận. Tool đang xuất CSV...")
                    return True
                if data.startswith("khads_cancel:"):
                    tool.telegram_answer_callback(callback_id, "Đã hủy xuất CSV.")
                    if chat_id and message_id:
                        tool.telegram_edit_message(chat_id, message_id, "Đã hủy xuất CSV cho lô này.")
                    return False
        if chat_id and message_id:
            tool.telegram_edit_message(chat_id, message_id, "Hết thời gian chờ xác nhận. Chưa xuất CSV.")
        return None

    def _auto_scan_loop(self):
        while self.auto_scan:
            try:
                interval = max(30, int(self.vars["SCAN_INTERVAL_SECONDS"].get() or "300"))
            except ValueError:
                interval = 300
            try:
                pages = self._query_pending_pages()
                if pages:
                    signature = self._page_signature(pages)
                    if signature == self.last_canceled_signature:
                        self.log("Có bài chờ xuất nhưng lô này đã bị hủy trên Telegram, chờ thay đổi mới.")
                    elif self.vars["TELEGRAM_CONFIRM_EXPORT"].get():
                        decision = self._request_telegram_export_confirmation(pages, interval)
                        if decision is True:
                            self.last_canceled_signature = ""
                            self._export_worker(False)
                        elif decision is False:
                            self.last_canceled_signature = signature
                            self.log("Đã hủy xuất theo xác nhận Telegram.")
                        else:
                            self.log("Chưa có xác nhận Telegram, chưa xuất CSV.")
                    else:
                        self._export_worker(False)
                else:
                    self.log("Tự quét: chưa có bài phù hợp để xuất.")
            except Exception as exc:
                self.log(f"Lỗi tự quét: {exc}")
            for _ in range(interval):
                if not self.auto_scan:
                    break
                time.sleep(1)

    def open_exports(self):
        path = APP_DIR / "exports"
        path.mkdir(exist_ok=True)
        os.startfile(path)

    def _run_background(self, target, *args):
        def runner():
            try:
                target(*args)
            except Exception as exc:
                self.log(f"Lỗi: {exc}")
                self._message_error(APP_TITLE, str(exc))

        threading.Thread(target=runner, daemon=True).start()

    def log(self, message):
        stamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{stamp}] {message}\n")

    def _drain_logs(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(150, self._drain_logs)

    def _message_info(self, title, message):
        self.after(0, lambda: messagebox.showinfo(title, message))

    def _message_warning(self, title, message):
        self.after(0, lambda: messagebox.showwarning(title, message))

    def _message_error(self, title, message):
        self.after(0, lambda: messagebox.showerror(title, message))


if __name__ == "__main__":
    BulkAdsApp().mainloop()

