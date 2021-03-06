"""The model decorator."""

import typing
import numpy as np

from glotaran.analysis.result import Result
from glotaran.parameter import ParameterGroup
from glotaran.parse.register import register_model

from .dataset_descriptor import DatasetDescriptor
from .model import Model
from .util import wrap_func_as_method


MatrixFunction = typing.Callable[
    [typing.Type[DatasetDescriptor], typing.Any, np.ndarray],
    typing.Tuple[typing.List[str], np.ndarray]]
"""A `MatrixFunction` calculates the matrix for a model."""

GlobalMatrixFunction = typing.Callable[
    [typing.Type[DatasetDescriptor], np.ndarray],
    typing.Tuple[typing.List[str], np.ndarray]]
"""A `GlobalMatrixFunction` calculates the global matrix for a model."""

ConstrainMatrixFunction = typing.Callable[
    [typing.Type[Model], ParameterGroup, typing.List[str], np.ndarray, float],
    typing.Tuple[typing.List[str], np.ndarray]]
"""A `ConstrainMatrixFunction` applies constraints on a matrix."""

FinalizeFunction = typing.Callable[
    [typing.Type[Model], Result], None]
"""A `FinalizeFunction` gets called after optimization."""

PenaltyFunction = typing.Callable[
    [typing.Type[Model], ParameterGroup, typing.List[str], np.ndarray, float],
    np.ndarray]
"""A `PenaltyFunction` calculates additional penalties for the optimization."""


def model(model_type: str,
          attributes: typing.Dict[str, typing.Any] = {},
          dataset_type: typing.Type[DatasetDescriptor] = DatasetDescriptor,
          megacomplex_type: typing.Any = None,
          matrix: MatrixFunction = None,
          global_matrix: GlobalMatrixFunction = None,
          matrix_dimension: str = None,
          global_dimension: str = None,
          constrain_matrix_function: ConstrainMatrixFunction = None,
          additional_penalty_function: PenaltyFunction = None,
          finalize_result_function: FinalizeFunction = None,
          allow_grouping: bool = True,
          ) -> typing.Callable:
    """The `@model` decorator is intended to be used on subclasses of :class:`glotaran.model.Model`.
    It creates properties for the given attributes as well as functions to add access them. Also it
    adds the functions (e.g. for `matrix`) to the model ansures they are added wrapped in a correct
    way.

    Parameters
    ----------
    model_type :
        Human readable string used by the parser to identify the correct model.
    attributes :
        A dictionary of attribute names and types. All types must be decorated with the
        :func:`glotaran.model.model_attribute` decorator.
    dataset_type :
     A subclass of :class:`DatasetDescriptor`
    megacomplex_type :
        A class for the model megacomplexes. The class must be decorated with the
        :func:`glotaran.model.model_attribute` decorator.
    matrix :
        A function to calculate the matrix for the model.
    global_matrix :
        A function to calculate the global matrix for the model.
    matrix_dimension :
        The name of model matrix row dimension.
    global_dimension :
        The name of model global matrix row dimension.
    constrain_matrix_function :
        A function to constrain the global matrix for the model.
    None
    additional_penalty_function : PenaltyFunction
        A function to calculate additional penalties when optimizing the model.
    finalize_result_function :
        A function to finalize a result after optimization.
    allow_grouping :
        If `True`, datasets can can be grouped along the global dimension.
    """

    def decorator(cls):

        setattr(cls, '_model_type', model_type)
        setattr(cls, '_finalize_result', finalize_result_function)
        setattr(cls, '_constrain_matrix_function',
                constrain_matrix_function)
        setattr(cls, '_additional_penalty_function',
                additional_penalty_function)
        setattr(cls, '_allow_grouping', allow_grouping)

        if matrix:
            c_mat = wrap_func_as_method(cls, name='matrix')(matrix)
            c_mat = staticmethod(c_mat)
            setattr(cls, 'matrix', c_mat)
        setattr(cls, 'matrix_dimension', matrix_dimension)

        if global_matrix:
            e_mat = wrap_func_as_method(cls, name='global_matrix')(global_matrix)
            e_mat = staticmethod(e_mat)
            setattr(cls, 'global_matrix', e_mat)
        setattr(cls, 'global_dimension', global_dimension)

        if not hasattr(cls, '_glotaran_model_attributes'):
            setattr(cls, '_glotaran_model_attributes', {})
        else:
            setattr(cls, '_glotaran_model_attributes',
                    getattr(cls, '_glotaran_model_attributes').copy())

        attributes['megacomplex'] = megacomplex_type
        attributes['dataset'] = dataset_type

        # Set annotations and methods for attributes
        for attr_name, attr_type in attributes.items():
            getattr(cls, '_glotaran_model_attributes')[attr_name] = None
            attr_prop = _create_property_for_attribute(cls, attr_name, attr_type)
            setattr(cls, attr_name, attr_prop)

            if getattr(attr_type, '_glotaran_has_label'):
                get_item = _create_get_func(cls, attr_name, attr_type)
                setattr(cls, get_item.__name__, get_item)
                set_item = _create_set_func(cls, attr_name, attr_type)
                setattr(cls, set_item.__name__, set_item)

            else:
                add_item = _create_add_func(cls, attr_name, attr_type)
                setattr(cls, add_item.__name__, add_item)

        init = _create_init_func(cls, attributes)
        setattr(cls, '__init__', init)

        register_model(model_type, cls)

        return cls

    return decorator


