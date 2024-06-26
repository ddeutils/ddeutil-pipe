import json
import pickle
from typing import Any

import pytest
from ddeutil.workflow.vendors.__dict import MetaDict, complies_variable_syntax


@pytest.fixture
def config() -> dict[str, Any]:
    dropout: list[list[float]] = [[0.1, 0.2]]
    special_tokens: list[list[str]] = [["<NUM>", "<YEAR>"]]
    tokenizer_params = {"special_tokens": special_tokens}
    return {
        "epochs": 10,
        "model": [
            {
                "type_": "mlp",
                "hidden_dims": [128, 256],
                "dropout": dropout,
            },
            {
                "type_": "lstm",
                "hidden_dim": 128,
                "dropout": dropout,
            },
        ],
        "optimizer": {
            "type_": "adam",
            "lr": 1.0e-3,
            "weight_decay": True,
        },
        "tokenizer_1": tokenizer_params,
        "tokenizer_2": tokenizer_params,
    }


@pytest.fixture
def list_of_tuples() -> list[tuple]:
    return [("a", [1, 2, 3]), ("b", {"c": 6})]


def test_init_from_dict(config: dict):
    cfg = MetaDict(config)
    assert cfg == config


def test_init_from_kwargs(config: dict):
    cfg = MetaDict(**config)
    assert cfg == config


def test_init_from_list_of_tuples(list_of_tuples: list[tuple]):
    cfg = MetaDict(list_of_tuples)
    assert cfg == dict(list_of_tuples)


def test_from_keys(config: dict):
    cfg = MetaDict.fromkeys(config.keys())
    config = dict.fromkeys(config.keys())
    assert cfg == config


def test_get_item(config: dict):
    cfg = MetaDict(config)
    assert cfg["model"][0]["type_"] == config["model"][0]["type_"]
    with pytest.raises(KeyError) as _:
        _ = cfg["some_missing_key"]


def test_get_attr(config: dict):
    cfg = MetaDict(config)
    assert cfg.model[0].type_ == config["model"][0]["type_"]
    with pytest.raises(AttributeError) as _:
        _ = cfg.some_missing_attr


def test_set_item(config: dict):
    cfg = MetaDict(config)
    cfg[("new", "key")] = "new_value"
    assert cfg[("new", "key")] == "new_value"


def test_set_attr(config: dict):
    cfg = MetaDict(config)
    cfg.new_attr = {"new_key": "new_value"}
    assert cfg.new_attr == {"new_key": "new_value"}
    assert cfg.new_attr.new_key == "new_value"


def test_del_item(config: dict):
    cfg = MetaDict(config)
    del cfg["model"][0]["type_"]
    del config["model"][0]["type_"]
    assert cfg == config
    with pytest.raises(KeyError) as _:
        del cfg["some_missing_key"]


def test_del_attr(config: dict):
    cfg = MetaDict(config)
    del cfg.model[0].type_
    del config["model"][0]["type_"]
    assert cfg == config
    with pytest.raises(AttributeError) as _:
        del cfg.some_missing_attr


def test_get(config: dict):
    cfg = MetaDict(config)
    assert cfg.get("model") == config.get("model")
    assert cfg.get("some_new_key", 100) == 100


def test_pop(config: dict):
    cfg = MetaDict(config)
    assert cfg.pop("model") == config.pop("model")
    assert cfg.pop("some_new_key", 100) == 100


def test_get_nested(config: dict):
    cfg = MetaDict(config)
    assert cfg.tokenizer_1.get("special_tokens") == config["tokenizer_1"].get(
        "special_tokens"
    )


def test_pop_nested(config: dict):
    cfg = MetaDict(config)
    assert cfg.optimizer.pop("lr") == config["optimizer"].pop("lr")
    assert cfg == config


def test_keys(config: dict):
    cfg = MetaDict(config)
    assert cfg.keys() == config.keys()


def test_values(config: dict):
    cfg = MetaDict(config)
    assert list(cfg.values()) == list(config.values())


def test_items(config: dict):
    cfg = MetaDict(config)
    assert cfg.items() == config.items()


def test_update(config: dict):
    cfg = MetaDict(config)
    cfg.update({"a": 1, "b": 2})
    config.update({"a": 1, "b": 2})
    assert cfg == config


def test_contains(config: dict):
    cfg = MetaDict(config)
    assert "model" in cfg


