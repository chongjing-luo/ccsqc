import subprocess, os #, webbrowser
from tkinter import messagebox

class QCViewer:
    def __init__(self, qc_type, path, presentdir, presentviewer,current_process=None):
        self.qc_type = qc_type
        self.path = path
        self.QC_DIR_type = presentdir
        self.Viewer_type = presentviewer
        self.current_process = current_process
        print(f"Opening Image: dirtype: {presentdir}; path: {path}")

    def start_viewing(self):

        self.terminate_current_process()
        if self.qc_type == "headmotion":
            if self.QC_DIR_type == "ccs_dir":
                if self.Viewer_type == "mricron":
                    self.open_Headmotion_CCS_mricron()
                elif self.Viewer_type == "fsleyes":
                    self.open_Headmotion_CCS_fsleye()
                elif self.Viewer_type == "freeview":
                    self.open_Headmotion_CCS_freeview()
                else:
                    messagebox.showerror(f"Error", "不支持使用{Viewer_type}打开本图像！")
            elif self.QC_DIR_type == "bids_dir":
                if self.Viewer_type == "mricron":
                    self.open_Headmotion_BIDS_mricron()
                elif self.Viewer_type == "fsleyes":
                    self.open_Headmotion_BIDS_fsleye()
                elif self.Viewer_type == "freeview":
                    self.open_Headmotion_BIDS_freeview()
                else:
                    messagebox.showerror(f"Error", "不支持使用{Viewer_type}打开本图像！")
            elif self.QC_DIR_type == "subject_dir":
                if self.Viewer_type == "mricron":
                    self.open_Headmotion_SUBJECT_mricron()
                elif self.Viewer_type == "fsleyes":
                    self.open_Headmotion_SUBJECT_fsleye()
                elif self.Viewer_type == "freeview":
                    self.open_Headmotion_SUBJECT_freeview()
                else:
                    messagebox.showerror(f"Error", "不支持使用{Viewer_type}打开本图像！")
            elif self.QC_DIR_type == "mriqc_dir":
                if self.Viewer_type == "mriqc":
                    self.open_Headmotion_MRIQC()
                else:
                    messagebox.showerror("Error", "请先选择mriqc作为Viewer！")

        elif self.qc_type == "skullstrip":
            if self.QC_DIR_type == "ccs_dir":
                if self.Viewer_type == "mricron":
                    self.open_SkullStripping_CCS_mricron()
                elif self.Viewer_type == "fsleyes":
                    self.open_SkullStripping_CCS_fsleye()
                elif self.Viewer_type == "freeview":
                    self.open_SkullStripping_CCS_freeview()
            elif self.QC_DIR_type == "subject_dir":
                if self.Viewer_type == "mricron":
                    self.open_SkullStripping_SUBJECT_mricron()
                elif self.Viewer_type == "fsleyes":
                    self.open_SkullStripping_SUBJECT_fsleye()
                elif self.Viewer_type == "freeview":
                    self.open_SkullStripping_SUBJECT_freeview()
            # else:
            #     messagebox.showerror("Error", "暂不支持，尽情期待！")
        elif self.qc_type == "reconstruct":
            if self.QC_DIR_type == "subject_dir" and self.Viewer_type == "freeview":
                self.open_Reconall_freesurfer()
            elif self.QC_DIR_type == "subject_dir" and self.Viewer_type == "freeviewLabel":
                self.open_Reconall_FSVisualQC()
            elif self.QC_DIR_type == "subject_dir" and self.Viewer_type == "freeviewFlat":
                self.open_Reconall_freesurfer_flat()
            else:
                messagebox.showerror("Error", "暂不支持，尽情期待！")
        elif self.qc_type == "registrate":
            messagebox.showerror("Error", "暂不支持，尽情期待！")

        return self.current_process

    def terminate_current_process(self):
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.current_process.wait()
            self.current_process = None

    def open_Headmotion_CCS_mricron(self):
        t1_image = os.path.join(self.path, "T1.nii.gz")
        if os.path.exists(t1_image):
            os.chdir(self.path)
            self.current_process = subprocess.Popen(["mricron", "T1.nii.gz"])
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")
    def open_Headmotion_CCS_fsleye(self):
        t1_image = os.path.join(self.path, "T1.nii.gz")
        if os.path.exists(t1_image):
            self.current_process = subprocess.Popen(["fsleyes", t1_image, "-dr", "15", "1500"])
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")
    def open_Headmotion_CCS_freeview(self):
        t1_image = os.path.join(self.path, "T1.nii.gz")
        if os.path.exists(t1_image):
            freeview_command = [
                "freeview", "--layout", "4", "--viewsize", "1000", "1000",
                "-v", f"{t1_image}:colormap=grayscale:grayscale=15,1500"
            ]
            try:
                self.current_process = subprocess.Popen(freeview_command)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run freeview: {str(e)}")
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")
    def open_Headmotion_BIDS_mricron(self):
        if os.path.exists(self.path):
            superdir = os.path.dirname(self.path)
            os.chdir(superdir)
            t1_image = os.path.basename(self.path)
            self.current_process = subprocess.Popen(["mricron", t1_image])
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")

    def open_Headmotion_BIDS_fsleye(self):
        if os.path.exists(self.path):
            self.current_process = subprocess.Popen(["fsleyes", self.path, "-dr", "15", "1500"])
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")

    def open_Headmotion_BIDS_freeview(self):
        if os.path.exists(self.path):
            freeview_command = [
                "freeview", "--layout", "4", "--viewsize", "1000", "1000",
                "-v", f"{self.path}:colormap=grayscale:grayscale=15,1500"
            ]
            try:
                self.current_process = subprocess.Popen(freeview_command)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run freeview: {str(e)}")
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")

    def open_Headmotion_SUBJECT_mricron(self):
        t1_image = os.path.join(self.path, "T1.nii.gz")
        if os.path.exists(t1_image):
            self.current_process = subprocess.Popen(["mricron", t1_image])
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")

    def open_Headmotion_SUBJECT_fsleye(self):
        t1_image = os.path.join(self.path, "T1.nii.gz")
        if os.path.exists(t1_image):
            self.current_process = subprocess.Popen(["fsleyes", t1_image, "-dr", "15", "1500"])
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")

    def open_Headmotion_SUBJECT_freeview(self):
        t1_image = os.path.join(self.path, "T1.nii.gz")
        if os.path.exists(t1_image):
            freeview_command = [
                "freeview", "--layout", "4", "--viewsize", "1000", "1000",
                "-v", f"{t1_image}:colormap=grayscale:grayscale=15,1500"
            ]
            try:
                self.current_process = subprocess.Popen(freeview_command)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run freeview: {str(e)}")
        else:
            messagebox.showerror("Error", f"T1 image not found in {self.path}.")

    def open_Headmotion_MRIQC(self):
        if os.path.exists(self.path):
            self.current_process = subprocess.Popen(['xdg-open', self.path])
            # webbrowser.open(self.path)
        else:
            messagebox.showerror("Error", f"HTML file not found in {self.path}.")


    ## ######################     skull stripping      ################################
    def open_SkullStripping_CCS_mricron(self):

        t1_image = os.path.join(self.path, "T1_crop_sanlm.nii.gz")
        mask_image = os.path.join(self.path, "T1_crop_sanlm_pre_mask.nii.gz")
        if os.path.exists(t1_image) and os.path.exists(mask_image):
            os.chdir(self.path)
            self.current_process = subprocess.Popen(["mricron", "T1_crop_sanlm.nii.gz", "-o",
                                                     "T1_crop_sanlm_pre_mask.nii.gz", "-b", "75"])
            # self.current_process = subprocess.Popen(["mricron", t1_image, "-o", mask_image, "-b", "75"])
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {self.path}.")

    def open_SkullStripping_CCS_fsleye(self):
        t1_image = os.path.join(self.path, "T1_crop_sanlm.nii.gz")
        mask_image = os.path.join(self.path, "T1_crop_sanlm_pre_mask.nii.gz")
        if os.path.exists(t1_image) and os.path.exists(mask_image):
            self.current_process = subprocess.Popen(["fsleyes", t1_image, "-dr", "15", "1500",
                                                     mask_image, "-cm", "red", "-a", "20"])
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {self.path}.")

    def open_SkullStripping_CCS_freeview(self):
        t1_image = os.path.join(self.path, "T1_crop_sanlm.nii.gz")
        mask_image = os.path.join(self.path, "T1_crop_sanlm_pre_mask.nii.gz")
        if os.path.exists(t1_image) and os.path.exists(mask_image):
            freeview_command = [
                "freeview", "--layout", "4", "--viewsize", "1000", "1000",
                "-v", f"{t1_image}:colormap=grayscale:grayscale=15,1500",
                "-v", f"{mask_image}:colormap=Turbo:opacity=0.40"
            ]
            try:
                self.current_process = subprocess.Popen(freeview_command)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run freeview: {str(e)}")
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {self.path}.")

    def open_SkullStripping_SUBJECT_mricron(self):
        t1_image = os.path.join(self.path, "mri", "T1.nii.gz")
        mask_image = os.path.join(self.path, "mri", "mask.nii.gz")
        path = os.path.join(self.path, "mri")
        if os.path.exists(t1_image) and os.path.exists(mask_image):
            os.chdir(path)
            # self.current_process = subprocess.Popen(["mricron", t1_image, "-o", mask_image, "-b", "75"])
            self.current_process = subprocess.Popen(["mricron", "T1.nii.gz", "-o", "mask.nii.gz", "-b", "75"])
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {self.path}.")

    def open_SkullStripping_SUBJECT_fsleye(self):
        t1_image = os.path.join(self.path, "mri", "T1.nii.gz")
        mask_image = os.path.join(self.path, "mri", "mask.nii.gz")
        if os.path.exists(t1_image) and os.path.exists(mask_image):
            cmd = ["fsleyes", "--displaySpace", "world", "--neuroOrientation", t1_image, "-dr", "1", "180", mask_image,
                   "-cm", "red", "-a", "20"]
            print(f"{' '.join(cmd)}")
            self.current_process = subprocess.Popen(cmd)
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {self.path}.")

    def open_SkullStripping_SUBJECT_freeview(self):
        t1_image = os.path.join(self.path, "mri", "T1.nii.gz")
        mask_image = os.path.join(self.path, "mri", "mask.nii.gz")
        if os.path.exists(t1_image) and os.path.exists(mask_image):
            freeview_command = [
                "freeview", "--layout", "4", "--viewsize", "1000", "1000",
                "-v", f"{t1_image}:colormap=grayscale:grayscale=0,180",
                "-v", f"{mask_image}:colormap=Turbo:opacity=0.40"
            ]
            print(f"{' '.join(freeview_command)}")
            try:
                self.current_process = subprocess.Popen(freeview_command)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run freeview: {str(e)}")
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {self.path}.")


    ##  ######################    reconstruction   ################################
    def open_Reconall_freesurfer(self):
        subject_path = self.path
        print(f"open subject_path: {subject_path}")
        brain = os.path.join(subject_path, "mri/brainmask.mgz")
        if os.path.exists(brain):
            lh_pial_annot = os.path.join(subject_path, "surf", "lh.pial")
            rh_pial_annot = os.path.join(subject_path, "surf", "rh.pial")
            lh_white_annot = os.path.join(subject_path, "surf", "lh.white")
            rh_white_annot = os.path.join(subject_path, "surf", "rh.white")
            lh_label_annot = os.path.join(subject_path, "label", "lh.aparc.annot")
            rh_label_annot = os.path.join(subject_path, "label", "rh.aparc.annot")

            cmd = [
                "freeview", "--layout", "4", "--viewsize", "400", "300",
                "-viewport", "axial", "-v", f"{brain}:opacity=1:grayscale=0,138", "-zoom", "1.3",
                "-f", f"{lh_pial_annot}:edgecolor=yellow:annot={lh_label_annot}",
                f"{rh_pial_annot}:edgecolor=yellow:annot={rh_label_annot}",
                f"{lh_white_annot}:edgecolor=red:annot={lh_label_annot}",
                f"{rh_white_annot}:edgecolor=red:annot={rh_label_annot}",
                "--hide-3d-slices"]
            self.current_process = subprocess.Popen(cmd)
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {subject_path}.")

    def open_Reconall_FSVisualQC(self):
        subject_path = self.path
        brain = os.path.join(subject_path, "mri/brainmask.mgz")
        if os.path.exists(brain):
            lh_pial_annot = os.path.join(subject_path, "surf", "lh.pial")
            rh_pial_annot = os.path.join(subject_path, "surf", "rh.pial")
            lh_white_annot = os.path.join(subject_path, "surf", "lh.white")
            rh_white_annot = os.path.join(subject_path, "surf", "rh.white")
            lh_label_annot = os.path.join(subject_path, "label", "lh.aparc.annot")
            rh_label_annot = os.path.join(subject_path, "label", "rh.aparc.annot")

            self.current_process = subprocess.Popen([
                "freeview", "--layout", "4", "--viewsize", "400", "300",
                "-viewport", "axial", "-v", f"{brain}:opacity=1:grayscale=0,138", "-zoom", "1.3",
                "-f", f"{lh_pial_annot}:edgecolor=overlay:annot={lh_label_annot}",
                f"{rh_pial_annot}:edgecolor=overlay:annot={rh_label_annot}",
                f"{lh_white_annot}:edgecolor=overlay:annot={lh_label_annot}",
                f"{rh_white_annot}:edgecolor=overlay:annot={rh_label_annot}",
                "--hide-3d-slices"])
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {subject_path}.")

    def open_Reconall_freesurfer_flat(self):
        subject_path = self.path
        brain = os.path.join(subject_path, "mri/brainmask.mgz")

        if os.path.exists(brain):
            lh_pial = os.path.join(subject_path, "surf", "lh.pial")
            rh_pial = os.path.join(subject_path, "surf", "rh.pial")
            lh_pial_annot = os.path.join(subject_path, "surf", "lh.pial")
            rh_pial_annot = os.path.join(subject_path, "surf", "rh.pial")
            lh_white_annot = os.path.join(subject_path, "surf", "lh.white")
            rh_white_annot = os.path.join(subject_path, "surf", "rh.white")
            lh_inflated = os.path.join(subject_path, "surf", "lh.inflated")
            rh_inflated = os.path.join(subject_path, "surf", "rh.inflated")
            lh_label_annot = os.path.join(subject_path, "label", "lh.aparc.annot")
            rh_label_annot = os.path.join(subject_path, "label", "rh.aparc.annot")

            if os.path.exists(lh_pial) and os.path.exists(rh_pial) and os.path.exists(lh_inflated) and os.path.exists(rh_inflated):
                # Open both hemispheres with freeview
                self.current_process = subprocess.Popen([
                    "freeview", "--layout", "4", "--viewsize", "400", "300",
                    "-viewport", "axial", "-v", f"{brain}:opacity=1:grayscale=0,138", "-zoom", "1.3",
                    "-f", f"{lh_pial_annot}:edgecolor=overlay:annot={lh_label_annot}",
                    f"{rh_pial_annot}:edgecolor=overlay:annot={rh_label_annot}",
                    f"{lh_white_annot}:edgecolor=overlay:annot={lh_label_annot}",
                    f"{rh_white_annot}:edgecolor=overlay:annot={rh_label_annot}",
                    f"{lh_inflated}:edgecolor=overlay:annot={lh_label_annot}:edgethickness=1",
                    f"{rh_inflated}:edgecolor=overlay:annot={rh_label_annot}:edgethickness=1",
                    "--hide-3d-slices"])
            else:
                messagebox.showerror("Error", "Required surface files not found.")
        else:
            messagebox.showerror("Error", f"Brain mask image not found in {subject_path}.")
