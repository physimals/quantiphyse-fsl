"""
Widgets for FSL tools

Copyright (c) 2013-2020 University of Oxford

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import division, unicode_literals, absolute_import, print_function

import sys
import os
import glob

try:
    from PySide import QtGui, QtCore, QtGui as QtWidgets
except ImportError:
    from PySide2 import QtGui, QtCore, QtWidgets

from fsl.data.atlases import AtlasRegistry

import quantiphyse
from quantiphyse.data import load, NumpyData
from quantiphyse.gui.options import OptionBox, NumericOption, TextOption, OutputNameOption, DataOption, BoolOption, ChoiceOption, PickPointOption, FileOption
from quantiphyse.gui.widgets import QpWidget, RunBox, TitleWidget, Citation, ElidedLabel
from quantiphyse.utils import QpException

from .process import FastProcess, BetProcess, FslAnatProcess, FslMathsProcess, fslimage_to_qpdata

from ._version import __version__

CITATIONS = {
    "fsl" : (
        "Advances in functional and structural MR image analysis and implementation as FSL",
        "S.M. Smith, M. Jenkinson, M.W. Woolrich, C.F. Beckmann, T.E.J. Behrens, H. Johansen-Berg, P.R. Bannister, M. De Luca, I. Drobnjak, D.E. Flitney, R. Niazy, J. Saunders, J. Vickers, Y. Zhang, N. De Stefano, J.M. Brady, and P.M. Matthews",
        "NeuroImage, 23(S1):208-19, 2004",
    ),
    "fast" : (
        "Segmentation of brain MR images through a hidden Markov random field model and the expectation-maximization algorithm",
        "Zhang, Y. and Brady, M. and Smith, S",
        "IEEE Trans Med Imag, 20(1):45-57, 2001."
    ),
    "bet" : (
        "Fast robust automated brain extraction",
        "S.M. Smith",
        "Human Brain Mapping, 17(3):143-155, November 2002."
    ),
}

class FslDirWidget(QtGui.QFrame):
    """
    Widget which reports current FSLDIR and allows it to be changed
    """
    sig_changed = QtCore.Signal(str)

    def __init__(self, **kwargs):
        QtGui.QFrame.__init__(self, **kwargs)
        self.setStyleSheet("QWidget { background-color: #609050; color: black; border-radius: 5;}")
        self._settings = QtCore.QSettings()

        hbox = QtGui.QHBoxLayout()
        self.setLayout(hbox)
        icon = QtGui.QLabel()
        info_icon = icon.style().standardIcon(QtGui.QStyle.SP_MessageBoxInformation)
        icon.setPixmap(info_icon.pixmap(32, 32))
        hbox.addWidget(icon)
        lbl = QtGui.QLabel("Using FSL in")
        hbox.addWidget(lbl)
        hbox.setAlignment(lbl, QtCore.Qt.AlignTop) # Because the elided label always goes to the top...
        vbox = QtGui.QVBoxLayout() 
        self._fsldir_label = ElidedLabel()
        vbox.addWidget(self._fsldir_label)
        self._fsldevdir_label = ElidedLabel()
        vbox.addWidget(self._fsldevdir_label)
        hbox.addLayout(vbox)

        btn = QtGui.QPushButton("Change")
        btn.clicked.connect(self._change_fsldir)
        hbox.addWidget(btn)
        self._update_label()

    @property
    def fslwsl(self):
        """Boolean flag indicating whether FSL is installed in Windows Subsystem for Linux """
        return self.fsldir.startswith("\\\\wsl$\\")

    @property
    def fsldir(self):
        """
        :return: Location of FSL installation

        This looks for a previously configured location from Quantiphyse, or alternatively
        for the FSLDIR environment variable, and lastly will check a few common
        locations.

        If a location is found which is not stored in the FSLDIR environment variable then
        this variable will be updated.
        """
        fsldir, _fsldevdir = self._get_fsl_dirs()
        return fsldir

    @property
    def fsldevdir(self):
        """
        :return: Location of updated FSL code

        This looks for a previously configured location from Quantiphyse, or alternatively
        for the FSLDEVDIR environment variable.

        If a location is found which is not stored in the FSLDEVDIR environment variable then
        this variable will be updated.
        """
        _fsldir, fsldevdir = self._get_fsl_dirs()
        return fsldevdir

    def _get_fsl_dirs(self):
        if not os.environ.get("FSLDIR", None):
            if self._settings.contains("fslqp/fsldir"):
                os.environ["FSLDIR"] = self._settings.value("fslqp/fsldir")
            else:
                places_to_try = [
                    "/usr/local/fsl",
                    "/opt/fsl",
                ]
                for place in places_to_try:
                    if self._possible_fsldir(place):
                        os.environ["FSLDIR"] = place
                        break

        if not os.environ.get("FSLDEVDIR", None):
            if self._settings.contains("fslqp/fsldevdir"):
                os.environ["FSLDEVDIR"] = self._settings.value("fslqp/fsldevdir")

        return os.environ.get("FSLDIR", None), os.environ.get("FSLDEVDIR", None)

    def _change_fsldir(self):
        dialog = FslDirDialog(self.fsldir, self.fsldevdir)
        response = dialog.exec_()
        if response:
            os.environ["FSLDIR"] = dialog.fsldir
            self._settings.setValue("fslqp/fsldir", dialog.fsldir)

            if dialog.fsldevdir:
                os.environ["FSLDEVDIR"] = dialog.fsldevdir
                self._settings.setValue("fslqp/fsldevdir", dialog.fsldevdir)
            else:
                self._settings.setValue("fslqp/fsldevdir", "")

            self._update_label()
            self.sig_changed.emit(self.fsldir)
            
    def _update_label(self):
        text = []
        if self.fsldir:
            text.append(self.fsldir + ("(NOT FOUND)" if not self._possible_fsldir(self.fsldir) else ""))
        if self.fsldevdir:
            text.append(self.fsldevdir)

        self._fsldevdir_label.setText("")
        if len(text) > 0:
            self._fsldir_label.setText(text[0])
            self._fsldir_label.setToolTip(text[0])
            if len(text) > 1:
                self._fsldevdir_label.setText(text[1])
                self._fsldevdir_label.setToolTip(text[1])
        else:
            self._fsldir_label.setText(" Not set - click button to set")
            self._fsldir_label.setToolTip("")

    def _possible_fsldir(self, folder):
        print("FSLDIR=", folder)
        print(os.path.exists(folder))
        return os.path.isfile(os.path.join(folder, "bin", "flirt"))

class FslDirDialog(QtGui.QDialog):
    """
    Dialog box to choose FSLDIR
    """

    def __init__(self, fsldir, fsldevdir):
        super(FslDirDialog, self).__init__(quantiphyse.gui.dialogs.MAINWIN)
        self.setWindowTitle("Choose location of FSL installation")
        vbox = QtGui.QVBoxLayout()

        self.optbox = OptionBox()
        self.optbox.add("FSL installation", FileOption(dirs=True, initial=fsldir), key="fsldir")
        self.optbox.add("FSL development code", FileOption(dirs=True, initial=fsldevdir), checked=True, enabled=bool(fsldevdir), key="fsldevdir")
        self.optbox.option("fsldir").sig_changed.connect(self._fsldir_changed)
        self.optbox.option("fsldevdir").sig_changed.connect(self._fsldevdir_changed)
        vbox.addWidget(self.optbox)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        self.button_box = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        hbox.addWidget(self.button_box)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def _fsldir_changed(self):
        fsldir = self.optbox.option("fsldir").value
        self.optbox.option("fsldir").value = self._check_dir(fsldir)

    def _fsldevdir_changed(self):
        fsldevdir = self.optbox.option("fsldevdir").value
        self.optbox.option("fsldevdir").value = self._check_dir(fsldevdir)

    def _check_dir(self, dir):
        # Seems to be a bug in QFileDialog that returns UNC WSL filepath with forward not
        # back slashes which causes fslpy to fail
        if dir.startswith("//wsl$"):
            dir = dir.replace("//wsl$", "\\\\wsl$", 1)

        prefixes = [""]
        if sys.platform.startswith("win"):
            # On Windows, look for the dir under \\wsl$\ as well because sometimes QFileDialog
            # does not return this part of the path
            prefixes.append("\\\\wsl$")

        for prefix in prefixes:
            trial_dir = prefix + dir
            if os.path.exists(trial_dir):
                return trial_dir
        return dir

    @property
    def fsldir(self):
        return self.optbox.values()["fsldir"]
        
    @property
    def fsldevdir(self):
        return self.optbox.values().get("fsldevdir", None)

class FslWidget(QpWidget):
    """
    Widget providing interface to FSL program
    """
    def __init__(self, **kwargs):
        QpWidget.__init__(self, icon="fsl.png", group="FSL", **kwargs)
        self.prog = kwargs["prog"]
        
    def init_ui(self, run_box=True):
        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)
        
        title = TitleWidget(self, help="fsl", subtitle="%s %s" % (self.description, __version__))
        self.vbox.addWidget(title)

        cite = Citation(*CITATIONS.get(self.prog, CITATIONS["fsl"]))
        self.vbox.addWidget(cite)

        self.options = OptionBox("%s options" % self.prog.upper())
        self.vbox.addWidget(self.options)
        
        if run_box:
            self.run_box = RunBox(self.get_process, self.get_options)
            self.vbox.addWidget(self.run_box)
        
        self.vbox.addStretch(1)

        fsldir = FslDirWidget()
        self.vbox.addWidget(fsldir)
        fsldir.sig_changed.connect(self._fsldir_changed)
        self._fsldir_changed(fsldir.fsldir)
        
    def _fsldir_changed(self, fsldir):
        self.options.setVisible(bool(fsldir))
        if hasattr(self, "run_box"):
            self.run_box.setVisible(bool(fsldir))

    def batch_options(self):
        return self.get_process().PROCESS_NAME, self.get_options()

    def get_options(self):
        return self.options.values()

class FastWidget(FslWidget):
    def __init__(self, **kwargs):
        FslWidget.__init__(self, prog="fast", description="FMRIB Automated Segmentation Tool", name="FAST", **kwargs)
    
    def init_ui(self):
        FslWidget.init_ui(self)
        
        self.options.add("Structural image (brain extracted)", DataOption(self.ivm, include_4d=False), key="data")
        self.options.add("Image type", ChoiceOption(["T1 weighted", "T2 weighted", "Proton Density"], return_values=[1, 2, 3]), key="type")
        self.options.add("Number of tissue type classes", NumericOption(intonly=True, minval=2, maxval=10, default=3), key="class")
        self.options.add("Output estimated bias field", BoolOption(), key="biasfield")
        self.options.add("Output bias-corrected image", BoolOption(), key="biascorr")
        self.options.add("Remove bias field", BoolOption(default=True), key="nobias")
        self.options.add("Bias field smoothing extent (mm)", NumericOption(minval=0, maxval=100, default=20), key="lowpass")
        self.options.add("Number of main-loop iterations during bias-field removal", NumericOption(intonly=True, minval=1, maxval=10, default=4), key="iter")
        self.options.add("Number of main-loop iterations after bias-field removal", NumericOption(intonly=True, minval=1, maxval=10, default=4), key="fixed")
        self.options.add("Number of segmentation iterations", NumericOption(intonly=True, minval=1, maxval=100, default=15), key="init")
        self.options.add("Initial segmentation spatial smoothness", NumericOption(minval=0, maxval=1, default=0.02), key="fHard")
        self.options.add("Spatial smoothness for mixeltype", NumericOption(minval=0, maxval=5, default=0.3), key="mixel")
        self.options.add("Segmentation spatial smoothness", NumericOption(minval=0, maxval=5, default=0.1), key="Hyper")
        
    def get_process(self):
        return FastProcess(self.ivm)

class BetWidget(FslWidget):
    def __init__(self, **kwargs):
        FslWidget.__init__(self, prog="bet", description="Brain Extraction Tool", name="BET", **kwargs)
    
    def init_ui(self):
        FslWidget.init_ui(self)
        
        data = self.options.add("Input data", DataOption(self.ivm), key="data")
        data.sig_changed.connect(self._data_changed)
        self.options.add("Output extracted brain image", OutputNameOption(src_data=data, suffix="_brain"), key="output-brain", checked=True, enabled=True)
        self.options.add("Output brain mask", OutputNameOption(src_data=data, suffix="_brain_mask"), key="output-mask", checked=True)
        self.options.add("Intensity threshold", NumericOption(minval=0, maxval=1, default=0.5), key="thresh")
        self.options.add("Head radius (mm)", NumericOption(intonly=True, minval=0, maxval=300, default=200), key="radius", checked=True)
        self.centre = self.options.add("Brain centre (raw co-ordinates)", PickPointOption(self.ivl), key="centre", checked=True)

    def _data_changed(self):
        if self.options.values()["data"] in self.ivm.data:
            self.centre.setGrid(self.ivm.data[self.options.values()["data"]].grid)

    def get_process(self):
        return BetProcess(self.ivm)

class FslAnatWidget(FslWidget):
    def __init__(self, **kwargs):
        FslWidget.__init__(self, prog="fsl_anat", description="Anatomical segmentation from structural image", name="FSL_ANAT", **kwargs)
    
    def init_ui(self):
        FslWidget.init_ui(self)
        
        self.options.add("Input structural data", DataOption(self.ivm), key="data")
        self.options.add("Image type", ChoiceOption(["T1 weighted", "T2 weighted", "Proton Density"], return_values=["T1", "T2", "PD"]), key="img_type")
        self.options.add("Strong bias field", BoolOption(), key="strongbias")
        self.options.add("Re-orientation to standard space", BoolOption(invert=True), key="noreorient")
        self.options.add("Automatic cropping", BoolOption(invert=True), key="nocrop")
        self.options.add("Bias field correction", BoolOption(invert=True), key="nobias")
        #self.options.add("Registration to standard space", BoolOption(invert=True), key="noreg")
        #self.options.add("Non-linear registration", BoolOption(invert=True), key="nononlinreg")
        self.options.add("Segmentation", BoolOption(invert=True), key="noseg")
        self.options.add("Sub-cortical segmentation", BoolOption(invert=True), key="nosubcortseg")
        self.options.add("BET Intensity threshold", NumericOption(minval=0, maxval=1, default=0.5), key="betfparam")
        self.options.add("Bias field smoothing extent (mm)", NumericOption(minval=0, maxval=100, default=20), key="bias_smoothing")

    def get_process(self):
        return FslAnatProcess(self.ivm)

class FslMathsWidget(FslWidget):
    def __init__(self, **kwargs):
        FslWidget.__init__(self, prog="fslmaths", description="Miscellaneous data processing", name="FSL Maths", **kwargs)
    
    def init_ui(self):
        FslWidget.init_ui(self, run_box=False)
        run_btn = QtGui.QPushButton("Run")
        run_btn.clicked.connect(self._run)
        self.options.add("Command string", TextOption(), run_btn, key="cmd")

        doc = QtGui.QLabel("Enter the fslmaths command line string as you would normally. Use the names of the Quantiphyse data sets you want to use as filenames")
        doc.setWordWrap(True)
        self.vbox.insertWidget(self.vbox.count()-1, doc)

    def _run(self):
        self.get_process().run(self.get_options())

    def get_process(self):
        return FslMathsProcess(self.ivm)

class FslAtlasWidget(QpWidget):
    """
    Widget for browsing and loading FSL atlases
    """

    def __init__(self, **kwargs):
        super(FslAtlasWidget, self).__init__(name="Atlases", icon="fsl.png", desc="Browse and display FSL atlases", group="FSL", **kwargs)
        self._registry = AtlasRegistry()

    def init_ui(self):  
        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(TitleWidget(self))
        vbox.addWidget(Citation(*CITATIONS["fsl"]))
        
        self.atlas_list = AtlasListWidget(self, self._registry)
        vbox.addWidget(self.atlas_list)
        self.atlas_desc = AtlasDescription(self, self._registry)
        vbox.addWidget(self.atlas_desc)

        self.atlas_list.sig_selected.connect(self.atlas_desc.set_atlas)

        fsldir = FslDirWidget()
        vbox.addWidget(fsldir)

        # This needs to be done after creating the FslDirWidget because otherwise we may not
        # have picked up a previously saved FSLDIR setting and the atlas list will be empty
        self._registry.rescanAtlases()
        self.atlas_list.init_list()

class AtlasDescription(QtGui.QGroupBox):
    """
    Displays atlas description
    """

    sig_selected = QtCore.Signal(object)

    def __init__(self, parent, registry):
        super(AtlasDescription, self).__init__(parent)
        self._registry = registry
        self.ivm = parent.ivm
        self._desc = None
        grid = QtGui.QGridLayout()
        self.setLayout(grid)

        grid.addWidget(QtGui.QLabel("Name"), 0, 0)
        self._name = QtGui.QLabel()
        grid.addWidget(self._name, 0, 1)
        grid.addWidget(QtGui.QLabel("Type"), 1, 0)
        self._type = QtGui.QLabel()
        grid.addWidget(self._type, 1, 1)
        grid.addWidget(QtGui.QLabel("Resolutions"), 2, 0)
        self._imgs = QtGui.QComboBox()
        grid.addWidget(self._imgs, 2, 1)

        self._label_table = QtGui.QTableView()
        self._label_model = QtGui.QStandardItemModel()
        self._label_table.setModel(self._label_model)
        self._label_table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self._label_table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self._label_table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self._label_table.selectionModel().selectionChanged.connect(self._region_changed)

        self._label_table.setStyleSheet("font-size: 10px; alternate-background-color: #6c6c6c;")
        self._label_table.setShowGrid(False)
        self._label_table.setTextElideMode(QtCore.Qt.ElideLeft)
        self._label_table.setAlternatingRowColors(True)
        self._label_table.verticalHeader().setVisible(False)
        self._label_table.verticalHeader().setDefaultSectionSize(self._label_table.verticalHeader().minimumSectionSize()+2)

        grid.addWidget(self._label_table, 3, 0, 1, 2)
        grid.setRowStretch(3, 1)
        
        self._load_options = OptionBox()
        self._load_options.add("Regions", ChoiceOption(["Selected region", "All regions"], ["sel", "all"]), key="regions")
        self._load_options.add("Load as", ChoiceOption(["New dataset", "Add to existing dataset"], ["new", "add"]), key="add")
        self._load_options.add("Dataset name", TextOption("atlas"), key="name")
        self._load_options.add("Existing dataset", DataOption(self.ivm), key="data")
        self._load_options.option("add").sig_changed.connect(self._add_changed)
        grid.addWidget(self._load_options, 4, 0, 1, 2)

        hbox = QtGui.QHBoxLayout()
        btn = QtGui.QPushButton("Load")
        btn.clicked.connect(self._load)
        hbox.addWidget(btn)
        hbox.addStretch(1)
        grid.addLayout(hbox, 5, 0, 1, 2)
        self._add_changed()

    def set_atlas(self, atlas_desc):
        self._desc = atlas_desc
        self._name.setText(atlas_desc.name)
        self._type.setText(atlas_desc.atlasType)
        self._load_options.option("name").value = atlas_desc.name.replace(" ", "_").replace("-", "_").lower()
        
        self._imgs.clear()
        for pixdim in atlas_desc.pixdims:
            pixdim_str = "%.2g mm x %.2g mm x %.2g mm" % pixdim
            self._imgs.addItem(pixdim_str, pixdim[0])
            
        self._label_model.clear()
        self._label_model.setColumnCount(2)
        self._label_model.setHorizontalHeaderLabels(["Index", "Name"])
        for label in atlas_desc.labels:
            index_item = QtGui.QStandardItem("%i" % label.index)
            name_item = QtGui.QStandardItem(label.name)
            self._label_model.appendRow([index_item, name_item])
        self._label_table.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self._label_table.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)

    def _region_changed(self):
        if self._load_options.values()["regions"] == "sel":
            indexes = self._label_table.selectionModel().selectedRows()
            region_name = self._label_model.item(indexes[0].row(), 1).text()
            if region_name:
                load_name = region_name.replace(" ", "_").replace("-", "_").replace(",", "").replace("(", "").replace(")", "").lower()
                self._load_options.option("name").value = load_name

    def _add_changed(self):
        add = self._load_options.values()["add"] == "add"
        self._load_options.set_visible("name", not add)
        self._load_options.set_visible("data", add)

    def _load(self):
        if self._desc is not None:
            res = self._imgs.itemData(self._imgs.currentIndex())
            atlas = self._registry.loadAtlas(self._desc.atlasID, loadSummary=False, resolution=res)
            is_roi = self._desc.atlasType == "label"

            new_name = self._load_options.option("name").value
            add_name = self._load_options.option("data").value
            add = self._load_options.option("add").value == "add"
            load_all = self._load_options.option("regions").value == "all"

            vol = None
            if not load_all:
                indexes = self._label_table.selectionModel().selectedRows()
                vol = int(self._label_model.item(indexes[0].row(), 0).text())
            new_data = fslimage_to_qpdata(atlas, vol=vol, name=new_name)

            if add and add_name in self.ivm.data:
                # User wants to add the region to an existing data set
                if load_all:
                    raise QpException("Cannot add data to existing data set when loading all regions")
                orig_data = self.ivm.data[add_name]
                if not orig_data.grid.matches(new_data.grid):
                    raise QpException("Can't add data to existing data set - grids do not match")
                if is_roi and not orig_data.roi:
                    raise QpException("Can't add data to existing data set - it is not an ROI")
                new_data = NumpyData(orig_data.raw() + new_data.raw(), grid=new_data.grid, name=add_name)
                
            self.ivm.add(new_data, roi=is_roi)

class AtlasListWidget(QtGui.QTableView):
    """
    Table showing available atlases
    """
    sig_selected = QtCore.Signal(object)

    def __init__(self, parent, registry):
        super(AtlasListWidget, self).__init__(parent)
        self.setStyleSheet("font-size: 10px; alternate-background-color: #6c6c6c;")
        self.setShowGrid(False)
        self.setTextElideMode(QtCore.Qt.ElideLeft)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().minimumSectionSize()+2)

        self._registry = registry
        self._atlases = {}
        self.init_list()

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.clicked.connect(self._clicked)

    def init_list(self):
        self.model = QtGui.QStandardItemModel()
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(["Name", "Type"])
        for atlas in sorted(self._registry.listAtlases(), key=lambda x: x.name):
            self.model.appendRow([QtGui.QStandardItem(s) for s in (atlas.name, atlas.atlasType)])
            self._atlases[atlas.name] = atlas
        self.setModel(self.model)
        self.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)

    def _clicked(self, idx):
        row = idx.row()
        name = self.model.item(row, 0).text()
        selected = self._atlases[name]
        self.sig_selected.emit(selected)

class FslDataWidget(QpWidget):
    """
    Widget for browsing and loading standard FSL data sets
    """

    def __init__(self, **kwargs):
        super(FslDataWidget, self).__init__(name="Standard Data", icon="fsl.png", desc="Browse and load standard FSL data sets", group="FSL", **kwargs)
        self._selected = None

    def init_ui(self):  
        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(TitleWidget(self))
        vbox.addWidget(Citation(*CITATIONS["fsl"]))
        
        self.data_list = FslDataListWidget(self)
        vbox.addWidget(self.data_list)
        self.data_list.sig_selected.connect(self._data_selected)
        
        hbox = QtGui.QHBoxLayout()
        self._load_btn = QtGui.QPushButton("Load")
        self._load_btn.clicked.connect(self._load)
        hbox.addWidget(self._load_btn)
        hbox.addWidget(QtGui.QLabel("Dataset name: "))
        self._load_name = QtGui.QLineEdit()
        hbox.addWidget(self._load_name)
        vbox.addLayout(hbox)

        fsldir = FslDirWidget()
        vbox.addWidget(fsldir)

    def _data_selected(self, fname):
        self._selected = fname
        self._load_btn.setEnabled(bool(fname))
        name = os.path.basename(fname).split(".", 1)[0]
        self._load_name.setText(self.ivm.suggest_name(name))

    def _load(self):
        if self._selected:
            qpdata = load(self._selected)
            roi = "_mask_" in self._selected or "_mask." in self._selected
            qpdata.roi = roi
            self.ivm.add(qpdata, name=self._load_name.text())

class FslDataListWidget(QtGui.QTableView):
    """
    Table showing standard FSL data sets
    """

    sig_selected = QtCore.Signal(object)

    def __init__(self, parent):
        super(FslDataListWidget, self).__init__(parent)
        self.setStyleSheet("font-size: 10px; alternate-background-color: #6c6c6c;")
        self.setShowGrid(False)
        self.setTextElideMode(QtCore.Qt.ElideLeft)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self.verticalHeader().minimumSectionSize()+2)
        self._init_list()

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.clicked.connect(self._clicked)

    def _init_list(self):
        self.model = QtGui.QStandardItemModel()
        self.model.setColumnCount(1)
        self.model.setHorizontalHeaderLabels(["File name"])
        for fname in sorted(glob.glob(os.path.join(os.environ["FSLDIR"], "data", "standard", "*"))):
            if os.path.isfile(fname):
                self.model.appendRow([QtGui.QStandardItem(os.path.basename(fname))])
        self.setModel(self.model)
        self.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

    def _clicked(self, idx):
        row = idx.row()
        fname = self.model.item(row, 0).text()
        self.sig_selected.emit(os.path.join(os.environ["FSLDIR"], "data", "standard", fname))
