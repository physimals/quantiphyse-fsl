"""
ENABLE Quantiphyse plugin

Author: Martin Craig <martin.craig@eng.ox.ac.uk>
Copyright (c) 2016-2017 University of Oxford, Martin Craig
"""
from .widget import FastWidget, BetWidget, FslAnatWidget, FslMathsWidget, FslAtlasWidget, FslDataWidget
from .process import FslProcess, FastProcess, BetProcess
from .flirt import FlirtRegMethod
from .fnirt import FnirtRegMethod
from .tests import FlirtProcessTest

QP_MANIFEST = {
    "widgets" : [FastWidget, BetWidget, FslAnatWidget, FslMathsWidget, FslAtlasWidget, FslDataWidget],
    "processes" : [FslProcess, FastProcess, BetProcess],
    "reg-methods" : [FlirtRegMethod, FnirtRegMethod],
    "module-dirs" : ["deps",],
    "process-tests" : [FlirtProcessTest, ],
}
