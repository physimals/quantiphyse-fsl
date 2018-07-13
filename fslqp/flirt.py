"""
Registration method using FSL FLIRT wrapper

Copyright (c) 2013-2018 University of Oxford
"""
from PySide import QtGui

import fsl.wrappers as fsl

from quantiphyse.data import QpData
from quantiphyse.gui.widgets import Citation
from quantiphyse.utils import get_plugins
from quantiphyse.utils.exceptions import QpException

from .process import qpdata_to_fslimage, fslimage_to_qpdata

CITE_TITLE = "Improved Optimisation for the Robust and Accurate Linear Registration and Motion Correction of Brain Images"
CITE_AUTHOR = "Jenkinson, M., Bannister, P., Brady, J. M. and Smith, S. M."
CITE_JOURNAL = "NeuroImage, 17(2), 825-841, 2002"

RegMethod = get_plugins("base-classes", class_name="RegMethod")[0]

class FlirtRegMethod(RegMethod):
    """
    FLIRT/MCFLIRT registration method
    """

    def __init__(self):
        RegMethod.__init__(self, "FLIRT/MCFLIRT")
        self.options_layout = None
        self.cost_models = {"Mutual information" : "mutualinfo",
                            "Woods" : "woods",
                            "Correlation ratio" : "corratio",
                            "Normalized correlation" : "normcorr",
                            "Normalized mutual information" : "normmi",
                            "Least squares" : "leastsq"}

    @classmethod
    def reg_3d(cls, reg_data, ref_data, options, queue):
        """
        Static function for performing 3D registration

        FIXME not working need to resolve output data space and return xform
        """
        reg = qpdata_to_fslimage(reg_data)
        ref = qpdata_to_fslimage(ref_data)
        
        flirt_output = fsl.flirt(reg, ref, out=fsl.LOAD, **options)
        print(flirt_output)
        qpdata = fslimage_to_qpdata(flirt_output["out"].data, reg_data.name)
        
        return qpdata, None, "flirt log"
      
    @classmethod
    def moco(cls, moco_data, ref, options, queue):
        """
        Motion correction
        
        We use MCFLIRT to implement this
        
        :param moco_data: A single 4D QpData instance containing data to motion correct.
        :param ref: Either 3D QpData containing reference data, or integer giving 
                    the volume index of ``moco_data`` to use
        :param options: Method options as dictionary
        :param queue: Queue object which method may put progress information on to. Progress 
                      should be given as a number between 0 and 1.
        
        :return Tuple of three items. 
        
                First, motion corrected data as 4D QpData in the same space as ``moco_data``
        
                Second, if options contains ``output-transform : True``, sequence of transformations
                found, one for each volume in ``reg_data``. Each is either an affine matrix transformation 
                or a sequence of 3 warp images, the same shape as ``regdata`` If ``output-transform`` 
                is not given, returns None instead.

                Third, log information from the registration as a string.
        """
        if moco_data.ndim != 4:
            raise QpException("Cannot motion correct 3D data")

        reg = qpdata_to_fslimage(moco_data)

        if isinstance(ref, int):
            options["refvol"] = ref
        elif isinstance(ref, QpData):
            options["reffile"] = qpdata_to_fslimage(ref)
        else:
            raise QpException("invalid reference object type: %s" % type(ref))
            
        mcflirt_output = fsl.mcflirt(reg, out=fsl.LOAD, **options)
        print(mcflirt_output)
        qpdata = fslimage_to_qpdata(mcflirt_output["out"], moco_data.name)
        
        return qpdata, None, "mcflirt log"
  
    def interface(self):
        if self.options_layout is None:      
            vbox = QtGui.QVBoxLayout()

            cite = Citation(CITE_TITLE, CITE_AUTHOR, CITE_JOURNAL)
            vbox.addWidget(cite)

            grid = QtGui.QGridLayout()

            grid.addWidget(QtGui.QLabel("Cost model"), 0, 0)
            self.cost_combo = QtGui.QComboBox()
            for name, opt in self.cost_models.items():
                self.cost_combo.addItem(name, opt)
            self.cost_combo.setCurrentIndex(self.cost_combo.findData("corratio"))
            grid.addWidget(self.cost_combo, 0, 1)

            grid.addWidget(QtGui.QLabel("Number of search stages"), 3, 0)
            self.stages = QtGui.QComboBox()
            for i in range(1, 5):
                self.stages.addItem(str(i), i)
            self.stages.setCurrentIndex(2)
            grid.addWidget(self.stages, 3, 1)

            self.final_label = QtGui.QLabel("Final stage interpolation")
            grid.addWidget(self.final_label, 4, 0)
            self.final = QtGui.QComboBox()
            self.final.addItem("None", "")
            self.final.addItem("Sinc", "sinc_final")
            self.final.addItem("Spline", "spline_final")
            self.final.addItem("Nearest neighbour", "nn_final")
            grid.addWidget(self.final, 4, 1)

            # grid.addWidget(QtGui.QLabel("Field of view (mm)"), 5, 0)
            # self.fov = QtGui.QSpinBox()
            # self.fov.setValue(20)
            # self.fov.setMinimum(1)
            # self.fov.setMaximum(100)
            # grid.addWidget(self.fov, 5, 1)

            grid.addWidget(QtGui.QLabel("Number of bins"), 6, 0)
            self.num_bins = QtGui.QSpinBox()
            self.num_bins.setMinimum(1)
            self.num_bins.setMaximum(1000)
            self.num_bins.setValue(256)
            grid.addWidget(self.num_bins, 6, 1)

            grid.addWidget(QtGui.QLabel("Number of transform degrees of freedom"), 7, 0)
            self.num_dofs = QtGui.QSpinBox()
            self.num_dofs.setMinimum(6)
            self.num_dofs.setMaximum(12)
            self.num_dofs.setValue(6)
            grid.addWidget(self.num_dofs, 7, 1)

            # grid.addWidget(QtGui.QLabel("Scaling"), 8, 0)
            # self.scaling = QtGui.QDoubleSpinBox()
            # self.scaling.setValue(6.0)
            # self.scaling.setMinimum(0.1)
            # self.scaling.setMaximum(10.0)
            # self.scaling.setSingleStep(0.1)
            # grid.addWidget(self.scaling, 8, 1)

            # grid.addWidget(QtGui.QLabel("Smoothing in cost function"), 9, 0)
            # self.smoothing = QtGui.QDoubleSpinBox()
            # self.smoothing.setValue(1.0)
            # self.smoothing.setMinimum(0.1)
            # self.smoothing.setMaximum(10.0)
            # self.smoothing.setSingleStep(0.1)
            # grid.addWidget(self.smoothing, 9, 1)

            # grid.addWidget(QtGui.QLabel("Scaling factor for rotation\noptimization tolerances"), 10, 0)
            # self.rotation = QtGui.QDoubleSpinBox()
            # self.rotation.setValue(1.0)
            # self.rotation.setMinimum(0.1)
            # self.rotation.setMaximum(10.0)
            # self.rotation.setSingleStep(0.1)
            # grid.addWidget(self.rotation, 10, 1)

            grid.addWidget(QtGui.QLabel("Search on gradient images"), 11, 0)
            self.gdt = QtGui.QCheckBox()
            grid.addWidget(self.gdt, 11, 1)
            grid.setColumnStretch(2, 1)
            
            vbox.addLayout(grid)
            self.options_layout = vbox
        return self.options_layout

    def options(self):
        self.interface()
        opts = {}
        opts["cost"] = self.cost_combo.itemData(self.cost_combo.currentIndex())
        opts["bins"] = self.num_bins.value()
        opts["dof"] = self.num_dofs.value()
        # opts["scaling"] = self.scaling.value()
        # opts["smooth"] = self.smoothing.value()
        # opts["rotation"] = self.rotation.value()
        # opts["stages"] = self.stages.itemData(self.stages.currentIndex())
        # opts["fov"] = self.fov.value()
        # if self.gdt.isChecked(): opts["gdt"] = ""

        # final_interp = self.final.currentIndex()
        # if final_interp != 0: opts[self.final.itemData(final_interp)] = ""

        for key, value in opts.items():
            self.debug(key, value)
        return opts
