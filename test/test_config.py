"""Testsuite for flashfocus.config."""
from pytest import fixture, mark, raises
from pytest_lazyfixture import lazy_fixture

from flashfocus.config import (
    construct_config_error_msg,
    dehyphen,
    hierarchical_merge,
    load_config,
    load_merged_config,
    merge_config_sources,
)
from flashfocus.syspaths import get_default_config_file


@fixture
def default_config():
    return load_config(get_default_config_file())


@fixture
def invalid_rules():
    rules = [
        # No window_class or window_id present
        [{"flash_on_focus": "True"}],
        [{"flash_lone_windows": "always"}],
        # Invalid values
        [{"window_class": "foo", "flash_on_focus": 2}],
        [{"window_class": "foo", "flash_on_focus": "bar"}],
        [{"window_class": "foo", "flash_on_focus": "this"}],
        [{"window_class": "foo", "flash_on_focus": "that"}],
        # List value for window class/id
        [{"window_class": ["foo", "bar"]}],
        [{"window_id": ["foo", "bar"]}],
    ]
    return rules


@mark.parametrize(
    "option,values",
    [
        ("flash_opacity", ["-1", "2", "foo", -1, 2]),
        ("default_opacity", ["-1", "2", "foo", -1, 2]),
        ("time", ["0", "-1", "foo", 0, -1]),
        ("ntimepoints", ["0", "-1", "foo", 0, -1]),
        ("simple", ["foo", "10"]),
        ("flash_lone_windows", ["foo", "true"]),
        ("rules", lazy_fixture("invalid_rules")),
    ],
)
@mark.parametrize("input_type", ["cli", "file"])
def test_invalid_param(option, values, input_type, blank_cli_options, default_config):
    if input_type == "cli" and option == "rules":
        return
    for value in values:
        # Need to refresh these variables as they might be altered during merge
        defaults = default_config
        blanks = blank_cli_options
        config = {option: value}
        with raises(SystemExit):
            if input_type == "cli":
                merge_config_sources(
                    cli_options=config, user_config=None, default_config=defaults
                )
            else:
                merge_config_sources(
                    cli_options=blanks, user_config=config, default_config=defaults
                )


def check_validated_config(config, expected_types):
    for name, value in config.items():
        try:
            if expected_types[name] == [bool]:
                assert value in [True, False]
            else:
                assert True in [isinstance(value, typ) for typ in expected_types[name]]
        except KeyError:
            pass


@mark.parametrize(
    "option,values",
    [
        ("flash_opacity", ["0.5", "0", "1", 0.5, 0, 1]),
        ("default_opacity", ["0.5", "0", "1", 0.5, 0, 1]),
        ("time", ["200", "50.5", 200, 50.5]),
        ("ntimepoints", ["10", 10]),
        ("simple", lazy_fixture("valid_bool")),
        ("flash_on_focus", ["True"]),
        ("flash_lone_windows", ["always", "never", "on_open_close", "on_switch"]),
    ],
)
@mark.parametrize("input_type", ["cli", "file"])
def test_valid_param(
    option,
    values,
    input_type,
    blank_cli_options,
    string_type,
    default_config,
    valid_config_types,
):
    for value in values:
        config = {option: value}
        if input_type == "cli":
            validated_config = merge_config_sources(
                cli_options=config, user_config=None, default_config=default_config
            )
        else:
            validated_config = merge_config_sources(
                cli_options=blank_cli_options,
                user_config=config,
                default_config=default_config,
            )
        check_validated_config(validated_config, valid_config_types)
        assert len(validated_config) == len(blank_cli_options)


@mark.parametrize(
    "rules",
    [
        # Match criteria without any action is valid (but useless)
        [{"window_class": "foo"}],
        # Multiple rules can be defined
        [
            {"window_id": "bar", "flash_opacity": "0.2"},
            {"window_class": "foo", "simple": "True"},
        ],
        # Check that global params are accepted
        [{"window_class": "foo", "default_opacity": "0.5"}],
        [{"window_class": "foo", "simple": "True"}],
        [{"window_class": "foo", "ntimepoints": "10"}],
        [{"window_class": "foo", "time": "100"}],
        [{"window_class": "foo", "flash_opacity": "0.2"}],
        [{"window_class": "foo", "flash_on_focus": True}],
        [{"window_class": "foo", "flash_lone_windows": "always"}],
        # Regexes are valid
        [{"window_class": "^indo.*$", "time": "100"}],
    ],
)
def test_rules_validation(rules, blank_cli_options, default_config, valid_config_types):
    rules_dict = {"rules": rules}
    validated_config = merge_config_sources(
        blank_cli_options, default_config, rules_dict
    )
    for rule in validated_config["rules"]:
        check_validated_config(rule, valid_config_types)


