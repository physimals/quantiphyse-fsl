"""
Quantiphyse - Registration method using FSL FNIRT wrapper

Copyright (c) 2013-2018 University of Oxford
"""
import six

try:
    from PySide import QtGui, QtCore, QtGui as QtWidgets
except ImportError:
    from PySide2 import QtGui, QtCore, QtWidgets

from quantiphyse.gui.widgets import Citation
from quantiphyse.gui.options import OptionBox, DataOption, ChoiceOption
from quantiphyse.utils import get_plugins
from quantiphyse.utils.exceptions import QpException

from .process import qpdata_to_fslimage, fslimage_to_qpdata

CITE_TITLE = "Non-linear registration, aka spatial normalisation"
CITE_AUTHOR = "Andersson JLR, Jenkinson M, Smith S"
CITE_JOURNAL = "FMRIB technical report TR07JA2, 2010"

RegMethod = get_plugins("base-classes", class_name="RegMethod")[0]

def _interp(order):
    return {0 : "nn", 1 : "trilinear", 2 : "spline", 3 : "spline"}[order]

class FnirtRegMethod(RegMethod):
    """
    FNIRT registration method
    """
    def __init__(self, ivm):
        RegMethod.__init__(self, "fnirt", ivm, display_name="FNIRT")
        self.options_widget = None

    @classmethod
    def apply_transform(cls, reg_data, transform, options, queue):
        """
        Apply a previously calculated transformation to a data set
        """
        from fsl import wrappers as fsl
        reg = qpdata_to_fslimage(reg_data)
        trans = qpdata_to_fslimage(transform)

        # Applywarp generates an output for each volume of reference image
        # for some reason. So use just the first volume of the transform
        # as the reference space
        ref = qpdata_to_fslimage(transform.volume(0, qpdata=True))

        log = six.StringIO()
        order = options.pop("interp-order", 1)
        interp = _interp(order)
        apply_output = fsl.applywarp(reg, ref, interp=interp, paddingsize=1, super=True, superlevel="a", 
                                     out=fsl.LOAD, log={"cmd" : log, "stdout" : log, "stderr" : log},
                                     warp=trans, rel=True)                       
        qpdata = fslimage_to_qpdata(apply_output["out"], name=reg_data.name)

        output_space = options.pop("output-space", "ref")
        if output_space == "ref":
            # Default is to output in reference space
            pass
        elif output_space == "reg":
            qpdata = qpdata.resample(reg_data.grid, suffix="", order=order)
            log += "Resampling onto input grid\n"
        else:
            raise QpException("FNIRT does not support output in transformed space")

        return qpdata, log.getvalue()

    @classmethod
    def reg_3d(cls, reg_data, ref_data, options, queue):
        """
        Static function for performing 3D registration

        FIXME return jacobian as part of xform?
        """
        from fsl import wrappers as fsl
        reg = qpdata_to_fslimage(reg_data)
        ref = qpdata_to_fslimage(ref_data)
        
        output_space = options.pop("output-space", "ref")
        log = six.StringIO()
        fnirt_output = fsl.fnirt(reg, ref=ref, iout=fsl.LOAD, fout=fsl.LOAD, log={"cmd" : log, "stdout" : log, "stderr" : log}, **options)
        transform = fslimage_to_qpdata(fnirt_output["fout"], name="fnirt_warp")
        transform.metadata["QpReg"] = "FNIRT"

        if output_space == "ref":
            qpdata = fslimage_to_qpdata(fnirt_output["iout"], name=reg_data.name)
        elif output_space == "reg":
            qpdata = fslimage_to_qpdata(fnirt_output["iout"], name=reg_data.name).resample(reg_data.grid, suffix="")
        else:
            raise QpException("FNIRT does not support output in transformed space")
            
        return qpdata, transform, log.getvalue()
      
    def interface(self, generic_options=None):
        if generic_options is None:
            generic_options = {}

        if self.options_widget is None:    
            self.options_widget = QtGui.QWidget()  
            vbox = QtGui.QVBoxLayout()
            self.options_widget.setLayout(vbox)

            cite = Citation(CITE_TITLE, CITE_AUTHOR, CITE_JOURNAL)
            vbox.addWidget(cite)

            self.optbox = OptionBox()
            self.optbox.add("Mask for registration data", DataOption(self.ivm, rois=True, data=False), key="inmask", checked=True)
            self.optbox.add("Mask for reference data", DataOption(self.ivm, rois=True, data=False), key="refmask", checked=True)
            self.optbox.add("Spline order", ChoiceOption([2, 3]), key="splineorder", checked=True)
            self.optbox.add("Use pre-defined configuration", ChoiceOption(["T1_2_MNI152_2mm", "FA_2_FMRIB58_1mm"]), key="config", checked=True)
            vbox.addWidget(self.optbox)

        return self.options_widget

    def options(self):
        self.interface()
        return self.optbox.values()
