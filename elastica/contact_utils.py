__doc__ = """ Helper functions for contact force calculation """

from math import sqrt
import numba
import numpy as np


@numba.njit(cache=True)
def _dot_product(a, b):
    sum = 0.0
    for i in range(3):
        sum += a[i] * b[i]
    return sum


@numba.njit(cache=True)
def _norm(a):
    return sqrt(_dot_product(a, a))


@numba.njit(cache=True)
def _clip(x, low, high):
    return max(low, min(x, high))


# Can this be made more efficient than 2 comp, 1 or?
@numba.njit(cache=True)
def _out_of_bounds(x, low, high):
    return (x < low) or (x > high)


@numba.njit(cache=True)
def _find_min_dist(x1, e1, x2, e2):
    e1e1 = _dot_product(e1, e1)
    e1e2 = _dot_product(e1, e2)
    e2e2 = _dot_product(e2, e2)

    x1e1 = _dot_product(x1, e1)
    x1e2 = _dot_product(x1, e2)
    x2e1 = _dot_product(e1, x2)
    x2e2 = _dot_product(x2, e2)

    s = 0.0
    t = 0.0

    parallel = abs(1.0 - e1e2 ** 2 / (e1e1 * e2e2)) < 1e-6
    if parallel:
        # Some are parallel, so do processing
        t = (x2e1 - x1e1) / e1e1  # Comes from taking dot of e1 with a normal
        t = _clip(t, 0.0, 1.0)
        s = (x1e2 + t * e1e2 - x2e2) / e2e2  # Same as before
        s = _clip(s, 0.0, 1.0)
    else:
        # Using the Cauchy-Binet formula on eq(7) in docstring referenc
        s = (e1e1 * (x1e2 - x2e2) + e1e2 * (x2e1 - x1e1)) / (e1e1 * e2e2 - (e1e2) ** 2)
        t = (e1e2 * s + x2e1 - x1e1) / e1e1

        if _out_of_bounds(s, 0.0, 1.0) or _out_of_bounds(t, 0.0, 1.0):
            # potential_s = -100.0
            # potential_t = -100.0
            # potential_d = -100.0
            # overall_minimum_distance = 1e20

            # Fill in the possibilities
            potential_t = (x2e1 - x1e1) / e1e1
            s = 0.0
            t = _clip(potential_t, 0.0, 1.0)
            potential_d = _norm(x1 + e1 * t - x2)
            overall_minimum_distance = potential_d

            potential_t = (x2e1 + e1e2 - x1e1) / e1e1
            potential_t = _clip(potential_t, 0.0, 1.0)
            potential_d = _norm(x1 + e1 * potential_t - x2 - e2)
            if potential_d < overall_minimum_distance:
                s = 1.0
                t = potential_t
                overall_minimum_distance = potential_d

            potential_s = (x1e2 - x2e2) / e2e2
            potential_s = _clip(potential_s, 0.0, 1.0)
            potential_d = _norm(x2 + potential_s * e2 - x1)
            if potential_d < overall_minimum_distance:
                s = potential_s
                t = 0.0
                overall_minimum_distance = potential_d

            potential_s = (x1e2 + e1e2 - x2e2) / e2e2
            potential_s = _clip(potential_s, 0.0, 1.0)
            potential_d = _norm(x2 + potential_s * e2 - x1 - e1)
            if potential_d < overall_minimum_distance:
                s = potential_s
                t = 1.0

    # Return distance, contact point of system 2, contact point of system 1
    return x2 + s * e2 - x1 - t * e1, x2 + s * e2, x1 - t * e1


@numba.njit(cache=True)
def _aabbs_not_intersecting(aabb_one, aabb_two):
    """Returns true if not intersecting else false"""
    if (aabb_one[0, 1] < aabb_two[0, 0]) | (aabb_one[0, 0] > aabb_two[0, 1]):
        return 1
    if (aabb_one[1, 1] < aabb_two[1, 0]) | (aabb_one[1, 0] > aabb_two[1, 1]):
        return 1
    if (aabb_one[2, 1] < aabb_two[2, 0]) | (aabb_one[2, 0] > aabb_two[2, 1]):
        return 1

    return 0


@numba.njit(cache=True)
def _prune_using_aabbs_rod_cylinder(
    rod_one_position_collection,
    rod_one_radius_collection,
    rod_one_length_collection,
    cylinder_position,
    cylinder_director,
    cylinder_radius,
    cylinder_length,
):
    max_possible_dimension = np.zeros((3,))
    aabb_rod = np.empty((3, 2))
    aabb_cylinder = np.empty((3, 2))
    max_possible_dimension[...] = np.max(rod_one_radius_collection) + np.max(
        rod_one_length_collection
    )
    for i in range(3):
        aabb_rod[i, 0] = (
            np.min(rod_one_position_collection[i]) - max_possible_dimension[i]
        )
        aabb_rod[i, 1] = (
            np.max(rod_one_position_collection[i]) + max_possible_dimension[i]
        )

    # Is actually Q^T * d but numba complains about performance so we do
    # d^T @ Q
    cylinder_dimensions_in_local_FOR = np.array(
        [cylinder_radius, cylinder_radius, 0.5 * cylinder_length]
    )
    cylinder_dimensions_in_world_FOR = np.zeros_like(cylinder_dimensions_in_local_FOR)
    for i in range(3):
        for j in range(3):
            cylinder_dimensions_in_world_FOR[i] += (
                cylinder_director[j, i, 0] * cylinder_dimensions_in_local_FOR[j]
            )

    max_possible_dimension = np.abs(cylinder_dimensions_in_world_FOR)
    aabb_cylinder[..., 0] = cylinder_position[..., 0] - max_possible_dimension
    aabb_cylinder[..., 1] = cylinder_position[..., 0] + max_possible_dimension
    return _aabbs_not_intersecting(aabb_cylinder, aabb_rod)


@numba.njit(cache=True)
def _prune_using_aabbs_rod_rod(
    rod_one_position_collection,
    rod_one_radius_collection,
    rod_one_length_collection,
    rod_two_position_collection,
    rod_two_radius_collection,
    rod_two_length_collection,
):
    max_possible_dimension = np.zeros((3,))
    aabb_rod_one = np.empty((3, 2))
    aabb_rod_two = np.empty((3, 2))
    max_possible_dimension[...] = np.max(rod_one_radius_collection) + np.max(
        rod_one_length_collection
    )
    for i in range(3):
        aabb_rod_one[i, 0] = (
            np.min(rod_one_position_collection[i]) - max_possible_dimension[i]
        )
        aabb_rod_one[i, 1] = (
            np.max(rod_one_position_collection[i]) + max_possible_dimension[i]
        )

    max_possible_dimension[...] = np.max(rod_two_radius_collection) + np.max(
        rod_two_length_collection
    )

    for i in range(3):
        aabb_rod_two[i, 0] = (
            np.min(rod_two_position_collection[i]) - max_possible_dimension[i]
        )
        aabb_rod_two[i, 1] = (
            np.max(rod_two_position_collection[i]) + max_possible_dimension[i]
        )

    return _aabbs_not_intersecting(aabb_rod_two, aabb_rod_one)