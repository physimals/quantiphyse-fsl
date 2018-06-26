"""
Author: Martin Craig <martin.craig@eng.ox.ac.uk>
Copyright (c) 2016-2017 University of Oxford, Martin Craig
"""

from __future__ import division, unicode_literals, absolute_import, print_function

from PySide import QtGui

from quantiphyse.gui.widgets import QpWidget, RunBox, OverlayCombo, RoiCombo, Citation, TitleWidget, NumericOption, ChoiceOption, OptionalName
from quantiphyse.gui.dialogs import TextViewerDialog, error_dialog, GridEditDialog
from quantiphyse.utils.exceptions import QpException

from .process import FslProcess, FastProcess, BetProcess

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

class FslWidget(QpWidget):
    """
    Widget providing interface to FSL program
    """
    def __init__(self, **kwargs):
        QpWidget.__init__(self, icon="fsl.png",  group="FSL", **kwargs)
        self.prog = kwargs["prog"]
        
    def init_ui(self):
        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)

        title = TitleWidget(self, help="fsl", subtitle="%s %s" % (self.description, __version__))
        vbox.addWidget(title)
              
        cite = Citation(*CITATIONS.get(self.prog, CITATIONS["fsl"]))
        vbox.addWidget(cite)

        self.grid = QtGui.QGridLayout()
        self.grid.addWidget(QtGui.QLabel("Command line"), 0, 0)
        self.argline = QtGui.QLineEdit()
        self.grid.addWidget(self.argline, 0, 1)

        self.grid.setColumnStretch(2, 1)
        vbox.addLayout(self.grid)

        self.run_box = RunBox(self.get_process, self.get_options)
        vbox.addWidget(self.run_box)

        vbox.addStretch(1)

    def activate(self):
        pass

    def deactivate(self):
        pass
        
    def batch_options(self):
        return self.get_process().PROCESS_NAME, self.get_options()

    def get_process(self):
        return FslProcess(self.ivm)

    def get_options(self):
        options = {
            "argline" : self.argline.text(),
            "prog" : self.prog,
        }
        return options

    def run(self):
        process = self.get_process()
        process.run(self.get_options())
    
class FastWidget(FslWidget):
    def __init__(self, **kwargs):
        FslWidget.__init__(self, prog="fast", description="FMRIB Automated Segmentation Tool", name="FAST", **kwargs)
    
    def init_ui(self):
        FslWidget.init_ui(self)
        
        self.grid.addWidget(QtGui.QLabel("Input data"), 0, 0)
        self.data_combo = OverlayCombo(self.ivm)
        self.grid.addWidget(self.data_combo, 0, 1)
        self.type = ChoiceOption("Image type", self.grid, 1, choices=["T1", "T2", "PD"])
        self.nclass = NumericOption("Number of tissue-type classes", self.grid, 2, intonly=True, minval=1, maxval=10, default=3)
        self.biasfield = QtGui.QCheckBox("Output estimated bias field")
        self.grid.addWidget(self.biasfield, 3, 0)
        self.biascorr = QtGui.QCheckBox("Output bias-corrected image")
        self.grid.addWidget(self.biascorr, 4, 0)
        self.nobias = QtGui.QCheckBox("Do not remove bias field")
        self.grid.addWidget(self.nobias, 5, 0)
        self.lowpass = NumericOption("Bias field smoothing extent (mm)", self.grid, 6, minval=0, maxval=100, default=20, intonly=True)
        self.iter = NumericOption("Number of main-loop iterations during bias-field removal", self.grid, 7, intonly=True, minval=1, maxval=10, default=4)
        self.fixed = NumericOption("Number of main-loop iterations after bias-field removal", self.grid, 8, intonly=True, minval=1, maxval=10, default=4)
        self.init = NumericOption("Number of segmentation-initialization iterations", self.grid, 9, intonly=True, minval=1, maxval=100, default=15)
        self.fhard = NumericOption("Initial segmentation spatial smoothness", self.grid, 10, minval=0, maxval=1, default=0.02)
        self.mixel = NumericOption("Spatial smoothness for mixeltype", self.grid, 11, minval=0, maxval=5, default=0.3)
        self.hyper = NumericOption("Segmentation spatial smoothness", self.grid, 12, minval=0, maxval=5, default=0.1)

    def get_process(self):
        return FastProcess(self.ivm)

    def get_options(self):
        options = {
            "data" : self.data_combo.currentText(),
            "class" : self.nclass.value(),
            "iter" : self.iter.value(),
            "lowpass" : self.lowpass.value(),
            "type" : self.type.combo.currentIndex()+1,
            "fHard" : self.fhard.value(),
            "biasfield" : self.biasfield.isChecked(),
            "biascorr" : self.biascorr.isChecked(),
            "nobias" : self.nobias.isChecked(),
            "init" : self.init.value(),
            "mixel" : self.mixel.value(),
            "fixed" : self.fixed.value(),
            "Hyper" : self.hyper.value(),
        }
        return options

class BetWidget(FslWidget):
    def __init__(self, **kwargs):
        FslWidget.__init__(self, prog="bet", description="Brain Extraction Tool", name="BET", **kwargs)
    
    def init_ui(self):
        FslWidget.init_ui(self)
        
        self.grid.addWidget(QtGui.QLabel("Input data"), 0, 0)
        self.data_combo = OverlayCombo(self.ivm)
        self.grid.addWidget(self.data_combo, 0, 1)
        self.brain = OptionalName("Output extracted brain image", self.grid, 1, default_on=True, default="brain")
        self.mask = OptionalName("Output brain mask", self.grid, 2, default_on=False, default="brain_mask")
        self.thresh = NumericOption("Intensity threshold", self.grid, 3, minval=0, maxval=1, default=0.5)
        
    def get_process(self):
        return BetProcess(self.ivm)

    def get_options(self):
        options = {
            "data" : self.data_combo.currentText(),
            "thresh" : self.thresh.value(),
        }
        if self.brain.selected(): options["output-brain"] = self.brain.value()
        if self.mask.selected(): options["output-mask"] = self.mask.value()
        
        return options
