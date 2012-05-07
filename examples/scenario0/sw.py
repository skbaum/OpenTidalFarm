import configuration 
import numpy
from reduced_functional import ReducedFunctional
from dolfin import *
from helpers import info, info_green, info_red, info_blue
set_log_level(DEBUG)

basin_x = 640.
basin_y = 320.

# We set the perturbation_direction with a constant seed, so that it is consistent in a parallel environment.
config = configuration.ScenarioConfiguration("mesh.xml", inflow_direction = [1, 0])
# Switch of the automatic scaling, since we will not solve an optimisation problem
config.params['automatic_scaling'] = False

# Place one turbine 
offset = 0.0
turbine_pos = [[basin_x/3 + offset, basin_y/2 + offset]] 
config.set_turbine_pos(turbine_pos)

model = ReducedFunctional(config)
m = model.initial_control()
j, state = model.run_forward_model_mem(m, return_final_state = True)
info_green("Power outcome: %f" % (j, ))

# Compute the Lanchester-Betz limit.
# The notation follows C. Garretta and P. Cummins, Limits to tidal current power
try: 
    u0 = state((1., basin_y/2))[0]
except RuntimeError:
    u0 = -100000
    pass
u0 = MPI.max(u0)

# Compute the average velocity in the turbine area
#u1 = 0.0
#for o_x in config.params["turbine_x"]*numpy.linspace(-1, 1, 50)/2:
#    for o_y in config.params["turbine_y"]*numpy.linspace(-1, 1, 50)/2:
#        try: 
#            u1 += state(numpy.array(turbine_pos[0]) + [o_x, o_y])[0]
#        except RuntimeError:
#            pass
#u1 = MPI.sum(u1)/(50*50)
try: 
    u1 = state(numpy.array(turbine_pos[0]))[0]
except RuntimeError:
    u1 = -100000
    pass
u1 = MPI.max(u1)

info_green("Inflow velocity u0: " + str(u0) + " m/s")
info_green("Turbine velocity u1: " + str(u1) + " m/s")
info_green("u1/u0: " + str(u1/u0) + " (Lanchester-Betz limit is reached at u1/u0 = 0.66666)")

dj = model.dj(m)
info_green("Functional gradient: " + str(dj))
