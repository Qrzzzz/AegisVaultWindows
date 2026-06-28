import base64
import os
import hashlib
import secrets
import string
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import ctypes
import threading
import time
import webbrowser
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def apply_blur_effect(window):
    """为 Windows 10/11 启用原生 Mica/Acrylic 效果"""
    window.update()
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), 4
        )
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(ctypes.c_int(3)), 4
        )
    except: pass

class AESModernSystem(ctk.CTk):

    def setup_ui(self):
        # 页脚
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.footer_frame.pack(side="bottom", fill="x", padx=30, pady=10)

        self.about_btn = ctk.CTkButton(self.footer_frame, text=self.translations["btn_about"][self.lang_mode], width=100, height=24, corner_radius=12, fg_color="transparent", text_color="#94A3B8", font=("Microsoft YaHei", 10), hover_color="#1E293B", border_width=1, border_color="#334155", command=self.show_copyright)
        self.about_btn.pack(side="left")

        # 主卡片面板
        self.main_container = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=20, border_width=1, border_color="#334155")
        self.main_container.pack(fill="both", expand=True, padx=40, pady=(20, 10))

        # 顶部工具
        self.top_tools = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_tools.pack(fill="x", padx=30, pady=(15, 0))
        self.lang_btn = ctk.CTkButton(self.top_tools, text="EN / 中文", width=80, height=26, corner_radius=13, fg_color="#334155", text_color="#F8FAFC", font=("Segoe UI", 11, "bold"), hover_color="#475569", command=self.toggle_language)
        self.lang_btn.pack(side="right")
        self.clear_btn = ctk.CTkButton(self.top_tools, text=self.translations["btn_clear"][self.lang_mode], width=80, height=26, corner_radius=13, fg_color="transparent", text_color="#EF4444", font=("Microsoft YaHei", 11), hover_color="#450A0A", command=self.clear_all)
        self.clear_btn.pack(side="right", padx=10)

        # 标题区
        self.main_title = ctk.CTkLabel(self.main_container, text=self.translations["title"][self.lang_mode], font=("Microsoft YaHei", 28, "bold"), text_color="#38BDF8")
        self.main_title.pack(pady=(10, 2))
        self.sub_title_label = ctk.CTkLabel(self.main_container, text=self.translations["sub_title"][self.lang_mode], font=("Microsoft YaHei", 12), text_color="#64748B")
        self.sub_title_label.pack(pady=(0, 10))

        # --- 新增：处理模式切换 (文本 / 文件) ---
        self.target_mode_var = tk.StringVar(value=self.translations["mode_text"][self.lang_mode])
        self.mode_switch = ctk.CTkSegmentedButton(
            self.main_container,
            values=[self.translations["mode_text"][self.lang_mode], self.translations["mode_file"][self.lang_mode]],
            variable=self.target_mode_var,
            font=("Microsoft YaHei", 12, "bold"),
            selected_color="#38BDF8",
            selected_hover_color="#0EA5E9",
            unselected_color="#334155",
            unselected_hover_color="#475569",
            command=self.on_mode_switch
        )
        self.mode_switch.pack(pady=(0, 15))
        # ----------------------------------------

        # 模式切换
        self.standard_mode_var = tk.BooleanVar(value=False)
        self.standard_chk = ctk.CTkCheckBox(self.main_container, text=self.translations["chk_standard"][self.lang_mode], variable=self.standard_mode_var, font=("Microsoft YaHei", 11), text_color="#94A3B8", fg_color="#38BDF8", hover_color="#0EA5E9", border_color="#475569", command=self.refresh_ui_text)
        self.standard_chk.pack(pady=(0, 15))

        # 密钥区
        self.create_field_header(self.translations["key_label"][self.lang_mode], "key_label_obj")

        key_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        key_frame.pack(fill="x", padx=50, pady=(0, 15))

        self.key_entry = ctk.CTkEntry(
            key_frame,
            height=45,
            corner_radius=10,
            border_width=1,
            border_color="#334155",
            fg_color="#0F172A",
            font=("Consolas", 14),
            placeholder_text=self.translations["ph_key"][self.lang_mode],
            show="*"
        )
        self.key_entry.pack(side="left", fill="x", expand=True)

        self.show_key = False
        self.show_key_btn = ctk.CTkButton(
            key_frame,
            text="🙈",
            width=45,
            height=45,
            corner_radius=10,
            fg_color="#334155",
            text_color="#38BDF8",
            font=("Microsoft YaHei", 12, "bold"),
            hover_color="#475569",
            command=self.toggle_key_visibility
        )
        self.show_key_btn.pack(side="left", padx=(5, 0))

        # 输入区 (引入 Wrapper 容器以实现平滑切换)
        self.create_field_header(self.translations["src_label"][self.lang_mode], "src_label_obj", has_paste=True)
        
        self.input_wrapper = ctk.CTkFrame(self.main_container, fg_color="transparent", height=140)
        self.input_wrapper.pack_propagate(False) # 固定容器高度，防止切换时窗口抖动
        self.input_wrapper.pack(fill="x", padx=50, pady=(0, 15))

        # 1. 文本输入框 (默认显示)
        self.input_text = ctk.CTkTextbox(self.input_wrapper, corner_radius=12, border_width=1, border_color="#334155", fg_color="#0F172A", font=("Consolas", 13), wrap="char")
        self.input_text.pack(fill="both", expand=True)

        # 2. 文件选择面板 (默认隐藏)
        self.file_input_frame = ctk.CTkFrame(self.input_wrapper, corner_radius=12, border_width=2, border_color="#334155", fg_color="#0F172A")
        
        self.select_file_btn = ctk.CTkButton(self.file_input_frame, text=self.translations["btn_select_file"][self.lang_mode], height=40, width=200, corner_radius=8, font=("Microsoft YaHei", 13, "bold"), fg_color="#334155", hover_color="#475569", command=self.select_file_action)
        self.select_file_btn.pack(pady=(35, 10))

        self.selected_file_path = "" # 用于在后台记录用户选中的文件路径
        self.file_path_label = ctk.CTkLabel(self.file_input_frame, text=self.translations["msg_no_file"][self.lang_mode], font=("Consolas", 11), text_color="#64748B")
        self.file_path_label.pack(padx=20)

        # 进度条
        self.progress = ctk.CTkProgressBar(self.main_container, height=4, progress_color="#38BDF8", fg_color="#0F172A")
        self.progress.set(0)
        self.progress.pack(fill="x", padx=50, pady=2)

        # 操作按钮
        btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        btn_frame.pack(pady=15)
        self.encode_btn = ctk.CTkButton(btn_frame, text=self.translations["btn_encrypt"][self.lang_mode], width=180, height=50, corner_radius=12, fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF", font=("Microsoft YaHei", 14, "bold"), command=self.encrypt_action)
        self.encode_btn.pack(side="left", padx=15)
        self.decode_btn = ctk.CTkButton(btn_frame, text=self.translations["btn_decrypt"][self.lang_mode], width=180, height=50, corner_radius=12, fg_color="#22C55E", hover_color="#16A34A", text_color="#FFFFFF", font=("Microsoft YaHei", 14, "bold"), command=self.decrypt_action)
        self.decode_btn.pack(side="left", padx=15)

        # 输出区
        self.create_field_header(self.translations["res_label"][self.lang_mode], "res_label_obj")
        self.result_text = ctk.CTkTextbox(self.main_container, height=140, corner_radius=12, border_width=1, border_color="#334155", fg_color="#0F172A", font=("Consolas", 13), wrap="char")
        self.result_text.pack(fill="x", padx=50, pady=(0, 15))

        # 复制按钮
        self.copy_btn = ctk.CTkButton(self.main_container, text=self.translations["btn_copy"][self.lang_mode], height=36, corner_radius=10, fg_color="transparent", border_width=1, border_color="#475569", text_color="#CBD5E1", command=self.copy_result, hover_color="#1E293B")
        self.copy_btn.pack(pady=(5, 20))

    def __init__(self):
        super().__init__()
        
        # 1. 优先级：最先定义状态变量与翻译字典
        self.lang_mode = 0 
        self.is_processing = False
        self.translations = {
            "title": ["AES 加密系统", "AES Encryption System"],
            "sub_title": ["基于 AES-256-GCM 算法的高级加密单元", "Advanced encryption unit based on AES-256-GCM"],
            "key_label": ["访问密钥 / 密码 (支持任意长度)", "ACCESS KEY / PASSWORD"],
            "src_label": ["原始数据 / 待解密报文", "SOURCE DATA / CIPHERTEXT"],
            "res_label": ["处理结果输出", "RESULT OUTPUT"],
            "btn_encrypt": ["安全加密", "SECURE ENCRYPT"],
            "btn_decrypt": ["安全解密", "SECURE DECRYPT"],
            "btn_encode": ["Base64 编码", "BASE64 ENCODE"],
            "btn_decode": ["Base64 解码", "BASE64 DECODE"],
            "btn_copy": ["复制结果", "COPY RESULT"],
            "btn_paste": ["粘贴内容", "PASTE"],
            "btn_copied": ["已成功复制", "COPIED!"],
            "btn_pasted": ["已成功粘贴", "PASTED!"],
            "btn_clear": ["清空全部", "CLEAR ALL"],
            "btn_about": ["ⓘ 软件声明", "ⓘ LEGAL NOTICE"],
            "chk_standard": ["简单 Base64 模式 (非加密)", "Simple Base64 Mode (Non-Enc)"],
            "msg_key_warning_title": ["⚠️ 安全风险警告", "⚠️ SECURITY RISK WARNING"],
            "msg_key_warning": [
                "您未输入密钥。系统可以生成随机密钥并【合并】到结果中，但这意味着：\n\n1. 任何人获取此字符串都能直接解密。\n2. 加密强度将形同虚设。\n\n是否确认执行此操作？",
                "No key entered. The system can bundle a key into the result, but:\n\n1. Anyone with this string can decrypt it.\n2. Security is significantly compromised.\n\nProceed anyway?"
            ],
            "msg_gen_ok": ["已生成随机密钥。请注意：此密文自带解密通行证！", "Random key generated. Warning: This ciphertext is self-decrypting!"],
            "msg_input_err": ["错误：请输入需要处理的内容！", "Error: Please enter content to process!"],
            "ph_key": ["在此输入密钥...", "Enter secret key here..."],
            "ph_input": ["在此输入需要加密或解密的内容...", "Enter text to process here..."],
            "mode_text": ["文本处理模式", "Text Mode"],
            "mode_file": ["文件处理模式", "File Mode"],
            "btn_select_file": ["📁 点击浏览并选择文件", "📁 Click to Browse / Select File"],
            "msg_no_file": ["当前未选择任何文件...", "No file selected yet..."],
        }

        # 2. 窗口基础属性
        self.title(self.translations["title"][self.lang_mode])
        self.geometry("850x920")
        self.resizable(False, False)
        self.center_window()
        self.configure(fg_color="#0F172A")

        # 3. 动态获取图标路径（兼容打包环境）
        if getattr(sys, 'frozen', False):
            # 打包后，文件会被释放到临时目录 _MEIPASS 下
            base_path = sys._MEIPASS
        else:
            # 开发环境下，直接从脚本同级目录获取
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        # 这里的文件名必须与打包命令中的文件名一致
        icon_path = os.path.join(base_path, "app_icon.ico")

        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass 

        # 4. 构建 UI
        self.setup_ui()
        apply_blur_effect(self)

    def center_window(self):
        self.update_idletasks()
        w, h = 850, 920
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')
        
    def select_file_action(self):
        """点击按钮选择文件"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title=("选择需要处理的文件", "Select file to process")[self.lang_mode]
        )
        if file_path:
            self.selected_file_path = file_path
            # 如果路径太长，截断显示中间部分以保持 UI 美观
            display_path = file_path if len(file_path) < 55 else file_path[:20] + " ... " + file_path[-30:]
            self.file_path_label.configure(text=display_path, text_color="#38BDF8")

    def encrypt_action(self):
        """这是一个路由函数，根据顶部的 Toggle 决定执行哪种加密"""
        is_file_mode = self.target_mode_var.get() in self.translations["mode_file"]
        
        if is_file_mode:
            self.encrypt_file_action()  # 调用文件加密逻辑
        else:
            self.encrypt_text_action()  # 调用文本加密逻辑

    def encrypt_text_action(self):
        """处理文本加密的核心逻辑"""
        if self.is_processing: return
        key_raw = self.key_entry.get().strip()
        plain = self.input_text.get("1.0", tk.END).strip()
        
        if not plain:
            messagebox.showwarning("Hint", self.translations["msg_input_err"][self.lang_mode])
            return

        auto_gen = False
        if not self.standard_mode_var.get() and not key_raw:
            if messagebox.askyesno(
                self.translations["msg_key_warning_title"][self.lang_mode], 
                self.translations["msg_key_warning"][self.lang_mode],
                icon='warning'
            ):
                # 生成 8 位随机密钥
                key_raw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
                auto_gen = True
            else:
                return

        def task():
            self._safe_ui_update(self.set_ui_state, "disabled")
            self._safe_ui_update(self.progress.set, 0.3)
            
            try:
                result = ""
                if self.standard_mode_var.get():
                    result = base64.b64encode(plain.encode('utf-8')).decode('utf-8')
                else:
                    key = hashlib.sha256(key_raw.encode('utf-8')).digest()
                    aesgcm = AESGCM(key)
                    nonce = os.urandom(12)
                    ciphertext = aesgcm.encrypt(nonce, plain.encode('utf-8'), None)
                    cipher_b64 = base64.b64encode(nonce + ciphertext).decode('utf-8')
                    
                    if auto_gen:
                        result = f"AK#{key_raw}#{cipher_b64}"
                        self._safe_ui_update(lambda: self.result_text.configure(border_color="#F59E0B"))
                        self._safe_messagebox("warning", "Key Generated", self.translations["msg_gen_ok"][self.lang_mode])
                    else:
                        result = cipher_b64
                        self._safe_ui_update(lambda: self.result_text.configure(border_color="#334155"))
                
                self._safe_ui_update(self.progress.set, 1.0)
                def update_result_text(txt):
                    self.result_text.delete("1.0", tk.END)
                    self.result_text.insert(tk.END, txt)
                self._safe_ui_update(update_result_text, result)

            except Exception as e:
                self._handle_exception(e, "encrypt")
            finally:
                self._safe_ui_update(self.set_ui_state, "normal")

        threading.Thread(target=task, daemon=True).start()

    def encrypt_file_action(self):
        """处理文件加密的核心逻辑"""
        if self.is_processing: return
        
        # 1. 验证是否已选择文件
        file_path = getattr(self, "selected_file_path", "").strip()
        if not file_path or not os.path.isfile(file_path):
            title = ("提示", "Hint")[self.lang_mode]
            msg = ("请先点击上方按钮选择一个文件！\n(如果已选择，请确保文件未被移动或删除)", 
                   "Please select a file first!\n(If selected, ensure it hasn't been moved or deleted.)")[self.lang_mode]
            
            # 因为目前在主线程，直接调用原生 messagebox 即可立即阻断
            messagebox.showwarning(title, msg)
            
            # 安全重置：清空失效的路径，并把 UI 标签恢复为默认提示
            self.selected_file_path = ""
            if hasattr(self, "file_path_label"):
                self.file_path_label.configure(text=self.translations["msg_no_file"][self.lang_mode])
            return
        # 👉 就是缺失了下面这一行，导致找不到 key_raw 变量
        key_raw = self.key_entry.get().strip()
        
        # 2. ====== 新增：强制禁止无密钥文件加密 ======
        # 只有在非 Base64 模式下（即真正的 AES 加密模式），才进行拦截
        if not self.standard_mode_var.get():
            if not key_raw:
                # 弹出系统级别的警告框，并终止执行
                self._safe_messagebox(
                    "warning", 
                    ("操作被拒绝", "Operation Denied")[self.lang_mode], 
                    ("安全拦截：\n为了防止文件永久丢失，文件加密模式下【必须】手动输入密钥！\n\n请在上方输入访问密钥后再试。", 
                     "Security Block:\nTo prevent permanent data loss, a secret key is MANDATORY for file encryption!\n\nPlease enter an access key above and try again.")[self.lang_mode]
                )
                return

        def task():
            self._safe_ui_update(self.set_ui_state, "disabled")
            self._safe_ui_update(self.progress.set, 0.2)
            
            try:
                # 2. 读取原始文件 (以二进制形式)
                with open(file_path, "rb") as f:
                    file_data = f.read()
                    
                self._safe_ui_update(self.progress.set, 0.5)

                if self.standard_mode_var.get():
                    # 如果勾选了简单 Base64 模式，将文件转为 Base64 文本并加上 .b64 后缀
                    result_data = base64.b64encode(file_data)
                    out_ext = ".b64"
                else:
                    # 3. 核心 AES-GCM 加密过程
                    key = hashlib.sha256(key_raw.encode('utf-8')).digest()
                    aesgcm = AESGCM(key)
                    nonce = os.urandom(12)
                    ciphertext = aesgcm.encrypt(nonce, file_data, None)
                    
                    # 组合 Nonce 和 密文 (二进制拼接，无需 Base64 编码，节省文件体积)
                    result_data = nonce + ciphertext
                    out_ext = ".aes" # 定义加密后的文件后缀

                self._safe_ui_update(self.progress.set, 0.8)

                # 4. 写入新文件 (原文件名 + 新后缀)
                out_path = file_path + out_ext
                with open(out_path, "wb") as f:
                    f.write(result_data)

                # 5. 更新 UI 输出框 (增加超链接支持)
                self._safe_ui_update(self.progress.set, 1.0)
                
                dir_path = os.path.dirname(os.path.abspath(out_path))
                title_str = ("加密成功", "Success")[self.lang_mode]
                orig_lbl = ("原文件:", "Original File:")[self.lang_mode]
                new_lbl = ("新文件:", "Encrypted File:")[self.lang_mode]
                dir_lbl = ("保存目录:", "Saved Directory:")[self.lang_mode]

                msg_prefix = f"[{title_str}]\n\n" \
                             f"{orig_lbl} {os.path.basename(file_path)}\n" \
                             f"{new_lbl} {os.path.basename(out_path)}\n\n" \
                             f"{dir_lbl} \n"
                             
                msg_suffix = ("\n\n(👆 点击上方路径可直接打开文件夹)", "\n\n(👆 Click the path above to open folder)")[self.lang_mode]

                def update_result():
                    self.result_text.delete("1.0", tk.END)
                    self.result_text.insert(tk.END, msg_prefix)
                    
                    start_index = self.result_text.index("end-1c")
                    self.result_text.insert(tk.END, dir_path)
                    end_index = self.result_text.index("end-1c")
                    
                    self.result_text.insert(tk.END, msg_suffix)
                    self.result_text.tag_add("link", start_index, end_index)
                    self.result_text.tag_config("link", foreground="#38BDF8", underline=True)
                    
                    self.result_text.tag_bind("link", "<Enter>", lambda e: self.result_text.configure(cursor="hand2"))
                    self.result_text.tag_bind("link", "<Leave>", lambda e: self.result_text.configure(cursor="arrow"))
                    
                    def open_directory(event):
                        import subprocess, sys
                        try:
                            if sys.platform == 'win32':
                                subprocess.run(['explorer', '/select,', os.path.normpath(out_path)])
                            elif sys.platform == 'darwin':
                                subprocess.call(["open", "-R", out_path])
                            else:
                                subprocess.call(["xdg-open", dir_path])
                        except Exception as e:
                            print(f"Failed to open directory: {e}")
                                
                    self.result_text.tag_bind("link", "<Button-1>", open_directory)
                    self.result_text.configure(border_color="#22C55E") 
                    
                self._safe_ui_update(update_result)

            except MemoryError:
                self._safe_messagebox("error", "Memory Error", ("文件过大，内存不足！建议处理 500MB 以下的文件。", "File too large, out of memory!")[self.lang_mode])
            except Exception as e:
                self._handle_exception(e, "encrypt_file")
            finally:
                self._safe_ui_update(self.set_ui_state, "normal")

        threading.Thread(target=task, daemon=True).start()

    # ==========================================================
    

    
    # -------------------------------------------------------------------------

    

    def on_mode_switch(self, selected_value):
        """处理 文本/文件 模式切换，动态更替 UI"""
        is_file_mode = selected_value in self.translations["mode_file"]
        m = self.lang_mode
        
        if is_file_mode:
            # 切换到文件模式
            self.input_text.pack_forget()         # 隐藏文本框
            self.paste_btn.pack_forget()          # 隐藏多余的粘贴按钮
            self.file_input_frame.pack(fill="both", expand=True) # 显示文件面板
            self.src_label_obj.configure(text=("待处理的文件", "FILE TO PROCESS")[m])
            # 清空之前的选择
            self.selected_file_path = ""
            self.file_path_label.configure(text=self.translations["msg_no_file"][m])
        else:
            # 切换到文本模式
            self.file_input_frame.pack_forget()   # 隐藏文件面板
            self.input_text.pack(fill="both", expand=True)       # 恢复文本框
            self.paste_btn.pack(side="right")     # 恢复粘贴按钮
            self.src_label_obj.configure(text=self.translations["src_label"][m])
            
        # 同步更新 Toggle 的高亮状态变量
        self.target_mode_var.set(selected_value)

    def create_field_header(self, text, obj_name, has_paste=False):
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(fill="x", padx=55, pady=(5, 2))
        lbl = ctk.CTkLabel(frame, text=text, font=("Microsoft YaHei", 11, "bold"), text_color="#94A3B8")
        lbl.pack(side="left")
        setattr(self, obj_name, lbl)
        if has_paste:
            self.paste_btn = ctk.CTkButton(frame, text=self.translations["btn_paste"][self.lang_mode], width=60, height=20, corner_radius=6, fg_color="#334155", text_color="#38BDF8", font=("Microsoft YaHei", 9, "bold"), hover_color="#475569", command=self.paste_from_clipboard)
            self.paste_btn.pack(side="right")
    
    def decrypt_action(self):
        """这是一个路由函数，根据顶部的 Toggle 决定执行哪种解密"""
        is_file_mode = self.target_mode_var.get() in self.translations["mode_file"]
        
        if is_file_mode:
            self.decrypt_file_action()  # 调用文件解密
        else:
            self.decrypt_text_action()  # 调用文本解密

    def decrypt_text_action(self):
        """处理文本解密的核心逻辑"""
        if self.is_processing: return
        
        # 这里的变量定义在 task 的外层，所以 task 里面的 nonlocal 可以找到它
        key_input = self.key_entry.get().strip()
        cipher_input = self.input_text.get("1.0", tk.END).strip()
        
        if not cipher_input:
            self._safe_messagebox("warning", "Hint", self.translations["msg_input_err"][self.lang_mode])
            return

        def task():
            self._safe_ui_update(self.set_ui_state, "disabled")
            self._safe_ui_update(self.progress.set, 0.3)
            
            nonlocal key_input, cipher_input
            
            try:
                # 处理 AK# 自动密钥
                if cipher_input.startswith("AK#"):
                    self._safe_ui_update(self.standard_mode_var.set, False)
                    self._safe_ui_update(self.refresh_ui_text)
                    parts = cipher_input.split("#", 2)
                    if len(parts) >= 3:
                        key_input = parts[1]
                        cipher_input = parts[2]
                        
                        def update_key_field(k):
                            self.key_entry.delete(0, tk.END)
                            self.key_entry.insert(0, k)
                            self.result_text.configure(border_color="#F59E0B")
                        self._safe_ui_update(update_key_field, key_input)

                result = ""
                if self.standard_mode_var.get():
                    result = base64.b64decode(cipher_input).decode('utf-8')
                else:
                    if not key_input:
                        msg = "解密 AES 密文需要输入密钥" if self.lang_mode==0 else "Key is required"
                        self._safe_messagebox("warning", "Hint", msg)
                        return 

                    key = hashlib.sha256(key_input.encode('utf-8')).digest()
                    
                    try:
                        raw_data = base64.b64decode(cipher_input)
                    except Exception:
                        raise ValueError("Invalid Base64") 

                    if len(raw_data) < 28:
                        raise ValueError("Data too short")

                    nonce, ciphertext = raw_data[:12], raw_data[12:]
                    aesgcm = AESGCM(key)
                    result_bytes = aesgcm.decrypt(nonce, ciphertext, None)
                    result = result_bytes.decode('utf-8')
                
                self._safe_ui_update(self.progress.set, 1.0)
                def update_success(txt):
                    self.result_text.delete("1.0", tk.END)
                    self.result_text.insert(tk.END, txt)
                self._safe_ui_update(update_success, result)

            except Exception as e:
                self._handle_exception(e, "decrypt")
            
            finally:
                self._safe_ui_update(self.set_ui_state, "normal")

        threading.Thread(target=task, daemon=True).start()

    def decrypt_file_action(self):
        """处理文件解密的核心逻辑"""
        if self.is_processing: return
        
        # 1. 鲁棒性验证：是否已选择真实存在的文件
        file_path = getattr(self, "selected_file_path", "").strip()
        if not file_path or not os.path.isfile(file_path):
            title = ("提示", "Hint")[self.lang_mode]
            msg = ("请先点击上方按钮选择一个文件！\n(如果已选择，请确保文件未被移动或删除)", 
                   "Please select a file first!\n(If selected, ensure it hasn't been moved or deleted.)")[self.lang_mode]
            
            # 因为目前在主线程，直接调用原生 messagebox 即可立即阻断
            messagebox.showwarning(title, msg)
            
            # 安全重置：清空失效的路径，并把 UI 标签恢复为默认提示
            self.selected_file_path = ""
            if hasattr(self, "file_path_label"):
                self.file_path_label.configure(text=self.translations["msg_no_file"][self.lang_mode])
            return
        key_raw = self.key_entry.get().strip()
        is_base64_mode = self.standard_mode_var.get()
        # 2. 强制拦截：非 Base64 模式下必须输入密钥
        if not is_base64_mode and not key_raw:
            self._safe_messagebox(
                "warning", 
                ("操作被拒绝", "Operation Denied")[self.lang_mode], 
                ("安全拦截：\n解密 AES 文件必须输入对应的访问密钥！", 
                 "Security Block:\nA secret key is MANDATORY for AES file decryption!")[self.lang_mode]
            )
            return

        def task():
            self._safe_ui_update(self.set_ui_state, "disabled")
            self._safe_ui_update(self.progress.set, 0.2)
            
            try:
                # 3. 读取加密文件 (二进制)
                with open(file_path, "rb") as f:
                    cipher_data = f.read()
                    
                self._safe_ui_update(self.progress.set, 0.4)

                if is_base64_mode:
                    # Base64 解码模式
                    try:
                        # 1. 剔除可能存在的不可见换行符（防止严格模式误拦截）
                        clean_data = cipher_data.replace(b'\r', b'').replace(b'\n', b'')
                        
                        # 2. 必须开启 validate=True，严格拒绝非 Base64 的二进制杂质文件
                        result_data = base64.b64decode(clean_data, validate=True)
                    except Exception:
                        # 3. 关键词修改为包含大写 "Valid Base64"，以便被异常中心精准捕获为"格式错误"
                        raise ValueError("Not Valid Base64 format")
                    
                    # 尝试去除 .b64 后缀
                    if file_path.endswith(".b64"):
                        out_path = file_path[:-4]
                    else:
                        out_path = file_path + ".decoded"
                        
                else:
                    # AES-GCM 解密模式
                    if len(cipher_data) < 28:
                        raise ValueError("Data too short")

                    key = hashlib.sha256(key_raw.encode('utf-8')).digest()
                    aesgcm = AESGCM(key)
                    
                    nonce = cipher_data[:12]
                    ciphertext = cipher_data[12:]
                    
                    self._safe_ui_update(self.progress.set, 0.6)
                    result_data = aesgcm.decrypt(nonce, ciphertext, None)

                    # 尝试去除 .aes 后缀
                    if file_path.endswith(".aes"):
                        out_path = file_path[:-4]
                    else:
                        out_path = file_path + ".decrypted"

                self._safe_ui_update(self.progress.set, 0.8)

                # 4. 防覆盖机制
                if os.path.exists(out_path):
                    base, ext = os.path.splitext(out_path)
                    suffix = "_解密版" if self.lang_mode == 0 else "_decrypted"
                    out_path = f"{base}{suffix}{ext}"

                # 5. 写入还原后的文件
                with open(out_path, "wb") as f:
                    f.write(result_data)

               # 6. 更新 UI 输出 (增加超链接支持)
                self._safe_ui_update(self.progress.set, 1.0)
                
                # 获取文件的绝对目录路径
                dir_path = os.path.dirname(os.path.abspath(out_path))
                
                # 动态获取当前语言的文案
                title_str = ("解密成功", "Success")[self.lang_mode]
                orig_lbl = ("原加密文件:", "Encrypted File:")[self.lang_mode]
                rest_lbl = ("已还原文件:", "Restored File:")[self.lang_mode]
                dir_lbl = ("保存目录:", "Saved Directory:")[self.lang_mode]

                # 将文本拆分为：前缀普通文本、路径文本、后缀普通文本
                msg_prefix = f"[{title_str}]\n\n" \
                             f"{orig_lbl} {os.path.basename(file_path)}\n" \
                             f"{rest_lbl} {os.path.basename(out_path)}\n\n" \
                             f"{dir_lbl} \n"
                             
                msg_suffix = ("\n\n(👆 点击上方路径可直接打开文件夹)", "\n\n(👆 Click the path above to open folder)")[self.lang_mode]

                def update_result():
                    # 1. 清空当前文本框
                    self.result_text.delete("1.0", tk.END)
                    
                    # 2. 插入前缀普通文本
                    self.result_text.insert(tk.END, msg_prefix)
                    
                    # 3. 记录当前光标位置，插入路径文本，并记录插入后的结束位置
                    start_index = self.result_text.index(tk.END + "-1c")
                    self.result_text.insert(tk.END, dir_path)
                    end_index = self.result_text.index(tk.END + "-1c")
                    
                    # 4. 插入后缀普通文本
                    self.result_text.insert(tk.END, msg_suffix)
                    
                    # 5. 为刚刚插入的路径文本添加一个名为 "link" 的 Tag
                    self.result_text.tag_add("link", start_index, end_index)
                    # 配置 "link" 的样式：变蓝、加下划线
                    self.result_text.tag_config("link", foreground="#38BDF8", underline=True)
                    
                    # 6. 绑定鼠标事件：悬停变小手，移开恢复光标
                    self.result_text.tag_bind("link", "<Enter>", lambda e: self.result_text.configure(cursor="hand2"))
                    self.result_text.tag_bind("link", "<Leave>", lambda e: self.result_text.configure(cursor="arrow"))
                    
                   # 7. 绑定点击事件：调用系统资源管理器并【高亮选中】该文件
                    def open_directory(event):
                        import subprocess, sys
                        try:
                            if sys.platform == 'win32':
                                # Windows: 打开资源管理器并选中指定文件
                                # 注意路径需要用 os.path.normpath 规范化，以防斜杠方向不对
                                subprocess.run(['explorer', '/select,', os.path.normpath(out_path)])
                            elif sys.platform == 'darwin':
                                # macOS: 打开 Finder 并选中文件 (-R 参数)
                                subprocess.call(["open", "-R", out_path])
                            else:
                                # Linux: 多数桌面环境没有通用的选中参数，回退到只打开目录
                                subprocess.call(["xdg-open", dir_path])
                        except Exception as e:
                            print(f"Failed to open directory: {e}")
                                
                    self.result_text.tag_bind("link", "<Button-1>", open_directory)

                    # 8. 成功状态绿框提示
                    self.result_text.configure(border_color="#22C55E") 
                    
                self._safe_ui_update(update_result)
                    
                self._safe_ui_update(update_result)

            except MemoryError:
                self._safe_messagebox("error", "Memory Error", ("文件过大，内存不足！建议处理 500MB 以下的文件。", "File too large, out of memory!")[self.lang_mode])
            except Exception as e:
                self._handle_exception(e, "decrypt_file")
            finally:
                self._safe_ui_update(self.set_ui_state, "normal")

        threading.Thread(target=task, daemon=True).start()

        
        
    def toggle_key_visibility(self):
        if self.show_key:
            self.key_entry.configure(show="*")
            self.show_key_btn.configure(text="🙈")
            self.show_key = False
        else:
            self.key_entry.configure(show="")
            self.show_key_btn.configure(text="🐵")
            self.show_key = True

    # -------------------------------------------------------------------------
    # 新增：线程安全辅助方法 (Thread-Safety Helpers)
    # -------------------------------------------------------------------------
    def _safe_ui_update(self, func, *args, **kwargs):
        """线程安全的 UI 更新调度器"""
        self.after(0, lambda: func(*args, **kwargs))
    
    def _safe_messagebox(self, type_, title, message):
        """线程安全的消息弹窗"""
        if type_ == "error":
            self.after(0, lambda: messagebox.showerror(title, message))
        elif type_ == "warning":
            self.after(0, lambda: messagebox.showwarning(title, message))
        elif type_ == "info":
            self.after(0, lambda: messagebox.showinfo(title, message))

    def _handle_exception(self, e, operation="process"):
        """统一的异常分类处理中心"""
        err_msg = str(e)
        title = "Error"
        msg = ""
        
        # 1. Base64 格式错误
        if "Valid Base64" in err_msg or "Incorrect padding" in err_msg or "binascii" in str(type(e)):
             title = "Format Error"
             msg = ("输入内容不是有效的 Base64 格式。\n请检查是否复制完整，或混入了非法字符。", 
                    "Input is not valid Base64.\nPlease check for incomplete copy or invalid characters.")[self.lang_mode]

        # 2. 认证失败 (密钥错误或数据篡改)
        elif "InvalidTag" in err_msg or "decryption failed" in err_msg.lower():
            title = "Authentication Failed"
            msg = ("解密失败：\n1. 密钥不正确\n2. 密文数据已被篡改\nAES-GCM 算法拒绝处理完整性受损的数据。", 
                   "Decryption Failed:\n1. Incorrect Key\n2. Ciphertext tampered\nAES-GCM rejects compromised data.")[self.lang_mode]

        # 3. 随机数/参数长度错误
        elif "nonce" in err_msg.lower() and "length" in err_msg.lower():
            title = "Protocol Error"
            msg = ("数据结构损坏：Nonce 长度必须为 12 字节。\n可能是密文截断或非本软件生成的密文。", 
                   "Data Corrupted: Nonce must be 12 bytes.\nCiphertext might be truncated or incompatible.")[self.lang_mode]

        # 4. 编码问题
        elif "utf-8" in err_msg.lower() or "decode" in err_msg.lower():
            title = "Encoding Error"
            msg = ("解密成功，但还原明文失败。\n原始数据可能不是文本，而是二进制文件或图片。", 
                   "Decrypted successfully, but text decoding failed.\nOriginal data might be binary (image/file), not text.")[self.lang_mode]
        
        # 5. 其他内部错误
        # 5. 其他内部错误 (自定义弹窗带邮箱链接)
        else:
            title = "System Error"
            msg = (f"发生未预期的错误：\n{err_msg}\n请截图并联系开发者：", 
                   f"Unexpected Error:\n{err_msg}\nPlease screenshot and contact the developer:")[self.lang_mode]
            
            def show_custom_error():
                err_win = ctk.CTkToplevel(self)
                err_win.title(title)
                err_win.geometry("500x260")
                err_win.attributes("-topmost", True)
                err_win.resizable(False, False)
                err_win.configure(fg_color="#0F172A")
                
                # 阻止用户与主窗口交互 (模态窗口)
                err_win.grab_set()
                err_win.focus_force()

                # 错误信息文本
                lbl_msg = ctk.CTkLabel(err_win, text=msg, font=("Microsoft YaHei", 13), text_color="#E2E8F0", justify="center")
                lbl_msg.pack(pady=(35, 10))

                # 可点击的邮箱地址
                email_addr = "offers-might-5b@icloud.com"
                lbl_email = ctk.CTkLabel(err_win, text=email_addr, font=("Consolas", 15, "bold", "underline"), text_color="#38BDF8", cursor="hand2")
                lbl_email.pack(pady=(0, 25))

                def open_email(event):
                    import webbrowser
                    webbrowser.open(f"mailto:{email_addr}")
                    # 点击后可选择是否自动关闭报错窗口，这里保留窗口以便用户截图
                    
                lbl_email.bind("<Button-1>", open_email)

                # 关闭按钮
                btn_close = ctk.CTkButton(
                    err_win, text=("关闭", "Close")[self.lang_mode], width=100, height=32, corner_radius=8,
                    fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF", font=("Microsoft YaHei", 12, "bold"),
                    command=lambda: [err_win.grab_release(), err_win.destroy()]
                )
                btn_close.pack(pady=10)

            # 确保 UI 在主线程中生成
            self.after(0, show_custom_error)
            
            # ⚠️ 必须 return，否则程序会继续往下执行触发普通的系统弹窗
            return 
        
        # 只有前面的 1, 2, 3, 4 种常规错误，才会走到这行普通弹窗
        self._safe_messagebox("error", title, msg)

    def show_copyright(self):
        """完全同步移植你提供的声明页逻辑"""
        about_win = ctk.CTkToplevel(self)
        about_win.title("Legal Documentation")
        screen_w = about_win.winfo_screenwidth()
        screen_h = about_win.winfo_screenheight()
        about_win.overrideredirect(True) 
        about_win.geometry(f"{screen_w}x{screen_h}+0+0")
        about_win.attributes("-topmost", True)
        about_win.configure(fg_color="black")
        
        container = tk.Frame(about_win, bg="black")
        container.pack(fill="both", expand=True)

        text_widget = tk.Text(
            container, bg="black", fg="white", font=("Times New Roman", 14),
            padx=100, pady=80, relief="flat", highlightthickness=0, wrap="word", cursor="arrow"
        )
        text_widget.pack(fill="both", expand=True)

        footer_exit_frame = tk.Frame(about_win, bg="black", pady=40)
        footer_exit_frame.pack(side="bottom", fill="x")

        exit_btn_label = tk.Label(
            footer_exit_frame, text="[ PRESS ESC TO EXIT ]", font=("Consolas", 24, "bold"),
            bg="black", fg="#ef4444", cursor="hand2", padx=20, pady=10
        )
        exit_btn_label.pack()

        text_widget.tag_configure("header", font=("Times New Roman", 60, "bold"), justify="center", foreground="#F8FAFC", spacing3=50)
        text_widget.tag_configure("subheader", font=("Times New Roman", 36, "bold"), justify="center", foreground="#CBD5E1", spacing3=40)
        text_widget.tag_configure("body", font=("Times New Roman", 24), justify="left", foreground="#E2E8F0", spacing2=20)
        text_widget.tag_configure("email", font=("Times New Roman", 26, "bold", "underline"), justify="center", foreground="#38BDF8", spacing1=30, spacing3=30)
        text_widget.tag_configure("signature", font=("Times New Roman", 30, "italic"), justify="right", foreground="#94A3B8", spacing1=50)

        text_widget.insert("end", "Copyright and Disclaimer\n", "header")
        text_widget.insert("end", f"Copyright © {time.strftime('%Y')} by z\n", "subheader")
        text_widget.insert("end", "All rights reserved.\n\n", "subheader")
        
        p1 = "This software program, including but not limited to its source code, user interface, functionality, algorithms, and documentation (hereinafter referred to as “the Work”), is an original creation independently completed by the author z.\n\n"
        p2 = "ChatGPT (developed by OpenAI) and Gemini (developed by Google DeepMind) provided auxiliary support during the development process, including suggestions for code structure, formatting, optimization, and user interface design. However, all core programming decisions, logic implementation, algorithm design, and final code content were independently determined and confirmed by the author z.\n\n"
        p3 = "No part of this Work may be reproduced, distributed, transmitted, stored in a retrieval system, or modified in any form or by any means, including electronic, mechanical, or digital methods, without the prior written permission of the author z.\n\n"
        p4 = "The author z bears sole responsibility for the functionality, security, and use of this Work. OpenAI, Google DeepMind, ChatGPT, and Gemini provide no warranty, guarantee, or liability regarding the performance, correctness, security, or appropriateness of this Work.\n\n"
        p5 = "For inquiries regarding copyright, authorization, modification, or any other matters related to this Work, please contact the author at:\n"

        email_addr = "offers-might-5b@icloud.com"
        text_widget.insert("end", p1, "body")
        text_widget.insert("end", p2, "body")
        text_widget.insert("end", p3, "body")
        text_widget.insert("end", p4, "body")
        text_widget.insert("end", p5, "body")
        text_widget.insert("end", f"{email_addr}\n", "email")
        text_widget.insert("end", "—z", "signature")

        text_widget.configure(state="disabled")

        def close_about(e=None):
            about_win.grab_release()
            about_win.destroy()

        def open_email(e=None):
            webbrowser.open(f"mailto:{email_addr}")
            close_about()

        text_widget.tag_bind("email", "<Enter>", lambda e: text_widget.configure(cursor="hand2"))
        text_widget.tag_bind("email", "<Leave>", lambda e: text_widget.configure(cursor="arrow"))
        text_widget.tag_bind("email", "<Button-1>", open_email)
        exit_btn_label.bind("<Enter>", lambda e: exit_btn_label.configure(bg="#ef4444", fg="white"))
        exit_btn_label.bind("<Leave>", lambda e: exit_btn_label.configure(bg="black", fg="#ef4444"))
        exit_btn_label.bind("<Button-1>", close_about)
        about_win.bind("<Escape>", close_about)
        about_win.focus_force()
        about_win.grab_set()

    def refresh_ui_text(self):
        m = self.lang_mode
        if self.standard_mode_var.get():
            self.encode_btn.configure(text=self.translations["btn_encode"][m])
            self.decode_btn.configure(text=self.translations["btn_decode"][m])
            self.key_entry.configure(state="disabled", fg_color="#1E293B")
        else:
            self.encode_btn.configure(text=self.translations["btn_encrypt"][m])
            self.decode_btn.configure(text=self.translations["btn_decrypt"][m])
            self.key_entry.configure(state="normal", fg_color="#0F172A")

    def toggle_language(self):
        self.lang_mode = 1 if self.lang_mode == 0 else 0
        m = self.lang_mode
        
        # 1. 恢复原有的所有 UI 文本更新
        self.title(self.translations["title"][m])
        self.main_title.configure(text=self.translations["title"][m])
        self.sub_title_label.configure(text=self.translations["sub_title"][m])
        self.key_label_obj.configure(text=self.translations["key_label"][m])
        self.src_label_obj.configure(text=self.translations["src_label"][m])
        self.res_label_obj.configure(text=self.translations["res_label"][m])
        self.copy_btn.configure(text=self.translations["btn_copy"][m])
        self.paste_btn.configure(text=self.translations["btn_paste"][m])
        self.about_btn.configure(text=self.translations["btn_about"][m])
        self.clear_btn.configure(text=self.translations["btn_clear"][m])
        self.standard_chk.configure(text=self.translations["chk_standard"][m])
        self.key_entry.configure(placeholder_text=self.translations["ph_key"][m])
        self.lang_btn.configure(text="CN / English" if m == 1 else "EN / 中文")

        # 2. 更新分段按钮的语言 (文本 / 文件 模式)
        current_is_file = self.target_mode_var.get() in self.translations["mode_file"]
        new_values = [self.translations["mode_text"][m], self.translations["mode_file"][m]]
        self.mode_switch.configure(values=new_values)
        self.target_mode_var.set(new_values[1] if current_is_file else new_values[0])
        
        # 如果当前处于文件模式，同步更新文件面板的提示语
        if current_is_file:
            self.src_label_obj.configure(text=("待处理的文件 (Source File)", "FILE TO PROCESS")[m])
            self.select_file_btn.configure(text=self.translations["btn_select_file"][m])
            if not getattr(self, "selected_file_path", ""):
                self.file_path_label.configure(text=self.translations["msg_no_file"][m])

        self.refresh_ui_text()

    def paste_from_clipboard(self):
        try:
            content = self.clipboard_get().strip()
            if content:
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", content)
                old_text = self.translations["btn_paste"][self.lang_mode]
                self.paste_btn.configure(text=self.translations["btn_pasted"][self.lang_mode], text_color="#34D399")
                self.after(1500, lambda: self.paste_btn.configure(text=old_text, text_color="#38BDF8"))
        except: pass

    def copy_result(self):
        content = self.result_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            old_text = self.translations["btn_copy"][self.lang_mode]
            self.copy_btn.configure(text=self.translations["btn_copied"][self.lang_mode], text_color="#34D399", border_color="#34D399")
            self.after(2000, lambda: self.copy_btn.configure(text=old_text, text_color="#CBD5E1", border_color="#475569"))

    def set_ui_state(self, state):
        self.is_processing = (state == "disabled")
        self.encode_btn.configure(state=state)
        self.decode_btn.configure(state=state)
        self.clear_btn.configure(state=state)

    def clear_all(self):
        self.input_text.delete("1.0", tk.END)
        self.result_text.delete("1.0", tk.END)
        self.key_entry.delete(0, tk.END)
        self.progress.set(0)
        self.result_text.configure(border_color="#334155")
        
        # --- 新增：同步清空文件选择状态 ---
        self.selected_file_path = ""
        if hasattr(self, "file_path_label"):
            self.file_path_label.configure(text=self.translations["msg_no_file"][self.lang_mode], text_color="#64748B")

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = AESModernSystem()
    app.mainloop()