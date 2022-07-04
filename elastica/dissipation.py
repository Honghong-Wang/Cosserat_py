__doc__ = """
(added in version 0.3.0)

Built in damper module implementations
"""
__all__ = [
    "DamperBase",
    "ExponentialDamper",
]
from abc import ABC, abstractmethod

from elastica.typing import RodType, SystemType

from numba import njit

import numpy as np


class DamperBase(ABC):
    """Base class for damping module implementations.

    Notes
    -----
    All damper classes must inherit DamperBase class.


    Attributes
    ----------
    system : SystemType (RodBase or RigidBodyBase)

    """

    _system: SystemType

    def __init__(self, *args, **kwargs):
        """Initialize damping module"""
        try:
            self._system = kwargs["_system"]
        except KeyError:
            raise KeyError(
                "Please use simulator.dampen(...).using(...) syntax to establish "
                "damping."
            )

    @property
    def system(self):  # -> SystemType: (Return type is not parsed with sphinx book.)
        """
        get system (rod or rigid body) reference

        Returns
        -------
        SystemType

        """
        return self._system

    @abstractmethod
    def dampen_rates(self, rod: SystemType, time: float):
        # TODO: In the future, we can remove rod and use self.system
        """
        Dampen rates (velocity and/or omega) of a rod object.

        Parameters
        ----------
        rod : Union[Type[RodBase], Type[RigidBodyBase]]
            Rod or rigid-body object.
        time : float
            The time of simulation.

        """
        pass


class ExponentialDamper(DamperBase):
    """
    Exponential damper class. This class corresponds to the analytical version of
    a linear damper, and uses the following equations to damp translational and
    rotational velocities:

    .. math::

        \\mathbf{v}^{n+1} = \\mathbf{v}^n \\exp \\left( -  \\nu~dt  \\right)

        \\pmb{\\omega}^{n+1} = \\pmb{\\omega}^n \\exp \\left( - \\frac{{\\nu}~m~dt } { \\mathbf{J}} \\right)

    Examples
    --------
    How to set exponential damper for rod or rigid body:

    >>> simulator.dampen(rod).using(
    ...     ExponentialDamper,
    ...     damping_constant=0.1,
    ...     time_step = 1E-4,   # Simulation time-step
    ... )

    Notes
    -----
    Since this class analytically treats the damping term, it is unconditionally stable
    from a timestep perspective, i.e. the presence of damping does not impose any additional
    restriction on the simulation timestep size. This implies that when using
    Exponential Damper, one can set `damping_constant` as high as possible, without worrying
    about the simulation becoming unstable. This now leads to a streamlined procedure
    for tuning the `damping_constant`:

    1. Set a high value for `damping_constant` to first acheive a stable simulation.
    2. If you feel the simulation is overdamped, reduce `damping_constant` until you
       feel the simulation is underdamped, and expected dynamics are recovered.

    Attributes
    ----------
    translational_exponential_damping_coefficient: numpy.ndarray
        1D array containing data with 'float' type.
        Damping coefficient acting on translational velocity.
    rotational_exponential_damping_coefficient : numpy.ndarray
        1D array containing data with 'float' type.
        Damping coefficient acting on rotational velocity.
    """

    def __init__(self, damping_constant, time_step, **kwargs):
        """
        Exponential damper initializer

        Parameters
        ----------
        damping_constant : float
            Damping constant for the exponential dampers.
        time_step : float
            Time-step of simulation
        """
        super().__init__(**kwargs)
        # Compute the damping coefficient for translational velocity
        nodal_mass = self._system.mass
        self.translational_exponential_damping_coefficient = np.exp(
            -damping_constant * time_step
        )

        # Compute the damping coefficient for exponential velocity
        element_mass = 0.5 * (nodal_mass[1:] + nodal_mass[:-1])
        element_mass[0] += 0.5 * nodal_mass[0]
        element_mass[-1] += 0.5 * nodal_mass[-1]
        self.rotational_exponential_damping_coefficient = np.exp(
            -damping_constant
            * time_step
            * element_mass
            * np.diagonal(self._system.inv_mass_second_moment_of_inertia).T
        )

    def dampen_rates(self, rod: SystemType, time: float):
        rod.velocity_collection[:] = (
            rod.velocity_collection * self.translational_exponential_damping_coefficient
        )

        rod.omega_collection[:] = rod.omega_collection * np.power(
            self.rotational_exponential_damping_coefficient, rod.dilatation
        )


class FilterDamper(DamperBase):
    """
    TODO modify stuff below
    Filter damper class. This class corresponds to the analytical version of
    a linear damper, and uses the following equations to damp translational and
    rotational velocities:

    .. math::

        \\mathbf{v}^{n+1} = \\mathbf{v}^n \\exp \\left( -  \\nu~dt  \\right)

        \\pmb{\\omega}^{n+1} = \\pmb{\\omega}^n \\exp \\left( - \\frac{{\\nu}~m~dt } { \\mathbf{J}} \\right)

    Examples
    --------
    How to set filter damper for rod:

    >>> simulator.dampen(rod).using(
    ...     FilterDamper,
    ...     filter_order = 2,   # order of the filter
    ... )

    Notes
    -----
    TODO modify stuff below

    Attributes
    ----------
    filter_order : int
        Order of the filter.
    velocity_filter_term: numpy.ndarray
        2D array containing data with 'float' type.
        Filter term that modifies rod translational velocity.
    omega_filter_term: numpy.ndarray
        2D array containing data with 'float' type.
        Filter term that modifies rod rotational velocity.
    """

    def __init__(self, filter_order: float, **kwargs):
        """
        Filter damper initializer

        Parameters
        ----------
        filter_order : int
            Order of the filter.
        """
        super().__init__(**kwargs)
        if not (filter_order > 0 and isinstance(filter_order, int)):
            raise ValueError(
                "Invalid filter order! Filter order must be a positive integer."
            )
        self.filter_order = filter_order
        self.velocity_filter_term = np.zeros_like(self._system.velocity_collection)
        self.omega_filter_term = np.zeros_like(self._system.omega_collection)

    def dampen_rates(self, rod: RodType, time: float) -> None:
        nb_filter_rate(
            rate_collection=rod.velocity_collection,
            filter_term=self.velocity_filter_term,
            filter_order=self.filter_order,
        )
        nb_filter_rate(
            rate_collection=rod.omega_collection,
            filter_term=self.omega_filter_term,
            filter_order=self.filter_order,
        )


@njit(cache=True)
def nb_filter_rate(
    rate_collection: np.ndarray, filter_term: np.ndarray, filter_order: int
) -> None:
    """
    Filters the rod rates (velocities) in numba njit decorator

    Parameters
    ----------
    rate_collection : numpy.ndarray
        2D array containing data with 'float' type.
        Array containing rod rates (velocities).
    filter_term: numpy.ndarray
        2D array containing data with 'float' type.
        Filter term that modifies rod rates (velocities).
    filter_order : int
        Order of the filter.

    Returns
    -------

    """

    filter_term[...] = rate_collection
    for i in range(filter_order):
        filter_term[..., 1:-1] = (
            -filter_term[..., 2:] - filter_term[..., :-2] + 2.0 * filter_term[..., 1:-1]
        ) / 4.0
        # dont touch boundary values
        filter_term[..., 0] = 0.0
        filter_term[..., -1] = 0.0
    rate_collection[...] = rate_collection - filter_term