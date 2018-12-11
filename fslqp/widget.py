"""
Widgets for FSL tools

Copyright (c) 2016-2017 University of Oxford, Martin Craig
"""

from __future__ import division, unicode_literals, absolute_import, print_function

import os

from PySide import QtGui, QtCore

from quantiphyse.gui.options import OptionBox, NumericOption, TextOption, OutputNameOption, DataOption, BoolOption, ChoiceOption, PickPointOption
from quantiphyse.gui.widgets import QpWidget, RunBox, TitleWidget, Citation, WarningBox

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

WARNING = """
FSL installation could not be found

FSL widgets require FSL to be installed 

If you do have FSL, make sure the environment variable $FSLDIR is set correctly
"""

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

        if "FSLDIR" not in os.environ and "FSLDEVDIR" not in os.environ:
            self.vbox.addWidget(WarningBox(WARNING))
            self.options.setVisible(False)
        elif run_box:
            self.run_box = RunBox(self.get_process, self.get_options)
            self.vbox.addWidget(self.run_box)
        
        self.vbox.addStretch(1)
        
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
        super(FslAtlasWidget, self).__init__(name="FSL Atlases", icon="fsl", desc="Browse and display FSL atlases", group="FSL", **kwargs)
        from fsl.data.atlases import AtlasRegistry
        self._registry = AtlasRegistry()

    def init_ui(self):  
        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(TitleWidget(self))
        vbox.addWidget(Citation(*CITATIONS["fsl"]))

        if "FSLDIR" not in os.environ and "FSLDEVDIR" not in os.environ:
            vbox.addWidget(WarningBox(WARNING))
            return
        
        self._registry.rescanAtlases()
        
        self.atlas_list = AtlasListWidget(self, self._registry)
        vbox.addWidget(self.atlas_list)
        self.atlas_desc = AtlasDescription(self, self._registry)
        vbox.addWidget(self.atlas_desc)

        self.atlas_list.sig_selected.connect(self.atlas_desc.set_atlas)

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
        grid.addWidget(self._label_table, 3, 0, 1, 2)
        grid.setRowStretch(3, 1)
        
        hbox = QtGui.QHBoxLayout()
        btn = QtGui.QPushButton("Load region")
        btn.clicked.connect(self._load)
        hbox.addWidget(btn)
        btn = QtGui.QPushButton("Load all regions")
        btn.clicked.connect(self._load_all)
        hbox.addWidget(btn)
        hbox.addStretch(1)
        grid.addLayout(hbox, 4, 0, 1, 2)

        grid.addWidget(QtGui.QLabel("Name"), 5, 0)
        self._load_name = QtGui.QLineEdit()
        grid.addWidget(self._load_name, 5, 1)

    def set_atlas(self, atlas_desc):
        self._desc = atlas_desc
        self._name.setText(atlas_desc.name)
        self._type.setText(atlas_desc.atlasType)
        self._load_name.setText(atlas_desc.name + "_atlas")

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

    def _load(self):
        if self._desc is not None:
            res = self._imgs.itemData(self._imgs.currentIndex())
            atlas = self._registry.loadAtlas(self._desc.atlasID, loadSummary=False, resolution=res)
            indexes = self._label_table.selectionModel().selectedRows()
            idx = self._label_model.item(indexes[0].row(), 0).text()
            if self._desc.atlasType == "label":
                self.ivm.add(fslimage_to_qpdata(atlas, region=int(idx), name="atlas"), roi=True)
            else:
                self.ivm.add(fslimage_to_qpdata(atlas, vol=int(idx), name="atlas"))

    def _load_all(self):
        if self._desc is not None:
            res = self._imgs.itemData(self._imgs.currentIndex())
            atlas = self._registry.loadAtlas(self._desc.atlasID, loadSummary=False, resolution=res)
            if self._desc.atlasType == "label":
                self.ivm.add(fslimage_to_qpdata(atlas, name="atlas"), roi=True)
            else:
                self.ivm.add(fslimage_to_qpdata(atlas, name="atlas"))

class AtlasListWidget(QtGui.QTableView):
    """
    Table showing available atlases
    """

    sig_selected = QtCore.Signal(object)

    def __init__(self, parent, registry):
        super(AtlasListWidget, self).__init__(parent)
        self._registry = registry
        self._atlases = {}
        self._init_list()

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.clicked.connect(self._clicked)

    def _init_list(self):
        self.model = QtGui.QStandardItemModel()
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(["Name", "Type"])
        for atlas in self._registry.listAtlases():
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
