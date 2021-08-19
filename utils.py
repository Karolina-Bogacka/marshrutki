import math
import numpy as np
from scipy.spatial import distance


def closest_divisors(n):
    a = round(math.sqrt(n))
    while n % a > 0: a -= 1
    p = a, n // a
    return np.asarray(p)


def combined_distance(point1, point2, point3):
    return distance.euclidean(point1, point2) + distance.euclidean(point2, point3) - distance.euclidean(point1, point3)