"""A register for models"""


from glotaran.model.model import Model

_model_register = {}


def register_model(model_type: str, model: Model):
    """register_model registers a model.

    Parameters
    ----------
    model_type :
        model_type is type of the model.
    model :
        model is the model to be registered.
    """
    _model_register[model_type] = model


def known_model(model_type: str) -> bool:
    """known_model returns True if the model_type is in the register.

    Parameters
    ----------
    model_type :
        model_type is type of the model.
    """
    return model_type in _model_register


def get_model(model_type: str) -> Model:
    """get_model gets a model from the register.

    Parameters
    ----------
    model_type :
        model_type is type of the model.
    """
    return _model_register[model_type]
