"""This package contains compartment constraint items."""

from typing import List, Tuple
from .model_item import model_item, model_item_typed


@model_item(
    attributes={
        'compartment': str,
        'interval': List[Tuple[any, any]],
    }, has_type=True, no_label=True)
class ZeroConstraint:
    """A zero constraint sets the calculated matrix row of a compartment to 0
    in the given intervals. """
    def applies(self, index: any) -> bool:
        """
        Returns true if the indexx is in one of the intervals.

        Parameters
        ----------
        index : any

        Returns
        -------
        applies : bool

        """
        return any(interval[0] <= x <= interval[1] for interval in self.intervals)


@model_item(
    attributes={
        'targets': List[str],
        'parameters': List[str],
    }, has_type=True, no_label=True)
class EqualConstraint(ZeroConstraint):
    """An equal constraint replaces the compartments calculated matrix row a sum
    of target compartments rows, each scaled by a parameter.

    C[compartment] = p1 * C[target1] + p2 * C[target2] + ...
    """
    def parameter_and_targets(self):
        """generates traget and parameter pairs """
        for i in range(len(self.parameters)):
            yield self.parameters[i], self.targets[i]


@model_item(attributes={
    'targets': List[str],
    'parameters': List[str],
    'weight': str,
}, has_type=True, no_label=True)
class EqualAreaConstraint(EqualConstraint):
    """An equal area constraint adds a the differenc of the sum of a
    compartements in the e matrix in one ore more intervals to the scaled sum
    of the e matrix of one or more target compartmants to resiudal. The additional
    residual is scaled with the weight.

    Parameters
    ----------
    compartment: label of the compartment
    intervals: list of tuples representing intervals on the estimated axies
    targets: list of target compartments
    parameters: list of scaling parameter for the targets
    weight: scaling factor for the residual
    """
    pass


@model_item_typed(types={
    'zero': ZeroConstraint,
    'equal': EqualConstraint,
    'equal_area': EqualAreaConstraint,
})
class CompartmentConstraint:
    """A compartment constraint is applied on one compartment on one or many
    intervals on the estimated axies type.

    There are three types: zeroe, equal and eqal area. See the documention of
    the respective classes for details.
    """
    pass
