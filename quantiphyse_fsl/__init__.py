"""
FSL Quantiphyse plugin

Author: Martin Craig <martin.craig@eng.ox.ac.uk>

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
from .widget import FastWidget, BetWidget, FslAnatWidget, FslMathsWidget, FslAtlasWidget, FslDataWidget
from .process import FslProcess, FastProcess, BetProcess
from .flirt import FlirtRegMethod
from .fnirt import FnirtRegMethod
from .tests import FlirtProcessTest

# Workaround ugly warning about wx
import logging
logging.getLogger("fsl.utils.platform").setLevel(logging.CRITICAL)

QP_MANIFEST = {
    "widgets" : [FastWidget, BetWidget, FslAnatWidget, FslMathsWidget, FslAtlasWidget, FslDataWidget],
    "processes" : [FslProcess, FastProcess, BetProcess],
    "reg-methods" : [FlirtRegMethod, FnirtRegMethod],
    "module-dirs" : ["deps",],
    "process-tests" : [FlirtProcessTest, ],
}
