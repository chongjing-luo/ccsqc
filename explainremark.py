
import json, os, re, glob, inspect
import pandas as pd
from collections import Counter
from builtins import setattr

class RemarkProcessor:
    def __init__(self):
        cwd = os.path.dirname(os.path.abspath(__file__))
        print(f"** Current working directory: {cwd}")
        with open(os.path.join(cwd,'regions.json'), 'r') as json_file:
            regions_info = json.load(json_file)
            self.regions = regions_info.get("regions", {})
            self.lobes_var_si = regions_info.get("vars_lobes_sigle", [])
            self.lobes_var_bi = regions_info.get("vars_lobes", [])
            self.severity_markers = regions_info.get("Severity", [])
            self.errortypes = regions_info.get("errortypes", [])
            self.errortypes_ss = ["OverStrip", "UnderStrip"]

        self.qctypes = ["headmotion", "skullstrip", "reconstruct", "registrate"]
        self.regions_var_si = list(self.regions.keys())
        self.regions_var_bi = [item for pair in zip([f"l_{region}" for region in self.regions], [f"r_{region}" for region in self.regions]) for item in pair]
        self.var_si = self.regions_var_si + self.lobes_var_si
        self.path_dict = {}
        self.results_summary_table_long = None
        self.colvalue = ["Key", "IndexAll", "QCType", "Status","Imgid", "Subid", "Rater","Remark", "CheckDone",
                    "NeedMoreCheck", "NonHeadMotionArtifacts", "ErrorTypes", "Score1", "Score1F", "Score2", "Score2F"] + self.lobes_var_bi + self.regions_var_bi

        self.vars_summary = (["Imgid", "QCType", "Rater", "Status", "Score1F_", "Score1_", "Score1", "Score2F_",
                              "Score2_", "Score2", "NeedMoreCheck", "NonHeadMotionArtifacts", "Remarks"] + self.lobes_var_bi + self.regions_var_bi +
                             ["IndexAll", "Key", "Subid", "Ses", "Run", "CheckDone","listshow","DirType","PresentViewer","RelativePath","Path"])


    def explain_remark(self, remark):

        remarks_lines = [line.strip() for line in remark.split(";")]
        remarks_lines = [' '.join(item.strip() for item in line.split(';')) for line in remarks_lines]
        remarks_lines = [line for line in remarks_lines if line] # 去除空行
        remarks_lines = [line.replace("L R", "B") for line in remarks_lines]
        remarks_lines = [line.replace("R L", "B") for line in remarks_lines]
        remarks_lines = [line.split() for line in remarks_lines] # 将每一行中的各个元素分离开
        print(f"** Explain remarks_lines: {remarks_lines}")

        error_table = []
        error_types = ''
        for line in remarks_lines:
            error_type = None
            index_error_type = None
            for i_et, token_et in enumerate(line):
                if token_et in (self.errortypes + ["OverStrip", "UnderStrip", "OtherNotes"]):
                    error_type = token_et
                    index_error_type = i_et
                    existing_error_types = error_types.split(', ')
                    if error_type not in existing_error_types:
                        if error_types:
                            error_types += f", {error_type}"
                        else:
                            error_types = error_type
                    break
            if error_type == "OtherNotes":
                del line[i_et]
                error_table.append(["OtherNotes", ' '.join(line)])
            elif error_type == 'ExtendTo':
                for i_token in range(0, i_et):
                    token = line[i_token]
                    if token in self.var_si:
                        # 找到token的severity marker
                        severity_marker = None
                        for j in range(i_token + 1, len(line)):
                            if line[j] in self.severity_markers:
                                severity_marker = line[j]
                                break
                        for i_token2 in range(index_error_type + 1, len(line)):
                            token2 = line[i_token2]
                            if token2 in self.var_si:
                                hemi = "B"
                                for j in range(i_token - 1, -1, -1):
                                    if line[j] in ["R", "L", "B"]:
                                        hemi = line[j]
                                        break
                                if hemi == "B":
                                    error_table.append([f"l_{token}", f"{severity_marker} {error_type} l_{token2}"])
                                    error_table.append([f"l_{token2}", f"{severity_marker} ExtendedBy l_{token}"])
                                    error_table.append([f"r_{token}", f"{severity_marker} {error_type} r_{token2}"])
                                    error_table.append([f"r_{token2}", f"{severity_marker} ExtendedBy r_{token}"])

                                else:
                                    hemi_ = f"{hemi.lower()}_"
                                    error_table.append([f"{hemi_}{token}", f"{severity_marker} {error_type} {hemi_}{token2}"])
                                    error_table.append([f"{hemi_}{token2}", f"{severity_marker} ExtendedBy {hemi_}{token}"])
            # skull strip
            elif error_type in self.errortypes_ss:
                for i, token in enumerate(line):
                    if token in self.lobes_var_bi:
                        severity_marker = None
                        for j in range(i + 1, len(line)):
                            if line[j] in self.severity_markers:
                                severity_marker = line[j]
                                break
                        error_table.append([token, f"{severity_marker} {error_type}"])

            else:
                for i, token in enumerate(line):
                    if token in self.var_si:
                        severity_marker = None
                        for j in range(i + 1, len(line)):
                            if line[j] in self.severity_markers:
                                severity_marker = line[j]
                                break
                        hemi = "B"
                        for j in range(i - 1, -1, -1):
                            if line[j] in ["R", "L", "B"]:
                                hemi = line[j]
                                break
                        if hemi == "B":
                            error_table.append([f"l_{token}", f"{severity_marker} {error_type}"])
                            error_table.append([f"r_{token}", f"{severity_marker} {error_type}"])
                        else:
                            error_table.append([f"{hemi.lower()}_{token}", f"{severity_marker} {error_type}"])

        # 当error_table中某些行的region相同时，将其合并
        error_table = self.merge_rows(error_table)
        return error_table, error_types

    def merge_rows(self, table):
        merged_dict = {}
        for row in table:
            key, value = row
            if key in merged_dict:
                merged_dict[key] += f"; {value}"
            else:
                merged_dict[key] = value
        return [[key, value] for key, value in merged_dict.items()]



    def add_to_data_dict(self, entry):
        key = (entry['subid'], entry['ses'], entry['run'])
        if key not in self.path_dict:
            self.path_dict[key] = {}
        self.path_dict[key].update(entry)

    def getlist_bids_dir(self, bids_dir, subjectslist=None):
        pattern_bids = r"sub-(?P<subid>[^_]+)(_ses-(?P<ses>[^_]+))?(_run-(?P<run>[^_]+))?_T1w.nii.gz"
        if subjectslist:
            for key, value in subjectslist.items():
                imgid = value.get("imgid")
                pattern = f"sub-{imgid}_T1w.nii.gz"
                file = glob.glob(os.path.join(bids_dir, "**", pattern), recursive=True)
                if len(file) == 1:
                    self.add_to_data_dict({"subid":key[0], "ses": key[1], "run": key[2], "path_bids_dir": file[0]})
                else:
                    print(f"** Error in get path_dict for bids file: key {key} file {file}")
        else:
            files = glob.glob(os.path.join(bids_dir, '**', '*_T1w.nii.gz'), recursive=True)
            for file in files:
                root, filename = os.path.split(file)
                match = re.match(pattern_bids, filename)
                if match:
                    # 生成数据字
                    entry = {
                        "imgid": filename.replace("_T1w.nii.gz", "").replace("sub-", ""),
                        "subid": match.group("subid"),
                        "ses": match.group("ses") or "01",
                        "run": match.group("run") or "01",
                        "path_bids_dir": file
                    }
                    self.add_to_data_dict(entry)
        print(f"** Get path_dict with in line 265 {len(self.path_dict)} entries")
        return self.path_dict

    def getlist_ccs_dir(self, ccs_dir, subjectslist=None):
        pattern_ccs = r"(?P<subid>[^_]+)(_(?P<ses>[^_]+))?"
        if subjectslist and "relative_path_ccs_dir" in next(iter(subjectslist.values())):
            for key, value in subjectslist.items():
                rela_path = value.get("relative_path_ccs_dir")

                file = os.path.join(ccs_dir, rela_path, "T1.nii.gz")
                if os.path.exists(file):
                    path_ccs_dir = os.path.join(ccs_dir, rela_path)
                    self.add_to_data_dict({"subid": key[0], "ses": key[1], "run": key[2],
                                           "path_ccs_dir": path_ccs_dir, "relative_path_ccs_dir": rela_path})
                else:
                    print(f"** Error in get path_dict for ccs file: key {key} file {file}")
        else:
            for dir_name in os.listdir(ccs_dir):
                subj_match = re.match(pattern_ccs, dir_name)
                if subj_match:
                    subid = subj_match.group("subid")
                    ses = subj_match.group("ses") if subj_match.group("ses") else "01"
                    subj_ccs_dir = os.path.join(ccs_dir, dir_name)
                    if os.path.isdir(subj_ccs_dir):
                        for subj_anat_ccs_dir in os.listdir(subj_ccs_dir):
                            anat_path = os.path.join(subj_ccs_dir, subj_anat_ccs_dir)
                            if subj_anat_ccs_dir.startswith("anat") and os.path.exists(os.path.join(anat_path, "T1.nii.gz")):
                                run = subj_anat_ccs_dir[4:] if subj_anat_ccs_dir[4:].isdigit() else "01"
                                relatve_path = os.path.join(dir_name, subj_anat_ccs_dir)
                                self.add_to_data_dict({
                                    "subid": subid, "ses": ses, "run": run,
                                    "path_ccs_dir": anat_path, "relative_path_ccs_dir": relatve_path
                            })
        print(f"** Get path_dict with in line 295 {len(self.path_dict)} entries")
        return self.path_dict

    def getlist_subject_dir(self, subject_dir, subjectslist=None):
        pattern_ccs = r"(?P<subid>[^_]+)(_(?P<ses>[^_]+))?"
        if subjectslist and "relative_path_subject_dir" in next(iter(subjectslist.values())):  # 判断是否有 relative_path_ccs_dir

            for key, value in subjectslist.items():
                rela_path = value.get("relative_path_subject_dir")
                file = os.path.join(subject_dir, rela_path, "surf", "rh.pial")
                if os.path.exists(file):
                    path_subject_dir = os.path.join(subject_dir, rela_path)
                    self.add_to_data_dict({"subid": key[0], "ses": key[1], "run": key[2],
                                           "path_subject_dir": path_subject_dir, "relative_path_subject_dir": rela_path})
                else:
                    print(f"** Error in get path_dict for subject file: key {key} file {file}")
        else:
            for dir_name in os.listdir(subject_dir):
                subj_match = re.match(pattern_ccs, dir_name)
                if subj_match:
                    subid = subj_match.group("subid")
                    ses = subj_match.group("ses") or "01"
                    subj_dir = os.path.join(subject_dir, dir_name)
                    if os.path.exists(os.path.join(subj_dir, "surf", "rh.pial")):
                        self.add_to_data_dict({
                            "subid": subid, "ses": ses, "run": "01",
                            "path_subject_dir": subj_dir, "relative_path_subject_dir": dir_name
                        })
                    elif os.path.isdir(subj_dir):
                        for anat_dir in os.listdir(subj_dir):
                            path_pial = os.path.join(subj_dir, anat_dir, "surf", "rh.pial")
                            if anat_dir.startswith("anat") and os.path.exists(path_pial):
                                run = anat_dir[4:] if anat_dir[4:].isdigit() else "01"
                                anat_path = os.path.join(subj_dir, anat_dir)
                                self.add_to_data_dict({
                                    "subid": subid, "ses": ses, "run": run,
                                    "path_subject_dir": anat_path,
                                    "relative_path_subject_dir": os.path.join(dir_name, anat_dir)
                                })
        print(f"** Get path_dict with in line 331 {len(self.path_dict)} entries")
        return self.path_dict

    def getlist_mriqc_dir(self, mriqc_dir, subjectslist=None):
        pattern_mriqc = r"sub-(?P<subid>[^_]+)(_ses-(?P<ses>[^_]+))?(_run-(?P<run>[^_]+))?_T1w.html"
        if subjectslist:
            for key, value in subjectslist.items():
                imgid = value.get("imgid")
                pattern = f"sub-{imgid}_T1w.html"
                file = os.path.join(mriqc_dir, pattern)
                if os.path.exists(file):
                    self.add_to_data_dict({"subid": key[0], "ses": key[1], "run": key[2], "path_mriqc_dir": file[0]})
                else:
                    print(f"** Error in get path_dict for mriqc file: key {key} file {file}")
        else:
            files = glob.glob(os.path.join(mriqc_dir, '*_T1w.html'))
            for file in files:
                filename = os.path.basename(file)
                match = re.match(pattern_mriqc, filename)

                if match:
                    # 提取匹配的组
                    subid = match.group("subid")
                    ses = match.group("ses") or "01"
                    run = match.group("run") or "01"

                    # 生成数据字典
                    entry = {
                        "imgid": filename.replace("_T1w.html", "").replace("sub-", ""),
                        "subid": subid,
                        "ses": ses,
                        "run": run,
                        "path_mriqc_dir": os.path.abspath(file)
                    }

                    # 添加到数据字典
                    self.add_to_data_dict(entry)
        print(f"** Get path_dict with in line 367 {len(self.path_dict)} entries")
        return self.path_dict

    def process_list_dir(self, list_dir):
        path_dict_out = {}

        # 判断是csv文件还是txt文件
        if list_dir.endswith('.csv'):
            df = pd.read_csv(list_dir)
        else:
            with open(list_dir, 'r') as f:
                lines = f.read().splitlines()
            columns = lines[0].split(',')
            data = [line.split(',') for line in lines[1:]]
            df = pd.DataFrame(data, columns=columns)

        # 去掉列名的前后空格
        df.columns = df.columns.str.strip()

        # 给df增加一列index
        df['index'] = range(len(df))

        # 定义优化的正则表达式模式
        pattern_bids = r"(?P<subid>[^_]+)(_ses-(?P<ses>\d+))?(_run-(?P<run>\d+))?"
        pattern_ccs = r"^(?P<subid>[^_/]+)(_(?P<ses>\d+))?/anat(?P<run>\d+)?$"
        pattern_subj = r"^(?P<subid>[^_/]+)(_(?P<ses>\d+))?(/anat(?P<run>\d+)?)?$"

        # 统一在一次循环中处理所有列
        for col in df.columns:
            if col == "relative_path_subject_dir":
                for i, row in df.iterrows():
                    index = row['index']
                    relative_path = row[col].strip()
                    match = re.match(pattern_subj, relative_path)
                    if match:
                        subid = match.group("subid")
                        ses = match.group("ses") or "01"
                        run = match.group("run") or "01"
                        if index not in path_dict_out:
                            path_dict_out[index] = {}
                        path_dict_out[index].update({
                            "relative_path_subject_dir": relative_path,
                            "subid": subid,
                            "ses": ses,
                            "run": run
                        })

            elif col == "relative_path_ccs_dir":
                for i, row in df.iterrows():
                    index = row['index']
                    relative_path = row[col].strip()
                    match = re.match(pattern_ccs, relative_path)
                    if match:
                        subid = match.group("subid")
                        ses = match.group("ses") or "01"
                        run = match.group("run") or "01"
                        if index not in path_dict_out:
                            path_dict_out[index] = {}
                        path_dict_out[index].update({
                            "relative_path_ccs_dir": relative_path,
                            "subid": subid,
                            "ses": ses,
                            "run": run
                        })

            elif col == "imgid":
                for i, row in df.iterrows():
                    index = row['index']
                    match = re.match(pattern_bids, row[col])
                    if match:
                        subid = match.group("subid")
                        ses = match.group("ses") or "01"
                        run = match.group("run") or "01"
                        if index not in path_dict_out:
                            path_dict_out[index] = {}
                        path_dict_out[index].update({
                            "imgid": row[col],
                            "subid": subid,
                            "ses": ses,
                            "run": run
                        })

        # 删除原有的键index,并将subid, ses, run作为键,imgid,relative_path_subject_dir,relative_path_ccs_dir作为值
        final_path_dict_out = {}
        for index, value in path_dict_out.items():
            subid = value.get("subid")
            ses = value.get("ses")
            run = value.get("run")
            final_path_dict_out[(subid, ses, run)] = {col: value.get(col) for col in df.columns if col in value}

        return final_path_dict_out


    def save_as_json(self, df, json_path):
        # 获取 DataFrame 的列名
        columns = df.columns.tolist()

        # 将列名保存到一个字典中
        columns_dict = {"columns": columns}

        # 将字典保存为 JSON 文件
        with open(json_path, 'w') as json_file:
            json.dump(columns_dict, json_file, indent=4)


    def splitSelectFilterText(self, navardf, filters):
        """
        将筛选条件字符串拆分为多个条件
        :param filters:
        :return: 返回一个字典，存储了变量选择和筛选条件的解释文本
        """
        print(f"** {inspect.currentframe().f_lineno}  filters: {filters}")
        # ################   第一步，将筛选条件字符串拆分为多个条件
        pattern = r'(\n\*\* SelectVar:|\n\*\* FilterPoint:|\*\* SelectVar:|\*\* FilterPoint:)'
        filters = f"** FilterPoint:  {filters}"
        split_conditions = re.split(pattern, filters)[1:]  # 去掉第一个空白匹配项
        print(f"** split_conditions {inspect.currentframe().f_lineno} : {split_conditions}")
        conditions = list(zip(split_conditions[::2], split_conditions[1::2]))

        #  ###############   第二步，进一步清洗各个条件

        # 初始化字典
        explanation_text_all = {}
        explanation_text_all['SelectVar'] = {}
        explanation_text_all['FilterPoint'] = {}
        idx_filter = 0

        for i, (key, value) in enumerate(conditions):
            value = value.strip()

            # 处理变量选择情况，只获得选择和排除文本而不是实际的数据
            if key in ["** SelectVar:", "\n** SelectVar:"]:
                # print(f"** {inspect.currentframe().f_lineno} SelectVar: {value}")
                # 把value按空格分割成一个列表，检测是否在df的列中，如果在则保留，否则报错
                explanation_text_all['SelectVar'] = self.explainSelect(navardf, value)

            # 处理筛选条件情况，执行筛选操作并生成解释文本
            elif key in ["** FilterPoint:", "\n** FilterPoint:"]:
                if value.strip() == '':  # 修复可能导致跳过条件的情况
                    explanation_text_all['FilterPoint'][f"FilterPoint {idx_filter}"] = ''
                    idx_filter += 1
                    continue

                explanation_text_all['FilterPoint'][f"FilterPoint {idx_filter}"] = value  # 更新字典，而不是重新赋值
                print(f"** {inspect.currentframe().f_lineno}  explanation_text_all {explanation_text_all}")
                idx_filter += 1
            else:
                raise ValueError(f"Unknown filter type: {key}")

        # 删除df_filtered[f"FilterPoint {-1}"], 将explanation_text_all的FilterPoint 0 字段的名字改为'Initial Inclusion'
        if 'FilterPoint 0' in explanation_text_all['FilterPoint']:
            explanation_text_all['FilterPoint']['Initial Inclusion'] = explanation_text_all['FilterPoint'].pop('FilterPoint 0')

        print(f"** {inspect.currentframe().f_lineno}  explanation_text_all: {explanation_text_all}")
        return explanation_text_all



    def selectVar(self, df, vars_summary):
        # 将变量名按照空格拆分,
        print(f"** {inspect.currentframe().f_lineno}  SelectVar: {vars_summary}")
        selected_vars = vars_summary.split()
        selected_vars = [var for var in selected_vars if var in df.columns]
        df = df[selected_vars]
        return df

    def explainSelect(self, navardf, value):
        """
        解释选择变量的操作
        """
        print(f"** {inspect.currentframe().f_lineno}  SelectVar: {value}")
        explanation_text = {}
        value2 = value.split()

        # 如果value2里面存在NOT include，则将两个字符合成一个字符串
        for i in range(len(value2) - 1, 0, -1):
            if value2[i] == "include" and value2[i - 1] == "NOT":
                value2[i - 1] = "NOT include"
                value2.pop(i)

        if value2[0] not in ["include" 'NOT include']:
            value2 = ["include"] + value2

        # 更改集合变量
        for var in value2:
            if var == 'OtherVars':
                index = value2.index(var)
                value2.pop(index)
                othervalue = list(set(navardf) - set(self.colvalue))
                for v in reversed(othervalue):
                    value2.insert(index, v)
            elif var == 'Regions':
                index = value2.index(var)
                value2.pop(index)
                for v in reversed(self.regions_var_bi):
                    value2.insert(index, v)
            elif var == 'Lobes':
                index = value2.index(var)
                value2.pop(index)
                for v in reversed(self.lobes_var_bi):
                    value2.insert(index, v)
        print(f"** {inspect.currentframe().f_lineno}  SelectVar: {value2}")

        value3 = []
        i = 0
        while i < len(value2):
            if value2[i] == "}":
                for j in range(i, -1, -1):
                    if value2[j] == "{":
                        # 将括号内的内容展开并添加到 value3
                        value3.extend(value2[j + 1:i])

                        # 删除从 '{' 到 '}' 的内容，包括这两个符号本身
                        del value2[j:i + 1]

                        # 调整 i 的位置以继续处理后续的内容
                        i = j - 1
                        break
            i += 1

        # 在处理完所有括号内容后，进行 var_sort 和 var_ascend 的处理
        print(f"** {inspect.currentframe().f_lineno}  Value3: {value3}")
        var2rank = []
        var_ascend = []
        for j in range(len(value3)):
            token = value3[j]
            # print(f"** {inspect.currentframe().f_lineno}  Token: {token}")
            if token not in ["0", "1"]:
                var2rank.append(token)
                if j + 1 < len(value3) and value3[j + 1] == "0":
                    var_ascend.append(False)
                else:
                    var_ascend.append(True)  # 默认升序

        # 从后往前遍历value2中的每个token，找这个token上一个的NOT include或include，然后将其存储到valueinclude或valueexclude中
        # print(f"** {inspect.currentframe().f_lineno}  navardf: {navardf}")
        valueinclude = []
        valueexclude = []
        for i in range(len(value2) - 1, 0, -1):
            if value2[i] not in ["include", "NOT include"]:
                if value2[i] in navardf:
                    for j in range(i - 1, -1, -1):
                        if value2[j] in ["include", "NOT include"]:
                            if value2[j] == "include":
                                valueinclude.append(value2[i])
                            else:
                                valueexclude.append(value2[i])
                            break
                else:
                    raise ValueError(f"Unknown variable: {value2[i]}")
            else:
                continue  # Skip 'include' and 'NOT include' at this stage

        explanation_text['include'] = valueinclude[::-1]  # 更新字典，而不是重新赋值
        explanation_text['Not include'] = valueexclude[::-1]   # 更新字典，而不是重新赋值
        explanation_text['var2rank'] = var2rank
        explanation_text['var_ascend'] = var_ascend

        return explanation_text


    def filterExplainPoint(self, df, filter_point):
        """
        解析并执行复杂的布尔表达式，生成标准化的解释和操作步骤
        """
        print(f"** {inspect.currentframe().f_lineno}  FilterPoint_before: {filter_point}")
        # 将字符串先转化为列表形式
        tokens = self.tokenClean(filter_point)

        # 进行布尔计算
        tokens2, boolall = self._BoolCal(df, tokens)

        # 使用boolall对df进行过滤
        filtered_df = df[boolall]

        return filtered_df

    def tokenClean(self, expression):
        """
        将布尔表达式字符串转换为标记列表
        """
        # 使用正则表达式拆分表达式，并识别逻辑操作符
        tokens = re.findall(
            r'\s+|\[|\]|\(|\)|,|:|\'|\"|\{|\}|>>|==|!=|>=|<=|>|<|\bAND\b|\bOR\b|\bNOT\b|\bin\b|\binclude\b|'
            r'\^\w[\w\-_]*\$|\^[\w\-_]+\.\*|\.\*[\w\-_]+\$|\.\*[\w\-_]+\.\*|\^[\w\-_]*|[\w\-_]+\$|[\w\.\*\-_]+',
            expression,
            flags=re.IGNORECASE
        )

        # 删除空白字符
        tokens = [token.strip() for token in tokens if not token.isspace()]

        print(f"** {inspect.currentframe().f_lineno}  Tokenize: {tokens}")
        # 从后往前遍历token，如果发现了' 或者“，则找到另一个' 或者“，然后将两者之间的token合并成一个元素
        i = len(tokens) - 1
        while i > 0:
            if tokens[i] in ["'", '"']:
                j = i - 1
                while j >= 0 and tokens[j] not in ["'", '"']:
                    j -= 1
                if j >= 0:
                    # 将引号和其之间的内容合并成一个字符串
                    tokens[j:i + 1] = [' '.join(tokens[j+1:i])]
                    # 调整索引，避免越界错误
                    i = j
            i -= 1

        print(f"** {inspect.currentframe().f_lineno}  Tokenize_after: {tokens}")

        # 遍历token，如果include和in前面是NOT，则两个token合并，然后删除后一个token
        for i in range(len(tokens) - 1, 0, -1):
            if tokens[i].lower() in ['include', 'in']:
                if tokens[i - 1].lower() == 'not':
                    tokens[i - 1] = f'NOT {tokens[i]}'
                    tokens.pop(i)
            elif tokens[i] in [',','"', "'"]:
                tokens.pop(i)
        print(f"** {inspect.currentframe().f_lineno}  Tokenize: {tokens}")
        return tokens

    def _BoolCal(self, df, tokens):
        nbool = 1
        tokens2 = tokens.copy()
        bool_dict = {}

        # 倒序进行布尔变量替换
        for i in range(len(tokens) - 1, -1, -1):
            token = tokens[i]
            if token in ['==', '!=', '>=', '<=', '>', '<', 'NOT in', 'in', 'NOT include', 'include']:
                var = tokens[i - 1]
                if tokens[i + 1] == '[':
                    j = i + 2
                    while tokens[j] != ']':
                        j += 1
                    value = tokens[i + 2:j]
                    indexlast = j
                else:
                    value = tokens[i + 1]
                    indexlast = i + 1

                # 执行替换
                bool_vector = self.filterData(df, var, token, value)
                bool_name = f"bool{nbool}"
                setattr(self, bool_name, bool_vector)
                bool_dict[bool_name] = bool_vector  # 将布尔向量存入字典
                # print(f"** {inspect.currentframe().f_lineno}  {bool_name}: {bool_vector}")
                tokens2[i - 1:indexlast + 1] = [bool_name]
                nbool += 1

        # 倒序进行括号的检测和删除
        for i in range(len(tokens2) - 1, 0, -1):
            token = tokens2[i]
            if token.startswith('bool'):
                if i > 0 and i < len(tokens2) - 1:
                    if tokens2[i - 1] == '(' and tokens2[i + 1] == ')':
                        tokens2.pop(i + 1)  # 删除右侧括号
                        tokens2.pop(i - 1)  # 删除左侧括号

        # 如果里面的有AND OR NOT,则进行替换，若没有，ballall为bool1
        if 'AND' in tokens2 or 'OR' in tokens2 or 'NOT' in tokens2:
            # 将列表转换为一个字符串表达式
            expression_str = ' '.join(tokens2)
            expression_str = expression_str.replace('AND', '&').replace('OR', '|').replace('NOT', '~')
            print(f"Evaluating expression: {expression_str}")

            # 使用 eval 来执行这个表达式
            try:
                boolall = eval(expression_str, {}, bool_dict)
            except Exception as e:
                raise ValueError(f"Error evaluating expression: {expression_str}") from e
        else:
            boolall = bool_dict['bool1']

        # print(f"** {inspect.currentframe().f_lineno} Tokens {tokens} Tokenize2: {tokens2}, boolall: {boolall}")
        print(f"** {inspect.currentframe().f_lineno} Tokens {tokens} Tokenize2: {tokens2}")
        return tokens2, boolall

    def filterData(self, df, var, calc, value):
        """
        对df的某个变量var执行一个条件calc，判断其是否满足给定的value，返回一个布尔向量。
        """
        print(f"** {inspect.currentframe().f_lineno} FilterData: var={var}, calc={calc}, value={value}")

        # 处理各种计算符号
        if calc in ['==', '!=', '>', '<', '>=', '<=']:
            # 根据var列的类型调整value的类型
            if df[var].dtype == 'object':
                value = str(value)
            elif df[var].dtype == 'int':
                value = int(value)
            elif df[var].dtype == 'float':
                value = float(value)
            else:
                raise ValueError(f"Unsupported data type: {df[var].dtype}")

            # 根据calc生成布尔向量
            if calc == '==':
                condition = df[var].fillna(float('inf')) == value
            elif calc == '!=':
                condition = df[var].fillna(float('inf')) != value
            elif calc == '>':
                condition = df[var].fillna(float('-inf')) > value
            elif calc == '<':
                condition = df[var].fillna(float('inf')) < value
            elif calc == '>=':
                condition = df[var].fillna(float('-inf')) >= value
            elif calc == '<=':
                condition = df[var].fillna(float('inf')) <= value

        elif calc in ['in', 'NOT in']:
            # 检查value是否是一个列表，如果不是则转化为列表
            if not isinstance(value, list):
                value = [value]
            value_new = self.explainin(df, var, value)
            print(f"** Final value_new: {value_new}")
            if calc == 'in':
                condition = df[var].isin(value_new)
            elif calc == 'NOT in':
                condition = ~df[var].isin(value_new)

        elif calc in ['include', 'NOT include']:
            if not isinstance(value, str):
                raise ValueError(f"For '{calc}' operation, value should be a string.")
            if calc == 'include':
                condition = df[var].str.contains(value, na=False)
            elif calc == 'NOT include':
                condition = ~df[var].str.contains(value, na=False)

        else:
            raise ValueError(f"Unsupported calculation: {calc}")

        print(f"** {inspect.currentframe().f_lineno} filterData finished")
        return condition

    def explainin(self, df, var, value):
        """解释in操作符"""
        print(f"** {inspect.currentframe().f_lineno}  Explainin: var={var}, value={value}")
        #  #################        开始处理       ##################
        value = [v for v in value if v not in ['[', ']', ',']]
        if pd.api.types.is_numeric_dtype(df[var]):
            var_value = df[var].fillna(float('inf'))
            var_type = 'numeric'
        else:
            var_value = df[var].fillna('')
            var_type = 'string'
        # 对var_value进行排序
        var_value = var_value.sort_values().tolist()

        tmp_value = []
        i = len(value) - 1
        while i >= 0:

            # 首先，处理单个位置索引的情况
            if value[i] == '}':
                print(f"** {inspect.currentframe().f_lineno} value: {value}")
                idx_value = []
                # 找到}前面上一个{及其位置，获取之间的值，但不包括{和}
                for idx in range(i, -1, -1):
                    if value[idx] == '{':
                        idx_value += value[idx + 1:i]
                        break
                idx_value = [int(v) for v in idx_value]
                if max(idx_value) >= len(var_value):
                    raise ValueError(f"Index out of range: {max(idx_value)} >= {len(var_value)}")

                tmp_value += [var_value[v] for v in idx_value if v < len(var_value)]
                print(f"** {inspect.currentframe().f_lineno} tmp_value: {tmp_value}")
                # 删除value中的}及其前面的{及其之间的值
                del value[idx:i + 1]
                i = idx - 1  # 调整索引，继续向前

            # 第二，处理首个元素和最后一个元素的情况
            elif value[i] == '>>':
                pattern_before = re.compile(value[i - 1])
                pattern_after = re.compile(value[i + 1])

                value_before = [item for item in var_value if pattern_before.match(item)]
                value_before = sorted(value_before)
                value_before_last = value_before[-1]

                value_after = [item for item in var_value if pattern_after.match(item)]
                value_after = sorted(value_after)
                value_after_1st = value_after[0]

                # 找到var_value中的value_before和value_after的索引，并获取之间的值，包括value_before和value_after，tmp_value
                index_before = var_value.index(value_before_last)
                index_after = var_value.index(value_after_1st)
                tmp_value += var_value[index_before:index_after] + value_before + value_after

                del value[i - 1:i + 2]
                i -= 2  # 调整索引，继续向前

            # 第三，处理范围索引的情况
            elif value[i] == ':':
                # 提取:前后两个,并转化为整数
                value_before = int(value[i - 1])
                value_after = int(value[i + 1])
                tmp_value += var_value[value_before:value_after + 1]

                del value[i - 1:i + 2]
                i -= 2  # 调整索引，继续向前
            i -= 1  # 无论如何，索引都要递减

        # 第四，处理剩余的value
        for i in range(len(value) - 1, -1, -1):
            # 单个数字，直接添加到tmp_value
            if value[i].isdigit():
                tmp_value += [value[i]]

            else:
                pattern = re.compile(value[i])
                tmp_value += [item for item in var_value if pattern.match(item)]

            del value[i]

        # print(f"** {inspect.currentframe().f_lineno} tmp_value: {tmp_value}")
        if var_type == 'numeric':
            tmp_value.extend([int(v) for v in value if v.isdigit()])
        elif var_type == 'string':
            tmp_value.extend(value)

        print(f"** {inspect.currentframe().f_lineno}  Explainin: finished")
        tmp_value = list(set(tmp_value))  # 排除重复的元素
        return tmp_value

    def sort_pdDataFrame_col(self, df, SelectVar):
        include = SelectVar.get('include', [])
        Notinclude = SelectVar.get('Not include', [])
        var2rank = SelectVar.get('var2rank', []).copy()  # 使用 copy() 方法创建副本
        var_ascend = SelectVar.get('var_ascend', []).copy()
        print(f"** {inspect.currentframe().f_lineno}  SelectVar: {SelectVar}")

        # Use list comprehensions to remove elements from the list
        vars_summary = self.vars_summary
        if Notinclude:
            vars_summary = [var for var in vars_summary if var not in Notinclude]

        if include:
            vars_summary = [var for var in vars_summary if var not in include]
            vars_summary = include + vars_summary


        # 获取当前 DataFrame 的列名
        current_columns = df.columns.tolist()
        new_column_order = []
        seen_columns = set()  # 用于跟踪已经添加的列名

        # 遍历 vars_summary 中的每个变量名
        for var in vars_summary:
            # 找到所有以该变量名开头的列名
            matching_columns = [col for col in current_columns if col.startswith(var)]
            # 将这些列名添加到新的列名顺序列表中，避免重复
            for col in matching_columns:
                if col not in seen_columns:
                    new_column_order.append(col)
                    seen_columns.add(col)

        # 根据新的列名顺序重新排列 DataFrame 的列
        sorted_df = df[new_column_order]

        # 如果 'QCType' 在 new_column_order 中，按新的序号列排序
        sorted_df = sorted_df.copy()  # 确保 sorted_df 是一个副本

        # 保证var2rank不为空，且每个在new_column_order中
        var2rank = ["Imgid", "QCType"] if var2rank == [] else var2rank
        var_ascend = [True, True] if var2rank == ["Imgid", "QCType"] else var_ascend
        for i in range(len(var2rank) - 1, -1, -1):
            var = var2rank[i]
            if var not in new_column_order:
                var2rank.pop(i)
                var_ascend.pop(i)
        # print(f"** {inspect.currentframe().f_lineno}  var2rank: {var2rank}")

        if 'QCType' in var2rank:
            # 创建 QCType 的映射，生成 QCType_order 列
            qctype_mapping = {qctype: i for i, qctype in enumerate(self.qctypes)}
            sorted_df.loc[:, 'QCType_order'] = sorted_df['QCType'].map(qctype_mapping)
            var2rank = ['QCType_order' if col == 'QCType' else col for col in var2rank]
            print(f"** {inspect.currentframe().f_lineno}  var2rank: {var2rank} var_ascend: {var_ascend}")
            sorted_df = sorted_df.sort_values(by=var2rank, ascending=var_ascend)
            sorted_df = sorted_df.drop(columns='QCType_order')
        elif not var2rank:
            sorted_df = sorted_df.sort_values(by='Imgid', ascending=True)
        else:
            sorted_df = sorted_df.sort_values(by=var2rank, ascending=var_ascend)

        # print(f"{inspect.currentframe().f_lineno} SelectVar {SelectVar}")

        return sorted_df


    def flatten_dict(self, nested_dict):
        """
        将三层嵌套字典展平为二层字典，并删除以 'Rater' 和 'QCType' 开头的字段。
        """
        flat_dict = {}
        for outer_key, inner_dict in nested_dict.items():
            for inner_key, values in inner_dict.items():
                # 保持第一层的键不变
                if outer_key not in flat_dict:
                    flat_dict[outer_key] = {}

                # 合并第二层的键
                for key, value in values.items():
                    # 构建新的键名
                    if key not in ["IndexAll", "Imgid", "Subid", "Ses", "Run"]:
                        new_key = f"{key}_{inner_key}"
                    else:
                        new_key = key

                    # 删除以 'Rater' 和 'QCType' 开头的字段
                    if not (key.startswith('Rater') or key.startswith('QCType')):
                        flat_dict[outer_key][new_key] = value

        return flat_dict

    def merge_results(self, df_input, summary):
        df_output = df_input.copy()

        def merge_scores(values, merge_method):
            # 剔除空值
            values = [value for value in values if value is not None]
            numvalue = len(values)
            if numvalue == 0:
                return None
            elif numvalue == 1:
                return values[0]
            else:
                if merge_method == "mean":
                    return sum(values) / numvalue
                elif merge_method == "max":
                    return max(values)
                elif merge_method == "min":
                    return min(values)
                elif merge_method == "vote":
                    return Counter(values).most_common(1)[0][0]


        # 获得所有imgid的名单
        for qc_type in summary["summary_incld"]:
            if summary["summary_incld"][qc_type] == 1:
                imgids = list(df_input[df_input['QCType'] == qc_type]['Imgid'].unique())
                merge_method = summary["presentMergeMethod"][qc_type]
                if merge_method:
                    for imgid in imgids:
                        # df_input中找出QCTypes为qc_type，Imgid为imgid的行的索引
                        idx = df_input[(df_input['QCType'] == qc_type) & (df_input['Imgid'] == imgid)].index
                        value = df_input.loc[idx, 'Score1'].tolist()
                        df_output.loc[idx, f"Score1F"] = merge_scores(value, merge_method)
                        value = df_input.loc[idx, 'Score2'].tolist()
                        df_output.loc[idx, f"Score2F"] = merge_scores(value, merge_method)
                else:
                    print(f"** No merge method for {qc_type}")

        return df_output


    def dflong2wide(self, long_df, index_column='Imgid', pivot_columns=['QCType', 'Rater']):
        # 确保对于每个 ImgID，keep_columns 中的值是一致的
        keep_columns = ["Key", "Subid", "Ses", "Run", "IndexAll"]
        # 这一步假设数据已经是预期的格式，如有需要应进行数据清洗保证一致性
        first_values = long_df.groupby(index_column)[keep_columns].first().reset_index()

        # 将需要保留的列移除，避免重复
        long_df = long_df.drop(columns=keep_columns)

        # 使用 pivot 将长格式转换为宽格式
        wide_df = long_df.pivot(index=index_column, columns=pivot_columns)

        # 展平多级列索引，并生成新的列名
        wide_df.columns = [f"{col[0]}_{col[1]}_{col[2]}" for col in wide_df.columns.values]

        # 重置索引，以便列名整齐
        wide_df.reset_index(inplace=True)

        # 将 keep_columns 的数据合并回来
        wide_df = pd.merge(wide_df, first_values, on=index_column, how='left')
        print(f"** Long DataFrame transformed to Wide DataFrame")
        return wide_df

    def get_dict_depth(self, d):
        """获取字典的深度"""
        if not isinstance(d, dict) or not d:
            return 0
        else:
            return 1 + max(self.get_dict_depth(v) for v in d.values())

    def convert_deep_dict(self, dictionary, parent_key='', level=1, max_depth=2):
        """递归地将深度大于2的字典转换为深度为2的字典"""
        new_dict = {}

        for key, value in dictionary.items():
            # 组合当前层的键名
            new_key = f"{parent_key}_{key}" if parent_key else key

            if isinstance(value, dict) and level < max_depth:
                # 递归处理嵌套字典，直到达到 max_depth
                deeper_dict = self.convert_deep_dict(value, new_key, level + 1, max_depth)
                new_dict.update(deeper_dict)
            else:
                # 如果达到最大深度或值不是字典，直接赋值到新的字典中
                new_dict[new_key] = value

        # print(f"** {inspect.currentframe().f_lineno} New dict: {new_dict}")
        return new_dict

    def dict_to_df(self, dict, sort_keys=None):
        """将深度为2的字典转换为行列表"""

        all_keys = list({k for d in dict.values() for k in d.keys()})
        rows = []
        for key, value in dict.items():
            row = [key] + [value.get(column, None) for column in all_keys]
            rows.append(row)

        if sort_keys:
            rows.sort(key=lambda x: tuple(x[all_keys.index(k) + 1] for k in sort_keys))
        elif sort_keys == 0:
            rows.sort(key=lambda x: x[0])

        df = pd.DataFrame(rows, columns=["Key"] + all_keys)
        return df

    def save_df_to_csv(self, df, ptdf_csv, ptdict_json=None):
        """保存DataFrame为CSV文件"""
        if ptdf_csv:
            # 如果csv路径只有一层，则从json路径获取基础路径
            if len(ptdf_csv.split("/")) == 1 and ptdict_json:
                ptdf_csv = os.path.join(os.path.dirname(ptdict_json), ptdf_csv)
            if os.path.exists(ptdf_csv):
                os.remove(ptdf_csv)
            df.to_csv(ptdf_csv, index=False)
            print(f"** Save DataFrame to {ptdf_csv}")

    def save_dict_to_json(self, data, ptdict_json, ptdf_csv=None):
        """保存字典为JSON文件"""
        if ptdict_json:
            # 如果json路径只有一层，则从csv路径获取基础路径
            if len(ptdict_json.split("/")) == 1 and ptdf_csv:
                ptdict_json = os.path.join(os.path.dirname(ptdf_csv), ptdict_json)
            if os.path.exists(ptdict_json):
                os.remove(ptdict_json)
            with open(ptdict_json, 'w') as file:
                json.dump(data, file, indent=4)
            print(f"** Save dict to {ptdict_json}")

    def save_dict_as_csv(self, data, ptdf_csv=None, sort_keys=None, ptdict_json=None):
        """主函数：保存字典为CSV或JSON文件"""
        if isinstance(data, dict):
            depth = self.get_dict_depth(data)
            if depth >= 2:
                # 将字典转换为新的字典，前两层的键名作为新字典的键名
                new_dict = self.convert_deep_dict(data) if depth > 2 else data
                df = self.dict_to_df(new_dict, sort_keys)
                self.save_df_to_csv(df, ptdf_csv, ptdict_json)
                self.save_dict_to_json(data, ptdict_json, ptdf_csv)
                return df, data
            else:
                print("Dictionary depth is 1 or less, no conversion necessary.")
                return None, data

        elif isinstance(data, pd.DataFrame):
            self.save_df_to_csv(data, ptdf_csv)
            return data, None

        print("Unsupported data type")
        return None, None