def test_copy():
    cfg = MetaDict(a=1)
    cfg2 = cfg.copy()
    cfg2.a = 2
    assert cfg.a == 1
    assert cfg2.a == 2


def test_copy_recursive():
    cfg = MetaDict()
    cfg2 = MetaDict(a=cfg)
    cfg.a = cfg2
    cfg3 = cfg.copy()
    assert cfg3.a == cfg2
    assert cfg3.a.a == cfg
    assert cfg3.a.a.a == cfg2


def test_str(config: dict):
    cfg = MetaDict(config)
    assert str(cfg) == str(config)


def test_repr(config: dict):
    cfg = MetaDict(config)
    assert repr(cfg) == repr(config)


def test_dir(config: dict):
    cfg = MetaDict(config)
    assert set(dir(cfg)) == set(
        dir(MetaDict)
        + [key for key in cfg._data.keys() if complies_variable_syntax(key)]
    )


def test_nested_assignment_default(config: dict):
    cfg = MetaDict(config)
    with pytest.raises(AttributeError) as _:
        cfg.x.y.z = 100
    assert cfg.nested_assign is False


def test_nested_assignment(config: dict):
    cfg = MetaDict(config)
    cfg.enable_nested_assignment()
    assert cfg.nested_assign is True
    cfg.x.y.z = 100
    assert cfg.x.y.z == 100
    cfg.disable_nested_assignment()
    assert cfg.nested_assign is False


def test_nested_assignment_contextmanager(config: dict):
    cfg = MetaDict(config)
    with cfg.enabling_nested_assignment() as cfg:
        assert cfg.nested_assign is True
        cfg.x.y.z = 100
        assert cfg.x.y.z == 100
    assert cfg.nested_assign is False


def test_json(config: dict):
    cfg = MetaDict(config)
    cfg_json = json.loads(json.dumps(cfg))
    assert cfg_json == config
    assert isinstance(cfg_json, dict)


def test_pickle(config: dict):
    cfg = MetaDict(config)
    cfg_pickle = pickle.loads(pickle.dumps(cfg))
    assert cfg_pickle == cfg
    assert isinstance(cfg_pickle, MetaDict)


def test_pickle_with_nested_assignment(config: dict):
    cfg = MetaDict(config)

    with cfg.enabling_nested_assignment() as cfg:
        cfg.x.y.z = 100
        cfg_pickle = pickle.loads(pickle.dumps(cfg))
        assert cfg_pickle == cfg
        assert isinstance(cfg_pickle, MetaDict)
        assert cfg_pickle.nested_assign is True
    assert cfg.nested_assign is False


def test_is_instance_dict(config: dict):
    cfg = MetaDict(config)
    assert isinstance(cfg, dict)


def test_to_dict(config: dict):
    cfg = MetaDict(config)
    cfg_dict = cfg.to_dict()
    assert cfg_dict == config
    assert isinstance(cfg_dict, dict)
    assert isinstance(cfg_dict["model"][0], dict)


def test_references(config: dict):
    cfg = MetaDict(config)
    assert (
        cfg.tokenizer_1.special_tokens
        is config["tokenizer_1"]["special_tokens"]
    )


def test_append_dict_to_list(config: dict):
    cfg = MetaDict(config)
    cfg.model.append({"type_": "gru"})
    assert isinstance(cfg.model[-1], dict)

    cfg.model.append(MetaDict({"type_": "gru"}))
    assert isinstance(cfg.model[-1], MetaDict)


@pytest.mark.parametrize("value", ["wrong_type", 999])
def test_init_type_checks(value, config):
    with pytest.raises(TypeError) as _:
        MetaDict(config, nested_assign=value)


def test_warning_protected_key():
    with pytest.warns(UserWarning) as warn_inf:
        MetaDict(items=[1, 2, 3])
        assert (
            str(warn_inf.list[0].message)
            == "'MetaDict' object uses 'items' internally. "
            "'items' can only be accessed via `obj['items']`."
        )


@pytest.mark.parametrize(
    "name, expected",
    [
        ("models", True),
        ("text_100", True),
        ("1name", False),
        ("&%?=99", False),
        ("100", False),
        (100, False),
        ((1, 2, 3), False),
    ],
)
def test_complies_variable_syntax(name: Any, expected: bool):
    assert complies_variable_syntax(name) == expected
