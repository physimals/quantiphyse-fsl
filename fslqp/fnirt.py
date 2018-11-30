"""
Quantiphyse - Registration method using FSL FNIRT wrapper

Copyright (c) 2013-2018 University of Oxford
"""
import six
from PySide import QtGui

from quantiphyse.gui.widgets import Citation
from quantiphyse.gui.options import OptionBox, BoolOption
from quantiphyse.utils import get_plugins
from quantiphyse.utils.exceptions import QpException

from .process import qpdata_to_fslimage, fslimage_to_qpdata

CITE_TITLE = "Non-linear registration, aka spatial normalisation"
CITE_AUTHOR = "Andersson JLR, Jenkinson M, Smith S"
CITE_JOURNAL = "FMRIB technical report TR07JA2, 2010"

RegMethod = get_plugins("base-classes", class_name="RegMethod")[0]

class FnirtRegMethod(RegMethod):
    """
    FNIRT registration method
    """
    def __init__(self):
        RegMethod.__init__(self, "FNIRT")
        self.options_widget = None

    @classmethod
    def apply_transform(cls, reg_data, transform, options, queue):
        """
        Apply a previously calculated transformation to a data set
        """
        raise QpException("FNIRT: apply_transform not yet implemented")
        #output_space = options.pop("output-space", "ref")
        #if output_space == "ref":
        #    qpdata = qpdata.resample(transform.ref_grid, suffix="")
        #    log += "Resampling onto reference grid\n"
        #elif output_space == "reg":
        #    qpdata = qpdata.resample(transform.reg_grid, suffix="")
        #    log += "Resampling onto reference grid\n"
            
        #return qpdata, log

    @classmethod
    def reg_3d(cls, reg_data, ref_data, options, queue):
        """
        Static function for performing 3D registration

        FIXME need to resolve output data space and return xform
        """
        from fsl import wrappers as fsl
        reg = qpdata_to_fslimage(reg_data)
        ref = qpdata_to_fslimage(ref_data)
        
        output_space = options.pop("output-space", "ref")
        log = six.StringIO()
        fnirt_output = fsl.fnirt(reg, ref=ref, iout=fsl.LOAD, fout=fsl.LOAD, log={"cmd" : log, "stdout" : log, "stderr" : log}, **options)
        transform = fslimage_to_qpdata(fnirt_output["fout"], name="fnirt_warp")

        if output_space == "ref":
            qpdata = fslimage_to_qpdata(fnirt_output["iout"], name=reg_data.name)
        elif output_space == "reg":
            qpdata = fslimage_to_qpdata(fnirt_output["iout"], name=reg_data.name).resample(reg_data.grid, suffix="")
        else:
            raise QpException("FNIRT does not support output in transformed space")
            
        return qpdata, transform, log.getvalue()
      
    def interface(self):
        if self.options_widget is None:    
            self.options_widget = QtGui.QWidget()  
            vbox = QtGui.QVBoxLayout()
            self.options_widget.setLayout(vbox)

            cite = Citation(CITE_TITLE, CITE_AUTHOR, CITE_JOURNAL)
            vbox.addWidget(cite)

            self.optbox = OptionBox()
            #FIXME self.optbox.add("Make it actually work", BoolOption(), key="work")
            vbox.addWidget(self.optbox)

        return self.options_widget

    def options(self):
        self.interface()
        return self.optbox.values()
