import math
import numpy as np
from icecream import ic


def closest_divisors(n):
    a = round(math.sqrt(n))
    while n % a > 0: a -= 1
    p = a, n // a
    return np.asarray(p)
