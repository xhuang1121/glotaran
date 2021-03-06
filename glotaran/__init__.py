# Glotaran package __init__.py

from . import model, parameter, io  # noqa: F401

__version__ = '0.0.10'

ParameterGroup = parameter.ParameterGroup

read_parameter_from_csv_file = ParameterGroup.from_csv
read_parameter_from_yml = ParameterGroup.from_yaml
read_parameter_from_yml_file = ParameterGroup.from_yaml_file

from .models import spectral_temporal  # noqa: E402
KineticModel = spectral_temporal.KineticModel

from .models import doas  # noqa: E402
DOASModel = doas.DOASModel


from .parse import parser  # noqa: E402

read_model_from_yml = parser.load_yml
read_model_from_yml_file = parser.load_yml_file
