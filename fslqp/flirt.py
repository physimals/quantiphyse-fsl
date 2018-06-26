import os

from PySide import QtGui

from quantiphyse.data import DataGrid, ImageVolumeManagement, load
from quantiphyse.gui.widgets import Citation
from quantiphyse.utils import debug, get_plugins
from quantiphyse.utils.cmdline import CommandProcess, _run_cmd
from quantiphyse.utils.exceptions import QpException

from .process import FslProcess

CITE_TITLE = "Improved Optimisation for the Robust and Accurate Linear Registration and Motion Correction of Brain Images"
CITE_AUTHOR = "Jenkinson, M., Bannister, P., Brady, J. M. and Smith, S. M."
CITE_JOURNAL = "NeuroImage, 17(2), 825-841, 2002"

RegMethod = get_plugins("base-classes", class_name="RegMethod")[0]

class FlirtRegMethod(RegMethod):
    def __init__(self):
        RegMethod.__init__(self, "flirt")
        self.options_layout = None
        self.cost_models = {"Mutual information" : "mutualinfo",
                            "Woods" : "woods",
                            "Correlation ratio" : "corratio",
                            "Normalized correlation" : "normcorr",
                            "Normalized mutual information" : "normmi",
                            "Least squares" : "leastsq"}

    @classmethod
    def reg_3d(cls, reg_data, reg_grid, ref_data, ref_grid, options, queue):
        """
        Static function for performing 3D registration

        Mess at the moment. No returning of transforms, clunky use of command process
        should use mcflirt for moco...

        When revising, need to bear in mind that we can NOT call any asynchronous 
        multiprocessing here, because this function is called by multiprocessing as a
        daemon, and can therefore not spawn child  processes (although Popen seems to
        work fine)
        """
        ivm = ImageVolumeManagement()
        reg_data = ivm.add_data(reg_data, name="reg", grid=DataGrid(reg_data.shape, reg_grid))
        ref_data = ivm.add_data(ref_data, name="ref", grid=DataGrid(ref_data.shape, ref_grid))

        cmdline = ""
        for key in options.keys():
            value = options.pop(key)
            if value:
                cmdline += "-%s %s " % (key, value)
            else:
                cmdline += "-%s " % key

        cmdline += "-in reg -ref ref -out flirt_out"
        options = {
            "cmd" : "flirt", 
            "cmdline" : cmdline,
        }

        process = FslProcess(ivm, multiproc=False)
        process.add_data("reg")
        process.add_data("ref")

        cmdline = process.get_cmdline(options)
        worker_id, success, ret = _run_cmd(0, None, process.workdir, cmdline, {}, {})
        if not success:
            raise ret
        log, data, rois = ret
        qpdata = load(os.path.join(process.workdir, "flirt_out.nii.gz"))
        return qpdata.raw(), None, log
      
    @classmethod
    def moco(cls, moco_data, moco_grid, ref, ref_grid, options, queue):
        """
        Motion correction
        
        We use MCFLIRT to implement this
        
        :param moco_data: A single 4D Numpy array containing data to motion correct.
        :param moco_grid: 4x4 array giving grid-to-world transformation for ``moco_data``. 
                          World co-ordinates should be in mm.
        :param ref: Either 3D Numpy array containing reference data, or integer giving 
                    the volume index of ``moco_data`` to use
        :param ref_grid: 4x4 array giving grid-to-world transformation for ref_data. 
                         Ignored if ``ref`` is an integer.
        :param options: Method options as dictionary
        :param queue: Queue object which method may put progress information on to. Progress 
                      should be given as a number between 0 and 1.
        
        :return Tuple of three items. 
        
                First, motion corrected data as a 4D Numpy array in the same space as ``moco_data``
        
                Second, if options contains ``output-transform : True``, sequence of transformations
                found, one for each volume in ``reg_data``. Each is either an affine matrix transformation 
                or a sequence of 3 warp images, the same shape as ``regdata`` If ``output-transform`` 
                is not given, returns None instead.

                Third, log information from the registration as a string.
        """
        if moco_data.ndim != 4:
            raise QpException("Cannot motion correct 3D data")
        
        ivm = ImageVolumeManagement()
        ivm.add_data(moco_data, name="moco_data", grid=DataGrid(moco_data.shape[:3], moco_grid))

        cmdline = ""
        for key in options.keys():
            value = options.pop(key)
            if value:
                cmdline += "-%s %s " % (key, value)
            else:
                cmdline += "-%s " % key

        process = FslProcess(ivm, multiproc=False)
        process.add_data("moco_data")
        cmdline += "-in moco_data -out mcflirt_out"
        if isinstance(ref, int):
            cmdline += " -refvol %i" % ref
        else:
            ivm.add_data(ref, name="ref_data", grid=DataGrid(ref.shape, ref_grid))
            cmdline += " -reffile ref_data"
            process.add_data("ref_data")
        options = {
            "cmd" : "mcflirt", 
            "cmdline" : cmdline,
        }

        cmdline = process.get_cmdline(options)
        worker_id, success, ret = _run_cmd(0, None, process.workdir, cmdline, {}, {})
        if not success:
            import traceback
            traceback.print_exc(ret)
            raise ret
        log, data, rois = ret
        print(log)
        qpdata = load(os.path.join(process.workdir, "mcflirt_out.nii.gz"))
        return qpdata.raw(), None, log
  
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
