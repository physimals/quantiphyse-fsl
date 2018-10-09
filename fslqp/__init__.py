"""
ENABLE Quantiphyse plugin

Author: Martin Craig <martin.craig@eng.ox.ac.uk>
Copyright (c) 2016-2017 University of Oxford, Martin Craig
"""
from .widget import FastWidget, BetWidget, FslAnatWidget, FslMathsWidget
from .process import FslProcess, FastProcess, BetProcess
from .flirt import FlirtRegMethod

QP_MANIFEST = {
    "widgets" : [FastWidget, BetWidget, FslAnatWidget, FslMathsWidget],
    "processes" : [FslProcess, FastProcess, BetProcess],
    "reg-methods" : [FlirtRegMethod],
    "module-dirs" : ["deps",],
}
