__doc__ = """Fixed joint example, for detailed explanation refer to Zhang et. al. Nature Comm.  methods section."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation as R
import sys

# FIXME without appending sys.path make it more generic
sys.path.append("../../")
from elastica import *
from examples.JointCases.external_force_class_for_joint_test import (
    EndpointForcesSinusoidal,
)
from examples.JointCases.joint_cases_callback import JointCasesCallback
from examples.JointCases.joint_cases_postprocessing import (
    plot_position,
    plot_video,
    plot_video_xy,
    plot_video_xz,
)


class FixedJointSimulator(
    BaseSystemCollection, Constraints, Connections, Forcing, Damping, CallBacks
):
    pass


fixed_joint_sim = FixedJointSimulator()

# setting up test params
n_elem = 10
direction = np.array([0.0, 0.0, 1.0])
normal = np.array([0.0, 1.0, 0.0])
roll_direction = np.cross(direction, normal)
base_length = 0.2
base_radius = 0.007
base_area = np.pi * base_radius ** 2
density = 1750
E = 3e7
poisson_ratio = 0.5
shear_modulus = E / (poisson_ratio + 1.0)

start_rod_1 = np.zeros((3,))
start_rod_2 = start_rod_1 + direction * base_length

# Create rod 1
rod1 = CosseratRod.straight_rod(
    n_elem,
    start_rod_1,
    direction,
    normal,
    base_length,
    base_radius,
    density,
    0.0,  # internal damping constant, deprecated in v0.3.0
    E,
    shear_modulus=shear_modulus,
)
fixed_joint_sim.append(rod1)
# Create rod 2
rod2 = CosseratRod.straight_rod(
    n_elem,
    start_rod_2,
    direction,
    normal,
    base_length,
    base_radius,
    density,
    0.0,  # internal damping constant, deprecated in v0.3.0
    E,
    shear_modulus=shear_modulus,
)
fixed_joint_sim.append(rod2)

# Apply boundary conditions to rod1.
fixed_joint_sim.constrain(rod1).using(
    OneEndFixedBC, constrained_position_idx=(0,), constrained_director_idx=(0,)
)

# Connect rod 1 and rod 2
fixed_joint_sim.connect(
    first_rod=rod1, second_rod=rod2, first_connect_idx=-1, second_connect_idx=0
).using(FixedJoint, k=1e5, nu=1., kt=1e3, nut=1e-3)

# Add forces to rod2
fixed_joint_sim.add_forcing_to(rod2).using(
    UniformTorques, torque=5e-3, direction=np.array([0.0, 0.0, 1.0])
)

# add damping
damping_constant = 0.4
dt = 1e-5
fixed_joint_sim.dampen(rod1).using(
    ExponentialDamper,
    damping_constant=damping_constant,
    time_step=dt,
)
fixed_joint_sim.dampen(rod2).using(
    ExponentialDamper,
    damping_constant=damping_constant,
    time_step=dt,
)


pp_list_rod1 = defaultdict(list)
pp_list_rod2 = defaultdict(list)


fixed_joint_sim.collect_diagnostics(rod1).using(
    JointCasesCallback, step_skip=1000, callback_params=pp_list_rod1
)
fixed_joint_sim.collect_diagnostics(rod2).using(
    JointCasesCallback, step_skip=1000, callback_params=pp_list_rod2
)

fixed_joint_sim.finalize()
timestepper = PositionVerlet()

final_time = 1
dl = base_length / n_elem
dt = 1e-5
total_steps = int(final_time / dt)
print("Total steps", total_steps)
integrate(timestepper, fixed_joint_sim, final_time, total_steps)


def plot_orientation_vs_time(title, time, directors):
    quat = []
    for t in range(len(time)):
        quat_t = R.from_matrix(directors[t].T).as_quat()
        quat.append(quat_t)
    quat = np.array(quat)

    plt.figure(num=title)
    plt.plot(time, quat[:, 0], label="x")
    plt.plot(time, quat[:, 1], label="y")
    plt.plot(time, quat[:, 2], label="z")
    plt.plot(time, quat[:, 3], label="w")
    plt.title(title)
    plt.legend()
    plt.xlabel("Time [s]")
    plt.ylabel("Quaternion")
    plt.show()


plot_orientation_vs_time(
    "Orientation of last node of rod 1",
    pp_list_rod1["time"],
    np.array(pp_list_rod1["director"])[..., -1],
)
plot_orientation_vs_time(
    "Orientation of last node of rod 2",
    pp_list_rod2["time"],
    np.array(pp_list_rod2["director"])[..., -1],
)
