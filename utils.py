import math
import numpy as np
from icecream import ic
from scipy.spatial import distance


def closest_divisors(n):
    a = round(math.sqrt(n))
    while n % a > 0: a -= 1
    p = a, n // a
    return np.asarray(p)


def check_boundaries(pos, boundaries):
    if int(pos[0]) >= boundaries[0][0] and int(pos[1]) >= boundaries[0][1]:
        if int(pos[0]) < boundaries[1][0] and int(pos[1]) < boundaries[1][1]:
            return True
    return False


def combined_distance(point1, point2, point3):
    return distance.euclidean(point1, point2) + distance.euclidean(point2, point3) - distance.euclidean(point1, point3)
