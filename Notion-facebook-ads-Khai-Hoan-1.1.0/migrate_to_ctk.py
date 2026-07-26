import re

def migrate(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    in_widget_creation = False
    paren_depth = 0
    current_widget = None
    
    for i, line in enumerate(lines):
        # Imports
        if 'import tkinter as tk' in line:
            line = line.replace('import tkinter as tk', 'import customtkinter as ctk\nimport tkinter as tk')
            
        # Handle .configure() updates
        if '.configure(' in line:
            line = re.sub(r'\bbg\s*=', 'fg_color=', line)
            line = re.sub(r'\bfg\s*=', 'text_color=', line)
            line = re.sub(r'\bhighlightthickness\s*=\s*\d+,?', '', line)
            line = re.sub(r'\bhighlightbackground\s*=\s*[^,)]+,?', '', line)
            line = re.sub(r'\bhighlightcolor\s*=\s*[^,)]+,?', '', line)

        # Widgets
        replacements = [
            (r'\btk\.Tk\(', r'ctk.CTk('),
            (r'\btk\.Toplevel\(', r'ctk.CTkToplevel('),
            (r'\btk\.Frame\(', r'ctk.CTkFrame('),
            (r'\bttk\.Frame\(', r'ctk.CTkFrame('),
            (r'\btk\.Label\(', r'ctk.CTkLabel('),
            (r'\bttk\.Label\(', r'ctk.CTkLabel('),
            (r'\btk\.Button\(', r'ctk.CTkButton('),
            (r'\bttk\.Button\(', r'ctk.CTkButton('),
            (r'\btk\.Entry\(', r'ctk.CTkEntry('),
            (r'\bttk\.Entry\(', r'ctk.CTkEntry('),
            (r'\bttk\.Combobox\(', r'ctk.CTkComboBox('),
            (r'\btk\.Checkbutton\(', r'ctk.CTkCheckBox('),
            (r'\bttk\.Checkbutton\(', r'ctk.CTkCheckBox('),
            (r'\btk\.Text\(', r'ctk.CTkTextbox('),
            (r'\btk\.Canvas\(', r'ctk.CTkCanvas('),
            (r'\btk\.Scrollbar\(', r'ctk.CTkScrollbar('),
            (r'\bttk\.Scrollbar\(', r'ctk.CTkScrollbar(')
        ]
        for old, new in replacements:
            line = re.sub(old, new, line)

        if 'orient=' in line and 'ctk.CTkScrollbar' in line:
            line = line.replace('orient=', 'orientation=')

        if 'ctk.CTk' in line and '(' in line:
            in_widget_creation = True
            if 'CTkComboBox' in line:
                current_widget = 'CTkComboBox'
            elif 'CTkCheckBox' in line:
                current_widget = 'CTkCheckBox'
            else:
                current_widget = 'other'

        strip_padding = False
        if in_widget_creation and not '.pack(' in line and not '.grid(' in line:
            strip_padding = True

        if in_widget_creation:
            kwargs_to_remove = ['bg', 'fg', 'relief', 'borderwidth', 'bd', 'highlightthickness', 'highlightbackground', 'highlightcolor', 'insertbackground', 'activebackground', 'activeforeground', 'style', 'selectcolor']
            for kwarg in kwargs_to_remove:
                pattern1 = r',\s*' + kwarg + r'\s*=\s*(?:COLORS\[[^\]]+\]|"[^"]*"|\'[^\']*\'|\([^)]+\)|[^,)\n]+)'
                line = re.sub(pattern1, '', line)
                pattern2 = kwarg + r'\s*=\s*(?:COLORS\[[^\]]+\]|"[^"]*"|\'[^\']*\'|\([^)]+\)|[^,)\n]+)\s*,\s*'
                line = re.sub(pattern2, '', line)
                pattern3 = kwarg + r'\s*=\s*(?:COLORS\[[^\]]+\]|"[^"]*"|\'[^\']*\'|\([^)]+\)|[^,)\n]+)'
                line = re.sub(pattern3, '', line)
            
            if strip_padding:
                for kwarg in ['padx', 'pady']:
                    pattern1 = r',\s*' + kwarg + r'\s*=\s*(?:COLORS\[[^\]]+\]|"[^"]*"|\'[^\']*\'|\([^)]+\)|[^,)\n]+)'
                    line = re.sub(pattern1, '', line)
                    pattern2 = kwarg + r'\s*=\s*(?:COLORS\[[^\]]+\]|"[^"]*"|\'[^\']*\'|\([^)]+\)|[^,)\n]+)\s*,\s*'
                    line = re.sub(pattern2, '', line)
                    pattern3 = kwarg + r'\s*=\s*(?:COLORS\[[^\]]+\]|"[^"]*"|\'[^\']*\'|\([^)]+\)|[^,)\n]+)'
                    line = re.sub(pattern3, '', line)

            if current_widget in ['CTkComboBox', 'CTkCheckBox']:
                line = line.replace('textvariable=', 'variable=')

        paren_depth += line.count('(')
        paren_depth -= line.count(')')
        
        if paren_depth <= 0:
            in_widget_creation = False
            current_widget = None
            paren_depth = 0

        if "class BulkAdsApp(tk.Tk):" in line:
            line = line.replace("class BulkAdsApp(tk.Tk):", "class BulkAdsApp(ctk.CTk):")
            
        if "self._build_styles()" in line:
            line = ""

        if "super().__init__()" in line:
            line = line.replace("super().__init__()", "super().__init__()\n        ctk.set_appearance_mode('System')\n        ctk.set_default_color_theme('blue')")

        new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    print(f"Successfully migrated {file_path}")

if __name__ == "__main__":
    migrate("gui_app.py")
