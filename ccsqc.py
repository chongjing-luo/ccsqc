# #######################################################################
# # 本代码文件是CCSQC的主程序，用于评分和查看评分结果
# author: chongjing.luo@mail.bnu.edu.cn
# date: 2024-08-27
# #######################################################################
import json, os, re, datetime, glob, subprocess, argparse, shutil, inspect,sys
import pandas as pd
from tkinter import (Tk, Frame, Label, INSERT, IntVar, Button, Entry, filedialog, END, StringVar, OptionMenu, Toplevel,
                     Checkbutton, Text, VERTICAL, Radiobutton, messagebox, Menu, Scrollbar, ttk)
import tkinter as tk
from tkinter.ttk import Treeview
from qc_viewer import QCViewer
from explainremark import RemarkProcessor


class ccsqc:
    def __init__(self, master, projectname, scale=0):

        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.popup_table = None # 弹出的窗口
        self.cansave = True # 是否可以保存评分记录，用来调整右键菜单
        self.scale = scale  # Define the scale factor as a numeric value
        self.current_process = None
        self.codes_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = ""
        self.processor = RemarkProcessor()

        with open(os.path.join(self.codes_dir, 'regions.json'), 'r') as json_file:
            regions_info = json.load(json_file)
            self.regions = regions_info.get("regions", {})
            self.Severity = regions_info.get("Severity", {})
            self.lobes_var_bi = regions_info.get("vars_lobes", [])
            self.lobes_var_ss_bi = regions_info.get("vars_lobes_ss", [])
            self.regions_var_bi = [item for pair in zip([f"l_{region}" for region in self.regions],
                                                        [f"r_{region}" for region in self.regions]) for item in pair]
            self.var_bi = ["OtherNotes"] + self.lobes_var_bi + self.regions_var_bi
            self.vars_lobes_sigle = regions_info.get("vars_lobes_sigle", [])
            self.errortypes = regions_info.get("errortypes", {})

        self.qctype = "summary"
        self.qctypes = ["headmotion", "skullstrip", "reconstruct", "registrate"]

        # 每一个qc页面数据的初始化
        self.CheckDone = IntVar()
        self.NeedMoreCheck = IntVar()
        self.score1 = StringVar()
        self.score2 = StringVar()
        self.NonHeadMotionArtifacts = IntVar()
        self.ss_lobe_error = {lobe: IntVar() for lobe in self.lobes_var_bi}
        self.raters = StringVar()
        self.remarks = ""  # 每个影像文件评分备注的文本内容，实际上基本不使用
        self.remarks_table_dict = {}  # 每个影像文件评分备注的字典内容
        self.ErrorTypes = ''

        # 路径和结果的表格和字典的初始化
        self.list_dict = {qc_type: {"list": [], "dict": {}, "list_dict": {}}
                          for qc_type in ["headmotion", "skullstrip", "reconstruct", "registrate"]}
        self.path_dict = {}  # 初始化数据存储
        self.results_all_dict = {} # 所有的qc结果的初步字典
        self.results_all_table = pd.DataFrame() # 初始化数据存储,存储select and filter后的table
        self.results_all = {}  # 初始化数据存储,存储select and filter后的分层table
        self.results_table_show_long = [] # 用来展示的长表格
        self.results_table_show_wide = [] # 用来展示的宽表格

        self.qctypes_project = {}
        self.dirs = {}
        self.select_filter = {}
        self.qctypes_options = {}

        # tkinter 初始化
        self.remarks_tk = None
        self.tk_dirs = {
            "output_dir": {"label": "OUTPUT_DIR", "path": None},
            "bids_dir": {"label": "BIDS_DIR", "path": None},
            "ccs_dir": {"label": "CCS_DIR", "path": None},
            "subject_dir": {"label": "SUBJECT_DIR", "path": None},
            "mriqc_dir": {"label": "MRIQC_DIR", "path": None},
            "list_dir": {"label": "LIST_DIR", "path": None}
        }
        self.tkparts = {qc_type: {key: None for key in
                                  ["rater_entry", "summary_incld", "presentdirtype", "presentviewer",
                                   "raters_selection", "presentMergeMethod"]}
                        for qc_type in ["headmotion", "skullstrip", "reconstruct", "registrate"]}

        self.display_projects_and_create_new(projectname)
        self.save_load_result_dict(operation="load")
        self.create_initial_widgets()

    def display_projects_and_create_new(self, projectname):
        # Display existing projects
        path_proj = os.path.join(self.codes_dir, "projects.json")
        if os.path.exists(path_proj):
            with open(path_proj, 'r') as f:
                projects = json.load(f)
                self.projects = projects.get("projects", {})

        self.projectname = projectname
        self.settings_path = self.projects.get(projectname, "")
        print(f"**Project name: {projectname}, settings path: {self.settings_path}")

        with open(self.settings_path, 'r') as f:
            settings = json.load(f)
            self.qctypes_project = settings.get("qctypes_project", {})
            self.dirs = settings.get("dirs", {})
            self.select_filter = settings.get("select_filter", {})
            self.qctypes_options = settings.get("qctypes_options", {})

        self.dirs["output_dir"] = {"path": os.path.dirname(self.settings_path)}

        with open(path_proj, 'w') as f:
            json.dump({"projects": self.projects, "last_project": projectname}, f, indent=4)

    def on_closing(self):
        """关闭整个软件时执行"""
        if messagebox.askokcancel("Quit", "Do You Want to Quit?"):
            self.master.destroy()
            self.backup()
            self.save_load_result_dict(["qc_types", "settings", "results_all_dict", "results_all_table", "path_dict"], "save")
            self.master.quit()

    def create_initial_widgets(self):
        self.clear_frame()
        self.master.title("CCSQC")
        self.master.geometry("520x750")
        self.qctype = 'summary'

        # initial_widgets：path of folder and list
        frame_upper = Frame(self.master)
        frame_upper.place(x=0, y=0, width=520, height=190)

        # 一、初始化页面的第一部分：收集项目的路径tkinter entry: set path of each dir or list /
        for i, (dir_type, details) in enumerate(self.tk_dirs.items()):
            # (1) 标签
            Label(frame_upper, text=f"{self.tk_dirs[dir_type]['label']}: ", font=("Arial", 8 + self.scale),
                  width=13, height=1, anchor="center").place(x=10, y=10 + 30 * i)

            # (2) 获得每个dir的路径
            details["path"] = StringVar(value=self.dirs[dir_type]["path"])

            # (3) 输入框
            entry = Entry(frame_upper, font=("Arial", 9 + self.scale), textvariable=details["path"])
            entry.place(x=90, y=10 + 30 * i, width=330, height=20)

            # (4) 当details["path"]变化时，更新self.dirs[dir_type]["path"]
            details["path"].trace("w", lambda *args, sv=details["path"],
                                              dt=dir_type: self.dirs.__setitem__(dt, {"path": sv.get()}))

            # (5) 按钮
            Button(frame_upper, text="Browse", command=lambda dt=dir_type: self.operate_init("BrowseDir", dt),
                   font=("Arial", 8 + self.scale)).place(x=430, y=10 + 30 * i, width=80, height=22)


        # 二、初始化页面的第二部分：设置每种qc的dir和iewer / initial_widgets: dir type and viewer of each qctype
        frame_qc = Frame(self.master)
        frame_qc.place(x=0, y=195, width=520, height=120)
        Label(frame_qc, text="DIR type: ", font=("Arial", 10 + self.scale)).place(x=10, y=30)
        Label(frame_qc, text="Viewer: ", font=("Arial", 10 + self.scale)).place(x=10, y=60)

        for i, (qc_type, qc_details) in enumerate(self.qctypes_options.items()):
            x_posi = 100 + i * 105
            Label(frame_qc, text=qc_details["label"], font=("Arial",9+self.scale)).place(x=x_posi, y=10)

            # 为每个 qc_type 设置dirtype，存储在self.qctypes_project[qc_type]["presentdirtype"]
            dirtype_var = StringVar(value=self.qctypes_project[qc_type]["presentdirtype"])
            dirtype_var.trace("w", lambda *args, sv=dirtype_var,
                                          qt=qc_type: self.qctypes_project[qt].__setitem__("presentdirtype", sv.get()))

            option_menu_dirtype = OptionMenu(frame_qc, dirtype_var, *qc_details["dirtype"])
            option_menu_dirtype.config(font=("Arial", 9 + self.scale))
            option_menu_dirtype["menu"].config(font=("Arial", 9 + self.scale))
            option_menu_dirtype.place(x=x_posi, y=30, width=100, height=30)

            # 为每个 qc_type 设置viewer,存储在self.qctypes_project[qc_type]["presentviewer"]
            viewer_var = StringVar(value=self.qctypes_project[qc_type]["presentviewer"])
            option_menu_viewer = OptionMenu(frame_qc, viewer_var, *qc_details["viewer"])
            viewer_var.trace("w", lambda *args, sv=viewer_var,
                                         qt=qc_type: self.qctypes_project[qt].__setitem__("presentviewer", sv.get()))

            option_menu_viewer.config(font=("Arial", 9 + self.scale))
            option_menu_viewer["menu"].config(font=("Arial", 9 + self.scale))
            option_menu_viewer.place(x=x_posi, y=60, width=100, height=30)

            # 启动特定qc的按钮
            Button(frame_qc, text="Start QC", command=lambda qt=qc_type: self.operate_init("StartQC", qt),
                   font=("Arial", 10 + self.scale)).place(x=x_posi, y=90, width=100, height=30)

        # 三、初始化页面的第三部分：summary包括哪些qc_type，以及每个qc_type的rater和合并方法
        frame_rater = Frame(self.master)
        frame_rater.place(x=0, y=350, width=520, height=90)

        Label(frame_rater, text="Results:", font=("Arial", 12 + self.scale)).place(x=0, y=0, width=90, height=20)
        Label(frame_rater, text="RatersSelection:", font=("Arial", 9 + self.scale)).place(x=2, y=30, width=100, height=20)
        Label(frame_rater, text="MergeMethod:", font=("Arial", 9 + self.scale)).place(x=2, y=55, width=100, height=20)

        for i, qc_type in enumerate(self.qctypes):
            qc_x_position = 102 + i * 105
            qc_details = self.qctypes_project[qc_type]

            # (1) 为每个 qc_type 设置summary_incld，使其是否包含在summary中
            summary_incld = IntVar(value=self.select_filter['summary']["summary_incld"][qc_type])
            Checkbutton(frame_rater, text=f"{self.qctypes_options[qc_type]['label']}", font=("Arial", 8 + self.scale),
                        variable=summary_incld).place(x=qc_x_position, y=0)
            summary_incld.trace("w", lambda *args, sv=summary_incld,
                                            qt=qc_type: self.select_filter['summary']["summary_incld"].__setitem__(qt, sv.get()))

            # (2) 为每个 qc_type 设置raters_selection，设置包含哪些rater
            raters_selection = StringVar(value=self.select_filter['summary']["raters_selection"][qc_type])
            raters_selection.trace("w", lambda *args, sv=raters_selection, qt=qc_type: self.select_filter['summary'][
                "raters_selection"].__setitem__(qt, sv.get()))
            entry_Rater = Entry(frame_rater, font=("Arial", 8 + self.scale), textvariable=raters_selection)
            entry_Rater.place(x=qc_x_position + 5, y=30, width=90, height=20)

            # (3) 为每个 qc_type 设置presentMergeMethod（合并方法）
            presentMergeMethod = StringVar(value=self.select_filter['summary']["presentMergeMethod"][qc_type])
            tk_merge_method = OptionMenu(frame_rater, presentMergeMethod, *self.select_filter['summary']["mergeoptions"])
            tk_merge_method.place(x=qc_x_position, y=55, width=100, height=30)
            tk_merge_method["menu"].config(font=("Arial", 9 + self.scale))
            presentMergeMethod.trace("w", lambda *args, sv=presentMergeMethod,
                                                 qt=qc_type: self.select_filter['summary']["presentMergeMethod"].__setitem__(qt, sv.get()))

        # Showbox and buttons
        frame_show_and_buttons = Frame(self.master)
        frame_show_and_buttons.place(x=0, y=440, width=520, height=300)

        # 初始化界面的第四部分：展示summary的结果
        frame_showbox = Frame(frame_show_and_buttons)
        frame_showbox.place(x=10, y=0, width=370, height=300)

        # 创建Treeview小部件并放置在Frame中
        self.showbox = Treeview(frame_showbox, columns=("Column1"), show='')
        self.showbox.column("Column1", width=1500, minwidth=150)

        vsb = Scrollbar(frame_showbox, orient="vertical", command=self.showbox.yview)
        hsb = Scrollbar(frame_showbox, orient="horizontal", command=self.showbox.xview)
        self.showbox.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.showbox.pack(expand=True, fill="both")

        # 初始化界面的第五部分：summary的按钮，
        frame_summary = Frame(frame_show_and_buttons)
        frame_summary.place(x=380, y=0, width=120, height=300)
        Button(frame_summary, text="Get the list", command=lambda: self.operate_init("getthelist"),
               font=("Arial", 10 + self.scale)).place(x=5, y=10, width=115, height=40)
        Button(frame_summary, text="Select and Filter", command=lambda: self.operate_init("selectandfilter"),
               font=("Arial", 10 + self.scale)).place(x=5, y=60, width=115, height=40)
        Button(frame_summary, text="Show the table", command=lambda: self.operate_init("showthetable"),
               font=("Arial", 10 + self.scale)).place(x=5, y=110, width=115, height=40)
        Button(frame_summary, text="Table transform", command=lambda: self.operate_init("tabletrans"),
               font=("Arial", 10 + self.scale)).place(x=5, y=160, width=115, height=40)
        Button(frame_summary, text="Save the table", command=lambda: self.operate_init("savethetable"),
               font=("Arial", 10 + self.scale)).place(x=5, y=210, width=115, height=40)
        Button(frame_summary, text="Summary", command=lambda: self.operate_init("summary"),
               font=("Arial", 10 + self.scale)).place(x=5, y=260, width=115, height=40)

        content = self.select_filter['summary']["select_filter_explained"]
        self.display_content(content,'init')

    def create_specific_widgets(self, qc_type, imgid=None, rater=None, cansave=True):
        """设置4个qc页面的评分页面（相同代码部分）"""

        self.clear_frame()
        self.qctype = qc_type

        # 设置每个qc页面的大小和标题
        if qc_type == "headmotion":
            self.master.geometry("520x500")
            self.master.title("Head motion and Image Error")
        elif qc_type == "skullstrip":
            self.master.geometry("520x700")
            self.master.title("Skull Striping")
        elif qc_type == "reconstruct":
            self.master.geometry("520x720")
            self.master.title("Surface Reconstruction")
        elif qc_type == "registrate":
            self.master.geometry("520x500")
            self.master.title("T1w and T2w image Registrate")

        frame_top = Frame(self.master)
        frame_top.place(x=10, y=5, width=500, height=40)

        # ###################      第一部分：顶部按钮和rater输入框        ###################
        # 1.1 返回初始页面，重新选择qc_type
        Button(frame_top, text="reSelect QC Type", command=lambda:self.operate_qc("reselectQCType", qc_type),
               font=("Arial", 9 + self.scale)).place(x=10, y=5, width=100, height=30)

        # 1.2 选择和过滤
        Button(frame_top, text="Select and Filter", command=lambda: self.operate_qc("selectandfilter", qc_type),
               font=("Arial", 9 + self.scale)).place(x=115, y=5, width=110, height=30)

        # 1.3 设置rater
        Label(frame_top, text="Rater:", font=("Arial", 10 + self.scale)).place(x=230, y=5, width=35, height=30)
        rater_entry = StringVar(value=self.qctypes_project[qc_type]["rater"])
        tk_entry_rater = Entry(frame_top, width=12, font=("Arial", 10 + self.scale), textvariable=rater_entry)
        tk_entry_rater.place(x=270, y=8, width=80, height=25)
        rater_entry.trace("w", lambda *args, sv=rater_entry,
                                      qt=qc_type: self.qctypes_project[qt].__setitem__("rater", sv.get()))
        # 1.4 刷新list
        Button(frame_top, text="Refresh", command=lambda: self.operate_qc("refresh", qc_type),
               font=("Arial", 10 + self.scale)).place(x=360, y=5, width=70, height=30)

        # 第二部分：中间的listbox
        frame_middle = Frame(self.master)
        frame_middle.place(x=10, y=50, width=500, height=300)

        style = ttk.Style()
        style.configure("Treeview", font=("Arial", 10))
        self.listbox = Treeview(frame_middle, columns=("index", "imgid", "score1", "isdone"), show='',
                                selectmode='browse')
        self.listbox.column("index", width=35, minwidth=35, anchor="e")
        self.listbox.column("imgid", width=220, minwidth=220, anchor="e")
        self.listbox.column("score1", width=30, minwidth=30, anchor="center")
        self.listbox.column("isdone", width=60, minwidth=60, anchor="w")

        scrollbar = Scrollbar(frame_middle)
        scrollbar.grid(row=0, column=1, rowspan=2, sticky='ns')
        scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.grid(row=0, column=0, padx=(0, 10), pady=11)

        # 左键切换到某张图片
        self.listbox.bind('<Double-Button-1>', lambda event: self.operate_qc("navigate_subject", qc_type, 0))
        # 右键菜单，弹出选项
        self.right_click_menu = Menu(self.master, tearoff=0)
        self.listbox.bind("<Button-3>", lambda event: self.show_right_click_menu(self.listbox, event, qc_type))

        # 第三部分：底部的按钮
        frame_buttons = Frame(frame_middle)
        frame_buttons.place(x=370, y=0, width=125, height=230)

        Button(frame_buttons, text="Previous", command=lambda: self.operate_qc("navigate_subject", qc_type, -1),
               font=("Arial", 10 + self.scale)).place(x=0, y=0, width=125, height=40)
        Button(frame_buttons, text="SaveRating", command=lambda: self.operate_qc("save_rating", qc_type),
               font=("Arial", 10 + self.scale)).place(x=0, y=45, width=125, height=40)
        Button(frame_buttons, text="SaveAndNext", command=lambda: self.operate_qc("navigate_subject", qc_type, 1),
               font=("Arial", 10 + self.scale)).place(x=0, y=90, width=125, height=40)

        Checkbutton(frame_buttons, text="Check Done", variable=self.CheckDone, anchor="w",
                    font=("Arial", 10 + self.scale), height=3).place(x=0, y=145, width=125, height=30)
        Checkbutton(frame_buttons, text="NeedMoreCheck", variable=self.NeedMoreCheck, anchor="w",
                    font=("Arial", 10 + self.scale), height=3).place(x=0, y=180, width=125, height=30)

        frame_qcscore = Frame(self.master)
        frame_qcscore.place(x=10, y=270, width=500, height=100)

        Label(frame_qcscore, text=f"{self.qctypes_options[qc_type]['namescore1']}", font=("Arial",10 + self.scale)).place(
            x=5, y=10)
        num_score1 = self.qctypes_options[qc_type]["numscore1"]
        score1_width = (505 - 125) // num_score1 - 5
        for i in range(num_score1):
            Radiobutton(frame_qcscore, text=str(i), variable=self.score1, font=("Arial", 10+self.scale), indicatoron=0,
                        value=str(i)).place(x=120 + i * (5 + score1_width), y=5, width=score1_width, height=40)

        Label(frame_qcscore, text=f"{self.qctypes_options[qc_type]['namescore2']}",
              font=("Arial",10 + self.scale)).place(x=5, y=50, height=30)
        num_score2 = self.qctypes_options[qc_type]["numscore2"]
        score2_width = (505 - 125) // num_score2 - 5
        for i in range(num_score2):
            Radiobutton(frame_qcscore, text=str(i), variable=self.score2, font=("Arial", 10+self.scale), indicatoron=0,
                        value=str(i)).place(x=120 + i * (score2_width + 5), y=50, width=score2_width, height=30)

        self.create_specific_lobe_region_widgets(qc_type, imgid,  rater, cansave)

    def create_specific_lobe_region_widgets(self, qc_type, imgid,  rater, cansave):
        if qc_type == "headmotion":
            frame_tags = Frame(self.master)
            frame_tags.place(x=160, y=350, width=500, height=40)

            Checkbutton(frame_tags, text="Non-head motion artifacts", variable=self.NonHeadMotionArtifacts,
                        font=("Arial", 12+self.scale), width=20, height=2).grid(row=0, column=0, pady=3, sticky="w")

            frame_remarks = Frame(self.master)
            frame_remarks.place(x=10, y=400, width=500, height=80)
            Label(frame_remarks, text="Notes:", font=("Arial", 12+self.scale)).place(x=10, y=0, width=80, height=30)
            self.remarks_tk = Text(frame_remarks, font=("Arial", 10+self.scale))
            self.remarks_tk.place(x=100, y=0, width=400, height=80)

            scrollbar = Scrollbar(frame_remarks, orient=VERTICAL, command=self.remarks_tk.yview)
            scrollbar.place(x=480, y=0, width=20, height=80)
            self.remarks_tk.config(yscrollcommand=scrollbar.set)

        elif qc_type == "skullstrip":
            frame_input = Frame(self.master)
            frame_input.place(x=0, y=350, width=520, height=100)

            Label(frame_input, text="Location with Error",
                  font=("Arial", 12 + self.scale)).place(x=0, y=10, width=210,height=20)
            self.remarks_tk = Text(frame_input, font=("Arial", 10 + self.scale), height=30)
            self.remarks_tk.place(x=10, y=33, width=270, height=50)

            self.error_oper = ["Explain", "Delete", "OtherNotes", "Clear"]
            for i, oper in enumerate(self.error_oper):
                button = Button(frame_input, text=oper, font=("Arial", 10 + self.scale))
                button.config(command=lambda qt=qc_type, op=oper: self.operate_qc("error_oper", qt, op))
                button.place(x=290 + (i % 2) * 110, y=12 + (i // 2) * 35, width=100, height=33)

            # 严重程度和错误类型按钮
            frame_SevErr = Frame(self.master)
            frame_SevErr.place(x=0, y=440, width=500, height=100)
            for i, sev in enumerate(self.Severity + ["OverStrip", "UnderStrip", ";"]):
                button = Button(frame_SevErr, text=f"{sev}", font=("Arial", 10 + self.scale))
                button.config(command=lambda s=sev: self.operate_qc("error_option", s))
                button.place(x=10 + i * 82, y=2, width=75, height=33)

            # 脑叶按钮
            frame_tags = Frame(self.master)
            frame_tags.place(x=0, y=475, width=240, height=300)
            for i, lobe in enumerate(self.lobes_var_ss_bi):
                column = 0 if 'l_' in lobe else 1
                button = Button(frame_tags, text=lobe, font=("Arial", 10 + self.scale))
                button.config(command=lambda l=lobe: self.operate_qc("error_option", l))
                button.place(x=15 + 100 * column, y=10 + 40 * (i // 2), width=90, height=35)

            # 问题解释后的结果框
            frame_table = Frame(self.master)
            frame_table.place(x=220, y=485, width=300, height=200)
            columns = ["Location", "Problem"]
            self.tree = Treeview(frame_table, columns=columns, show="headings")
            for col in columns:
                self.tree.heading(col, text=col)

            self.tree.column("Location", width=70)
            self.tree.column("Problem", width=200)

            vsb = Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
            hsb = Scrollbar(frame_table, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            self.tree.grid(row=0, column=0, sticky='nsew')
            vsb.grid(row=0, column=1, sticky='ns')
            hsb.grid(row=1, column=0, sticky='ew')

            frame_table.grid_columnconfigure(0, weight=1)
            frame_table.grid_rowconfigure(0, weight=1)

        elif qc_type == "reconstruct":
            # 输入框
            frame_input = Frame(self.master)
            frame_input.place(x=0, y=350, width=520, height=250)
            label = Label(frame_input, text="Location with Error:", font=("Arial", 14+self.scale))
            label.place(x=300, y=10, width=210, height=30)
            self.remarks_tk = Text(frame_input, font=("Arial", 10+self.scale), height=3)
            self.remarks_tk.place(x=10, y=15, width=300, height=50)

            # 解释，删除，其他备注，清除按钮
            self.error_oper = ["Explain", "Delete", "OtherNotes", "Clear"]
            for i, oper in enumerate(self.error_oper):
                button = Button(frame_input, text=oper, font=("Arial", 10+self.scale))
                button.config(command=lambda qt=qc_type, op=oper: self.operate_qc("error_oper", qt, op))
                button.place(x=320 + (i % 2) * 95, y=40 + (i // 2) * 35, width=90, height=30)

            # 为每个 reconstruct 设置severity按钮
            for i, sev in enumerate(["L", "R"]+self.Severity):
                button = Button(frame_input, text=f"{sev}", font=("Arial", 10+self.scale))
                button.config(command=lambda s=sev: self.operate_qc("error_option", s))
                button.place(x=10 + 62 * i, y=70, width=58, height=35)

            # region and lobe 按钮
            frame_main = Frame(self.master)
            frame_main.place(x=10, y=460, width=500, height=250)
            for region_name, region_info in self.regions.items():
                lobe = region_info["lobe"]
                color = region_info["color"]
                pos = region_info["position"]
                button = Button(frame_main, text=region_name, font=("Arial", 10 + self.scale), **{"foreground": "white"}, bg=color)
                button.config(command=lambda rn=region_name: self.operate_qc("error_option", rn))
                button.place(x=pos[1] * 38, y=pos[0] * 36, width=34, height=33)

            # lobe 按钮
            for i, lobe_name in enumerate([";"] + self.vars_lobes_sigle):
                button = Button(frame_main, text=lobe_name, font=("Arial", 8 + self.scale))
                button.config(command=lambda ln=lobe_name: self.operate_qc("error_option", ln))
                button.place(x=190, y=i * 36, width=60, height=35)

            # 错误类型按钮
            for i, errortype in enumerate(self.errortypes):
                button = Button(frame_main, text=errortype, font=("Arial", 8 + self.scale))
                button.config(command=lambda et=errortype: self.operate_qc("error_option", et))
                button.place(x=255 + (i % 3) * 80, y=(i // 3) * 36, width=75, height=35)

            # 问题解释后的结果框
            frame_table = Frame(frame_main)
            frame_table.place(x=255, y=75, width=260, height=180)
            columns = ["Location", "Problem"]
            self.tree = Treeview(frame_table, columns=columns, show="headings")
            for col in columns:
                self.tree.heading(col, text=col)

            self.tree.column("Location", width=70)
            self.tree.column("Problem", width=220)

            vsb = Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
            hsb = Scrollbar(frame_table, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            self.tree.grid(row=0, column=0, sticky='nsew')
            vsb.grid(row=0, column=1, sticky='ns')
            hsb.grid(row=1, column=0, sticky='ew')

            frame_table.grid_columnconfigure(0, weight=1)
            frame_table.grid_rowconfigure(0, weight=1)

        elif qc_type == "registrate":
            frame_remarks = Frame(self.master)
            frame_remarks.place(x=10, y=380, width=500, height=100)
            Label(frame_remarks, text="Notes:", font=("Arial", 12+self.scale)).place(x=10, y=0, width=80, height=30)
            self.remarks_tk = Text(frame_remarks, font=("Arial", 10+self.scale))
            self.remarks_tk.place(x=100, y=0, width=380, height=100)

            scrollbar = Scrollbar(frame_remarks, orient=VERTICAL, command=self.remarks_tk.yview)
            scrollbar.place(x=480, y=0, width=20, height=100)
            self.remarks_tk.config(yscrollcommand=scrollbar.set)

        # 获取当前的imgid，如果没有则根据list_dict的index为0进行设置
        if imgid is None:
            imgid = self.qctypes_project[qc_type]["imgid"]
            if imgid not in self.list_dict[qc_type]["list_dict"]:
                imgid = self.getDictValue(self.list_dict[qc_type]["list_dict"], 0, "index")
                print(f"**Imgid not in list_dict, set to the first one: {imgid}")
        if rater is None:
            rater = self.qctypes_project[qc_type]["rater"]

        self.qctypes_project[qc_type]["imgid"] = imgid
        self.show_present_list(qc_type, self.list_dict[qc_type]["list_dict"])
        self.save_load_rating("load", qc_type, rater, imgid)
        self.cansave = cansave

    def open_settings_popup(self, popup_type):
        popup = Toplevel(self.master)
        popup.title("Settings")
        popup.geometry("600x850")

        # 选择和过滤的输入框
        Label(popup, text="Select and filter:", font=("Arial", 11+self.scale)).place(x=10, y=10)
        self.selection_filter = Text(popup, font=("Arial", 9+self.scale), height=10)

        self.selection_filter.place(x=120, y=10, width=450, height=80)
        vsb = Scrollbar(popup, orient="vertical", command=self.selection_filter.yview)
        vsb.place(x=570, y=10, width=15, height=80)
        self.selection_filter.config(yscrollcommand=vsb.set)

        print(f"{inspect.currentframe().f_lineno} self.select_filter[popup_type] : {self.select_filter[popup_type]}")
        filter_text = self.select_filter[popup_type]["select_filter_text"]
        self.selection_filter.delete("1.0", END)  # Clear existing content
        self.selection_filter.insert("1.0", filter_text)

        # 选择和过滤后的结果
        Label(popup, text="Explained:", font=("Arial", 11+self.scale)).place(x=10, y=100)
        frame_showbox = Frame(popup)
        frame_showbox.place(x=120, y=100, width=460, height=200)

        self.showbox_select = Treeview(frame_showbox, columns=("Column1"), show='')
        self.showbox_select.column("Column1", width=1500, minwidth=150)

        vsb = Scrollbar(frame_showbox, orient="vertical", command=self.showbox_select.yview)
        hsb = Scrollbar(frame_showbox, orient="horizontal", command=self.showbox_select.xview)
        self.showbox_select.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.showbox_select.pack(expand=True, fill="both")

        frame_confer = Frame(popup)
        frame_confer.place(x=0, y=300, width=580, height=40)
        xposition = 10
        self.oper_selec_filt = ["SelectVar", "FilterPoint", "Enter", "Explain", "Delete", "Clear", "Help"]
        for i, oper in enumerate(self.oper_selec_filt):
            button = Button(frame_confer, text=oper, font=("Arial", 10+self.scale))
            button.config(command=lambda op=oper, qt=popup_type: self.select_and_filter("select_filt", op, qt))
            wid = 85 if oper in ["SelectVar", "FilterPoint"] else 70
            button.place(x=xposition, y=5, width=wid, height=30)
            xposition += wid + 5

        frame_var = Frame(popup)
        frame_var.place(x=0, y=340, width=600, height=150)

        var_buttons = ["qc_types"] + list(self.qctypes_project.keys()) + ["Key", "IndexAll", "QCType", "Imgid", "Subid", "Rater", "Regions", "Lobes",
                                                                  "ErrorTypes", "Score1", "Score1F", "Score2", "Score2F", "0", "1", "2", "3", "4"]
        for i, button_text in enumerate(var_buttons):
            button = Button(frame_var, text=button_text, font=("Arial", 10 + self.scale))
            button.config(command=lambda bt=button_text: self.select_and_filter("words", bt))
            if button_text in ["0", "1", "2", "3", "4"]:
                button.place(x=340 + int(button_text)*50, y=74, width=45, height=30)
            else:
                button.place(x=20+(i % 7) * 80, y=10+(i // 7) * 32, width=75, height=30)

        var_buttons2 = ["OtherVars","Remark", "CheckDone","NeedMoreCheck","NonHeadMotionArtifacts"]
        xp = 105
        for i, button_text in enumerate(var_buttons2):
            button = Button(frame_var, text=button_text, font=("Arial", 10 + self.scale))
            button.config(command=lambda bt=button_text: self.select_and_filter("words", bt))
            if button_text == "OtherVars":
                button.place(x=10, y=108, width=80, height=30)
            else:
                wid = 80+25*(i-1)
                button.place(x=xp, y=108, width=wid, height=30)
                xp = wid + xp + 5

        frame_compt = Frame(popup)
        frame_compt.place(x=0, y=490, width=600, height=80)
        compt_buttons = ["==", "!=", ">", "<", ">=", "<=", "include", "in", ':', '>>',
                         "AND", "OR", "NOT", ',', "[", "]", "(", ")",'{', '}']
        for i, button_text in enumerate(compt_buttons):
            button = Button(frame_compt, text=button_text, font=("Arial", 10 + self.scale))
            button.config(command=lambda bt=button_text: self.select_and_filter("words", bt))
            button.place(x=5+(i % 10) * 59, y=5+(i // 10) * 32, width=56, height=30)

        frame_input=Frame(popup)
        frame_input.place(x=0, y=560, width=600, height=40)
        # 为每个 reconstruct 设置severity按钮
        for i, errortype in enumerate(["OverStrip", "UnderStrip"] + self.errortypes):
            button = Button(frame_input, text=errortype, font=("Arial", 8 + self.scale))
            button.config(command=lambda et=errortype: self.select_and_filter("words", et))
            button.place(x=5+i*74, y=5, width=70, height=35)

        # region and lobe 按钮
        frame_main = Frame(popup)
        frame_main.place(x=5, y=600, width=600, height=250)
        for region_name, region_info in self.regions.items():
            color = region_info["color"]
            pos = region_info["position"]
            button = Button(frame_main, text=f"l_{region_name}", font=("Arial", 10 + self.scale), **{"foreground": "white"}, bg=color)
            button.config(command=lambda rn=f"l_{region_name}": self.select_and_filter("words", rn))
            button.place(x=pos[1] * 44, y=10+pos[0] * 32, width=42, height=30)
            button = Button(frame_main, text=f"r_{region_name}", font=("Arial", 10 + self.scale), **{"foreground": "white"}, bg=color)
            button.config(command=lambda rn=f"r_{region_name}": self.select_and_filter("words", rn))
            button.place(x=110+(10-pos[1]) * 44, y=10+pos[0] * 32, width=42, height=30)

        # lobe 按钮
        for i, lobe_name in enumerate(self.vars_lobes_sigle):
            button = Button(frame_main, text=f"l_{lobe_name}", font=("Arial", 8 + self.scale))
            button.config(command=lambda ln=f"l_{lobe_name}": self.select_and_filter("words", ln))
            button.place(x=222, y=10+32 + i * 32, width=73, height=30)
            button = Button(frame_main, text=f"l_{lobe_name}", font=("Arial", 8 + self.scale))
            button.config(command=lambda ln=f"l_{lobe_name}": self.select_and_filter("words", ln))
            button.place(x=297, y=10+32 + i * 32, width=73, height=30)

        # 错误类型按钮
        for i, errortype in enumerate(self.Severity):
            button = Button(frame_main, text=errortype, font=("Arial", 8 + self.scale))
            button.config(command=lambda et=errortype: self.select_and_filter("words", et))
            button.place(x=222 + i * 50, y=2, width=47, height=35)


    def show_right_click_menu(self, listbox, event, qc_type_summary):
        def cancel_right_click_menu(event=None):
            # 取消右键菜单
            if hasattr(self, 'right_click_menu'):
                self.right_click_menu.unpost()

            # 解除主窗口上的绑定
            if hasattr(self, 'cancel_id') and self.cancel_id is not None:
                self.master.unbind("<Button-1>", self.cancel_id)
                self.cancel_id = None

            # 如果popup_table存在，解除绑定
            if hasattr(self, 'popup_table') and hasattr(self, 'popup_cancel_id'):
                try:
                    if self.popup_table.winfo_exists():
                        self.popup_table.unbind("<Button-1>", self.popup_cancel_id)
                        self.popup_cancel_id = None
                    else:
                        print("popup_table 已经被销毁，无法解绑。")
                except tk.TclError as e:
                    print(f"Warning: {e}")

        def on_popup_table_destroy(event=None):
            # 当popup_table被销毁时取消右键菜单
            cancel_right_click_menu()

        # 确保菜单对象已创建
        if not hasattr(self, 'right_click_menu'):
            self.right_click_menu = Menu(self.master, tearoff=0)

        # 获取右键选中项目的imgid
        item = listbox.identify_row(event.y)
        if item:
            selected_item = listbox.item(item, "values")
            if qc_type_summary == "summary":
                imgid = selected_item[self.Imgid_index]
            else:
                imgid = selected_item[1]

            print(f"** Right clicked on imgid: -{imgid}-")
            qctypes2show = [key for key in self.qctypes_options.keys() if key != "qc_type"]

            # 删除当前imgid的所有 {qc_type}_{rater} 项
            result_dict_imgid = self.results_all_dict.get(imgid, {})
            if qc_type_summary in self.qctypes_options:
                rater = self.qctypes_project[qc_type_summary]["rater"]
                key_to_exclude = f"{qc_type_summary}_{rater}"
                if key_to_exclude in result_dict_imgid:
                    del result_dict_imgid[key_to_exclude]

            # 清空并重新填充菜单项
            if self.right_click_menu:
                self.right_click_menu.delete(0, END)
            try:
                # 获取鼠标点击位置的索引
                item = listbox.identify_row(event.y)
                if item:
                    listbox.selection_set(item)

                    # 动态添加菜单项，标签为 "open image of {label}"
                    for key in qctypes2show:
                        label = self.qctypes_options[key].get("label", "No label")
                        self.right_click_menu.add_command(
                            label=f"Open image of {label}",
                            command=lambda q=key, i=imgid: self.operate_qc("openimg", q, i)
                        )
                    for ratings in result_dict_imgid:
                        listshow = self.results_all_dict[imgid][ratings]["listshow"]
                        qc_type, rater = ratings.split("_")
                        self.right_click_menu.add_command(
                            label=f"Open rating results of {ratings} {listshow}",
                            command=lambda q=qc_type, i=imgid, r=rater: self.operate_qc("openNew", q, i, r, "NotSave")
                        )
                    if qc_type_summary == "summary":
                        for ratings in result_dict_imgid:
                            listshow = self.results_all_dict[imgid][ratings]["listshow"]
                            qc_type, rater = ratings.split("_")
                            self.right_click_menu.add_command(
                                label=f"Open rating results of {ratings} {listshow} (can save)",
                                command=lambda q=qc_type, i=imgid, r=rater: self.operate_qc("openNew", q, i, r, "Save")
                            )

                # 显示右键菜单
                self.right_click_menu.post(event.x_root, event.y_root)

                # 绑定点击页面其他地方的事件
                if not hasattr(self, 'cancel_id') or self.cancel_id is None:
                    self.cancel_id = self.master.bind("<Button-1>", cancel_right_click_menu, add="+")

                # 绑定 popup_table 的销毁事件
                if hasattr(self, 'popup_table'):
                    if not hasattr(self, 'popup_cancel_id') or self.popup_cancel_id is None:
                        self.popup_cancel_id = self.popup_table.bind("<Destroy>", on_popup_table_destroy)

            except Exception as e:
                print(f"{inspect.currentframe().f_lineno} Error: {e}")

    def display_content(self, content, type):

        if type == "init":
            self.showbox.delete(*self.showbox.get_children())
        elif type in self.qctypes:
            self.showbox_select.delete(*self.showbox_select.get_children())
        elif type == 'summary':
            self.showbox.delete(*self.showbox.get_children())


        if content:
            content_explained = []

            FilterPoint = content.get("FilterPoint", {})
            content_explained.append(f"FilterPoints:")
            if FilterPoint:
                print(f"{inspect.currentframe().f_lineno} FilterPoint: {FilterPoint}")
                for point, value in FilterPoint.items():
                    content_explained.append(f"{point}:")
                    content_explained.append(f"    {value}")

            SelectVar = content.get("SelectVar", {})
            if SelectVar:
                print(f"{inspect.currentframe().f_lineno} SelectVar: {SelectVar}")
                content_explained.append(f"SelectVar:")
                for convar in ['include', 'Not include', 'var2rank']:
                    value = SelectVar.get(convar, [])
                    if value:
                        value = ", ".join(value)
                        content_explained.append(f"    {convar}: {value}")

            for item in content_explained:
                if type == "init":
                    self.showbox.insert('', 'end', values=(item,))
                elif type in self.qctypes:
                    self.showbox_select.insert('', 'end', values=(item,))
                elif type == 'summary':
                    self.showbox.insert('', 'end', values=(item,))
                    self.showbox_select.insert('', 'end', values=(item,))



    def clear_frame(self):
        for widget in self.master.winfo_children():
            if self.popup_table and widget == self.popup_table:
                continue
            widget.destroy()


    def operate_init(self, oper_type, *params):
        """初始化页面的各个按钮和操作"""

        if oper_type == "BrowseDir":
            dir_type = params[0]
            if dir_type == "list_dir":
                directory = filedialog.askopenfilename()
            else:
                directory = filedialog.askdirectory()
            if directory:
                self.tk_dirs[dir_type]["path"].set(directory) # 将选择的路径显示在输入框中
                self.dirs[dir_type]["path"] = directory  # 存储选择的路径

        # 启动特定qc的按钮
        elif oper_type == "StartQC":
            self.create_specific_widgets(params[0])

        elif oper_type == "selectandfilter":
            self.open_settings_popup("summary")

        elif oper_type == "getthelist":
            self.get_path_dict()
            self.get_result_all_dict()
            self.save_load_result_dict("results_all_dict", "save")
            self.handle_selection_filter('basic_filter')

        elif oper_type == "showthetable":
            self.show_the_table(type="summary")

        elif oper_type == "tabletrans":
            if self.select_filter['summary']["tableformat"] == "long":
                self.select_filter['summary']["tableformat"] = "wide"
            else:
                self.select_filter['summary']["tableformat"] = "long"
            self.show_the_table(type="summary")

        elif oper_type == "savethetable":
            self.save_the_table()

        elif oper_type == "summary":
            self.show_summary()

    def operate_qc(self, oper_type, *params):

        if oper_type == "reselectQCType":
            self.create_initial_widgets()
            self.save_load_result_dict(params, "save") # 保存list_dict

        elif oper_type == "selectandfilter":
            self.open_settings_popup(params[0])

        elif oper_type == "refresh":
            self.get_path_dict()
            self.get_result_all_dict()
            if self.select_filter[params[0]]["select_filter_text"] != "":
                self.handle_selection_filter(params[0])  # 将结果赋值给list_dict[qc_type]["list_dict"]
                self.show_present_list(params[0], self.results_all_dict_tmp)
            else:
                self.show_present_list(params[0])
            # self.save_load_result_dict("settings","save")
            print("** Refreshed successfully!")

        elif oper_type == "navigate_subject":

            qc_type = params[0]
            offset = params[1]
            self.navigate_subject(qc_type, offset)

        elif oper_type == "save_rating":
            qc_type = params[0]
            rater = self.qctypes_project[qc_type]["rater"]
            imgid = self.qctypes_project[qc_type]["imgid"]
            self.save_load_rating("save", qc_type, rater, imgid)
            self.show_present_list(qc_type, self.list_dict[qc_type]["list_dict"], imgid)

        elif oper_type == "openimg":
            qc_type = params[0]
            imgid = params[1]
            dict_imgid = self.path_dict.get(imgid, None)
            presentdir = self.qctypes_project[qc_type]["presentdirtype"]
            if not dict_imgid:
                print(f"!!!!!! imgid not found in previous_dict: {imgid}")
                return
            path_rel = dict_imgid.get(f"path_{presentdir}", "")
            path = os.path.join(self.dirs[presentdir]["path"], path_rel)
            presentviewer = self.qctypes_project[qc_type]["presentviewer"]
            qc_viewer = QCViewer(qc_type, path, presentdir, presentviewer)
            qc_viewer.start_viewing()

        elif oper_type =="openNew":
            qc_type = params[0]
            imgid = params[1]
            rater = params[2]
            cansave = params[3]
            if cansave == "NotSave":
                print(f"** Open new Python process for {qc_type} of {imgid} by {rater}")
                path_python = sys.executable  # 获取当前正在运行的Python解释器的路径
                subprocess.Popen(
                    [path_python, os.path.join(self.codes_dir, 'openNew.py'), self.projectname, qc_type, imgid, rater])
            elif cansave == "Save":
                print(f"** Open image {qc_type} of {imgid} by {rater}")
                self.create_specific_widgets(qc_type, imgid, rater, True)

        elif oper_type == "error_option":
            op = params[0]
            cursor_index = self.remarks_tk.index(INSERT)

            # Get characters before and after the cursor
            before_cursor = self.remarks_tk.get(f"{cursor_index} - 1c", cursor_index)
            after_cursor = self.remarks_tk.get(cursor_index, f"{cursor_index} + 1c")

            # Remove all spaces before the cursor
            while before_cursor == " ":
                self.remarks_tk.delete(f"{cursor_index} - 1c", cursor_index)
                cursor_index = self.remarks_tk.index(INSERT)
                before_cursor = self.remarks_tk.get(f"{cursor_index} - 1c", cursor_index)

            # Remove all spaces after the cursor
            while after_cursor == " ":
                self.remarks_tk.delete(cursor_index, f"{cursor_index} + 1c")
                after_cursor = self.remarks_tk.get(cursor_index, f"{cursor_index} + 1c")

            cursor_index = self.remarks_tk.index(INSERT)  # Update cursor index after deletion

            if op == ";":
                # Ensure no space before ";" and one space after it
                if before_cursor == ";":
                    self.remarks_tk.insert(cursor_index, " ")
                elif after_cursor == ";":
                    return
                else:
                    self.remarks_tk.insert(cursor_index, "; ")
            else:
                # Ensure exactly one space between other content
                if before_cursor not in ["", " "] and after_cursor not in ["", " "]:
                    self.remarks_tk.insert(cursor_index, f" {op} ")
                elif before_cursor not in ["", " "]:
                    self.remarks_tk.insert(cursor_index, f" {op}")
                elif after_cursor not in ["", " "]:
                    self.remarks_tk.insert(cursor_index, f"{op} ")
                else:
                    self.remarks_tk.insert(cursor_index, f"{op}")
                # Set cursor index to after the inserted text
                self.remarks_tk.mark_set(INSERT, f"{cursor_index} + {len(op) + 1}c")
                self.remarks = self.remarks_tk.get("1.0", END).strip()

        elif oper_type == "error_oper":
            qc_type = params[0]
            op = params[1]
            if op == "OtherNotes":
                self.operate_qc("error_option", "OtherNotes")

            elif op == "Delete":
                current_index = self.remarks_tk.index(INSERT)
                current_text = self.remarks_tk.get("1.0", current_index)
                last_space = current_text.rstrip().rfind(" ")
                last_semicolon_newline = current_text.rstrip().rfind(";\n")
                last_position = max(last_space, last_semicolon_newline)
                if last_position == -1:
                    self.remarks_tk.delete("1.0", current_index)
                else:
                    self.remarks_tk.delete(f"1.0 + {last_position + 1}c", current_index)

            elif op == "Explain":
                self.remarks = self.remarks_tk.get("1.0", END).strip()
                remarks_table, self.ErrorTypes = self.processor.explain_remark(self.remarks)
                self.remarks_table_dict = {row[0]: row[1] for row in remarks_table}
                self.tree.delete(*self.tree.get_children())
                for row in remarks_table:
                    self.tree.insert("", "end", values=row)

            elif op == "Clear":
                self.remarks_tk.delete('1.0', END)
                self.tree.delete(*self.tree.get_children())

    def select_and_filter(self, oper_type, *params):
        if oper_type == "words":
            op = params[0]
            cursor_index = self.selection_filter.index(INSERT)
            # Get characters before and after the cursor
            before_cursor = self.selection_filter.get(f"{cursor_index} - 1c", cursor_index)
            after_cursor = self.selection_filter.get(cursor_index, f"{cursor_index} + 1c")
            # Remove all spaces before the cursor
            while before_cursor == " ":
                self.selection_filter.delete(f"{cursor_index} - 1c", cursor_index)
                cursor_index = self.selection_filter.index(INSERT)
                before_cursor = self.selection_filter.get(f"{cursor_index} - 1c", cursor_index)

            # Remove all spaces after the cursor
            while after_cursor == " ":
                self.selection_filter.delete(cursor_index, f"{cursor_index} + 1c")
                after_cursor = self.selection_filter.get(cursor_index, f"{cursor_index} + 1c")

            cursor_index = self.selection_filter.index(INSERT)  # Update cursor index after deletion

            if op in [";", ',']:
                # Ensure no space before ";" and one space after it
                if before_cursor == op:
                    self.selection_filter.insert(cursor_index, " ")
                elif after_cursor == op:
                    return
                else:
                    self.selection_filter.insert(cursor_index, f"{op} ")
            elif op in ["SelectVar", "FilterPoint"]:
                # 如果前面没有内容，则直接插入，否则换行后插入
                if before_cursor == "":
                    self.selection_filter.insert(cursor_index, f"** {op}: ")
                else:
                    self.selection_filter.insert(cursor_index, f"\n** {op}: ")
            else:
                if op in ["OverStrip", "UnderStrip"] + self.errortypes + self.Severity:
                    op = f"'{op}'"
                # Ensure exactly one space between other content
                if before_cursor not in ["", " "] and after_cursor not in ["", " "]: # 如果前后都没有空格
                    if op in ["(", "["]:
                        self.selection_filter.insert(cursor_index, f" {op}")
                    elif op in [")", "]"]:
                        self.selection_filter.insert(cursor_index, f"{op} ")
                    else:
                        if before_cursor in ["(", "["]:
                            self.selection_filter.insert(cursor_index, f"{op} ")
                        else:
                            self.selection_filter.insert(cursor_index, f" {op} ")
                else:
                    self.selection_filter.insert(cursor_index, f"{op}")
                # Set cursor index to after the inserted text
                self.selection_filter.mark_set(INSERT, f"{cursor_index} + {len(op) + 1}c")
                self.remarks = self.selection_filter.get("1.0", END).strip()

        elif oper_type == "select_filt":
            op = params[0]
            if op == "Enter":
                self.handle_selection_filter("summary")
            elif op in ["SelectVar","FilterPoint"]:
                self.select_and_filter("words", op)
            elif op == "Explain":
                explaintype = params[1]
                filter_text = self.selection_filter.get("1.0", END).strip()
                explained_filter_text = {}
                if filter_text:
                    try:
                        navardf = self.results_all_table.columns.tolist() + ["Score1F", "Score2F"]
                        explained_filter_text = self.processor.splitSelectFilterText(navardf, filter_text)
                    except Exception as e:
                        raise ValueError(f"Error: {e}")
                    self.select_filter[explaintype]["select_filter_explained"] = explained_filter_text
                    self.handle_selection_filter(explaintype)

                self.select_filter[explaintype]["select_filter_explained"] = explained_filter_text
                self.select_filter[explaintype]["select_filter_text"] = filter_text
                self.display_content(explained_filter_text, explaintype)
                print(f"** {inspect.currentframe().f_lineno} Explained filter text: {explained_filter_text}")


            elif op == "Delete":  # 删除最后一个单词或符号
                current_index = self.selection_filter.index(INSERT)
                current_text = self.selection_filter.get("1.0", current_index)

                last_space = current_text.rstrip().rfind(" ")
                last_left_parenthesis = current_text.rstrip().rfind("(")-1
                last_right_parenthesis = current_text.rstrip().rfind(")")-1
                last_left_bracket = current_text.rstrip().rfind("[")-1
                last_right_bracket = current_text.rstrip().rfind("]")-1
                last_single_quote = current_text.rstrip().rfind("'")-1

                last_position = max(last_space-1, last_left_parenthesis, last_right_parenthesis, last_left_bracket,
                                    last_right_bracket, last_single_quote)
                if last_position == -1:
                    self.selection_filter.delete("1.0", current_index)
                else:
                    self.selection_filter.delete(f"1.0 + {last_position + 1}c", current_index)

            elif op == "Clear": # 清空所有内容
                self.selection_filter.delete('1.0', END)
                self.display_content([],self.qctype)

    def get_path_dict(self):
        # 使用存储的路径
        paths = {dir_type: details["path"] for dir_type, details in self.dirs.items()}
        self.path_dict = {}
        if paths.get("list_dir"):
            sublist = self.processor.process_list_dir(paths["list_dir"])
        else:
            sublist = None

        if paths.get("bids_dir"):
            self.path_dict = self.processor.getlist_bids_dir(paths["bids_dir"], sublist)
        if paths.get("ccs_dir"):
            self.path_dict = self.processor.getlist_ccs_dir(paths["ccs_dir"], sublist)
        if paths.get("subject_dir"):
            self.path_dict = self.processor.getlist_subject_dir(paths["subject_dir"], sublist)
        if paths.get("mriqc_dir"):
            self.path_dict = self.processor.getlist_mriqc_dir(paths["mriqc_dir"], sublist)

        if sublist:
            self.path_dict = {key: value for key, value in self.path_dict.items() if key in sublist}

        # 确保每个字典条目都有 imgid
        for key, value in self.path_dict.items():
            if 'imgid' not in value:
                subid = value.get('subid', '')
                ses = value.get('ses', '')
                run = value.get('run', '')
                imgid_parts = [subid]
                if ses:
                    imgid_parts.append(f"ses-{ses}")
                if run:
                    imgid_parts.append(f"run-{run}")
                value['imgid'] = '_'.join(imgid_parts)

        # 对字典按 imgid 排序
        sorted_data = sorted(self.path_dict.items(), key=lambda item: item[1].get('imgid', ''))

        # 为每个条目添加 index_all 字段
        for index, (key, value) in enumerate(sorted_data):
            self.path_dict[key]['IndexAll'] = index

        self.path_dict = {entry[1].get('imgid'): entry[1] for entry in sorted_data}
        for qc_type in self.qctypes:
            self.list_dict[qc_type]["list_dict"] = {key: {} for key in self.path_dict}

        print(f"** Get path_dict with {len(self.path_dict)} entries")

    def get_result_all_dict(self, qc_type=None, rater=None, imgid=None):
        """1. 从所有的单个评分文件中读取评分结果，并将其存储在 self.results_all_dict中
           2. 读取单个评分文件，更新 self.results_all_dict"""
        def update_one_result_dict(path_output):
            try:
                root, file = os.path.split(path_output)
                if file.endswith(".json"):
                    imgid = os.path.basename(root)
                    match = re.match(r'(.+?)_(.+?)_(.*?)_(.*?)\.json$', file)
                    if match:
                        qc_type, rater, Score1, isdone = match.groups()
                        with open(path_output, 'r') as f:
                            data = json.load(f)

                            if imgid not in self.results_all_dict:
                                self.results_all_dict[imgid] = {}
                            if f"{qc_type}_{rater}" not in self.results_all_dict[imgid]:
                                self.results_all_dict[imgid][f"{qc_type}_{rater}"] = {}

                            if imgid in self.path_dict:
                                if 'IndexAll' in self.path_dict[imgid]:
                                    self.results_all_dict[imgid][f"{qc_type}_{rater}"]['IndexAll'] = \
                                        self.path_dict[imgid]['IndexAll']
                                else:
                                    print(f"IndexAll not found in self.path_dict[{imgid}]")
                            else:
                                print(f"{imgid} not found in self.path_dict")

                            # Update results_all_dict with JSON data
                            self.results_all_dict[imgid][f"{qc_type}_{rater}"].update(data)
                            self.results_all_dict[imgid][f"{qc_type}_{rater}"]["listshow"] = f"{Score1} {isdone}"
                            if imgid not in self.list_dict[qc_type]["list_dict"]:
                                self.list_dict[qc_type]["list_dict"][imgid] = {}
                            self.list_dict[qc_type]["list_dict"][imgid]["listshow"] = f"{Score1} {isdone}"

                            # 将以Score1开头的键名转变为"Score1"键名
                            keys_to_modify = [key for key in self.results_all_dict[imgid][f"{qc_type}_{rater}"] if
                                              key.startswith("Score1") or key.startswith("Score2")]
                            for key in keys_to_modify:
                                if key.startswith("Score1"):
                                    value = self.results_all_dict[imgid][f"{qc_type}_{rater}"].pop(key)
                                    self.results_all_dict[imgid][f"{qc_type}_{rater}"]["Score1"] = int(
                                        value) if value else None
                                elif key.startswith("Score2"):
                                    value = self.results_all_dict[imgid][f"{qc_type}_{rater}"].pop(key)
                                    self.results_all_dict[imgid][f"{qc_type}_{rater}"]["Score2"] = int(
                                        value) if value else None
                        print(f"** Save rating results into self.results_all_dict, path: {path_output}")
                    else:
                        print(f"Filename format does not match: {file}")
            except Exception as e:
                print(f"Error processing {path_output}: {e}")

        path = self.dirs["output_dir"]["path"]
        if qc_type and rater and imgid:
            pattern = os.path.join(path, "RatingResults", qc_type, rater, imgid, f"{qc_type}_{rater}*.json")
            matching_files = glob.glob(pattern)
            if len(matching_files) == 1:
                update_one_result_dict(matching_files[0])
            elif len(matching_files) == 0:
                print(f"****** ERROR in read rating files: No file found in {qc_type}/{rater}/{imgid} *******")
            elif len(matching_files) > 1:
                print(f"****** ERROR in read rating files: Multiple files found in {qc_type}/{rater}/{imgid} *****")
        else:
            self.results_all_dict = {}
            for key, data in self.path_dict.items():
                self.results_all_dict[key] = {}
            if path:
                for root, dirs, files in os.walk(os.path.join(path, "RatingResults")):
                    for file in files:
                        if re.match(r'(.+?)_(.+?)_(.*?)_(.*?)\.json$', file):
                            path_output = os.path.join(root, file)
                            update_one_result_dict(path_output)
            else:
                print("output_dir is not set")

    def show_present_list(self, qc_type, dict_list=None, imgid=None):
        """
        (1) Show the present list for a given QC type; (2) Update the listbox selection (specifically for imgid)
        """
        rater = self.qctypes_project[qc_type].get("rater", "")

        # ######################    更新整个列表    ######################
        if imgid is None:
            if dict_list is None:
                dict_list = dict(self.path_dict.items())  # 如果未定义则初始化
            else:
                dict_list = dict(dict_list.items())  # 如果已经定义则使用传入的值

            dict_new = {}
            for imgid in dict_list:
                dict_new[imgid] = {}
                if imgid in self.results_all_dict and f"{qc_type}_{rater}" in self.results_all_dict[imgid]:
                    dict_new[imgid]["listshow"] = self.results_all_dict[imgid].get(f"{qc_type}_{rater}", {}).get(
                        "listshow", "")
                else:
                    dict_new[imgid]["listshow"] = ""

            sorted_dict = sorted(dict_new.items(), key=lambda x: x[0])
            for index, (key, value) in enumerate(sorted_dict):
                value["index"] = index
                dict_new[key] = value

            self.list_dict[qc_type]["list_dict"] = dict_new
            self.listbox.delete(*self.listbox.get_children())  # Clear existing listbox entries

            for i, (imgid, value) in enumerate(sorted_dict):
                listshow = dict_new[imgid].get("listshow", "")
                score1, isdone = listshow.split(" ") if listshow else ("", "")
                self.listbox.insert('', 'end', values=(i + 1, imgid, score1, isdone))

        # ############################       更新单个列表条目          ############################
        else:
            # 直接根据imgid更新listbox中的值
            index = self.list_dict[qc_type]["list_dict"][imgid].get("index", 0)
            listshow = self.results_all_dict[imgid].get(f"{qc_type}_{rater}",{}).get("listshow", "")
            self.list_dict[qc_type]["list_dict"][imgid]["listshow"] = listshow
            score1, isdone = listshow.split(" ") if listshow else ("", "")
            item_id = self.listbox.get_children()[index]
            self.listbox.item(item_id, values=(index + 1, imgid, score1, isdone))

        # Update the listbox selection
        self.master.after(500, lambda: self.update_listbox_selection(self.qctypes_project[qc_type]["imgid"]))

    def update_listbox_selection(self, imgid):
        # 清除所有选择项
        self.listbox.selection_clear()
        # 遍历所有项的ID
        for item_id in self.listbox.get_children():
            # 获取该项的值
            item_values = self.listbox.item(item_id, "values")
            # 检查imgid是否在该项中
            if imgid in item_values:
                # 选择该项并确保它可见
                self.listbox.selection_set(item_id)
                self.listbox.see(item_id)
                break

    def show_the_table(self, table=None, type="summary"):
        # self.popup_table已经打开，则关闭它
        if hasattr(self, 'popup_table') and self.popup_table:
            self.popup_table.destroy()
            self.popup_table = None

        if table is None:
            if type == "summary":
                if self.select_filter['summary']["tableformat"] == "wide":
                    table = self.results_table_show_wide
                elif self.select_filter['summary']["tableformat"] == "long":
                    table = self.results_table_show_long

        # 将DataFrame中的None和NaN替换为空字符串
        table = table.fillna('')  # 将NaN替换为空字符串
        table = table.replace({None: ''})  # 将None替换为空字符串
        self.Imgid_index = table.columns.get_loc("Imgid") + 1

        # 将DataFrame转换为二维列表
        data = table.values.tolist()
        headers = table.columns.tolist()
        data.insert(0, headers)  # 将表头插入到数据的第一行

        # Create a new Toplevel window
        self.popup_table = Toplevel(self.master)
        self.popup_table.title("Table Summary")
        self.popup_table.geometry("1400x800")

        # Determine the number of columns from the first row of the table
        columns = len(data[0])
        column_ids = ["Index"] + [f"Column{i + 1}" for i in range(columns)]

        # Create a Treeview widget with dynamic columns, including the index column
        # Initialize the Treeview
        self.listbox_table = Treeview(self.popup_table, columns=column_ids, show='headings')

        # Set the column headings dynamically using the first row of the table as headers
        for i, col_id in enumerate(column_ids):
            self.listbox_table.heading(col_id, text=headers[i - 1] if i > 0 else "index")
            self.listbox_table.column(col_id, width=150, stretch=False)  # 设置默认宽度，不启用stretch

        # 使用 grid 布局来布局 Treeview 和滚动条
        self.listbox_table.grid(row=0, column=0, sticky="nsew")

        # 右键菜单绑定
        self.right_click_menu = Menu(self.popup_table, tearoff=0)
        self.listbox_table.bind("<Button-3>",
                                lambda event: self.show_right_click_menu(self.listbox_table, event, "summary"))
        self.right_click_menu = Menu(self.master, tearoff=0)

        # Insert data into the Treeview
        for index, row in enumerate(data[1:], start=1):
            self.listbox_table.insert('', 'end', values=[index] + row)

        # Add scrollbars
        vsb = Scrollbar(self.popup_table, orient="vertical", command=self.listbox_table.yview)
        hsb = Scrollbar(self.popup_table, orient="horizontal", command=self.listbox_table.xview)

        # 配置滚动条
        self.listbox_table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 使用 grid 布局来放置滚动条
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 确保主窗口在调整大小时调整布局
        self.popup_table.grid_rowconfigure(0, weight=1)
        self.popup_table.grid_columnconfigure(0, weight=1)


    def show_summary(self):
        pass

    def navigate_subject(self, qc_type, offset):

        presentdir = self.qctypes_project[qc_type]["presentdirtype"]
        presentviewer = self.qctypes_project[qc_type]["presentviewer"]
        rater = self.qctypes_project[qc_type]["rater"]
        dict = self.list_dict[qc_type]["list_dict"]

        # 保存当前图像的评分
        imgid = self.qctypes_project[qc_type]["imgid"]
        index = dict.get(imgid, {}).get("index", 0)
        if imgid in dict:
            self.save_load_rating("save", qc_type, rater, imgid)
            self.show_present_list(qc_type, self.list_dict[qc_type]["list_dict"], imgid)

        # 根据offset切换打开图片并更新评分
        if offset == 1 or offset == -1:
            index = index + offset
            if 0 <= index < len(dict):
                imgid = None
                for key, value in dict.items():
                    if value.get("index") == index:
                        imgid = key
                        break
            else:
                print(f"Index out of range: {index}")
                return
        elif offset == 0:
            selected_item_id = self.listbox.selection()
            print(f"selected_index: {selected_item_id}")
            if selected_item_id:
                selected_item = self.listbox.item(selected_item_id[0], "values")
                imgid = selected_item[1]  # imgid 是第二列的值
                index = dict[imgid].get("index", 0)
        else:
            imgid = offset

        # 准备打开图片
        self.qctypes_project[qc_type]["imgid"] = imgid
        dict_imgid = self.path_dict[imgid]
        path_rel = dict_imgid.get(f"path_{presentdir}", "")
        path = os.path.join(self.dirs[presentdir]["path"], path_rel)
        idx = index + 1

        print(f"********     Show image: {idx}. {imgid}   **********")
        qc_viewer = QCViewer(qc_type, path, presentdir, presentviewer, self.current_process)
        self.current_process = qc_viewer.start_viewing()
        self.save_load_rating("load", qc_type, rater, imgid)
        self.show_present_list(qc_type, self.list_dict[qc_type]["list_dict"], imgid)

    def getDictValue(self, dict, value, value_var, output_var=None):
        for key, val in dict.items():
            if val.get(value_var) == value:
                return val.get(output_var) if output_var and output_var in val else key
        return None

    def save_load_rating(self, operation, qc_type=None, rater=None, imgid=None):
        """
        1. 清除评分界面的内容
        2. 保存评分结果到文件，并更新self.results_all_dict
        3. 读取评分文件，并更新评分界面的内容
        """

        if operation == "clear":
            self.score1.set("")
            self.score2.set("")
            self.CheckDone.set(0)
            self.NeedMoreCheck.set(0)
            self.remarks_tk.delete(1.0, END)
            if self.qctype == "headmotion":
                self.NonHeadMotionArtifacts.set(0)
            elif self.qctype == "skullstrip":
                self.tree.delete(*self.tree.get_children())
            elif self.qctype == "reconstruct":
                self.tree.delete(*self.tree.get_children())

            elif self.qctype == "registrate":
                pass
        # save and load rating file
        else:
            if not rater:
                print("********** Rater doesn't exist! Please enter rater. *************")
                self.save_load_rating("clear")
                return

            path_output = self.dirs["output_dir"]["path"]
            dirtype = self.qctypes_project[qc_type]["presentdirtype"]
            path_result_img = os.path.join(path_output, "RatingResults", f"{qc_type}", f"{rater}", f"{imgid}")
            pattern = os.path.join(path_result_img, f"{qc_type}_{rater}_*.json")
            rating_file_path = glob.glob(pattern)

            # save rating files
            if operation == "save":
                if not self.cansave:
                    print("********** You are in browse mode! Don't save rating file! *************")
                    return

                if not os.path.exists(path_output):
                    try:
                        os.makedirs(path_output, exist_ok=True)
                    except OSError as e:
                        print(f"Error creating output directory: {e}")
                        return

                os.makedirs(path_result_img, exist_ok=True)
                path_base = self.dirs[dirtype]["path"]
                dict_imgid = self.path_dict.get(imgid, None)
                print(f"** Save rating file: {qc_type} - {rater} - {imgid}  dict_imgid: {dict_imgid}")
                path_rel = dict_imgid.get(f"relative_path_{dirtype}", "")

                # 保存评分
                rating_data = {
                    "Imgid": imgid,
                    "Subid": dict_imgid.get('subid', ''),
                    "Ses": dict_imgid.get('ses', ''),
                    "Run": dict_imgid.get('run', ''),
                    "Time": datetime.datetime.now().isoformat(),
                    "QCType": qc_type,
                    "DirType": dirtype,
                    "DirPath": path_base,
                    "RelativePath": path_rel,
                    "PresentViewer": self.qctypes_project[qc_type]['presentviewer'],
                    "Rater": rater,
                    "Status": "done" if self.CheckDone.get() else "undone",
                    "Score1": self.score1.get(),
                    "Score2": self.score2.get(),
                    "NeedMoreCheck": self.NeedMoreCheck.get(),
                    "CheckDone": self.CheckDone.get(),
                    "Remark": self.remarks_tk.get('1.0', END).strip()
                }
                if qc_type in ["skullstrip", "reconstruct"]:
                    self.operate_qc("error_oper", qc_type, "Explain")
                    rating_data["ErrorTypes"] = self.ErrorTypes

                if qc_type == "headmotion":
                    rating_data["NonHeadMotionArtifacts"] = self.NonHeadMotionArtifacts.get()
                elif qc_type == "skullstrip":
                    for var in self.lobes_var_bi:
                        rating_data[var] = self.remarks_table_dict.get(var, '')
                elif qc_type == "reconstruct":
                    for var in self.var_bi:
                        rating_data[var] = self.remarks_table_dict.get(var, '')
                elif qc_type == "registrate":
                    pass

                # 删除已有的评分文件
                for file_path in rating_file_path:
                    if os.path.exists(file_path):
                        os.remove(file_path)

                rating_file = os.path.join(path_result_img,
                                           f"{qc_type}_{rater}_{self.score1.get()}_{rating_data['Status']}.json")
                with open(rating_file, 'w') as f:
                    json.dump(rating_data, f, indent=4)

                self.get_result_all_dict(qc_type, rater, imgid)
                print(f"** Save rating file successfully: {qc_type} - {rater} - {imgid}")

            elif operation == "load":
                # 检查评分结果文件是否存在
                if not rating_file_path:
                    print(f"** Rating file not found, it have been evaluated: {qc_type} - {rater} - {imgid}")
                    self.save_load_rating("clear")
                    return
                elif len(rating_file_path) > 1:
                    messagebox.showerror("警告", f"More than one rating file for \n {qc_type} {rater}, please check!")

                rating_file_path = rating_file_path[0]
                with open(rating_file_path, 'r') as f:
                    rating_data = json.load(f)

                    self.score1.set(rating_data.get("Score1", ""))
                    self.score2.set(rating_data.get("Score2", ""))
                    self.CheckDone.set(rating_data.get("CheckDone", 0))
                    self.NeedMoreCheck.set(rating_data.get("NeedMoreCheck", 0))
                    self.remarks_tk.delete(1.0, END)
                    self.remarks_tk.insert(END, rating_data.get("Remark", ""))

                    if qc_type == "headmotion":
                        self.NonHeadMotionArtifacts.set(rating_data.get("NonHeadMotionArtifacts", 0))
                    elif qc_type == "skullstrip":
                        self.operate_qc("error_oper", "reconstruct", "Explain")
                        self.ErrorTypes = rating_data.get("ErrorTypes", {})
                    elif qc_type == "reconstruct":
                        self.operate_qc("error_oper", "reconstruct", "Explain")
                    elif qc_type == "registrate":
                        pass
                print(f"** Load rating file successfully: {qc_type} - {rater} - {imgid}")

    def save_load_result_dict(self, result_types=None, operation="save"):

        def save_path_list(imgid_list, output_file):
            if os.path.exists(output_file):
                os.remove(output_file)
            with open(output_file, 'w') as file:
                if output_file.endswith(".csv"):
                    file.write("imgid, relative_path_ccs_dir, relative_path_subject_dir\n")
                    for imgid in imgid_list:
                        relative_path_ccs_dir = self.path_dict[imgid].get("relative_path_ccs_dir", "")
                        relative_path_subject_dir = self.path_dict[imgid].get("relative_path_subject_dir", "")
                        file.write(f"{imgid},{relative_path_ccs_dir},{relative_path_subject_dir}\n")
                else:
                    file.write("imgid relative_path_ccs_dir relative_path_subject_dir\n")
                    for imgid in imgid_list:
                        relative_path_ccs_dir = self.path_dict[imgid].get("relative_path_ccs_dir", "")
                        relative_path_subject_dir = self.path_dict[imgid].get("relative_path_subject_dir", "")
                        file.write(f"{imgid} {relative_path_ccs_dir} {relative_path_subject_dir}\n")

        if isinstance(result_types, str):
            result_types = [result_types]
        path_results = os.path.join(self.dirs["output_dir"]["path"], "DataAndTable")
        if not os.path.exists(path_results):
            os.makedirs(path_results, exist_ok=True)
        if result_types == None:
            self.save_load_result_dict(["results_all_dict", "path_dict", "qc_types", "results_all_table"], operation)
        else:
            for result_type in result_types:

                if result_type == "results_all_dict":
                    path_csv = os.path.join(path_results, "results_all_table.csv")
                    path_json = os.path.join(path_results, "results_all_dict.json")
                    if operation == "save" and self.cansave:
                        self.results_all_table = self.processor.save_dict_as_csv(self.results_all_dict, path_csv, 0,f"results_all_dict.json")[0]
                        print(f"** Save results_all_dict successfully. Number: {len(self.results_all_dict)}")
                    elif operation == "load":
                        if os.path.exists(path_json):
                            with open(path_json, 'rb') as file:
                                self.results_all_dict = json.load(file)
                            if self.results_all_dict == {} or len(self.results_all_dict) == 0:
                                self.get_result_all_dict()
                        if os.path.exists(path_csv):
                            self.results_all_table = pd.read_csv(path_csv)
                        print(f"** Load results_all_dict successfully. Number: {len(self.results_all_dict)}")

                elif result_type in self.qctypes:

                    if operation == "save" and self.cansave:
                        path = os.path.join(path_results, f"list_dict_{result_type}.csv")
                        self.processor.save_dict_as_csv(self.list_dict[result_type]["list_dict"], path, 0,f"list_dict_{result_type}.json")
                        print(f"** Save list_dict_{result_type} successfully. Number: {len(self.list_dict[result_type]['list_dict'])}")

                    elif operation == "load":
                        qc_type_dict_path = os.path.join(path_results, f"list_dict_{result_type}.json")
                        if os.path.exists(qc_type_dict_path):
                            with open(qc_type_dict_path, 'rb') as file:
                                self.list_dict[result_type]["list_dict"] = json.load(file)
                            print(f"** Load list_dict_{result_type} successfully. Number: {len(self.list_dict[result_type]['list_dict'])}")
                        else:
                            print(f"!!!!!!! {qc_type_dict_path} don't exist: ")

                elif result_type == "path_dict":
                    if operation == "save" and self.cansave:
                        path_dict_path = os.path.join(path_results, "Path_All_table.csv")
                        self.processor.save_dict_as_csv(self.path_dict, path_dict_path, 0, "Path_All_dict.json")
                        path_subject_all = os.path.join(path_results, "subjects_all.csv")
                        save_path_list(self.path_dict.keys(), path_subject_all)
                        print(f"** Save self.path_dict successfully in {path_dict_path}")

                    elif operation == "load":
                        data_dict_path = os.path.join(path_results, "Path_All_dict.json")
                        if os.path.exists(data_dict_path):
                            with open(data_dict_path, 'rb') as file:
                                self.path_dict = json.load(file)
                        if self.path_dict == {} or len(self.path_dict) == 0:
                            self.get_path_dict()
                        print(f"** Load path_dict successfully. Number: {len(self.path_dict)}")

                elif result_type == 'results_table_show':
                    path_wide = os.path.join(path_results, "results_table_show_wide.csv")
                    path_long = os.path.join(path_results, "results_table_show_long.csv")

                    if operation == "save" and self.cansave:
                        if os.path.exists(path_wide):
                            os.remove(path_wide)
                        self.processor.save_df_to_csv(self.results_table_show_wide, path_wide)
                        if os.path.exists(path_long):
                            os.remove(path_long)
                        self.processor.save_df_to_csv(self.results_table_show_long, path_long)
                        print(f"** Save results_table_show successfully.")

                    elif operation == "load":
                        if os.path.exists(path_wide):
                            self.results_table_show_wide = pd.read_csv(path_wide)
                        else:
                            print(f"!!!!!! results_table_show don't exist: {path_wide}")
                        if os.path.exists(path_long):
                            self.results_table_show_long = pd.read_csv(path_long)
                        else:
                            print(f"!!!!!! results_table_show don't exist: {path_long}")
                        print(f"** Load results_table_show successfully.")

                elif result_type == "settings":
                    settings_file = os.path.join(self.settings_path)
                    if operation == "save" and self.cansave:
                        try:
                            settings = {"qctypes_project": self.qctypes_project, "dirs": self.dirs, "select_filter": self.select_filter, "qctypes_options": self.qctypes_options}
                            with open(settings_file, 'w') as f:
                                json.dump(settings, f, indent=4)
                        except Exception as e:
                            print(f"!!!!!! settings saving error: {e}")

                    elif operation == "load":
                        try:
                            if not os.path.exists(settings_file):
                                messagebox.showerror("警告", "未找到设置文件！")
                                return
                            with open(settings_file, 'r') as f:
                                settings = json.load(f)
                                self.qctypes_project = settings.get("qctypes_project", self.qctypes_project)
                                self.dirs = settings.get("dirs", self.dirs)
                                self.select_filter = settings.get("select_filter", self.select_filter)
                                self.qctypes_options = settings.get("qctypes_options", self.qctypes_options)
                            print("** settings loaded successfully.")
                        except Exception as e:
                            print(f"!!!!!! settings loading error: {e}")

                elif result_type == "qc_types":
                    qc_types = self.qctypes
                    self.save_load_result_dict(qc_types, operation)


    def handle_selection_filter(self, operation=None):

        df = self.processor.save_dict_as_csv(self.results_all_dict)[0]
        def basic_filter(df):
            self.results_table_show_long = pd.DataFrame()
            summary_incld = self.select_filter['summary']['summary_incld']
            # 检查4个是否都为0,如果都为0，则不进行过滤且打印信息
            if sum(summary_incld.values()) == 0:
                print("!!!!!! No qctype included for summary. Please setting summary inclusion.")
                return
            for i, key in enumerate(summary_incld.keys()):
                value = summary_incld[key]
                if value == 1:
                    raters = self.select_filter['summary']['raters_selection'][key]
                    text = f"QCType == '{key}' AND Rater in ['{raters}']" if raters else f"QCType == '{key}'"
                    dfqctype = self.processor.filterExplainPoint(df, text)
                    self.results_table_show_long = pd.concat([self.results_table_show_long, dfqctype], ignore_index=True)

            if FilterPoint.get('Initial Inclusion', None):
                self.results_table_show_long = self.processor.filterExplainPoint(self.results_table_show_long, FilterPoint['Initial Inclusion'])
            self.results_table_show_long = self.processor.merge_results(self. results_table_show_long, self.select_filter['summary'])
            self.results_table_show_wide = self.processor.dflong2wide(self.results_table_show_long)
            self.results_all['Initial Inclusion'] = {}
            self.results_all['Initial Inclusion']['wide'] = self.results_table_show_wide
            self.results_all['Initial Inclusion']['long'] = self.results_table_show_long

        # ############   对qctype和被试进行初步过滤

        FilterPoint = self.select_filter['summary']["select_filter_explained"].get("FilterPoint", {})
        SelectVar = self.select_filter['summary']["select_filter_explained"].get("SelectVar", {})
        print(f"** {inspect.currentframe().f_lineno} SelectVar: {SelectVar}")
        if operation == "basic_filter":
            basic_filter(df)
            self.results_table_show_long = self.processor.sort_pdDataFrame_col(self.results_table_show_long, SelectVar)
            self.results_table_show_wide = self.processor.sort_pdDataFrame_col(self.results_table_show_wide, SelectVar)

        if operation == "summary":
            basic_filter(df)
            keys = sorted([key for key in FilterPoint.keys() if key.startswith("FilterPoint")])
            if keys:
                for key in keys:
                    if FilterPoint[key]:
                        self.results_table_show_long = self.processor.filterExplainPoint(self.results_table_show_long, FilterPoint[key])
                        self.results_table_show_wide = self.processor.dflong2wide(self.results_table_show_long)
                        self.results_all[key] = {}
                        self.results_all[key]['wide'] = self.results_table_show_wide
                        self.results_all[key]['long'] = self.results_table_show_long
            self.results_table_show_long = self.processor.sort_pdDataFrame_col(self.results_table_show_long, SelectVar)
            self.results_table_show_wide = self.processor.sort_pdDataFrame_col(self.results_table_show_wide, SelectVar)


        elif operation in list(self.qctypes):
            self.results_all_dict_tmp = {}
            FilterPoint = self.select_filter[operation]['select_filter_explained']['FilterPoint']['Initial Inclusion']
            print(f"** {inspect.currentframe().f_lineno} FilterPoint: {FilterPoint}")
            list_qctypee_table = self.processor.filterExplainPoint(df, FilterPoint)

            # 获得所有的imgid，并获取唯一的imgid
            imgid_list = list_qctypee_table['Imgid'].tolist()
            imgid_list = list(set(imgid_list))
            for imgid in imgid_list:
                self.results_all_dict_tmp[imgid] = self.results_all_dict[imgid]


    def save_the_table(self):
        table_path = os.path.join(self.dirs["output_dir"]["path"], "DataAndTable")

        # 保存summary表格
        for key, value in self.results_all.items():
            table_wide = value['wide']
            table_long = value['long']
            self.processor.save_df_to_csv(table_long, os.path.join(table_path, f"{key}_long.csv"))
            self.processor.save_df_to_csv(table_wide, os.path.join(table_path, f"{key}_wide.csv"))


        # 保存最终结果表格
        self.save_load_result_dict("results_all_table", "save")

        # 保存最终名单
        imgid_list = self.results_table_show_wide["Imgid"].tolist()
        pttxt = os.path.join(table_path, "sublist_imgid.txt")
        with open(pttxt, 'w') as f:
            for imgid in imgid_list:
                f.write(f"{imgid}\n")

        pttxt = os.path.join(table_path, "sublist_subject_dir.txt")
        with open(pttxt, 'w') as f:
            for imgid in imgid_list:
                relapath_dict = self.path_dict.get(imgid, {}).get("relative_path_subject_dir", "")
                f.write(f"{relapath_dict}\n")

    def backup(self):
        pass

def askproject(projectname):

    def creatnewproject(projectname, output_dir, codes_dir, projects_file):
        print(f"** Create a new project: {projectname}\n** Output directory: {output_dir}")
        print(f"** Project settings file: {projects_file}")

        outputname = f"easyqc_{projectname}"
        if outputname != os.path.basename(output_dir):
            output_dir_new = os.path.join(output_dir, outputname)
        else:
            output_dir_new = output_dir

        if not os.path.exists(output_dir_new):
            os.makedirs(output_dir_new, exist_ok=True)

        setting_path = os.path.join(output_dir_new, f"settings_{projectname}.json")
        if not os.path.exists(setting_path):
            shutil.copy(os.path.join(codes_dir, "settings.json"), setting_path)

        projects_file["projects"][projectname] = setting_path
        projects_file["last_project"] = projectname
        with open(os.path.join(codes_dir, "projects.json"), 'w') as f:  # Change 'r' to 'w'
            json.dump(projects_file, f, indent=4)
        return

    def dirask(dirname):
        output_dir = input(f"** Please enter the path of {dirname}, or quit (q): ")
        if output_dir == "q":
            quit()
        elif not os.path.exists(output_dir):
            print(f"** {dirname} does not exist: {output_dir} ")
            return dirask(dirname)  # 返回递归调用的结果
        else:
            return output_dir

    def openanexistproject(codes_dir,projects_file):
        filedir = input("Please entry the path of project .json file which start with 'settings_' (entry 'quit' to exit): ")
        settings_filename = os.path.basename(filedir)
        print(f"** settings_filename: {settings_filename}")
        if not settings_filename.startswith("settings_") or not settings_filename.endswith(".json"):
            print("The project setting file should starts with 'settings_' and end with '.json'.")
            return openanexistproject(codes_dir, projects_file)
        elif not os.path.exists(filedir):
            print(f"** Project setting file does not exist: {filedir}")
            return openanexistproject(codes_dir, projects_file)
        elif filedir == "quit":
            quit()
        else:
            with open(filedir, 'r') as f:
                settings = json.load(f)
                projectdir = settings.get("dirs", {}).get("output_dir", {}).get("path", "")
                print(f"** Project output directory: {projectdir}")
            if not os.path.exists(projectdir):
                input(f"** The output directory does not exist: {projectdir}. Do you want to \n"
                      f"   - create this folder (yes), \n"
                      f"   - re-entry setting file path (no), \n"
                      f"   - or quit (quit)? \n"
                      f" : ")
                if input("yes"):
                    os.makedirs(projectdir, exist_ok=True)
                elif input("no"):
                    return openanexistproject(codes_dir, projects_file)
                elif input("quit"):
                    quit()
            projectname = settings_filename.split("_")[1].split(".")[0]
            projects_file["projects"][projectname] = filedir
            projects_file["last_project"] = projectname
            print(f"** Open the project: {projectname}")
            with open(os.path.join(codes_dir, "projects.json"), 'w') as f:
                json.dump(projects_file, f, indent=4)
            return projectname


    codes_dir = os.path.dirname(os.path.abspath(__file__))
    path_proj = os.path.join(codes_dir, "projects.json")  # 本代码文件的路径中的projects.json文件
    with open(path_proj, 'r') as f:
        projects_file = json.load(f)
        projects = projects_file.get("projects", {})
        last_project = projects_file.get("last_project", "")

    if projectname == "":  # 如果没有输入项目名称，则询问是否打开上一个项目或则打开默认项目
        if last_project != "" and os.path.exists(projects[last_project]):  # 如果上一个项目存在，则询问是否打开上一个项目
            print(f"** You don't entry a project name. Opening the last project: {last_project}")
            return last_project
        else:
            creatnew = input("** You don't entry a project name. You can \n"
                             "   - create a new project (yes) \n"
                             "   - open an exist project with setting .json file (no) , \n"
                             "   - quit (quit)\n"
                             " : ")
            if creatnew == "yes":
                projectname = input("Please enter the name of the project: ")
                output_dir = dirask("Output")
                creatnewproject(projectname, output_dir, codes_dir, projects_file)
                return projectname
            elif creatnew == "no":
                projectname = openanexistproject(codes_dir, projects_file)
                return projectname
            elif creatnew == "quit":
                quit()

    else:  # 如果输入了项目名称，则检查是否存在，不存在则询问是否创建新项目
        # 如果项目或路径不存在，则询问是否创建新项目
        if projectname not in projects or not os.path.exists(projects[projectname]):  # 检查项目是否存在
            create_new = input(f"** The project {projectname} does not exist. You can \n"
                               f"    - create a new project (yes), \n"
                               f"    - open an exist project (no), \n"
                               f"    - or quit (quit)? \n"
                               f" : ")
            if create_new == "yes":
                output_dir = dirask("Output")
                creatnewproject(projectname, output_dir, codes_dir, projects_file)
                return projectname
            elif create_new == "no":
                projectname = openanexistproject(codes_dir, projects_file)
                return projectname
            elif create_new == "quit":
                quit()
        else:
            return projectname



if __name__ == "__main__":
    print('*******************************************************')
    print('                       CCSQC v1.0                      ')
    print('Author: chongjing.luo@mail.bnu.edu.cn')
    print('Date: 2024-08-30')
    print(" ")
    print(f"** Python version: {sys.version}")

    parser = argparse.ArgumentParser(description="Start the CCSQC application.")
    parser.add_argument("--ProjectName", type=str, default="",
                        help="The name of the project you want to open (e.g., adhd)."
                             " If the project does not exist, it will be created.")
    parser.add_argument("--DeleteProject", type=str, help="The name of the project you want to delete from "
                                                          "settings file, rating files will not delete.")

    args = parser.parse_args()
    codes_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(codes_dir)
    with open("projects.json", 'r') as f:
        projects_file = json.load(f)
        projects = projects_file.get("projects", {})
        last_project = projects_file.get("last_project", "")

    print('-------------------------------------------------------')
    print("** Existing projects:")
    for i, project in enumerate(projects.keys()):
        print(f"  -- {i + 1}. {project}")
    print(f"** last project: {last_project}")
    print('-------------------------------------------------------')

    if args.DeleteProject:
        if args.DeleteProject in projects:
            confirm_delete = input(f"Are you sure you want to delete the project {args.DeleteProject}? (yes/no): ")
            if confirm_delete == "yes":
                del projects[args.DeleteProject]
                if args.DeleteProject == last_project:
                    last_project = ""
                with open("projects.json", 'w') as f:
                    json.dump({"projects": projects, "last_project": last_project}, f, indent=4)
                print(f"Project {args.DeleteProject} deleted.")
            else:
                print(f"Project {args.DeleteProject} not deleted.")
        else:
            print(f"The project {args.DeleteProject} does not exist!")
    else:
        ProjectName = askproject(args.ProjectName)
        root = Tk()
        app = ccsqc(master=root, projectname=ProjectName)
        root.mainloop()
