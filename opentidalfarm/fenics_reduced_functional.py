import sys
import os.path
import numpy
import helpers
import dolfin_adjoint
from dolfin import *
from dolfin_adjoint import *
from solvers import Solver
from functionals import TimeIntegrator, PrototypeFunctional

class FenicsReducedFunctional(object):
    """
    Following parameters are expected:

    :ivar functional: a :class:`PrototypeFunctional` class.
    :ivar controls: a :class:`dolfin_adjoint.DolfinAdjointControl` class.
    :ivar solver: a :class:`Solver` object.

    This class has a parameter attribute for further adjustments.
    """

    def __init__(self, functional, controls, solver):

        self.solver = solver
        if not isinstance(solver, Solver):
            raise ValueError, "solver argument of wrong type."

        self.functional = functional
        if not PrototypeFunctional in functional.__bases__:
            raise ValueError, "invalid functional argument."

        # Hidden attributes
        self._solver_params = solver.parameters
        self._problem_params = solver.problem.parameters
        self._time_integrator = None

        # Controls
        if not hasattr(controls, "__getitem__"):
            controls = [controls]
        self.controls = controls

    def _compute_gradient(self, forget=True):
        """ Compute the functional gradient """

        J = self.time_integrator.dolfin_adjoint_functional()

        dj = dolfin_adjoint.compute_gradient(J, self.controls, forget=forget)
        dolfin.parameters["adjoint"]["stop_annotating"] = False

        return dj

    def _compute_functional(self, annotate=True):
        """ Compute the functional of interest for the turbine positions/frictions array """
        farm = self.solver.problem.parameters.tidal_farm

        # Configure dolfin-adjoint
        adj_reset()
        dolfin.parameters["adjoint"]["record_all"] = True

        # Solve the shallow water system and integrate the functional of
        # interest.
        final_only = (not self.solver.problem._is_transient or
                      self._problem_params.functional_final_time_only)
        functional = self.functional(farm, rho=self._problem_params.rho)
        self.time_integrator = TimeIntegrator(self.solver.problem, functional,
                                              final_only)

        for sol in self.solver.solve(annotate=annotate):
            self.time_integrator.add(sol["time"], sol["state"], sol["tf"],
                                     sol["is_final"])

        return self.time_integrator.integrate()

    def evaluate(self, annotate=True):
        """ Return the functional value for the given control values. """

        log(INFO, 'Start evaluation of j')
        timer = dolfin.Timer("j evaluation")
        j = self._compute_functional(annotate=annotate)
        timer.stop()

        log(INFO, 'Runtime: %f s.' % timer.value())
        log(INFO, 'j = %e.' % float(j))

        return j

    def derivative(self, forget=False, **kwargs):
        """ Computes the first derivative of the functional with respect to its
        controls by solving the adjoint equations. """

        log(INFO, 'Start evaluation of dj')
        timer = dolfin.Timer("dj evaluation")
        dj = self._compute_gradient(forget)

        log(INFO, "Runtime: " + str(timer.stop()) + " s")

        return dj