@mark.parametrize(
    "input,expected",
    [
        ({"foo-bar": 1, "car": 2}, {"foo_bar": 1, "car": 2}),
        ({"car": 2}, {"car": 2}),
        ({"car": 2, "rules": [{"foo-bar": 3}]}, {"car": 2, "rules": [{"foo_bar": 3}]}),
        (dict(), dict()),
    ],
)
def test_dehyphen(input, expected):
    dehyphen(input)
    assert input == expected


@mark.parametrize(
    "dicts,expected",
    [
        ([{"a": 1, "b": 2}, {"a": 2, "c": 3}], {"a": 2, "b": 2, "c": 3}),
        ([None, {"a": 2, "c": 3}], {"a": 2, "c": 3}),
        ([{"a": 2, "c": 3}, None], {"a": 2, "c": 3}),
        ([dict(), {"a": 2, "c": 3}], {"a": 2, "c": 3}),
        ([{"a": 2, "c": 3}, dict()], {"a": 2, "c": 3}),
        ([{"a": 2}, {"a": 3}, {"a": 4}], {"a": 4}),
    ],
)
def test_hierarchical_merge(dicts, expected):
    assert hierarchical_merge(dicts) == expected


def test_hierarchical_merge_returns_a_new_dict():
    a = {"a": 1, "b": 2}
    a_copy = a.copy()
    b = {"a": 2, "b": 2, "c": 3}
    hierarchical_merge([a, b])
    assert a == a_copy


def test_rule_defaults_inherited_from_global_param(default_config, blank_cli_options):
    user_config = {"rules": [{"window_class": "foo"}]}
    validated = merge_config_sources(blank_cli_options, default_config, user_config)
    assert validated["rules"][0]["flash_opacity"] == default_config["flash_opacity"]


def test_rules_added_to_config_dict_if_not_present_in_config(
    default_config, blank_cli_options
):
    validated = merge_config_sources(blank_cli_options, default_config, default_config)
    assert "rules" in validated


def test_load_config(configfile):
    assert load_config(configfile) == {"default_opacity": 1, "flash_opacity": 0.5}


def test_construct_rules_config_error_message(default_config):
    default_config["rules"] = [{"default_opacity": 0.8}]
    errors = {"rules": {0: ["msg"]}}
    expected = "Failed to parse config\n"
    expected += "  - rules:\n"
    expected += "    - rule 1:\n"
    expected += "      - msg\n"
    assert construct_config_error_msg(default_config, errors) == expected


def test_construct_non_rules_config_error_message(default_config):
    default_config["flash_opacity"] = "2"
    errors = {"flash_opacity": ["msg"]}
    expected = "Failed to parse config\n"
    expected += "  - flash-opacity:\n"
    expected += "    - msg\n"
    assert construct_config_error_msg(default_config, errors) == expected


@fixture
def invalid_yaml(tmpdir):
    yml = tmpdir.join("invalid.yml")
    yml.write("1 :::1: 1:")
    return yml


def test_invalid_yaml_passed_to_load_config(invalid_yaml):
    with raises(SystemExit):
        load_config(invalid_yaml)


def test_load_merged_config_with_no_custom_config(
    monkeypatch, blank_cli_options, configfile
):
    monkeypatch.setattr(
        "flashfocus.config.init_user_configfile",
        lambda *args, **kwargs: str(configfile),
    )
    config = load_merged_config(blank_cli_options)
    assert config["flash_opacity"] == 0.5


def test_load_merged_config_with_custom_config(
    monkeypatch, blank_cli_options, configfile_with_02_flash_opacity
):
    blank_cli_options["config"] = str(configfile_with_02_flash_opacity)
    config = load_merged_config(blank_cli_options)
    assert config["flash_opacity"] == 0.2
