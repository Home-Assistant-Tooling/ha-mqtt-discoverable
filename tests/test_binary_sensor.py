#
#    Copyright 2022-2024 Joe Block <jpb@unixorn.net>
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
from unittest.mock import patch

import pytest
from paho.mqtt.client import MQTT_ERR_SUCCESS

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo


@pytest.fixture(name="sensor", params=["on", "custom_on"])
def binary_sensor(request) -> BinarySensor:
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = BinarySensorInfo(name="test", payload_on=request.param)
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    return BinarySensor(settings)


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = BinarySensorInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    sensor = BinarySensor(settings)
    assert sensor is not None


def test_generate_config(sensor: BinarySensor):
    config = sensor.generate_config()

    assert config is not None
    # If we have defined a custom payload, check that is part of the output config
    assert config["payload_on"] == sensor._entity.payload_on


def test_update_state(sensor: BinarySensor):
    sensor.on()
    sensor.off()


@pytest.mark.parametrize("state", [True, False])
def test_set_state_expected_payload(sensor: BinarySensor, state: bool):
    with patch.object(sensor, "_update_state") as mock_update_state:
        sensor.set_state(state)

    expected_payload = sensor._entity.payload_on if state else sensor._entity.payload_off
    mock_update_state.assert_called_once_with(state=expected_payload, force_update=False)


@pytest.mark.parametrize(
    ("second_state", "force_update", "expected_call_count"),
    [(True, False, 1), (True, True, 2), (False, False, 2), (False, True, 2)],
)
def test_set_state_duplicate(sensor: BinarySensor, second_state: bool, force_update: bool, expected_call_count: int):
    sensor.wrote_configuration = True
    with patch.object(sensor.mqtt_client, "publish") as mock_publish:
        mock_publish.return_value.rc = MQTT_ERR_SUCCESS

        sensor.set_state(True)
        sensor.set_state(second_state, force_update=force_update)

    assert mock_publish.call_count == expected_call_count


def test_on_uses_set_state(sensor: BinarySensor):
    with patch.object(sensor, "set_state") as mock_set_state:
        sensor.on()
        mock_set_state.assert_called_once_with(True, force_update=False)


def test_off_uses_set_state(sensor: BinarySensor):
    with patch.object(sensor, "set_state") as mock_set_state:
        sensor.off(force_update=True)
    mock_set_state.assert_called_once_with(False, force_update=True)
