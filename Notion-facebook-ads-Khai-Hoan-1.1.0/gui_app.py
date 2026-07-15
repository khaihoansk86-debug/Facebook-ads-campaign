#!/usr/bin/env python3
import json
import os
import queue
import hashlib
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import bulk_ads_tool as tool


APP_TITLE = "Notion -> Facebook Ads Khải Hoàn"

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

ENV_PATH = APP_DIR / ".env"
ASSET_DIR = APP_DIR / "assets"
SAMPLE_DIR = APP_DIR / "sample"
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


class BulkAdsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1240x820")
        self.minsize(1080, 720)
        self.configure(bg=COLORS["bg"])
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
            "SUPABASE_URL": tk.StringVar(value="https://kuelttmrhdkajclaaths.supabase.co"),
            "SUPABASE_PUBLISHABLE_KEY": tk.StringVar(),
            "SUPABASE_SECRET_KEY": tk.StringVar(),
            "ADS_SYNC_TOKEN": tk.StringVar(),
            "MARK_EXPORTED": tk.BooleanVar(value=True),
            "INCLUDE_EXPORTED": tk.BooleanVar(value=False),
            "EXPORT_IN_PROGRESS": tk.BooleanVar(value=False),
            "TELEGRAM_CONFIRM_EXPORT": tk.BooleanVar(value=True),
        }
        self.planner_creative_mode_var = tk.StringVar(value="Dùng bài có sẵn")
        self.planner_summary_var = tk.StringVar(value="Chưa chọn planner bundle nào.")
        self.planner_campaign_detail_var = tk.StringVar(value="Chọn một mẫu chiến dịch để xem cấu hình campaign.")
        self.planner_audience_summary_var = tk.StringVar(value="Chưa chọn tệp đối tượng.")
        self.planner_dataset_summary_var = tk.StringVar(value="Chưa chọn tập dữ liệu.")
        self.planner_budget_summary_var = tk.StringVar(value="Chưa chọn ngân sách.")
        self.planner_placement_summary_var = tk.StringVar(value="Chưa chọn vị trí quảng cáo.")
        self.planner_matrix_summary_var = tk.StringVar(value="Chưa có dữ liệu để tạo planner.")
        self.planner_budget_type_var = tk.StringVar(value="Ngân sách/ngày")
        self.planner_budget_amount_var = tk.StringVar()

        self._load_env_to_vars()
        self._build_styles()
        self._build_ui()
        self.after(150, self._drain_logs)

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["surface"], relief="flat")
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("CardMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI Semibold", 18))
        style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI Semibold", 12))
        style.configure("StepTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI Semibold", 11))
        style.configure("StepMeta.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=COLORS["field_border"], lightcolor=COLORS["field_border"], padding=10)
        style.map("TEntry", bordercolor=[("focus", COLORS["primary"])], lightcolor=[("focus", COLORS["primary"])])
        style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 10))
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
            font=("Segoe UI Semibold", 10),
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
            font=("Segoe UI Semibold", 10),
            padding=(14, 10),
            borderwidth=1,
            relief="flat",
            bordercolor=COLORS["field_border"],
            lightcolor="#ffffff",
            darkcolor=COLORS["field_border"],
        )
        style.map("Secondary.TButton", background=[("active", "#f4f8ff")], bordercolor=[("active", COLORS["primary"])])
        style.configure("Danger.TButton", background=COLORS["danger"], foreground="#ffffff", font=("Segoe UI Semibold", 10), padding=(12, 8), borderwidth=0)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=240)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        main = tk.Frame(self, bg=COLORS["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self._build_sidebar(sidebar)
        self._build_header(main)

        container = tk.Frame(main, bg=COLORS["bg"])
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
        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=18, pady=(18, 20))

        self.logo_image = None
        if APP_LOGO.exists():
            try:
                self.logo_image = tk.PhotoImage(file=str(APP_LOGO)).subsample(18, 18)
                tk.Label(brand, image=self.logo_image, bg=COLORS["sidebar"]).pack(anchor="w")
            except tk.TclError:
                pass

        tk.Label(
            brand,
            text="Khải Hoàn Ads",
            bg=COLORS["sidebar"],
            fg="#ffffff",
            font=("Segoe UI Semibold", 15),
        ).pack(anchor="w", pady=(10, 0))
        tk.Label(
            brand,
            text="Notion -> Facebook Ads",
            bg=COLORS["sidebar"],
            fg="#b9c7dc",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        nav_items = [
            ("dashboard", "Tổng quan"),
            ("import", "Nhập link bài"),
            ("audiences", "Tệp đối tượng"),
            ("export", "Xuất CSV"),
            ("config", "Cấu hình"),
            ("notion", "Notion mẫu"),
            ("logs", "Nhật ký"),
        ]
        for key, label in nav_items:
            btn = tk.Button(
                sidebar,
                text=label,
                anchor="w",
                relief="flat",
                bd=0,
                padx=18,
                pady=12,
                bg=COLORS["sidebar"],
                fg="#dce7f8",
                activebackground="#17365f",
                activeforeground="#ffffff",
                font=("Segoe UI Semibold", 10),
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = btn

        footer = tk.Frame(sidebar, bg=COLORS["sidebar"])
        footer.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Label(
            footer,
            text="Template-match mode\nGiữ cấu hình CSV mẫu",
            justify="left",
            bg=COLORS["sidebar"],
            fg="#91a6c5",
            font=("Segoe UI", 8),
        ).pack(anchor="w")

    def _build_header(self, main):
        header = tk.Frame(main, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 18))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Tạo nháp từ link Facebook, duyệt trên Notion, xuất CSV theo đúng file mẫu Ads Manager.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        actions = tk.Frame(header, bg=COLORS["bg"])
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(actions, text="Mở exports", style="Secondary.TButton", command=self.open_exports).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Xuất CSV", style="Primary.TButton", command=self.export_now).pack(side="left")

    def _card(self, parent, title=None, subtitle=None):
        outer = tk.Frame(parent, bg=COLORS["shadow"])
        border = tk.Frame(outer, bg=COLORS["border"])
        border.pack(fill="both", expand=True, padx=(0, 0), pady=(0, 3))
        inner = tk.Frame(border, bg=COLORS["surface"], padx=22, pady=20)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        if title:
            ttk.Label(inner, text=title, style="Section.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(inner, text=subtitle, style="CardMuted.TLabel", wraplength=820).pack(anchor="w", pady=(4, 12))
        content = tk.Frame(inner, bg=COLORS["surface"])
        content.pack(fill="both", expand=True)
        return outer, content

    def _mini_step(self, parent, number, title, desc):
        box = tk.Frame(parent, bg=COLORS["surface"])
        badge = tk.Label(
            box,
            text=number,
            bg=COLORS["surface_alt"],
            fg=COLORS["primary"],
            font=("Segoe UI Semibold", 16),
            width=3,
            pady=6,
        )
        badge.pack(anchor="w")
        ttk.Label(box, text=title, style="StepTitle.TLabel").pack(anchor="w", pady=(12, 2))
        ttk.Label(box, text=desc, style="StepMeta.TLabel", wraplength=220, justify="left").pack(anchor="w")
        return box

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
        return bundle.get("objectiveName") or bundle.get("campaignType") or bundle.get("name") or bundle.get("code")

    def _campaign_card_subtitle(self, bundle):
        return bundle.get("name") or bundle.get("code") or ""

    def _current_import_links(self):
        if not hasattr(self, "import_links_text"):
            return []
        return [line.strip() for line in self.import_links_text.get("1.0", "end").splitlines() if line.strip()]

    def _adset_flow_tag(self, adset_bundle):
        code = adset_bundle.get("code", "")
        if code.startswith("AWR_VIDEO"):
            return "Nhận biết / Video"
        if code.startswith("AWR_"):
            return "Nhận biết"
        if code in ("LEAD_WEB_FORM", "LEAD_WEB_CALL", "LEAD_FORM_MESSENGER"):
            return "Lead / Nhiều vị trí"
        if code.startswith("LEAD_"):
            return "Lead / Một vị trí"
        if code in ("SALE_WEB_APP", "SALE_WEB_SHOP", "SALE_WEB_APP_STORE", "SALE_WEB_CALL"):
            return "Sales / Nhiều vị trí"
        if code.startswith("SALE_WEBSITE"):
            return "Sales / Web"
        if code.startswith("SALE_APP"):
            return "Sales / Ứng dụng"
        if code.startswith("SALE_MESSAGE"):
            return "Sales / Tin nhắn"
        if code == "SALE_CALL":
            return "Sales / Cuộc gọi"
        if code.startswith("ENG_VIDEO"):
            return "Tương tác / ThruPlay"
        if code.startswith("ENG_MESSAGE"):
            return "Tương tác / Tin nhắn"
        if code.startswith("ENG_POST"):
            return "Tương tác / Bài viết"
        if code == "TRF_WEB_LPV":
            return "Traffic / Xem trang đích"
        if code == "TRF_WEB_CLICK":
            return "Traffic / Click link"
        if code == "TRF_WEB_DAILY_REACH":
            return "Traffic / Web Reach"
        if code == "TRF_WEB_CONVERSATIONS":
            return "Traffic / Web Chat"
        if code == "TRF_WEB_IMPRESSIONS":
            return "Traffic / Web Hiển thị"
        if code == "TRF_APP_EVENTS":
            return "Traffic / Ứng dụng"
        if code == "TRF_MESSAGE_DAILY_REACH":
            return "Traffic / Tin nhắn Reach"
        if code == "TRF_MESSAGE_CONVO":
            return "Traffic / Tin nhắn"
        if code == "TRF_MESSAGE_IMPRESSIONS":
            return "Traffic / Tin nhắn Hiển thị"
        if code == "TRF_PAGE_VISIT":
            return "Traffic / Truy cập trang"
        if code == "TRF_CALL":
            return "Traffic / Cuộc gọi"
        return adset_bundle.get("name") or code

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
        frame.configure(bg=palette["line"] if selected else COLORS["canvas_line"])
        refs["body"].configure(bg=palette["bg"] if selected else "#121b29")
        bar.configure(bg=palette["line"])
        title.configure(bg=palette["bg"] if selected else "#121b29", fg=palette["text"])
        subtitle.configure(bg=palette["bg"] if selected else "#121b29", fg=palette["muted"])
        dot.configure(text="◆" if focused else "●", bg=palette["line"] if selected else "#2c3b50")

    def _render_all_campaign_card_states(self):
        for code in self.planner_campaign_cards:
            self._render_campaign_card_state(code)

    def _toggle_campaign_bundle(self, code):
        if code not in self.planner_campaign_vars:
            return
        current = bool(self.planner_campaign_vars[code].get())
        if current and self.planner_focus_campaign_code != code:
            self.planner_focus_campaign_code = code
            self._render_all_campaign_card_states()
            self._refresh_planner_adset_list()
            return
        self.planner_campaign_vars[code].set(not current)
        if not current:
            self.planner_focus_campaign_code = code
        elif self.planner_focus_campaign_code == code:
            selected_codes = [
                item.get("code")
                for item in self.planner_campaign_bundles
                if self.planner_campaign_vars.get(item.get("code")) and self.planner_campaign_vars[item.get("code")].get()
            ]
            self.planner_focus_campaign_code = selected_codes[0] if selected_codes else None
        self._render_all_campaign_card_states()
        self._refresh_planner_adset_list()

    def _toggle_conversion_location(self, key):
        if key not in self.planner_location_vars:
            return
        current = bool(self.planner_location_vars[key].get())
        self.planner_location_vars[key].set(not current)
        self._refresh_planner_adset_list()

    def _on_adset_listbox_select(self, listbox, bundles):
        bundle_codes = {bundle.get("code") for bundle in bundles if bundle.get("code")}
        self.planner_selected_adset_codes.difference_update(bundle_codes)
        self.planner_selected_adset_codes.update(
            bundles[index].get("code")
            for index in listbox.curselection()
            if index < len(bundles) and bundles[index].get("code")
        )
        self._refresh_matrix_summary()

    def _remove_selected_adset_code(self, code):
        self.planner_selected_adset_codes.discard(code)
        self._restore_rendered_adset_selections()
        self._refresh_matrix_summary()

    def _toggle_adset_chip(self, code):
        if code in self.planner_selected_adset_codes:
            self.planner_selected_adset_codes.discard(code)
        elif code:
            self.planner_selected_adset_codes.add(code)
        self._restore_rendered_adset_selections()
        self._refresh_matrix_summary()

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
                chip.configure(
                    bg=palette["line"] if selected else "#182437",
                    fg="#ffffff" if selected else COLORS["canvas_text"],
                )

    def _current_allowed_adset_codes(self):
        campaign_codes = set(self._selected_campaign_bundle_codes())
        return {
            bundle.get("code")
            for bundle in self.planner_catalog.get("adSetBundles", [])
            if bundle.get("campaignBundleCode") in campaign_codes and bundle.get("code")
        }

    def _selected_adset_code_set(self):
        return self.planner_selected_adset_codes.intersection(self._current_allowed_adset_codes())

    def _campaign_detail_text(self, bundle):
        if not bundle:
            return "Chọn ít nhất một mẫu chiến dịch để xem cấu hình."
        settings = bundle.get("campaignSettings", {})
        objective = bundle.get("objectiveName") or bundle.get("name") or bundle.get("code")
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
        campaigns = len(self._selected_campaign_bundle_codes()) if hasattr(self, "planner_campaign_vars") else 0
        adsets = len(self._selected_adset_bundle_codes()) if hasattr(self, "planner_adset_listboxes") else 0
        audiences = len(self._selected_audience_preset_codes()) if hasattr(self, "planner_audience_listbox") else 0
        dataset = self._selected_dataset_preset_code() if hasattr(self, "planner_dataset_listbox") else None
        budget = self._selected_budget_preset_code() if hasattr(self, "planner_budget_listbox") else None
        custom_budget = self._custom_budget_values() if hasattr(self, "planner_budget_amount_var") else {}
        placement = self._selected_placement_preset_code() if hasattr(self, "planner_placement_listbox") else None
        audience_multiplier = audiences if audiences else 1
        total = len(links) * adsets * audience_multiplier
        self._refresh_selected_adset_tags()
        if not links and not campaigns:
            self.planner_matrix_summary_var.set("Chưa có dữ liệu để tạo planner.")
            self._refresh_link_plan_preview()
            return
        lines = [
            f"{len(links)} link x {campaigns} campaign x {adsets} nhóm x {audiences or 1} tệp = {total} dòng Notion",
            f"Dataset: {dataset or 'chưa chọn'} · Ngân sách: {self._budget_summary_text(budget, custom_budget)} · Vị trí: {placement or 'chưa chọn'}",
        ]
        if audiences == 0:
            lines.append("Nếu chưa chọn tệp đối tượng, tool sẽ tạo theo mẫu nhóm đang chọn.")
        self.planner_matrix_summary_var.set("\n".join(lines))
        self._refresh_link_plan_preview()

    def _page_base(self, container):
        page = tk.Frame(container, bg=COLORS["bg"])
        page.grid_columnconfigure(0, weight=1)
        return page

    def _page_dashboard(self, container):
        page = self._page_base(container)
        grid = tk.Frame(page, bg=COLORS["bg"])
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
            tk.Label(inner, text=num, bg=COLORS["surface_alt"], fg=COLORS["primary"], font=("Segoe UI Semibold", 18), width=3).pack(anchor="w")
            ttk.Label(inner, text=title, style="Section.TLabel").pack(anchor="w", pady=(12, 2))
            ttk.Label(inner, text=desc, style="CardMuted.TLabel", wraplength=250).pack(anchor="w")

        outer, inner = self._card(page, "Quy trình chuẩn", "Không export bản nháp nếu chưa duyệt, trừ khi bật tùy chọn xuất In progress.")
        outer.pack(fill="x", pady=(18, 0))
        text = (
            "- Link mới tạo trong Notion ở trạng thái In progress.\n"
            "- Khi quản lý duyệt xong, đổi trạng thái sang To-do hoặc Ready.\n"
            "- Sau khi xuất thành công, tool tick Đã xuất và chuyển trạng thái sang Done.\n"
            "- Cấu hình nhóm quảng cáo được lấy nguyên từ file CSV mẫu theo Tên nhóm QC."
        )
        tk.Label(inner, text=text, justify="left", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(anchor="w")
        return page

    def _page_import(self, container):
        page = self._page_base(container)
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(page, bg=COLORS["bg"], highlightthickness=0, bd=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        page_scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        page_scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=page_scrollbar.set)

        content = tk.Frame(canvas, bg=COLORS["bg"])
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def _sync_import_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _resize_import_width(event):
            canvas.itemconfigure(content_window, width=event.width)

        def _bind_import_wheel(_event=None):
            canvas.bind_all("<MouseWheel>", _on_import_wheel)

        def _unbind_import_wheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        def _on_import_wheel(event):
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            canvas.yview_scroll(delta, "units")

        content.bind("<Configure>", _sync_import_scroll)
        canvas.bind("<Configure>", _resize_import_width)
        canvas.bind("<Enter>", _bind_import_wheel)
        canvas.bind("<Leave>", _unbind_import_wheel)

        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        link_outer, link_inner = self._card(content, "Link nguồn")
        link_outer.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        link_inner.grid_columnconfigure(0, weight=1)
        link_inner.grid_columnconfigure(1, weight=0)
        link_inner.grid_rowconfigure(1, weight=1)

        ttk.Label(link_inner, text="Danh sách link Facebook", style="Card.TLabel").grid(row=0, column=0, sticky="w", columnspan=2)
        self.import_links_text = tk.Text(
            link_inner,
            height=5,
            wrap="word",
            relief="flat",
            bd=0,
            bg=COLORS["field"],
            fg=COLORS["text"],
            insertbackground=COLORS["primary"],
            font=("Segoe UI", 10),
            highlightthickness=2,
            highlightbackground=COLORS["field_border"],
            highlightcolor=COLORS["primary"],
            padx=14,
            pady=14,
        )
        self.import_links_text.grid(row=1, column=0, sticky="nsew", pady=(10, 14), padx=(0, 16))
        self.import_links_text.bind("<KeyRelease>", lambda _event: self._refresh_matrix_summary())

        side_actions = tk.Frame(link_inner, bg=COLORS["surface"])
        side_actions.grid(row=1, column=1, sticky="ns")
        ttk.Button(side_actions, text="Đưa link vào Notion", style="Secondary.TButton", command=self.import_links_to_notion).pack(fill="x")
        ttk.Button(side_actions, text="Mở Notion", style="Secondary.TButton", command=self.open_notion).pack(fill="x", pady=(8, 0))

        ttk.Label(link_inner, text="Tên nháp khi chỉ nhập 1 link", style="Card.TLabel").grid(row=2, column=0, sticky="w")
        self.import_name_var = tk.StringVar()
        ttk.Entry(link_inner, textvariable=self.import_name_var).grid(row=3, column=0, sticky="ew", pady=(8, 0), padx=(0, 16))

        self.link_plan_preview_host = tk.Frame(link_inner, bg=COLORS["surface"])
        self.link_plan_preview_host.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self.link_plan_preview_host.grid_columnconfigure(0, weight=1)

        planner_shadow = tk.Frame(content, bg=COLORS["shadow"])
        planner_shadow.grid(row=1, column=0, sticky="nsew")
        planner_outer = tk.Frame(planner_shadow, bg=COLORS["canvas_line"])
        planner_outer.pack(fill="both", expand=True, pady=(0, 4))
        planner_inner = tk.Frame(planner_outer, bg=COLORS["canvas"], padx=12, pady=12)
        planner_inner.pack(fill="both", expand=True, padx=1, pady=1)
        planner_inner.grid_columnconfigure(0, weight=7)
        planner_inner.grid_columnconfigure(1, weight=5)
        planner_inner.grid_rowconfigure(4, weight=0, minsize=120)
        planner_inner.grid_rowconfigure(5, weight=1, minsize=130)

        header = tk.Frame(planner_inner, bg=COLORS["canvas"])
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(2, weight=0)

        tk.Label(
            header,
            text="Planner bundle",
            bg=COLORS["canvas"],
            fg=COLORS["canvas_text"],
            font=("Segoe UI Semibold", 15),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Campaign, bundle nhóm và tệp đối tượng",
            bg=COLORS["canvas"],
            fg="#8ea5c2",
            font=("Segoe UI", 9),
        ).grid(row=0, column=1, sticky="e", padx=(0, 14))
        tk.Label(
            header,
            text="Kiểu nội dung",
            bg=COLORS["canvas"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 9),
        ).grid(row=0, column=2, sticky="e", padx=(0, 8))
        self.planner_creative_mode_combo = ttk.Combobox(
            header,
            textvariable=self.planner_creative_mode_var,
            state="readonly",
            values=list(self._planner_creative_mode_options().keys()),
            style="Planner.TCombobox",
            width=22,
        )
        self.planner_creative_mode_combo.grid(row=0, column=3, sticky="e")

        tk.Label(
            planner_inner,
            text="Mẫu chiến dịch",
            bg=COLORS["canvas"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 10),
        ).grid(row=1, column=0, sticky="w", pady=(10, 4))

        campaign_wrap = tk.Frame(planner_inner, bg=COLORS["canvas"])
        campaign_wrap.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        for col in range(5):
            campaign_wrap.grid_columnconfigure(col, weight=1)
        self.planner_campaign_cards_host = campaign_wrap

        self.planner_bundle_heading_label = tk.Label(
            planner_inner,
            text="Bundle nhóm quảng cáo",
            bg=COLORS["canvas"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 10),
        )
        self.planner_bundle_heading_label.grid(row=3, column=0, sticky="w", pady=(0, 4))
        self.planner_selected_tags_host = tk.Frame(planner_inner, bg=COLORS["canvas"])
        self.planner_selected_tags_host.grid(row=3, column=1, sticky="ew", pady=(0, 4))
        self.planner_selected_tags_host.grid_columnconfigure(0, weight=1)

        list_wrap = tk.Frame(planner_inner, bg=COLORS["canvas_line"])
        list_wrap.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.planner_adset_groups_host = tk.Frame(list_wrap, bg=COLORS["canvas_soft"], padx=6, pady=6)
        self.planner_adset_groups_host.pack(fill="both", expand=True, padx=1, pady=1)
        self.planner_adset_groups_host.grid_columnconfigure(0, weight=1)

        audience_wrap = tk.Frame(planner_inner, bg=COLORS["canvas_line"])
        audience_wrap.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        audience_inner = tk.Frame(audience_wrap, bg=COLORS["canvas_soft"])
        audience_inner.pack(fill="both", expand=True, padx=1, pady=1)
        audience_inner.grid_columnconfigure(0, weight=1)
        audience_inner.grid_columnconfigure(2, weight=1)
        audience_inner.grid_columnconfigure(4, weight=1)
        audience_inner.grid_columnconfigure(6, weight=1)

        self.planner_audience_heading_label = tk.Label(
            audience_inner,
            text="Tệp đối tượng",
            bg=COLORS["canvas_soft"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=5,
        )
        self.planner_audience_heading_label.grid(row=0, column=0, sticky="w")

        self.planner_audience_listbox = tk.Listbox(
            audience_inner,
            selectmode="multiple",
            height=2,
            exportselection=False,
            relief="flat",
            bd=0,
            bg=COLORS["canvas_soft"],
            fg=COLORS["canvas_text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            activestyle="none",
            highlightthickness=0,
        )
        self.planner_audience_listbox.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.planner_audience_listbox.bind("<<ListboxSelect>>", lambda _event: self._refresh_matrix_summary())
        audience_scrollbar = ttk.Scrollbar(audience_inner, orient="vertical", command=self.planner_audience_listbox.yview)
        audience_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 8), padx=(0, 8))
        self.planner_audience_listbox.configure(yscrollcommand=audience_scrollbar.set)

        tk.Label(
            audience_inner,
            text="Tập dữ liệu",
            bg=COLORS["canvas_soft"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=5,
        ).grid(row=0, column=2, sticky="w")
        self.planner_dataset_listbox = tk.Listbox(
            audience_inner,
            selectmode="browse",
            height=2,
            exportselection=False,
            relief="flat",
            bd=0,
            bg=COLORS["canvas_soft"],
            fg=COLORS["canvas_text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            activestyle="none",
            highlightthickness=0,
        )
        self.planner_dataset_listbox.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 8))
        self.planner_dataset_listbox.bind("<<ListboxSelect>>", lambda _event: self._refresh_matrix_summary())

        tk.Label(
            audience_inner,
            text="Ngân sách",
            bg=COLORS["canvas_soft"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=5,
        ).grid(row=0, column=4, sticky="w")
        self.planner_budget_listbox = tk.Listbox(
            audience_inner,
            selectmode="browse",
            height=2,
            exportselection=False,
            relief="flat",
            bd=0,
            bg=COLORS["canvas_soft"],
            fg=COLORS["canvas_text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            activestyle="none",
            highlightthickness=0,
        )
        self.planner_budget_listbox.grid(row=1, column=4, sticky="ew", padx=8, pady=(0, 8))
        self.planner_budget_listbox.bind("<<ListboxSelect>>", lambda _event: self._refresh_matrix_summary())
        budget_custom = tk.Frame(audience_inner, bg=COLORS["canvas_soft"])
        budget_custom.grid(row=2, column=4, sticky="ew", padx=8, pady=(0, 8))
        budget_custom.grid_columnconfigure(1, weight=1)
        self.planner_budget_type_combo = ttk.Combobox(
            budget_custom,
            textvariable=self.planner_budget_type_var,
            state="readonly",
            values=["Ngân sách/ngày", "Ngân sách trọn đời"],
            width=16,
            style="Planner.TCombobox",
        )
        self.planner_budget_type_combo.grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.planner_budget_type_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_matrix_summary())
        self.planner_budget_amount_entry = ttk.Entry(
            budget_custom,
            textvariable=self.planner_budget_amount_var,
            width=14,
        )
        self.planner_budget_amount_entry.grid(row=0, column=1, sticky="ew")
        self.planner_budget_amount_entry.bind("<KeyRelease>", lambda _event: self._refresh_matrix_summary())

        tk.Label(
            audience_inner,
            text="Vị trí quảng cáo",
            bg=COLORS["canvas_soft"],
            fg="#dbe6f7",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=5,
        ).grid(row=0, column=6, sticky="w")
        self.planner_placement_listbox = tk.Listbox(
            audience_inner,
            selectmode="browse",
            height=2,
            exportselection=False,
            relief="flat",
            bd=0,
            bg=COLORS["canvas_soft"],
            fg=COLORS["canvas_text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            activestyle="none",
            highlightthickness=0,
        )
        self.planner_placement_listbox.grid(row=1, column=6, sticky="ew", padx=8, pady=(0, 8))
        self.planner_placement_listbox.bind("<<ListboxSelect>>", lambda _event: self._refresh_matrix_summary())

        matrix_outer = tk.Frame(planner_inner, bg=COLORS["canvas_line"])
        matrix_outer.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        matrix_inner = tk.Frame(matrix_outer, bg="#101a2a")
        matrix_inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(
            matrix_inner,
            textvariable=self.planner_matrix_summary_var,
            bg="#101a2a",
            fg=COLORS["canvas_text"],
            justify="left",
            wraplength=1280,
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=7,
        ).pack(anchor="w")

        planner_actions = tk.Frame(planner_inner, bg=COLORS["canvas"])
        planner_actions.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(planner_actions, text="Nạp lại mẫu", style="Secondary.TButton", command=self.reload_planner_catalog).pack(side="left")
        ttk.Button(planner_actions, text="Xem số dòng sẽ tạo", style="Secondary.TButton", command=self.preview_planner_selection).pack(side="left", padx=8)
        ttk.Button(planner_actions, text="Tạo planner vào Notion", style="Primary.TButton", command=self.import_links_with_planner).pack(side="left")
        self.reload_planner_catalog()
        self._refresh_matrix_summary()
        return page

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
            font=("Segoe UI", 10),
            activestyle="none",
            highlightthickness=1,
            highlightbackground=COLORS["field_border"],
        )
        self.audience_library_listbox.grid(row=0, column=0, sticky="nsew")
        self.audience_library_listbox.bind("<<ListboxSelect>>", lambda _event: self._load_selected_audience_preset())
        list_scrollbar = ttk.Scrollbar(list_inner, orient="vertical", command=self.audience_library_listbox.yview)
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
            ttk.Label(form_inner, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=6)
            ttk.Entry(form_inner, textvariable=self.audience_form_vars[key]).grid(row=row, column=1, sticky="ew", pady=6, padx=(12, 0))

        actions = tk.Frame(form_inner, bg=COLORS["surface"])
        actions.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Button(actions, text="Tạo mới", style="Secondary.TButton", command=self.clear_audience_form).pack(side="left")
        ttk.Button(actions, text="Lưu tệp đối tượng", style="Primary.TButton", command=self.save_audience_preset).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Nạp lại", style="Secondary.TButton", command=self.reload_audience_library).pack(side="left", padx=(8, 0))

        self.reload_audience_library()
        return page

    def _page_export(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Xuất CSV Facebook", "CSV xuất ra giữ format UTF-16 + tab và clone cấu hình từ file mẫu cũ.")
        outer.pack(fill="x")

        checks = tk.Frame(inner, bg=COLORS["surface"])
        checks.pack(fill="x")
        ttk.Checkbutton(checks, text="Đánh dấu Đã xuất sau khi xuất", variable=self.vars["MARK_EXPORTED"]).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Xuất cả bài đã xuất", variable=self.vars["INCLUDE_EXPORTED"]).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Xuất cả bản nháp In progress", variable=self.vars["EXPORT_IN_PROGRESS"]).pack(side="left")

        buttons = tk.Frame(inner, bg=COLORS["surface"])
        buttons.pack(fill="x", pady=(18, 0))
        ttk.Button(buttons, text="Xuất CSV ngay", style="Primary.TButton", command=self.export_now).pack(side="left")
        ttk.Button(buttons, text="Mở thư mục exports", style="Secondary.TButton", command=self.open_exports).pack(side="left", padx=8)

        scan_outer, scan_inner = self._card(page, "Tự quét Notion", "Bật khi muốn tool tự kiểm tra bài Ready theo chu kỳ.")
        scan_outer.pack(fill="x", pady=(18, 0))
        row = tk.Frame(scan_inner, bg=COLORS["surface"])
        row.pack(fill="x")
        ttk.Label(row, text="Chu kỳ quét (giây)", style="Card.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=self.vars["SCAN_INTERVAL_SECONDS"], width=12).pack(side="left", padx=10)
        self.scan_button = ttk.Button(row, text="Bật tự quét", style="Secondary.TButton", command=self.toggle_auto_scan)
        self.scan_button.pack(side="left")
        ttk.Checkbutton(
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

        actions = tk.Frame(inner, bg=COLORS["surface"])
        actions.grid(row=len(fields), column=0, columnspan=3, sticky="ew", pady=(18, 0))
        ttk.Button(actions, text="Lưu cấu hình", style="Primary.TButton", command=self.save_config).pack(side="left")
        ttk.Button(actions, text="Test Telegram", style="Secondary.TButton", command=self.test_telegram).pack(side="left", padx=8)
        ttk.Button(actions, text="Mở thư mục tool", style="Secondary.TButton", command=lambda: os.startfile(APP_DIR)).pack(side="left")
        return page

    def _page_notion(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Notion mẫu", "Chỉ cần dùng nếu muốn tạo database mới từ một page cha trong Notion.")
        outer.pack(fill="both", expand=True)
        inner.grid_columnconfigure(1, weight=1)
        self._field(inner, 0, "Parent page ID", self.vars["PARENT_PAGE_ID"])
        ttk.Button(inner, text="Tạo database Notion mẫu", style="Primary.TButton", command=self.create_template).grid(row=1, column=0, sticky="w", pady=(14, 0))
        ttk.Button(inner, text="Lưu cấu hình", style="Secondary.TButton", command=self.save_config).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(14, 0))
        guide = (
            "1. Tạo một page trống trong Notion.\n"
            "2. Share page đó cho integration đang giữ token.\n"
            "3. Copy Page ID và dán vào ô trên.\n"
            "4. Bấm tạo database mẫu, sau đó copy Data Source ID vào cấu hình."
        )
        tk.Label(inner, text=guide, justify="left", bg=COLORS["surface"], fg=COLORS["text"], font=("Segoe UI", 10)).grid(row=2, column=0, columnspan=3, sticky="w", pady=(18, 0))
        return page

    def _page_logs(self, container):
        page = self._page_base(container)
        outer, inner = self._card(page, "Nhật ký hoạt động", "Theo dõi thao tác nhập link, export CSV và tự quét Notion.")
        outer.pack(fill="both", expand=True)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(0, weight=1)
        self.log_text = tk.Text(inner, wrap="word", state="disabled", relief="flat", bd=0, bg="#0f172a", fg="#dbeafe", insertbackground="#ffffff", font=("Consolas", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(inner, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        return page

    def _field(self, parent, row, label, var, show=None, browse=False):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        entry = ttk.Entry(parent, textvariable=var, show=show)
        entry.grid(row=row, column=1, sticky="ew", pady=7, padx=(12, 8))
        if browse:
            ttk.Button(parent, text="Chọn file", style="Secondary.TButton", command=self._choose_sample_csv).grid(row=row, column=2, pady=7)
        return entry

    def show_page(self, key):
        for nav_key, btn in self.nav_buttons.items():
            if nav_key == key:
                btn.configure(bg=COLORS["sidebar_active"], fg="#ffffff")
            else:
                btn.configure(bg=COLORS["sidebar"], fg="#dce7f8")
        self.pages[key].tkraise()

    def open_notion(self):
        os.startfile("https://app.notion.com/p/0d89661f16ee43fcaa7abad46058b9bc?v=a62193e84656430f970a676d812b3a31")

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

            frame = tk.Frame(self.planner_campaign_cards_host, bg=COLORS["canvas_line"], cursor="hand2")
            frame.grid(row=0, column=index, sticky="nsew", padx=(0, 8), pady=(0, 0))
            self.planner_campaign_cards_host.grid_rowconfigure(0, weight=1)

            body = tk.Frame(frame, bg="#121b29", padx=7, pady=6, cursor="hand2")
            body.pack(fill="both", expand=True, padx=1, pady=1)
            body.grid_columnconfigure(1, weight=1)

            bar = tk.Frame(body, bg=palette["line"], width=3)
            bar.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))
            dot = tk.Label(body, text="●", bg="#121b29", fg=palette["line"], font=("Segoe UI", 8), cursor="hand2")
            dot.grid(row=0, column=2, sticky="ne")
            title = tk.Label(
                body,
                text=self._campaign_card_title(item),
                bg="#121b29",
                fg=COLORS["canvas_text"],
                font=("Segoe UI Semibold", 9),
                anchor="w",
                justify="left",
                cursor="hand2",
            )
            title.grid(row=0, column=1, sticky="w")
            subtitle = tk.Label(
                body,
                text=self._campaign_card_subtitle(item),
                bg="#121b29",
                fg="#9fb0c5",
                font=("Segoe UI", 7),
                anchor="w",
                justify="left",
                wraplength=220,
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
        self.planner_audience_listbox.delete(0, "end")
        self.planner_dataset_listbox.delete(0, "end")
        self.planner_budget_listbox.delete(0, "end")
        self.planner_placement_listbox.delete(0, "end")
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

            group = tk.Frame(self.planner_adset_groups_host, bg=palette["line"])
            group.grid(row=row, column=0, sticky="ew", pady=(0, 6))
            group.grid_columnconfigure(0, weight=1)

            body = tk.Frame(group, bg="#121b29", padx=8, pady=8)
            body.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
            body.grid_columnconfigure(0, weight=1)

            tk.Label(
                body,
                text=self._campaign_card_title(campaign),
                bg="#121b29",
                fg=palette["text"],
                font=("Segoe UI Semibold", 9),
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                body,
                text=f"{len(campaign_adsets)} bundle nhóm · {len(campaign_bundles)} campaign trong kế hoạch",
                bg="#121b29",
                fg=palette["muted"],
                font=("Segoe UI", 8),
                anchor="e",
            ).grid(row=0, column=1, sticky="e")

            location_groups = {}
            for item in campaign_adsets:
                location = item.get("conversionLocation") or "Chưa phân loại vị trí chuyển đổi"
                interaction = item.get("interactionType") or "Chưa phân loại tương tác"
                location_groups.setdefault(location, {}).setdefault(interaction, []).append(item)

            location_picker = tk.Frame(body, bg="#121b29")
            location_picker.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            location_picker.grid_columnconfigure(0, weight=1)
            location_picker.grid_columnconfigure(1, weight=1)
            location_picker.grid_columnconfigure(2, weight=1)
            location_picker.grid_columnconfigure(3, weight=1)

            for location_index, location in enumerate(location_groups):
                location_key = f"{campaign_code}:{location}"
                if location_key not in self.planner_location_vars:
                    self.planner_location_vars[location_key] = tk.BooleanVar(value=False)
                selected_location = self.planner_location_vars[location_key].get()
                location_card = tk.Frame(
                    location_picker,
                    bg=palette["line"] if selected_location else COLORS["canvas_line"],
                    cursor="hand2",
                )
                location_card.grid(
                    row=location_index // 4,
                    column=location_index % 4,
                    sticky="ew",
                    padx=(0, 6),
                    pady=(0, 6),
                )
                location_body = tk.Frame(
                    location_card,
                    bg=palette["bg"] if selected_location else "#182437",
                    padx=7,
                    pady=5,
                    cursor="hand2",
                )
                location_body.pack(fill="both", expand=True, padx=1, pady=1)
                location_count = sum(len(items) for items in location_groups[location].values())
                location_label = tk.Label(
                    location_body,
                    text=f"{location} · {location_count}",
                    bg=palette["bg"] if selected_location else "#182437",
                    fg=palette["text"],
                    font=("Segoe UI Semibold", 8),
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
                location_frame = tk.Frame(body, bg="#182437")
                location_frame.grid(row=current_row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
                location_frame.grid_columnconfigure(0, weight=1)
                current_row += 1

                tk.Label(
                    location_frame,
                    text=f"Vị trí chuyển đổi: {location}",
                    bg="#182437",
                    fg=palette["text"],
                    font=("Segoe UI Semibold", 9),
                    anchor="w",
                    padx=10,
                    pady=5,
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
                        list_frame = tk.Frame(location_frame, bg=COLORS["canvas_line"])
                        list_frame.grid(row=interaction_row, column=0, sticky="ew", padx=8, pady=(0, 8))
                        interaction_row += 1
                    else:
                        interaction_frame = tk.Frame(location_frame, bg="#101a2a")
                        interaction_frame.grid(row=interaction_row, column=0, sticky="ew", padx=8, pady=(0, 8))
                        interaction_frame.grid_columnconfigure(0, weight=1)
                        interaction_row += 1

                        tk.Label(
                            interaction_frame,
                            text=f"Loại tương tác: {interaction}",
                            bg="#101a2a",
                            fg="#dbe6f7",
                            font=("Segoe UI", 9),
                            anchor="w",
                            padx=8,
                            pady=6,
                        ).grid(row=0, column=0, sticky="ew")

                        list_frame = tk.Frame(interaction_frame, bg=COLORS["canvas_line"])
                        list_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
                    list_frame.grid_columnconfigure(0, weight=1)

                    chip_host = tk.Frame(list_frame, bg=COLORS["canvas_soft"], padx=5, pady=5)
                    chip_host.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
                    for col in range(3):
                        chip_host.grid_columnconfigure(col, weight=1)

                    chips = []
                    for item_index, item in enumerate(bundles):
                        selected = item.get("code") in self.planner_selected_adset_codes
                        chip = tk.Label(
                            chip_host,
                            text=item.get("performanceGoal") or item.get("name") or item.get("code"),
                            bg=palette["line"] if selected else "#182437",
                            fg="#ffffff" if selected else COLORS["canvas_text"],
                            font=("Segoe UI Semibold", 8),
                            anchor="w",
                            justify="left",
                            padx=8,
                            pady=5,
                            cursor="hand2",
                        )
                        chip.grid(
                            row=item_index // 3,
                            column=item_index % 3,
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
                text=f"Bundle nhóm quảng cáo · {len(campaign_bundles)} campaign · {len(self.planner_adset_bundles)} bundle"
            )
        allowed_audiences = {
            code
            for bundle in campaign_bundles
            for code in bundle.get("allowedAudiencePresetCodes", [])
        }
        self.planner_audience_presets = [
            item for item in self.planner_catalog.get("audiencePresets", []) if item.get("code") in allowed_audiences
        ]
        for item in self.planner_audience_presets:
            label = item.get("name")
            self.planner_audience_listbox.insert("end", label)
        self.planner_dataset_presets = self.planner_catalog.get("datasetPresets", [])
        for item in self.planner_dataset_presets:
            self.planner_dataset_listbox.insert("end", item.get("name") or item.get("code"))
        if self.planner_dataset_presets:
            self.planner_dataset_listbox.selection_set(0)
        self.planner_budget_presets = self.planner_catalog.get("budgetPresets", [])
        for item in self.planner_budget_presets:
            self.planner_budget_listbox.insert("end", item.get("name") or item.get("code"))
        if self.planner_budget_presets:
            self.planner_budget_listbox.selection_set(0)
        self.planner_placement_presets = self.planner_catalog.get("placementPresets", [])
        for item in self.planner_placement_presets:
            self.planner_placement_listbox.insert("end", item.get("name") or item.get("code"))
        if self.planner_placement_presets:
            self.planner_placement_listbox.selection_set(0)
        self.planner_audience_summary_var.set(
            f"Có {len(self.planner_audience_presets)} tệp đối tượng dùng chung theo campaign đang chọn."
        )
        if hasattr(self, "planner_audience_heading_label"):
            self.planner_audience_heading_label.configure(
                text=f"Tệp đối tượng · {len(self.planner_audience_presets)} mẫu"
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
            tk.Label(
                self.planner_selected_tags_host,
                text="Chưa chọn tag nhóm",
                bg=COLORS["canvas"],
                fg="#8ea5c2",
                font=("Segoe UI", 9),
                anchor="e",
            ).grid(row=0, column=0, sticky="e")
            return

        for index, code in enumerate(selected_codes[:6]):
            bundle = adset_lookup.get(code, {})
            palette = self._campaign_palette(bundle.get("campaignBundleCode"))
            tag = self._adset_flow_tag(bundle)
            chip = tk.Frame(self.planner_selected_tags_host, bg=palette["line"])
            chip.grid(row=index // 3, column=index % 3, sticky="e", padx=(4, 0), pady=(0, 4))
            tk.Label(
                chip,
                text=tag,
                bg=palette["line"],
                fg="#ffffff",
                font=("Segoe UI Semibold", 8),
                padx=7,
                pady=3,
            ).pack(side="left")
            close = tk.Label(
                chip,
                text="x",
                bg=palette["line"],
                fg="#ffffff",
                font=("Segoe UI Semibold", 8),
                padx=6,
                pady=3,
                cursor="hand2",
            )
            close.pack(side="left")
            close.bind("<Button-1>", lambda _event, item_code=code: self._remove_selected_adset_code(item_code))
        if len(selected_codes) > 6:
            tk.Label(
                self.planner_selected_tags_host,
                text=f"+{len(selected_codes) - 6}",
                bg="#132033",
                fg="#dbe6f7",
                font=("Segoe UI Semibold", 8),
                padx=7,
                pady=3,
            ).grid(row=2, column=2, sticky="e", padx=(4, 0))

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

    def _selected_adset_bundles(self):
        adset_lookup = {
            item.get("code"): item
            for item in self.planner_catalog.get("adSetBundles", [])
            if item.get("code")
        }
        return [
            adset_lookup[code]
            for code in self._selected_adset_bundle_codes()
            if code in adset_lookup
        ]

    def _refresh_link_plan_preview(self):
        if not hasattr(self, "link_plan_preview_host"):
            return
        for child in self.link_plan_preview_host.winfo_children():
            child.destroy()

        links = self._current_import_links()
        adset_bundles = self._selected_adset_bundles() if hasattr(self, "planner_adset_listboxes") else []
        audience_count = len(self._selected_audience_preset_codes()) if hasattr(self, "planner_audience_listbox") else 0
        multiplier = audience_count if audience_count else 1

        if not links:
            return

        tags = []
        seen = set()
        for bundle in adset_bundles:
            tag = self._adset_flow_tag(bundle)
            if tag not in seen:
                seen.add(tag)
                tags.append((tag, bundle.get("campaignBundleCode")))

        for row, link in enumerate(links[:8]):
            card = tk.Frame(self.link_plan_preview_host, bg=COLORS["field_border"])
            card.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            card.grid_columnconfigure(1, weight=1)

            body = tk.Frame(card, bg="#ffffff", padx=12, pady=10)
            body.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
            body.grid_columnconfigure(1, weight=1)

            tk.Label(
                body,
                text=f"Link {row + 1}",
                bg="#ffffff",
                fg=COLORS["primary"],
                font=("Segoe UI Semibold", 9),
            ).grid(row=0, column=0, sticky="w", padx=(0, 10))
            tk.Label(
                body,
                text=link,
                bg="#ffffff",
                fg=COLORS["text"],
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=820,
                justify="left",
            ).grid(row=0, column=1, sticky="ew")

            tag_host = tk.Frame(body, bg="#ffffff")
            tag_host.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            if tags:
                for col, (tag, campaign_code) in enumerate(tags[:8]):
                    palette = self._campaign_palette(campaign_code)
                    chip = tk.Label(
                        tag_host,
                        text=tag,
                        bg=palette["line"],
                        fg="#ffffff",
                        font=("Segoe UI Semibold", 9),
                        padx=8,
                        pady=4,
                    )
                    chip.grid(row=0, column=col, sticky="w", padx=(0, 6), pady=(0, 4))
                if len(tags) > 8:
                    tk.Label(
                        tag_host,
                        text=f"+{len(tags) - 8} luồng",
                        bg=COLORS["surface_alt"],
                        fg=COLORS["muted"],
                        font=("Segoe UI", 9),
                        padx=8,
                        pady=4,
                    ).grid(row=0, column=8, sticky="w")
            else:
                tk.Label(
                    tag_host,
                    text="Chưa chọn bundle nhóm",
                    bg=COLORS["surface_alt"],
                    fg=COLORS["muted"],
                    font=("Segoe UI", 9),
                    padx=8,
                    pady=4,
                ).grid(row=0, column=0, sticky="w")

            rows_text = f"{len(tags) * multiplier} dòng Notion" if tags else "0 dòng Notion"
            tk.Label(
                body,
                text=rows_text,
                bg="#ffffff",
                fg=COLORS["muted"],
                font=("Segoe UI", 9),
            ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        if len(links) > 8:
            tk.Label(
                self.link_plan_preview_host,
                text=f"Còn {len(links) - 8} link khác sẽ dùng cùng bộ tag đang chọn.",
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9),
            ).grid(row=8, column=0, sticky="w")

    def _selected_audience_preset_codes(self):
        return [
            self.planner_audience_presets[index].get("code")
            for index in self.planner_audience_listbox.curselection()
            if index < len(self.planner_audience_presets)
        ]

    def _selected_budget_preset_code(self):
        selection = self.planner_budget_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.planner_budget_presets):
            return None
        return self.planner_budget_presets[index].get("code")

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
        selection = self.planner_dataset_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.planner_dataset_presets):
            return None
        return self.planner_dataset_presets[index].get("code")

    def _selected_placement_preset_code(self):
        selection = self.planner_placement_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self.planner_placement_presets):
            return None
        return self.planner_placement_presets[index].get("code")

    def preview_planner_selection(self):
        links = self._current_import_links()
        campaign_bundles = self._selected_campaign_bundles()
        adset_codes = self._selected_adset_bundle_codes()
        audience_codes = self._selected_audience_preset_codes()
        dataset_code = self._selected_dataset_preset_code()
        budget_code = self._selected_budget_preset_code()
        custom_budget_values = self._custom_budget_values()
        placement_code = self._selected_placement_preset_code()
        if not campaign_bundles:
            self._message_warning(APP_TITLE, "Cần chọn ít nhất 1 mẫu chiến dịch.")
            return
        if not adset_codes:
            self._message_warning(APP_TITLE, "Cần chọn ít nhất 1 mẫu nhóm quảng cáo.")
            return
        audience_multiplier = len(audience_codes) if audience_codes else 1
        total_rows = len(links) * len(adset_codes) * audience_multiplier
        message = (
            f"Số mẫu chiến dịch: {len(campaign_bundles)}\n"
            f"Kiểu nội dung: {self.planner_creative_mode_var.get()}\n"
            f"Số link: {len(links)}\n"
            f"Số mẫu nhóm: {len(adset_codes)}\n"
            f"Số tệp đối tượng: {len(audience_codes) if audience_codes else 0}\n"
            f"Tập dữ liệu: {dataset_code or 'chưa chọn'}\n"
            f"Ngân sách: {self._budget_summary_text(budget_code, custom_budget_values)}\n"
            f"Vị trí quảng cáo: {placement_code or 'chưa chọn'}\n"
            f"Số dòng Notion dự kiến: {total_rows}"
        )
        self.log(message.replace("\n", " | "))
        self._message_info("Xem nhanh planner", message)

    def import_links_with_planner(self):
        self.save_config()
        links = self._current_import_links()
        if not links:
            messagebox.showwarning(APP_TITLE, "Cần dán ít nhất 1 link Facebook.")
            return
        campaign_bundles = self._selected_campaign_bundles()
        adset_codes = self._selected_adset_bundle_codes()
        audience_codes = self._selected_audience_preset_codes()
        dataset_code = self._selected_dataset_preset_code()
        budget_code = self._selected_budget_preset_code()
        custom_budget_values = self._custom_budget_values()
        placement_code = self._selected_placement_preset_code()
        if not campaign_bundles:
            messagebox.showwarning(APP_TITLE, "Cần chọn ít nhất 1 mẫu chiến dịch.")
            return
        if not adset_codes:
            messagebox.showwarning(APP_TITLE, "Cần chọn ít nhất 1 mẫu nhóm quảng cáo.")
            return
        self._run_background(
            self._import_links_with_planner_worker,
            links,
            self.import_name_var.get().strip(),
            [bundle.get("code") for bundle in campaign_bundles],
            adset_codes,
            audience_codes,
            dataset_code,
            budget_code,
            custom_budget_values,
            placement_code,
            self._selected_creative_mode(),
        )

    def _import_links_with_planner_worker(
        self,
        links,
        ad_name,
        campaign_bundle_codes,
        adset_codes,
        audience_codes,
        dataset_code,
        budget_code,
        custom_budget_values,
        placement_code,
        creative_mode,
    ):
        data_source_id = os.environ.get("NOTION_DATA_SOURCE_ID") or os.environ.get("NOTION_DATABASE_ID") or tool.DEFAULT_DATA_SOURCE_ID
        adset_lookup = {item.get("code"): item for item in self.planner_catalog.get("adSetBundles", [])}
        campaign_to_adsets = {}
        for code in adset_codes:
            adset_bundle = adset_lookup.get(code)
            if not adset_bundle:
                continue
            campaign_to_adsets.setdefault(adset_bundle.get("campaignBundleCode"), []).append(code)
        created = 0
        for index, link in enumerate(links, start=1):
            self.log(
                f"Planner: đang tạo nháp {index}/{len(links)} với {len(campaign_to_adsets)} mẫu chiến dịch, {len(adset_codes)} mẫu nhóm và {len(audience_codes) if audience_codes else 0} tệp đối tượng..."
            )
            name = ad_name if len(links) == 1 else ""
            for campaign_code in campaign_bundle_codes:
                scoped_adsets = campaign_to_adsets.get(campaign_code, [])
                if not scoped_adsets:
                    continue
                result = tool.create_notion_ad_drafts_from_bundles(
                    data_source_id,
                    link,
                    campaign_code,
                    scoped_adsets,
                    audience_preset_codes=audience_codes,
                    dataset_preset_code=dataset_code,
                    budget_preset_code=budget_code,
                    custom_budget_values=custom_budget_values,
                    placement_preset_code=placement_code,
                    creative_mode=creative_mode,
                    ad_name=name or None,
                )
                created += len(result)
        self.log(f"Planner: đã tạo {created} dòng nháp trong Notion.")
        self._message_info(APP_TITLE, f"Planner đã tạo {created} dòng nháp trong Notion.")

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

