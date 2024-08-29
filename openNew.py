import sys
from tkinter import Tk
from ccsqc import ccsqc

if __name__ == "__main__":
    projectname = sys.argv[1]
    qc_type = sys.argv[2]
    imgid = sys.argv[3]
    rater = sys.argv[4]

    root = Tk()
    new_app = ccsqc(root, projectname=projectname, scale=0)
    print(f"** qc_type: {qc_type}, imgid: {imgid}, rater: {rater}")
    new_app.create_specific_widgets(qc_type, imgid, rater, False)
    root.mainloop()
