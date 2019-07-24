#!/usr/bin/env python3.7

"""
File:       Fascicle.py
Author:     Jake Cariello
Created:    July 24, 2019

Description:

    OVERVIEW

    INITIALIZER

    PROPERTIES

    METHODS

    TODO: check if inners are overlapping

"""

# import math
from typing import List, Tuple
import itertools
from typing import List
from matplotlib import path as pth

from src.core import Trace
from src.utils import Exceptionable, SetupMode


class Fascicle(Exceptionable):

    def __init__(self, exception_config, inners: List[Trace], outer: Trace):
        # set up superclass
        Exceptionable.__init__(self, SetupMode.OLD, exception_config)

        self.inners = inners
        self.outer = outer

        # ensure all inner Traces are actually inside outer Trace
        if any([inner for inner in inners if inner.is_inside(outer)]):
            self.throw(8)

        # ensure no Traces intersect
        self.pairs: List[Tuple[Trace]] = list(itertools.combinations(inners + [outer], 2))
        if any([pair[0].intersects(pair[1]) for pair in self.pairs]):
            self.throw(9)

    def intersects(self, other: 'Fascicle') -> bool:
        """
        :param other: the other Fascicle to check
        :return: True if the outer traces of the Fascicles intersect
        """
        return self.outer.intersects(other.outer)

# # might use this code for checking if points are within elliptical nerve
# # get bounding ellipse parameters
#
# ((h, k), (a, b)) = outer.ellipse()
#
# for point in inner.points:
#     (x, y, _) = tuple(point)
#     if ((math.pow((x - h), 2) // math.pow(a, 2)) + (math.pow((y - k), 2) // math.pow(b, 2))) < 1:
#         self.throw()