def _create_init_func(cls, attributes):

    @wrap_func_as_method(cls)
    def __init__(self):
        for attr_name, attr_item in attributes.items():
            if getattr(attr_item, '_glotaran_has_label'):
                setattr(self, f'_{attr_name}', {})
            else:
                setattr(self, f'_{attr_name}', [])
        super(cls, self).__init__()

    return __init__


def _create_add_func(cls, name, type):

    @wrap_func_as_method(cls, name=f'add_{name}')
    def add_item(self, item: type):
        f'''Adds an `{type.__name__}` object.

        Parameters
        ----------
        item :
            The `{type.__name__}` item.
        '''

        if not isinstance(item, type):
            if not hasattr(type, "_glotaran_model_attribute_typed") or \
               not isinstance(item, tuple(type._glotaran_model_attribute_types.values())):
                raise TypeError
        getattr(self, f'_{name}').append(item)
    return add_item


def _create_get_func(cls, name, type):

    @wrap_func_as_method(cls, name=f'get_{name}')
    def get_item(self, label: str) -> type:
        f'''
        Returns the `{type.__name__}` object with the given label.

        Parameters
        ----------
        label :
            The label of the `{type.__name__}` object.
        '''
        return getattr(self, f'_{name}')[label]

    return get_item


def _create_set_func(cls, name, type):

    @wrap_func_as_method(cls, name=f'set_{name}')
    def set_item(self, label: str, item: type):
        f'''
        Sets the `{type.__name__}` object with the given label with to the item.

        Parameters
        ----------
        label :
            The label of the `{type.__name__}` object.
        item :
            The `{type.__name__}` item.
        '''

        if not isinstance(item, type):
            if not hasattr(type, "_glotaran_model_attribute_typed") or \
               not isinstance(item, tuple(type._glotaran_model_attribute_types.values())):
                raise TypeError
        getattr(self, f'_{name}')[label] = item

    return set_item


def _create_property_for_attribute(cls, name, type):

    return_type = typing.Dict[str, type] if hasattr(type, '_glotaran_has_label') \
            else typing.List[type]

    doc_type = 'dictionary' if hasattr(type, '_glotaran_has_label') else 'list'

    @property
    @wrap_func_as_method(cls, name=f'{name}')
    def attribute(self) -> return_type:
        f'''A {doc_type} containing {type.__name__}'''
        return getattr(self, f'_{name}')

    return attribute
